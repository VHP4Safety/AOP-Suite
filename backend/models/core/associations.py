from dataclasses import dataclass
from typing import Dict, List, Optional, Any
import logging
from abc import ABC, abstractmethod

from backend.models.cytoscape.elements import CytoscapeNode, CytoscapeEdge
from backend.models.constants import NodeType, EdgeType

logger = logging.getLogger(__name__)

@dataclass
class BaseAssociation(ABC):
    """Abstract base class for all association types"""
    
    @abstractmethod
    def to_cytoscape_elements(self) -> List[Dict[str, Any]]:
        """Convert to Cytoscape elements (nodes and edges)"""
        pass
    
    def get_nodes(self) -> List[CytoscapeNode]:
        """Extract nodes from cytoscape elements"""
        elements = self.to_cytoscape_elements()
        nodes = []
        for element in elements:
            if element.get("group") != "edges" and "data" in element:
                data = element["data"]
                if "source" not in data and "target" not in data:  # It's a node
                    node = CytoscapeNode(
                        id=data.get("id", ""),
                        label=data.get("label", ""),
                        node_type=data.get("type", ""),
                        classes=element.get("classes", ""),
                        properties=data
                    )
                    nodes.append(node)
        return nodes
    
    def get_edges(self) -> List[CytoscapeEdge]:
        """Extract edges from cytoscape elements"""
        elements = self.to_cytoscape_elements()
        edges = []
        for element in elements:
            if element.get("group") == "edges" or ("data" in element and "source" in element["data"]):
                data = element["data"]
                if "source" in data and "target" in data:  # It's an edge
                    edge = CytoscapeEdge(
                        id=data.get("id", f"{data.get('source', '')}_{data.get('target', '')}"),
                        source=data.get("source", ""),
                        target=data.get("target", ""),
                        label=data.get("label", ""),
                        properties=data
                    )
                    edges.append(edge)
        return edges


@dataclass
class GeneAssociation(BaseAssociation):
    """Represents gene associations with Key Events"""

    ke_uri: str
    gene_id: str
    protein_id: Optional[str] = None

    def to_cytoscape_elements(self) -> List[Dict[str, Any]]:
        """Convert to Cytoscape elements (nodes and edges)"""
        elements = []

        # Gene node
        gene_node_id = f"gene_{self.gene_id}"
        elements.append(
            {
                "data": {
                    "id": gene_node_id,
                    "label": self.gene_id,
                    "type": NodeType.GENE.value,
                    "gene_id": self.gene_id,
                },
                "classes": "gene-node",
            }
        )

        # Protein node and relationships (only if proteins are included)
        if self.protein_id and self.protein_id != "NA":
            protein_node_id = f"protein_{self.protein_id}"
            elements.append(
                {
                    "data": {
                        "id": protein_node_id,
                        "label": self.protein_id,
                        "type": NodeType.PROTEIN.value,
                        "protein_id": self.protein_id,
                    },
                    "classes": "protein-node",
                }
            )

            # Translates to edge
            elements.append(
                {
                    "data": {
                        "id": f"{gene_node_id}_{protein_node_id}",
                        "source": gene_node_id,
                        "target": protein_node_id,
                        "label": "translates to",
                        "type": EdgeType.TRANSLATES_TO.value,
                    }
                }
            )

            # Part of edge (protein to KE)
            elements.append(
                {
                    "data": {
                        "id": f"{protein_node_id}_{self.ke_uri}",
                        "source": protein_node_id,
                        "target": self.ke_uri,
                        "label": "part of",
                        "type": EdgeType.PART_OF.value,
                    }
                }
            )
        else:
            # Direct gene to KE connection when no protein is included
            elements.append(
                {
                    "data": {
                        "id": f"{gene_node_id}_{self.ke_uri}",
                        "source": gene_node_id,
                        "target": self.ke_uri,
                        "label": "part of",
                        "type": EdgeType.PART_OF.value,
                    }
                }
            )

        return elements


