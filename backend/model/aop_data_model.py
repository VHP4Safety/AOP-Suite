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
    COMPONENT_PROCESS = "component_process"
    COMPONENT_OBJECT = "component_object"
    CUSTOM = "custom"


class EdgeType(Enum):
    KER = "ker"
    INTERACTION = "interaction"
    PART_OF = "part_of"
    TRANSLATES_TO = "translates_to"
    EXPRESSION_IN = "expression_in"
    CUSTOM = "custom"
    IS_STRESSOR_OF = "is stressor of"
    HAS_PROCESS = "has process"
    HAS_OBJECT = "has object"
    NA = "na"
    # Component actions https://pmc.ncbi.nlm.nih.gov/articles/PMC6060416/
    INCREASED = {
        "label": "increased process quality",
        "iri": "http://purl.obolibrary.org/obo/PATO_0002304",
    }
    DECREASED = {
        "label": "decreased process quality",
        "iri": "http://purl.obolibrary.org/obo/PATO_0002301",
    }
    DELAYED = {
        "label": "delayed",
        "iri": "http://purl.obolibrary.org/obo/PATO_0000502",
    }
    OCCURRENCE = {
        "label": "occurrence",
        "iri": "http://purl.obolibrary.org/obo/PATO_0000057",
    }
    ABNORMAL = {
        "label": "abnormal",
        "iri": "http://purl.obolibrary.org/obo/PATO_0000460",
    }
    PREMATURE = {
        "label": "premature",
        "iri": "http://purl.obolibrary.org/obo/PATO_0001028",
    }
    DISRUPTED = {
        "label": "disrupted",
        "iri": "http://purl.obolibrary.org/obo/PATO_0001507",
    }
    FUNCTIONAL_CHANGE = {
        "label": "functional change",
        "iri": "http://purl.obolibrary.org/obo/PATO_0001509",
    }
    MORPHOLOGICAL_CHANGE = {
        "label": "morphological change",
        "iri": "http://purl.obolibrary.org/obo/PATO_0000051",
    }
    PATHOLOGICAL = {
        "label": "pathological",
        "iri": "http://purl.obolibrary.org/obo/PATO_0001869",
    }
    ARRESTED = {
        "label": "arrested",
        "iri": "http://purl.obolibrary.org/obo/PATO_0000297",
    }

    @classmethod
    def get_iri(cls) -> Set[str]:
        return {item.value["iri"] for item in cls if isinstance(item.value, dict) and "iri" in item.value}
    @classmethod
    def get_label(cls) -> Set[str]:
        return {item.value["label"] for item in cls if isinstance(item.value, dict) and "label" in item.value}

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
class ComponentAssociation:
    """Represents component associations with KEs"""

    ke_uri: str
    ke_name: str
    process: str
    process_name: str
    object: str
    object_name: str
    action: str

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
                "classes": "process-node",
            }
        )

        elements.append(
            {
                "data": {
                    "id": f"{ke}_{process_node_id}",
                    "source": self.ke_uri,
                    "target": process_node_id,
                    "label": (
                        self.action
                        if self.action in EdgeType.get_label()
                        else EdgeType.NA.value
                    ),
                    "type": EdgeType.HAS_PROCESS.value,
                }
            }
        )
        
        if self.object:
            object_node_id = f"object_{object}"
            
            elements.append(
                {
                    "data": {
                        "id": object_node_id,
                        "label": self.object_name,
                        "type": NodeType.COMPONENT_OBJECT.value,
                        "object_iri": self.object,  # Keep full IRI here instead of truncated
                        "object_name": self.object_name,
                        "object_id": object,  # Keep short ID for other uses
                    },
                    "classes": "object-node",
                }
            )
            
            elements.append(
                {
                    "data": {
                        "id": f"{ke}_{process_node_id}_{object_node_id}",
                        "source": process_node_id,
                        "target": object_node_id,
                        "label": EdgeType.HAS_OBJECT.value,
                        "type": EdgeType.HAS_OBJECT.value,
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


class AOPNetwork:
    """Main AOP Network model representing a complete AOP query result"""

    def __init__(self):
        self.key_events: Dict[str, AOPKeyEvent] = {}
        self.relationships: List[KeyEventRelationship] = []
        self.component_associations: List[ComponentAssociation] = []
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

    def add_component_association(self, association: ComponentAssociation):
        """Add a compound association"""
        self.component_associations.append(association)

    def get_genes_for_ke(self, ke_uri: str) -> List[GeneAssociation]:
        """Get all gene associations for a specific Key Event"""
        return [assoc for assoc in self.component_associations if assoc.ke_uri == ke_uri]

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
        for gene_assoc in self.component_associations:
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
            "gene_associations": len(self.component_associations),
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

    def add_component_associations(self, component_sparql_results: List[Dict[str, Any]]):
        """Add component associations from compound SPARQL results"""
        for result in component_sparql_results:
            process_iri = result.get("process", {}).get("value", "")
            if not process_iri:  # skip empty process iri (drop from network & table)
                continue
            association = ComponentAssociation(
                ke_uri=result.get("ke", {}).get("value", ""),
                ke_name=result.get("ke_name", {}).get("value", ""),
                process=process_iri,
                process_name=result.get("processName", {}).get("value", ""),
                object=result.get("object", {}).get("value", ""),
                object_name=result.get("objectName", {}).get("value", ""),
                action=result.get("action", {}).get("value", ""),
            )
            self.network.add_component_association(association)

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


class AOPTableBuilder:
    """Builds AOP table data"""

    def __init__(self, cy_elements: List[Dict[str, Any]]):
        self.parser = CytoscapeNetworkParser(cy_elements)
        self.aop_relationships = self._extract_aop_relationships()
        self.disconnected_nodes = self._extract_disconnected_nodes()

    def build_aop_table(self) -> List[Dict[str, str]]:
        """Build AOP table with proper data model structure"""
        table_entries = []

        # Process KER relationships
        for relationship in self.aop_relationships:
            table_entries.append(relationship.to_table_entry())

        # Process disconnected nodes
        for node_entry in self.disconnected_nodes:
            table_entries.append(node_entry)

        logger.info(f"Built AOP table with {len(table_entries)} entries using data model")
        return table_entries

    def _extract_aop_relationships(self) -> List['AOPRelationshipEntry']:
        """Extract AOP relationships from parsed network"""
        relationships = []

        for edge in self.parser.edges:
            # Only process edges with KER data
            if (edge.properties.get("ker_label") and 
                edge.properties.get("curie")):

                source_node = self._find_node_by_id(edge.source)
                target_node = self._find_node_by_id(edge.target)

                if source_node and target_node:
                    relationship = AOPRelationshipEntry(
                        source_node=source_node,
                        target_node=target_node,
                        edge=edge
                    )
                    relationships.append(relationship)

        return relationships

    def _extract_disconnected_nodes(self) -> List[Dict[str, str]]:
        """Extract disconnected nodes"""
        connected_node_ids = set()

        # Get all connected node IDs
        for edge in self.parser.edges:
            connected_node_ids.add(edge.source)
            connected_node_ids.add(edge.target)

        disconnected_entries = []
        for node in self.parser.nodes:
            if node.id not in connected_node_ids:
                # Extract AOP information
                aop_info = self._extract_aop_info_from_node(node)

                entry = {
                    "source_id": node.id,
                    "source_label": node.label or node.id,
                    "source_type": node.node_type or "unknown",
                    "aop_list": aop_info["aop_string"],
                    "aop_titles": aop_info["aop_titles_string"],
                    "is_connected": False,
                }
                disconnected_entries.append(entry)

        return disconnected_entries

    def _find_node_by_id(self, node_id: str) -> Optional['CytoscapeNode']:
        """Find node by ID"""
        for node in self.parser.nodes:
            if node.id == node_id:
                return node
        return None

    def _extract_aop_info_from_node(self, node) -> Dict[str, str]:
        """Extract AOP information from node properties"""
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

        aop_string = ",".join(sorted(aop_ids)) if aop_ids else "N/A"
        aop_titles_string = "; ".join(sorted(aop_titles)) if aop_titles else "N/A"

        return {
            "aop_string": aop_string,
            "aop_titles_string": aop_titles_string
        }


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


class CompoundTableBuilder:
    """Builds compound table data from Cytoscape network"""

    def __init__(self, parser: CytoscapeNetworkParser):
        self.parser = parser
        self.chemical_nodes = {node.id: node for node in self._get_chemical_nodes()}

    def _get_chemical_nodes(self) -> List[CytoscapeNode]:
        """Get all chemical nodes from the network"""
        return [
            node for node in self.parser.nodes
            if (node.classes == "chemical-node" or 
                node.node_type == "chemical" or
                node.id.startswith("chemical_"))
        ]

    def build_compound_table(self) -> List[Dict[str, str]]:
        """Build compound table from network chemical nodes"""
        table_entries = []
        seen_compounds = set()

        for node in self.chemical_nodes.values():
            # Extract compound information from node properties
            compound_name = (
                node.properties.get("compound_name") or 
                node.properties.get("chemical_label") or 
                node.label
            )
            
            pubchem_id = node.properties.get("pubchem_id", "")
            pubchem_compound = node.properties.get("pubchem_compound", "")
            cas_id = node.properties.get("cas_id", "N/A")
            
            # Create unique identifier to avoid duplicates
            compound_key = f"{compound_name}_{pubchem_id}"
            if compound_key not in seen_compounds:
                entry = {
                    "compound_name": compound_name,
                    "chemical_label": node.properties.get("chemical_label", compound_name),
                    "pubchem_id": pubchem_id,
                    "pubchem_compound": pubchem_compound,
                    "cas_id": cas_id,
                    "chemical_uri": node.properties.get("chemical_uri", ""),
                    "smiles": node.properties.get("smiles", ""),
                    "node_id": node.id,
                }
                table_entries.append(entry)
                seen_compounds.add(compound_key)

        logger.info(f"Built compound table with {len(table_entries)} entries")
        return table_entries


class ComponentTableBuilder:
    """Builds component table data from component elements"""

    def __init__(self, component_elements: List[Dict[str, Any]]):
        self.component_elements = component_elements
        self.component_nodes = self._get_component_nodes()
        self.component_edges = self._get_component_edges()

    def _get_component_nodes(self) -> List[Dict[str, Any]]:
        """Get all component nodes (process and object nodes)"""
        return [
            element for element in self.component_elements
            if element.get("data", {}).get("type") in ("component_process", "component_object")
        ]

    def _get_component_edges(self) -> List[Dict[str, Any]]:
        """Get all component edges"""
        return [
            element for element in self.component_elements
            if "source" in element.get("data", {}) and "target" in element.get("data", {})
        ]

    def build_component_table(self) -> List[Dict[str, str]]:
        """Build component table from component elements"""
        table_entries = []
        seen_components = set()

        # Group elements by KE
        ke_components = self._group_by_ke()

        for ke_id, components in ke_components.items():
            processes = components.get("processes", [])
            objects = components.get("objects", [])
            actions = components.get("actions", [])
            ke_name = self._get_ke_name(ke_id)  # NEW: resolve ke_name

            # Create entries for each process
            for process in processes:
                # Skip processes lacking iri (cleanup safeguard)
                if not process.get("iri"):
                    continue
                # Find associated objects and actions for this process
                process_objects = self._find_objects_for_process(process["id"], objects, actions)
                
                if process_objects:
                    for obj_data in process_objects:
                        entry = self._create_component_entry(ke_id, process, obj_data, ke_name)  # UPDATED
                        component_key = f"{ke_id}_{process['id']}_{obj_data.get('object_id', 'no_object')}"
                        
                        if component_key not in seen_components:
                            table_entries.append(entry)
                            seen_components.add(component_key)
                else:
                    # Process without object
                    entry = self._create_component_entry(ke_id, process, {}, ke_name)  # UPDATED
                    component_key = f"{ke_id}_{process['id']}_no_object"
                    
                    if component_key not in seen_components:
                        table_entries.append(entry)
                        seen_components.add(component_key)

        logger.info(f"Built component table with {len(table_entries)} entries")
        return table_entries

    def _group_by_ke(self) -> Dict[str, Dict[str, List[Dict[str, Any]]]]:
        """Group component elements by KE"""
        ke_components = {}

        # First, identify all KEs from edges - handle both URI formats
        for edge in self.component_edges:
            edge_data = edge.get("data", {})
            source = edge_data.get("source", "")
            target = edge_data.get("target", "")
            
            # KE→process edges (action edges)
            ke_id = self._normalize_ke_id(source)
            if ke_id and target.startswith("process_"):
                if ke_id not in ke_components:
                    ke_components[ke_id] = {"processes": [], "objects": [], "actions": []}

        # Add processes with their actions
        for edge in self.component_edges:
            edge_data = edge.get("data", {})
            source = edge_data.get("source", "")
            target = edge_data.get("target", "")
            label = edge_data.get("label", "")
            
            # KE→process edges
            ke_id = self._normalize_ke_id(source)
            if ke_id and target.startswith("process_") and ke_id in ke_components:
                # Find the process node
                process_node = None
                for node in self.component_nodes:
                    if node.get("data", {}).get("id") == target:
                        process_node = node
                        break
                
                if process_node:
                    node_data = process_node.get("data", {})
                    process_info = {
                        "id": target,
                        "name": node_data.get("process_name", node_data.get("label", "")),
                        "iri": node_data.get("process_iri", ""),
                        "action": label  # Action from KE→process edge
                    }
                    
                    # Check if this process already exists
                    existing_process = None
                    for p in ke_components[ke_id]["processes"]:
                        if p["id"] == target:
                            existing_process = p
                            break
                    
                    if not existing_process:
                        ke_components[ke_id]["processes"].append(process_info)

        # Add process→object relationships
        process_object_relationships = {}  # Maps process_id to list of objects
        
        for edge in self.component_edges:
            edge_data = edge.get("data", {})
            source = edge_data.get("source", "")
            target = edge_data.get("target", "")
            label = edge_data.get("label", "")
            
            if source.startswith("process_") and target.startswith("object_"):
                if source not in process_object_relationships:
                    process_object_relationships[source] = []
                
                # Find the object node
                object_node = None
                for node in self.component_nodes:
                    if node.get("data", {}).get("id") == target:
                        object_node = node
                        break
                
                if object_node:
                    node_data = object_node.get("data", {})
                    # Preserve both the full IRI and the shortened ID
                    full_object_iri = node_data.get("object_iri", "")
                    object_info = {
                        "object_id": target,
                        "object_name": node_data.get("object_name", node_data.get("label", "")),
                        "object_iri": full_object_iri,  # Keep full IRI for href
                        "object_iri_short": target.replace("object_", "") if target.startswith("object_") else target,  # Short ID for other uses
                        "relationship": label  # "has object" or similar
                    }
                    process_object_relationships[source].append(object_info)

        # Store the process-object relationships for later use
        self._process_object_relationships = process_object_relationships

        return ke_components

    def _normalize_ke_id(self, source: str) -> Optional[str]:
        """Convert KE URI to normalized aop.events_ format"""
        if source.startswith("aop.events_"):
            return source
        elif "aop.events/" in source:
            # Extract from URI format like https://identifiers.org/aop.events/756
            ke_number = source.split("aop.events/")[-1]
            return f"aop.events_{ke_number}"
        return None

    def _find_ke_for_node(self, node_id: str) -> Optional[str]:
        """Find the KE that a node belongs to"""
        for edge in self.component_edges:
            edge_data = edge.get("data", {})
            source = edge_data.get("source", "")
            target = edge_data.get("target", "")
            
            if target == node_id:
                return self._normalize_ke_id(source)
        return None

    def _find_ke_for_process(self, process_id: str) -> Optional[str]:
        """Find the KE that a process belongs to"""
        for edge in self.component_edges:
            edge_data = edge.get("data", {})
            source = edge_data.get("source", "")
            target = edge_data.get("target", "")
            
            if target == process_id:
                return self._normalize_ke_id(source)
        return None

    def _find_kes_for_object(self, object_id: str) -> List[str]:
        """Find all KEs connected to an object through processes"""
        kes = set()
        
        # Find processes connected to this object
        connected_processes = []
        for edge in self.component_edges:
            edge_data = edge.get("data", {})
            source = edge_data.get("source", "")
            target = edge_data.get("target", "")
            
            if target == object_id and source.startswith("process_"):
                connected_processes.append(source)
        
        # Find KEs for these processes
        for process_id in connected_processes:
            ke_id = self._find_ke_for_process(process_id)
            if ke_id:
                kes.add(ke_id)
        
        return list(kes)

    def _find_objects_for_process(self, process_id: str, objects: List[Dict[str, Any]], actions: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Find objects associated with a process"""
        # Use the stored process-object relationships
        if hasattr(self, '_process_object_relationships'):
            return self._process_object_relationships.get(process_id, [])
        return []

    def _create_component_entry(self, ke_id: str, process: Dict[str, Any], object_data: Dict[str, Any], ke_name: str = "") -> Dict[str, str]:
        """Create a component table entry"""
        # Extract KE number from ke_id
        ke_number = ke_id.replace("aop.events_", "") if ke_id.startswith("aop.events_") else ke_id
        
        # Extract process ID without prefix
        process_id = process["id"].replace("process_", "") if process["id"].startswith("process_") else process["id"]
        
        # Extract object ID 
        object_id = "N/A"
        object_iri = "N/A"
        if object_data.get("object_id"):
            object_id = object_data.get("object_iri_short", object_data["object_id"].replace("object_", ""))
            object_iri = object_data.get("object_iri", "N/A")  # Use full IRI for href

        return {
            "ke_id": ke_id,
            "ke_number": ke_number,
            "ke_uri": f"https://identifiers.org/aop.events/{ke_number}",
            "ke_name": ke_name or "N/A",
            "process_id": process_id,
            "process_name": process.get("name", ""),
            "process_iri": process.get("iri", ""),
            "object_id": object_id,
            "object_name": object_data.get("object_name", "N/A"),
            "object_iri": object_iri,  # Full IRI preserved for href
            "action": process.get("action", "N/A"),
            "relationship": object_data.get("relationship", "N/A"),
            "node_id": process["id"],
        }

    def _find_ke_and_action_for_process(self, process_id: str) -> Optional[Dict[str, str]]:
        """Find the KE and action for a process from KE process edges"""
        for edge in self.component_edges:
            edge_data = edge.get("data", {})
            source = edge_data.get("source", "")
            target = edge_data.get("target", "")
            label = edge_data.get("label", "")
            
            if target == process_id:
                ke_id = self._normalize_ke_id(source)
                if ke_id:
                    return {
                        "ke_id": ke_id,
                        "action": label  # This is the action from KE→process edge
                    }
        return None

    def _find_ke_for_process_object_relation(self, process_id: str) -> Optional[str]:
        """Find the KE for a process-object relationship"""
        # First find the KE that connects to this process
        ke_info = self._find_ke_and_action_for_process(process_id)
        return ke_info["ke_id"] if ke_info else None

    def _get_ke_name(self, ke_id: str) -> str:
        """Attempt to resolve the KE name (label) from provided elements"""
        # Possible KE identifiers in elements: raw normalized id or full URI
        candidates = {ke_id}
        if ke_id.startswith("aop.events_"):
            number = ke_id.replace("aop.events_", "")
            candidates.add(f"https://identifiers.org/aop.events/{number}")
        for element in self.component_elements:
            data = element.get("data", {})
            if data.get("id") in candidates:
                return data.get("label") or data.get("ke_label") or ""
        return ""
