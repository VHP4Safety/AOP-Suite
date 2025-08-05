from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, Set
from enum import Enum
import logging

logger = logging.getLogger(__name__)


class NodeType(Enum):
    MIE = "mie"
    KE = "ke"
    AO = "ao"
    CHEMICAL = "chemical"
    UNIPROT = "uniprot"
    ENSEMBL = "ensembl"
    ORGAN = "organ"
    CUSTOM = "custom"


class EdgeType(Enum):
    KER = "ker"
    INTERACTION = "interaction"
    PART_OF = "part_of"
    TRANSLATES_TO = "translates_to"
    EXPRESSION_IN = "expression_in"
    CUSTOM = "custom"
    IS_STRESSOR_OF = "is stressor of"


class DataSourceType(Enum):
    AOPWIKI = "aopwiki"
    QSPRPRED = "qsprpred"
    BGEE = "bgee"
    OPENTARGETS = "opentargets"
    CUSTOM_TABLE = "custom_table"
    MANUAL = "manual"


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


@dataclass
class GeneAssociation:
    """Represents gene associations with Key Events"""

    ke_uri: str
    ensembl_id: str
    uniprot_id: Optional[str] = None

    def to_cytoscape_elements(self) -> List[Dict[str, Any]]:
        """Convert to Cytoscape elements (nodes and edges)"""
        elements = []

        # Ensembl node
        ensembl_node_id = f"ensembl_{self.ensembl_id}"
        elements.append(
            {
                "data": {
                    "id": ensembl_node_id,
                    "label": self.ensembl_id,
                    "type": NodeType.ENSEMBL.value,
                    "ensembl_id": self.ensembl_id,
                },
                "classes": "ensembl-node",
            }
        )

        # UniProt node (if available)
        if self.uniprot_id and self.uniprot_id != "NA":
            uniprot_node_id = f"uniprot_{self.uniprot_id}"
            elements.append(
                {
                    "data": {
                        "id": uniprot_node_id,
                        "label": self.uniprot_id,
                        "type": NodeType.UNIPROT.value,
                        "uniprot_id": self.uniprot_id,
                    },
                    "classes": "uniprot-node",
                }
            )

            # Translates to edge
            elements.append(
                {
                    "data": {
                        "id": f"{ensembl_node_id}_{uniprot_node_id}",
                        "source": ensembl_node_id,
                        "target": uniprot_node_id,
                        "label": "translates to",
                        "type": EdgeType.TRANSLATES_TO.value,
                    }
                }
            )

            # Part of edge (protein to KE)
            elements.append(
                {
                    "data": {
                        "id": f"{uniprot_node_id}_{self.ke_uri}",
                        "source": uniprot_node_id,
                        "target": self.ke_uri,
                        "label": "part of",
                        "type": EdgeType.PART_OF.value,
                    }
                }
            )
        else:
            # Direct gene to KE connection if no protein
            elements.append(
                {
                    "data": {
                        "id": f"{ensembl_node_id}_{self.ke_uri}",
                        "source": ensembl_node_id,
                        "target": self.ke_uri,
                        "label": "part of",
                        "type": EdgeType.PART_OF.value,
                    }
                }
            )

        return elements


@dataclass
class CompoundAssociation:
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


class AOPNetwork:
    """Main AOP Network model representing a complete AOP query result"""

    def __init__(self):
        self.key_events: Dict[str, AOPKeyEvent] = {}
        self.relationships: List[KeyEventRelationship] = []
        self.gene_associations: List[GeneAssociation] = []
        self.compound_associations: List[CompoundAssociation] = []
        self.aop_info: Dict[str, AOPInfo] = {}

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

    def add_compound_association(self, association: CompoundAssociation):
        """Add a compound association"""
        self.compound_associations.append(association)

    def get_genes_for_ke(self, ke_uri: str) -> List[GeneAssociation]:
        """Get all gene associations for a specific Key Event"""
        return [assoc for assoc in self.gene_associations if assoc.ke_uri == ke_uri]

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

    def to_cytoscape_elements(self) -> List[Dict[str, Any]]:
        """Convert entire network to Cytoscape elements"""
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

        logger.info(f"Generated {len(elements)} Cytoscape elements")
        return elements

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
            "compound_associations": len(self.compound_associations),
            "total_aops": len(self.aop_info),
        }