@dataclass
class ComponentAssociation(BaseAssociation):
    """Represents component associations with KEs"""

    ke_uri: str
    ke_name: str
    process: str
    process_name: str
    object: str
    object_name: str
    action: str
    object_type: str

    def to_cytoscape_elements(self) -> List[Dict[str, Any]]:
        """Convert to Cytoscape elements (nodes and edges)"""
        if not self.process:  # DROP components with empty process IRI
            return []
        ke = "aop.events_" + self.ke_uri.split("/")[-1]
        process = self.process.split("/")[-1] if "/" in self.process else self.process
        object = self.object.split("/")[-1] if "/" in self.object else self.object
        elements = []
        process_node_id = f"process_{process}"

        elements.append(
            {
                "data": {
                    "id": process_node_id,
                    "label": self.process_name,
                    "type": NodeType.COMPONENT_PROCESS.value,
                    "process_iri": self.process,
                    "process_name": self.process_name,
                    "process_id": process,
                },
                "classes": "process-node component-node",
            }
        )

        # Determine edge label - use action if it's a valid component action, otherwise use has_process
        edge_label = self.action if self.action in EdgeType.get_component_actions() else EdgeType.HAS_PROCESS.value
        edge_type = EdgeType.HAS_PROCESS.value  # Always use has_process as the type

        elements.append(
            {
                "data": {
                    "id": f"{ke}_{process_node_id}",
                    "source": self.ke_uri,
                    "target": process_node_id,
                    "label": edge_label,
                    "type": edge_type,
                }
            }
        )

        if self.object:
            object_node_id = f"object_{object}"

            # Determine the type of the object node based on object_type or object_iri
            # Hacky patch for misassigned types in AOP WIKI RDF
            if (
                self.object_type == "http://aopkb.org/aop_ontology#OrganContext"
                or any(substring in object for substring in 
                       ["FMA", "UBERON"])
            ):
                object_node_type = NodeType.ORGAN.value
                object_classes = NodeType.ORGAN.value
            elif ("CellTypeContext" in self.object_type
                  or any(substring in object for substring in 
                         ["CL", "EFO"])
                  or self.object_name in ["cell", "mitochondrion"]):
                object_node_type = NodeType.CELL.value  
                object_classes = "cell-node"
            elif (self.object.endswith("PATO_0001241")
                  or any(substring in object for substring in 
                         ["PR"])):
                object_node_type = NodeType.PROTEIN.value
                object_classes = "protein-node"
            elif any(
                substring in object for substring in ["GO"]
            ):
                object_node_type = NodeType.CELLULAR_COMPONENT.value
                object_classes = "cellular-component-node"
            else:
                # Default to component object type
                object_node_type = NodeType.COMPONENT_OBJECT.value
                object_classes = "object-node component-node"

            elements.append(
                {
                    "data": {
                        "id": object_node_id,
                        "label": self.object_name,
                        "type": object_node_type,
                        "object_iri": self.object,
                        "object_name": self.object_name,
                        "object_id": object,
                    },
                    "classes": object_classes,
                }
            )

            elements.append(
                {
                    "data": {
                        "id": f"{ke}_{process_node_id}_{object_node_id}",
                        "source": process_node_id,
                        "target": object_node_id,
                        "label": EdgeType.INVOLVES.value,
                        "type": EdgeType.INVOLVES.value,
                    }
                }
            )
        return elements

    def to_table_entry(self) -> Dict[str, str]:
        """Convert to component table entry format"""
        # Extract KE ID from URI
        ke_id = self.ke_uri.split("/")[-1] if "/" in self.ke_uri else self.ke_uri
        # Extract process ID from URI
        process_id = self.process.split("/")[-1] if "/" in self.process else self.process

        # Extract object ID from URI
        object_id = self.object.split("/")[-1] if "/" in self.object else self.object

        return {
            "ke_id": ke_id,
            "ke_uri": self.ke_uri,
            "ke_label": self.ke_name if self.ke_name else "N/A",
            "process_id": process_id,
            "process_name": self.process_name,
            "process_iri": self.process,
            "object_id": object_id if self.object else "N/A",
            "object_name": self.object_name if self.object_name else "N/A", 
            "object_iri": self.object if self.object else "N/A",
            "action": self.action if self.action else "N/A",
            "node_id": f"process_{process_id}",
        }

