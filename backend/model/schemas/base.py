from dataclasses import dataclass, field
import logging

from ndex2.cx2 import CX2Network
from typing import List, Dict, Any, Optional

from backend.model.constants import NodeType
from backend.model.schemas.associations import (
    BaseAssociation,
    GeneAssociation,
    CompoundAssociation,
    ComponentAssociation,
    OrganAssociation,
    GeneExpressionAssociation,
)
from backend.model.cytoscape.styles import AOPStyleManager
from backend.model.cytoscape.elements import CytoscapeNode, CytoscapeEdge
from backend.model.constants import NodeType, EdgeType
from backend.model.parsers.cytoscape import CytoscapeNetworkParser

logger = logging.getLogger(__name__)

@dataclass
class AOPInfo:
    """Represents AOP metadata"""

    aop_id: str
    title: str
    uri: str

    def __str__(self) -> str:
        return f"AOP:{self.aop_id}"


@dataclass
class AOPKeyEvent:
    """Represents a Key Event in an AOP"""

    ke_id: str
    uri: str
    title: str
    ke_type: NodeType  # MIE, KE, or AO
    associated_aops: List[AOPInfo] = field(default_factory=list)

    def add_aop(self, aop_info: AOPInfo):
        """Add AOP association to this key event"""
        if aop_info not in self.associated_aops:
            self.associated_aops.append(aop_info)

    def get_aop_ids(self) -> List[str]:
        """Get list of AOP IDs for this key event"""
        return [aop.aop_id for aop in self.associated_aops]

    def to_cytoscape_data(self) -> Dict[str, Any]:
        """Convert to Cytoscape node data"""
        return {
            "id": self.uri,
            "label": self.title if self.title != "NA" else self.ke_id,
            "type": self.ke_type.value,
            "is_mie": self.ke_type == NodeType.MIE,
            "is_ao": self.ke_type == NodeType.AO,
            "aop": [aop.uri for aop in self.associated_aops],
            "aop_title": [aop.title for aop in self.associated_aops],
        }


@dataclass
class KeyEventRelationship:
    """Represents a relationship between two Key Events"""

    ker_id: str
    ker_uri: str
    upstream_ke: AOPKeyEvent
    downstream_ke: AOPKeyEvent

    def to_cytoscape_data(self) -> Dict[str, Any]:
        """Convert to Cytoscape edge data"""
        return {
            "id": f"{self.upstream_ke.uri}_{self.downstream_ke.uri}",
            "source": self.upstream_ke.uri,
            "target": self.downstream_ke.uri,
            "curie": f"aop.relationships:{self.ker_id}",
            "ker_label": self.ker_id,
            "type": EdgeType.KER.value,
        }