class AOPNetworkBuilder:
    """Builder class for constructing AOP networks from SPARQL results"""

    def __init__(self):
        self.network = AOPNetwork()
        self._temp_ke_data: Dict[str, Dict[str, Any]] = {}

    def process_sparql_binding(self, binding: Dict[str, Any]):
        """Process a single SPARQL result binding"""
        try:
            # Extract basic data
            aop_uri = binding.get("aop", {}).get("value", "")
            aop_title = binding.get("aop_title", {}).get("value", "")

            # Create AOP info
            aop_info = None
            if aop_uri and aop_title:
                aop_id = aop_uri.split("/")[-1] if "/" in aop_uri else aop_uri
                aop_info = AOPInfo(aop_id=aop_id, title=aop_title, uri=aop_uri)

            # Process MIE
            self._process_key_event(
                binding.get("MIE", {}).get("value", ""),
                binding.get("MIEtitle", {}).get("value", ""),
                NodeType.MIE,
                aop_info,
            )

            # Process AO
            self._process_key_event(
                binding.get("ao", {}).get("value", ""),
                binding.get("ao_title", {}).get("value", ""),
                NodeType.AO,
                aop_info,
            )

            # Process intermediate KEs
            upstream_uri = binding.get("KE_upstream", {}).get("value", "")
            upstream_title = binding.get("KE_upstream_title", {}).get("value", "")
            downstream_uri = binding.get("KE_downstream", {}).get("value", "")
            downstream_title = binding.get("KE_downstream_title", {}).get("value", "")

            if upstream_uri and upstream_uri not in [
                binding.get("MIE", {}).get("value", ""),
                binding.get("ao", {}).get("value", ""),
            ]:
                self._process_key_event(
                    upstream_uri, upstream_title, NodeType.KE, aop_info
                )

            if downstream_uri and downstream_uri not in [
                binding.get("MIE", {}).get("value", ""),
                binding.get("ao", {}).get("value", ""),
            ]:
                self._process_key_event(
                    downstream_uri, downstream_title, NodeType.KE, aop_info
                )

            # Process KER
            ker_uri = binding.get("KER", {}).get("value", "")
            if ker_uri and upstream_uri and downstream_uri:
                self._process_relationship(ker_uri, upstream_uri, downstream_uri)

        except Exception as e:
            logger.warning(f"Failed to process SPARQL binding: {e}")

    def _process_key_event(
        self, uri: str, title: str, ke_type: NodeType, aop_info: Optional[AOPInfo]
    ):
        """Process a key event from SPARQL data"""
        if not uri:
            return

        if uri in self.network.key_events:
            # Update existing KE with new AOP info
            if aop_info:
                self.network.key_events[uri].add_aop(aop_info)
        else:
            # Create new KE
            ke_id = uri.split("/")[-1] if "/" in uri else uri
            key_event = AOPKeyEvent(
                ke_id=ke_id, uri=uri, title=title if title else "NA", ke_type=ke_type
            )
            if aop_info:
                key_event.add_aop(aop_info)

            self.network.add_key_event(key_event)

    def _process_relationship(
        self, ker_uri: str, upstream_uri: str, downstream_uri: str
    ):
        """Process a key event relationship"""
        if (
            upstream_uri in self.network.key_events
            and downstream_uri in self.network.key_events
        ):
            ker_id = ker_uri.split("/")[-1] if "/" in ker_uri else ker_uri

            relationship = KeyEventRelationship(
                ker_id=ker_id,
                ker_uri=ker_uri,
                upstream_ke=self.network.key_events[upstream_uri],
                downstream_ke=self.network.key_events[downstream_uri],
            )

            self.network.add_relationship(relationship)

    def add_gene_associations(self, gene_sparql_results: List[Dict[str, Any]]):
        """Add gene associations from gene SPARQL results"""
        for result in gene_sparql_results:
            ke_uri = result.get("ke", {}).get("value", "")
            ensembl_id = result.get("ensembl", {}).get("value", "")
            uniprot_id = result.get("uniprot", {}).get("value", "")

            if ke_uri and ensembl_id:
                association = GeneAssociation(
                    ke_uri=ke_uri,
                    ensembl_id=ensembl_id,
                    uniprot_id=uniprot_id if uniprot_id else None,
                )
                self.network.add_gene_association(association)

    def add_compound_associations(self, compound_sparql_results: List[Dict[str, Any]]):
        """Add compound associations from compound SPARQL results"""
        for result in compound_sparql_results:
            aop_uri = result.get("aop", {}).get("value", "")
            chemical_uri = result.get("chemical", {}).get("value", "")
            pubchem_compound = result.get("pubchem_compound", {}).get("value", "")
            compound_name = result.get("compound_name", {}).get("value", "")
            cid = result.get("cid", {}).get("value", "")
            mie_uri = result.get("mie", {}).get("value", "")  # Get MIE directly from SPARQL
            
            if aop_uri and chemical_uri and pubchem_compound:
                association = CompoundAssociation(
                    aop_uri=aop_uri,
                    mie_uri=mie_uri,  # Use MIE from SPARQL results
                    chemical_uri=chemical_uri,
                    chemical_label=compound_name,  # Use compound_name as chemical_label
                    pubchem_compound=pubchem_compound,
                    compound_name=compound_name,
                    cas_id=cid if cid else None,  # Use cid as cas_id for now
                )

                self.network.add_compound_association(association)

    def build(self) -> AOPNetwork:
        """Return the constructed network"""
        return self.network