@dataclass
class CompoundAssociation(BaseAssociation):
    """Represents compound associations with AOPs"""

    aop_uri: str
    mie_uri: str
    chemical_uri: str
    chemical_label: str
    pubchem_compound: str
    compound_name: str
    cas_id: Optional[str] = None

    def to_cytoscape_elements(self) -> List[Dict[str, Any]]:
        """Convert to Cytoscape elements (nodes and edges)"""
        elements = []

        # Extract identifiers
        pubchem_id = (
            self.pubchem_compound.split("/")[-1]
            if "/" in self.pubchem_compound
            else self.pubchem_compound
        )
        chemical_node_id = f"chemical_{pubchem_id}"

        # Chemical node
        elements.append(
            {
                "data": {
                    "id": chemical_node_id,
                    "label": self.compound_name or self.chemical_label,
                    "type": NodeType.CHEMICAL.value,
                    "pubchem_id": pubchem_id,
                    "cas_id": self.cas_id,
                    "chemical_label": self.chemical_label,
                    "compound_name": self.compound_name,
                    "pubchem_compound": self.pubchem_compound,
                },
                "classes": "chemical-node",
            }
        )

        # Edge from chemical to MIE
        if self.mie_uri:
            elements.append(
                {
                    "data": {
                        "id": f"{chemical_node_id}_{self.mie_uri}",
                        "source": chemical_node_id,
                        "target": self.mie_uri,
                        "label": EdgeType.IS_STRESSOR_OF.value,
                        "type": EdgeType.IS_STRESSOR_OF.value,
                    }
                }
            )

        return elements

    def to_table_entry(self) -> Dict[str, str]:
        """Convert to compound table entry format"""
        # Extract PubChem ID from compound URI
        pubchem_id = (
            self.pubchem_compound.split("/")[-1]
            if "/" in self.pubchem_compound
            else self.pubchem_compound
        )

        # Extract AOP ID from URI
        aop_id = self.aop_uri.split("/")[-1] if "/" in self.aop_uri else self.aop_uri

        return {
            "compound_name": self.compound_name or self.chemical_label,
            "chemical_label": self.chemical_label,
            "pubchem_id": pubchem_id,
            "pubchem_compound": self.pubchem_compound,
            "cas_id": self.cas_id if self.cas_id else "N/A",
            "aop_id": f"AOP:{aop_id}",
            "aop_uri": self.aop_uri,
            "mie_uri": self.mie_uri,
            "chemical_uri": self.chemical_uri,
        }


@dataclass
class GeneExpressionAssociation(BaseAssociation):
    """Represents gene expression associations with organs"""

    def __init__(
        self,
        gene_id: str,
        anatomical_id: str,
        anatomical_name: str,
        expression_level: str,
        confidence_id: str,
        confidence_level_name: str,
        developmental_id: str,
        developmental_stage_name: str,
        expr: str,
    ):
        self.gene_id = gene_id
        self.anatomical_id = anatomical_id
        self.anatomical_name = anatomical_name
        self.expression_level = expression_level
        self.confidence_id = confidence_id
        self.confidence_level_name = confidence_level_name
        self.developmental_id = developmental_id
        self.developmental_stage_name = developmental_stage_name
        self.expr = expr

    def to_cytoscape_elements(self) -> List[Dict[str, Any]]:
        """Convert to Cytoscape elements (nodes and edges)"""
        elements = []
        
        # Organ node
        organ_node_id = f"{self.anatomical_id}"
        elements.append(
            {
                "data": {
                    "id": organ_node_id,
                    "label": self.anatomical_name,
                    "type": NodeType.ORGAN.value,
                    "anatomical_id": self.anatomical_id,
                    "anatomical_name": self.anatomical_name,
                },
                "classes": "organ-node",
            }
        )

        # Expression edge from gene to organ
        gene_node_id = f"gene_{self.gene_id}"
        expression_edge_id = f"{gene_node_id}_{organ_node_id}_expression"
        elements.append(
            {
                "data": {
                    "id": expression_edge_id,
                    "source": gene_node_id,
                    "target": organ_node_id,
                    "label": f"expressed in ({self.expression_level})",
                    "type": EdgeType.EXPRESSION_IN.value,
                    "expression_level": self.expression_level,
                    "confidence_level": self.confidence_level_name,
                    "developmental_stage": self.developmental_stage_name,
                }
            }
        )

        return elements

    def to_table_entry(self) -> Dict[str, str]:
        """Convert to gene expression table entry format"""
        return {
            "gene_id": self.gene_id,
            "organ": self.anatomical_name,
            "expression_level": self.expression_level,
            "confidence": self.confidence_level_name,
            "developmental_stage": self.developmental_stage_name,
        }


@dataclass
class OrganAssociation(BaseAssociation):
    """Represents an organ-key event association"""
    ke_uri: str
    organ_data: CytoscapeNode
    edge_data: CytoscapeEdge

    def to_cytoscape_elements(self) -> List[Dict[str, Any]]:
        """Convert to Cytoscape elements"""
        return [
            {"data": self.organ_data.to_dict()},
            {"data": self.edge_data.to_dict()}
        ]