class AOPNetwork:
    """Main AOP Network model representing a complete AOP query result"""

    def __init__(self):
        self.key_events: Dict[str, AOPKeyEvent] = {}
        self.relationships: List[KeyEventRelationship] = []
        self.component_associations: List[ComponentAssociation] = []
        self.gene_associations: List[GeneAssociation] = []
        self.compound_associations: List[CompoundAssociation] = []
        self.organ_associations: List[OrganAssociation] = []
        self.aop_info: Dict[str, AOPInfo] = {}
        self.node_list: List[CytoscapeNode] = []
        self.edge_list: List[CytoscapeEdge] = []
        self.gene_expression_associations: List[GeneExpressionAssociation] = []

        # Style management
        self.style_manager = AOPStyleManager() if AOPStyleManager else None

    @classmethod
    def from_cytoscape_elements(cls, elements: List[Dict[str, Any]]) -> "AOPNetwork":
        """Create AOPNetwork from Cytoscape elements - puts ALL nodes and edges into the network"""
        network = cls()

        # Parse all elements using the parser
        parser = CytoscapeNetworkParser(elements)

        # Add ALL nodes to the network
        network.node_list = parser.nodes

        # Add ALL edges to the network
        network.edge_list = parser.edges

        # Store original elements for position and style extraction
        network._original_elements = elements

        logger.info(
            f"Created AOPNetwork from {len(elements)} Cytoscape elements: {len(network.node_list)} nodes, {len(network.edge_list)} edges"
        )

        return network

    def add_key_event(self, key_event: AOPKeyEvent):
        """Add a key event to the network"""
        self.key_events[key_event.uri] = key_event

        # Register AOP info
        for aop in key_event.associated_aops:
            if aop.aop_id not in self.aop_info:
                self.aop_info[aop.aop_id] = aop

    def add_relationship(self, relationship: KeyEventRelationship):
        """Add a key event relationship"""
        # Ensure both KEs are in the network
        self.add_key_event(relationship.upstream_ke)
        self.add_key_event(relationship.downstream_ke)
        self.relationships.append(relationship)

    def add_gene_association(self, association: GeneAssociation):
        """Add a gene association"""
        self.gene_associations.append(association)
        self._update_nodes_and_edges(association)

    def add_gene_expression_association(self, association: GeneExpressionAssociation):
        """Add a gene expression association"""
        self.gene_expression_associations.append(association)
        self._update_nodes_and_edges(association)

    def add_compound_association(self, association: CompoundAssociation):
        """Add a compound association"""
        self.compound_associations.append(association)
        self._update_nodes_and_edges(association)

    def add_component_association(self, association: ComponentAssociation):
        """Add a component association"""
        self.component_associations.append(association)
        self._update_nodes_and_edges(association)

    def add_organ_association(self, association: OrganAssociation):
        """Add an organ association"""
        self.organ_associations.append(association)
        self._update_nodes_and_edges(association)

    def _update_nodes_and_edges(self, association: BaseAssociation):
        """Update node_list and edge_list with nodes and edges from association"""
        # Add nodes
        new_nodes = association.get_nodes()
        for node in new_nodes:
            # Avoid duplicates by checking node ID
            if not any(existing_node.id == node.id for existing_node in self.node_list):
                self.node_list.append(node)

        # Add edges
        new_edges = association.get_edges()
        for edge in new_edges:
            # Avoid duplicates by checking edge ID
            if not any(existing_edge.id == edge.id for existing_edge in self.edge_list):
                self.edge_list.append(edge)

    def get_genes_for_ke(self, ke_uri: str) -> List[GeneAssociation]:
        """Get all gene associations for a specific Key Event"""
        return [
            assoc for assoc in self.component_associations if assoc.ke_uri == ke_uri
        ]

    def get_compounds_for_aop(self, aop_uri: str) -> List[CompoundAssociation]:
        """Get all compound associations for a specific AOP"""
        return [
            assoc for assoc in self.compound_associations if assoc.aop_uri == aop_uri
        ]

    def get_ke_uris(self) -> List[str]:
        """Get all Key Event URIs in the network"""
        return list(self.key_events.keys())

    def get_aop_uris(self) -> List[str]:
        """Get all AOP URIs in the network"""
        return list(self.aop_info.keys())

    def get_ensembl_ids(self) -> List[str]:
        """Retrieve all Ensembl IDs from nodes in the network"""
        ensembl_ids = []

        # Check node_list for Ensembl nodes
        for node in self.node_list:
            if node.is_ensembl_node():
                # Extract Ensembl ID from node properties or ID
                ensembl_id = node.properties.get("ensembl_id", "")
                if not ensembl_id:
                    # Try to extract from node ID if it starts with ensembl_
                    if node.id.startswith("ensembl_"):
                        ensembl_id = node.id.replace("ensembl_", "")
                    else:
                        ensembl_id = node.label

                if ensembl_id and ensembl_id not in ensembl_ids:
                    ensembl_ids.append(ensembl_id)

        # Also check gene_associations for backward compatibility
        for gene_assoc in self.gene_associations:
            if gene_assoc.ensembl_id and gene_assoc.ensembl_id not in ensembl_ids:
                ensembl_ids.append(gene_assoc.ensembl_id)

        return ensembl_ids

    def get_organ_ids(self) -> List[str]:
        """Retrieve all organ IDs/names from nodes in the network"""
        organ_ids = []

        # Check node_list for organ nodes
        for node in self.node_list:
            if node.is_organ_node():
                # Use anatomical_name (organ name) rather than full URI
                organ_name = node.properties.get("anatomical_name", "")
                if not organ_name:
                    organ_name = node.label

                if organ_name and organ_name not in organ_ids:
                    organ_ids.append(organ_name)

        # Also check organ_associations for backward compatibility
        for organ_assoc in self.organ_associations:
            organ_node = organ_assoc.organ_data
            if organ_node and organ_node.is_organ_node():
                # Use anatomical_name (organ name) rather than full URI
                organ_name = organ_node.properties.get(
                    "anatomical_name", organ_node.label
                )
                if organ_name and organ_name not in organ_ids:
                    organ_ids.append(organ_name)
        return organ_ids

    def to_cytoscape_elements(self, include_styles: bool = True) -> Dict[str, Any]:
        """Convert entire network to Cytoscape format with optional styles"""
        elements = []

        # Add Key Event nodes
        for ke in self.key_events.values():
            elements.append({"data": ke.to_cytoscape_data()})

        # Add KER edges
        for relationship in self.relationships:
            elements.append({"data": relationship.to_cytoscape_data()})

        # Add gene associations
        for gene_assoc in self.gene_associations:
            elements.extend(gene_assoc.to_cytoscape_elements())

        # Add compound associations
        for compound_assoc in self.compound_associations:
            elements.extend(compound_assoc.to_cytoscape_elements())

        # Add component associations
        for comp_assoc in self.component_associations:
            elements.extend(comp_assoc.to_cytoscape_elements())

        # Add organ associations
        for organ_assoc in self.organ_associations:
            elements.extend(organ_assoc.to_cytoscape_elements())

        # Add gene expression associations
        for expr_assoc in self.gene_expression_associations:
            elements.extend(expr_assoc.to_cytoscape_elements())

        logger.info(f"Generated {len(elements)} Cytoscape elements")

        # Prepare response with elements
        result = {"elements": elements}

        # Add styles and layout if requested
        if include_styles:
            result["style"] = self.get_styles()
            result["layout"] = self.get_layout_config()

        return result

    def get_summary(self) -> Dict[str, int]:
        """Get network summary statistics"""
        mie_count = sum(
            1 for ke in self.key_events.values() if ke.ke_type == NodeType.MIE
        )
        ao_count = sum(
            1 for ke in self.key_events.values() if ke.ke_type == NodeType.AO
        )
        ke_count = sum(
            1 for ke in self.key_events.values() if ke.ke_type == NodeType.KE
        )

        return {
            "total_key_events": len(self.key_events),
            "mie_count": mie_count,
            "ao_count": ao_count,
            "ke_count": ke_count,
            "ker_count": len(self.relationships),
            "gene_associations": len(self.gene_associations),
            "gene_expression_associations": len(self.gene_expression_associations),
            "compound_associations": len(self.compound_associations),
            "component_associations": len(self.component_associations),
            "total_aops": len(self.aop_info),
        }

    def to_ndx_network(
        self,
        name: Optional[str] = None,
        description: Optional[str] = None,
        cytoscape_styles: Optional[Dict[str, Any]] = None,
    ):
        net_cx = CX2Network()

        # Set network attributes
        net_name = name or f"AOP Network ({len(self.node_list)} nodes)"
        net_cx.add_network_attribute("name", net_name)
        if description:
            net_cx.add_network_attribute("description", description)

        # Add simple node and edge counts as metadata
        net_cx.add_network_attribute("total_nodes", len(self.node_list))
        net_cx.add_network_attribute("total_edges", len(self.edge_list))

        # Extract position data from original elements
        position_map = {}

        if hasattr(self, "_original_elements"):
            for element in self._original_elements:
                if element.get("group") != "edges" and "data" in element:
                    # Node element - extract position
                    node_id = element["data"].get("id")
                    position = element.get("position", {})
                    if node_id and position:
                        position_map[node_id] = position

        # Add ALL nodes from node_list to CX2 with positions
        original_to_cx2_id = {}  # Map original node IDs to CX2 integer IDs

        for node in self.node_list:
            # Convert node to dict and remove CX2 reserved keys
            node_data = node.to_dict()
            node_data.pop("id", None)  # Remove conflicting id key

            # Extract position for this node
            position = position_map.get(node.id, {})
            x = position.get("x")
            y = position.get("y")

            # Add node with position coordinates if available
            if x is not None and y is not None:
                cx2_node_id = net_cx.add_node(
                    attributes=node_data, x=float(x), y=float(y)
                )
            else:
                cx2_node_id = net_cx.add_node(attributes=node_data)

            original_to_cx2_id[node.id] = cx2_node_id

        # Add ALL edges from edge_list to CX2
        for edge in self.edge_list:
            # Map source and target to CX2 node IDs
            source_cx2_id = original_to_cx2_id.get(edge.source)
            target_cx2_id = original_to_cx2_id.get(edge.target)

            if source_cx2_id is not None and target_cx2_id is not None:
                edge_data = edge.to_dict()
                # Remove ALL CX2 reserved keys
                edge_data.pop("id", None)
                edge_data.pop("source", None)
                edge_data.pop("target", None)

                net_cx.add_edge(
                    source=source_cx2_id, target=target_cx2_id, attributes=edge_data
                )

        # Use the actual Cytoscape styles if provided
        if cytoscape_styles:
            try:
                # Just pass the Cytoscape styles directly to CX2
                visual_properties = {"cytoscape_styles": cytoscape_styles}
                net_cx.set_visual_properties(visual_properties)
                logger.info(
                    f"Added Cytoscape styles to CX2 network ({len(cytoscape_styles)} style rules)"
                )
            except Exception as e:
                logger.warning(f"Could not add Cytoscape styles to CX2: {e}")

        logger.info(
            f"Created CX2 network with {len(self.node_list)} nodes and {len(self.edge_list)} edges, including positions and styles"
        )
        return net_cx

    def get_styles(self) -> List[Dict[str, Any]]:
        """Get styles for the network"""
        if not self.style_manager:
            return get_default_styles()

        return self.style_manager.get_styles()

    def get_layout_config(self) -> Dict[str, Any]:
        """Get layout configuration for the network"""
        if self.style_manager:
            return self.style_manager.get_layout_config()
        return get_layout_config()