@dataclass
class CytoscapeNode:
    """Represents a node in Cytoscape format"""

    id: str
    label: str
    node_type: str
    classes: str
    properties: Dict[str, Any]

    @classmethod
    def from_cytoscape_element(
        cls, element: Dict[str, Any]
    ) -> Optional["CytoscapeNode"]:
        """Create a node from a Cytoscape element"""
        if element.get("group") == "edges":
            return None

        data = element.get("data", {})
        node_id = data.get("id", "")

        if not node_id:
            return None

        return cls(
            id=node_id,
            label=data.get("label", ""),
            node_type=data.get("type", ""),
            classes=element.get("classes", ""),
            properties=data,
        )

    def is_ensembl_node(self) -> bool:
        """Check if this is an Ensembl gene node"""
        return (
            self.classes == "ensembl-node"
            or self.node_type == "ensembl"
            or self.id.startswith("ensembl_")
        )

    def is_uniprot_node(self) -> bool:
        """Check if this is a UniProt protein node"""
        return (
            self.classes == "uniprot-node"
            or self.node_type == "uniprot"
            or self.id.startswith("uniprot_")
        )


@dataclass
class CytoscapeEdge:
    """Represents an edge in Cytoscape format"""

    id: str
    source: str
    target: str
    label: str
    properties: Dict[str, Any]

    @classmethod
    def from_cytoscape_element(
        cls, element: Dict[str, Any]
    ) -> Optional["CytoscapeEdge"]:
        """Create an edge from a Cytoscape element"""
        if element.get("group") != "edges":
            return None

        data = element.get("data", {})

        source = data.get("source", "")
        target = data.get("target", "")

        if not source or not target:
            return None

        return cls(
            id=data.get("id", f"{source}_{target}"),
            source=source,
            target=target,
            label=data.get("label", ""),
            properties=data,
        )

    def is_gene_relationship(self) -> bool:
        """Check if this is a gene-related relationship"""
        return self.label in ["translates to", "part of"]


@dataclass
class GeneProteinPair:
    """Represents a gene-protein relationship"""

    gene_id: str
    gene_label: str
    protein_id: str
    protein_label: str
    uniprot_id: str
    ensembl_node_id: str
    uniprot_node_id: str

    def to_table_entry(self) -> Dict[str, str]:
        """Convert to gene table entry format"""
        return {
            "gene": self.gene_label if self.gene_label != "N/A" else "N/A",
            "protein": self.protein_label if self.protein_label != "N/A" else "N/A",
            "uniprot_id": self.uniprot_id if self.uniprot_id != "N/A" else "N/A",
            "ensembl_id": (
                self.ensembl_node_id if self.ensembl_node_id != "N/A" else "N/A"
            ),
            "uniprot_node_id": (
                self.uniprot_node_id if self.uniprot_node_id != "N/A" else "N/A"
            ),
        }


class CytoscapeNetworkParser:
    """Parses Cytoscape network elements into structured data"""

    def __init__(self, elements: List[Dict[str, Any]]):
        self.elements = elements
        self.nodes = self._parse_nodes()
        self.edges = self._parse_edges()
        logger.info(f"Parsed {len(self.nodes)} nodes and {len(self.edges)} edges")

    def _parse_nodes(self) -> List[CytoscapeNode]:
        """Parse all nodes from elements"""
        nodes = []
        for element in self.elements:
            node = CytoscapeNode.from_cytoscape_element(element)
            if node:
                nodes.append(node)
        return nodes

    def _parse_edges(self) -> List[CytoscapeEdge]:
        """Parse all edges from elements"""
        edges = []
        for element in self.elements:
            edge = CytoscapeEdge.from_cytoscape_element(element)
            if edge:
                edges.append(edge)
        return edges

    def get_gene_nodes(self) -> List[CytoscapeNode]:
        """Get all gene-related nodes"""
        return [node for node in self.nodes if node.is_ensembl_node()]

    def get_ensembl_nodes(self) -> List[CytoscapeNode]:
        """Get all Ensembl nodes"""
        return [node for node in self.nodes if node.is_ensembl_node()]

    def get_uniprot_nodes(self) -> List[CytoscapeNode]:
        """Get all UniProt nodes"""
        return [node for node in self.nodes if node.is_uniprot_node()]

    def get_gene_relationships(self) -> List[CytoscapeEdge]:
        """Get all gene-related edges"""
        return [edge for edge in self.edges if edge.is_gene_relationship()]


class GeneTableBuilder:
    """Builds gene table data from Cytoscape network"""

    def __init__(self, parser: CytoscapeNetworkParser):
        self.parser = parser
        self.ensembl_nodes = {node.id: node for node in parser.get_ensembl_nodes()}
        self.uniprot_nodes = {node.id: node for node in parser.get_uniprot_nodes()}
        self.gene_relationships = parser.get_gene_relationships()

    def build_gene_table(self) -> List[Dict[str, str]]:
        """Build complete gene table with many-to-many relationships"""
        gene_pairs = self._create_gene_protein_pairs()
        orphaned_genes = self._get_orphaned_genes(gene_pairs)
        orphaned_proteins = self._get_orphaned_proteins(gene_pairs)

        all_pairs = gene_pairs + orphaned_genes + orphaned_proteins

        # Convert to table entries and remove duplicates
        table_entries = []
        seen_pairs = set()

        for pair in all_pairs:
            entry = pair.to_table_entry()
            pair_key = f"{entry['gene']}_{entry['protein']}_{entry['uniprot_id']}"

            if pair_key not in seen_pairs:
                table_entries.append(entry)
                seen_pairs.add(pair_key)

        logger.info(f"Built gene table with {len(table_entries)} entries")
        return table_entries

    def _create_gene_protein_pairs(self) -> List[GeneProteinPair]:
        """Create gene-protein pairs from relationships"""
        pairs = []

        for edge in self.gene_relationships:
            if edge.label != "translates to":
                continue

            ensembl_node = None
            uniprot_node = None

            # Determine which is ensembl and which is uniprot
            source_node = self.ensembl_nodes.get(edge.source) or self.uniprot_nodes.get(
                edge.source
            )
            target_node = self.ensembl_nodes.get(edge.target) or self.uniprot_nodes.get(
                edge.target
            )

            if source_node and source_node.is_ensembl_node():
                ensembl_node = source_node
                uniprot_node = target_node
            elif target_node and target_node.is_ensembl_node():
                ensembl_node = target_node
                uniprot_node = source_node

            if ensembl_node and uniprot_node:
                pair = self._create_pair_from_nodes(ensembl_node, uniprot_node)
                if pair:
                    pairs.append(pair)

        logger.debug(f"Created {len(pairs)} gene-protein pairs from relationships")
        return pairs

    def _create_pair_from_nodes(
        self, ensembl_node: CytoscapeNode, uniprot_node: CytoscapeNode
    ) -> Optional[GeneProteinPair]:
        """Create a gene-protein pair from two nodes"""
        try:
            # Extract Ensembl information
            gene_label = ensembl_node.label
            ensembl_id = ensembl_node.properties.get("ensembl_id", ensembl_node.id)
            if ensembl_id.startswith("ensembl_"):
                ensembl_id = ensembl_id.replace("ensembl_", "")

            # Extract UniProt information
            protein_label = uniprot_node.label
            uniprot_id = uniprot_node.properties.get("uniprot_id", uniprot_node.id)
            if uniprot_id.startswith("uniprot_"):
                uniprot_id = uniprot_id.replace("uniprot_", "")

            # If protein label looks like UniProt ID, use it as the ID
            if len(protein_label) <= 10 and not protein_label.startswith("uniprot_"):
                if uniprot_id == "NA" or uniprot_id == uniprot_node.id:
                    uniprot_id = protein_label

            return GeneProteinPair(
                gene_id=ensembl_id,
                gene_label=gene_label,
                protein_id=uniprot_id,
                protein_label=protein_label,
                uniprot_id=uniprot_id,
                ensembl_node_id=ensembl_node.id,
                uniprot_node_id=uniprot_node.id,
            )
        except Exception as e:
            logger.warning(
                f"Failed to create pair from nodes {ensembl_node.id}, {uniprot_node.id}: {e}"
            )
            return None

    def _get_orphaned_genes(
        self, existing_pairs: List[GeneProteinPair]
    ) -> List[GeneProteinPair]:
        """Get genes without protein connections"""
        connected_gene_ids = {pair.ensembl_node_id for pair in existing_pairs}
        orphaned = []

        for node_id, node in self.ensembl_nodes.items():
            if node_id not in connected_gene_ids:
                ensembl_id = node.properties.get("ensembl_id", node.id)
                if ensembl_id.startswith("ensembl_"):
                    ensembl_id = ensembl_id.replace("ensembl_", "")

                pair = GeneProteinPair(
                    gene_id=ensembl_id,
                    gene_label=node.label,
                    protein_id="N/A",
                    protein_label="N/A",
                    uniprot_id="N/A",
                    ensembl_node_id=node.id,
                    uniprot_node_id="N/A",
                )
                orphaned.append(pair)

        logger.debug(f"Found {len(orphaned)} orphaned genes")
        return orphaned

    def _get_orphaned_proteins(
        self, existing_pairs: List[GeneProteinPair]
    ) -> List[GeneProteinPair]:
        """Get proteins without gene connections"""
        connected_protein_ids = {pair.uniprot_node_id for pair in existing_pairs}
        orphaned = []

        for node_id, node in self.uniprot_nodes.items():
            if node_id not in connected_protein_ids:
                uniprot_id = node.properties.get("uniprot_id", node.id)
                if uniprot_id.startswith("uniprot_"):
                    uniprot_id = uniprot_id.replace("uniprot_", "")

                # If label looks like UniProt ID, use it
                if len(node.label) <= 10 and not node.label.startswith("uniprot_"):
                    if uniprot_id == "NA" or uniprot_id == node.id:
                        uniprot_id = node.label

                pair = GeneProteinPair(
                    gene_id="N/A",
                    gene_label="N/A",
                    protein_id=uniprot_id,
                    protein_label=node.label,
                    uniprot_id=uniprot_id,
                    ensembl_node_id="N/A",
                    uniprot_node_id=node.id,
                )
                orphaned.append(pair)

        logger.debug(f"Found {len(orphaned)} orphaned proteins")
        return orphaned


@dataclass
class AOPRelationshipEntry:
    """Represents an AOP relationship entry for the table"""

    source_node: "CytoscapeNode"
    target_node: "CytoscapeNode"
    edge: "CytoscapeEdge"

    def to_table_entry(self) -> Dict[str, str]:
        """Convert to AOP table entry format"""
        # Extract AOP info from both nodes
        source_aop_info = self._extract_node_aop_info(self.source_node)
        target_aop_info = self._extract_node_aop_info(self.target_node)

        # Combine AOP information
        all_aop_ids = set(source_aop_info["aop_ids"] + target_aop_info["aop_ids"])
        all_aop_titles = set(
            source_aop_info["aop_titles"] + target_aop_info["aop_titles"]
        )

        aop_string = ",".join(sorted(all_aop_ids)) if all_aop_ids else "N/A"
        aop_titles_string = (
            "; ".join(sorted(all_aop_titles)) if all_aop_titles else "N/A"
        )

        return {
            "source_id": self.source_node.id,
            "source_label": self.source_node.label or self.source_node.id,
            "source_type": self.source_node.node_type or "unknown",
            "ker_label": self.edge.properties.get("ker_label", ""),
            "curie": self.edge.properties.get("curie", ""),
            "target_id": self.target_node.id,
            "target_label": self.target_node.label or self.target_node.id,
            "target_type": self.target_node.node_type or "unknown",
            "aop_list": aop_string,
            "aop_titles": aop_titles_string,
            "is_connected": True,
        }

    def _extract_node_aop_info(self, node) -> Dict[str, List[str]]:
        """Extract AOP information from a node"""
        aop_uris = node.properties.get("aop", [])
        aop_titles = node.properties.get("aop_title", [])

        if not isinstance(aop_uris, list):
            aop_uris = [aop_uris] if aop_uris else []
        if not isinstance(aop_titles, list):
            aop_titles = [aop_titles] if aop_titles else []

        # Convert URIs to AOP IDs
        aop_ids = []
        for aop_uri in aop_uris:
            if aop_uri and "aop/" in aop_uri:
                aop_id = aop_uri.split("aop/")[-1]
                aop_ids.append(f"AOP:{aop_id}")

        return {"aop_ids": aop_ids, "aop_titles": aop_titles}
