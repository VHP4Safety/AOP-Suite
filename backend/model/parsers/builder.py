from typing import Dict, List, Any, Optional
import logging


from backend.model.schemas.base import (
    AOPNetwork,
    AOPInfo,
    AOPKeyEvent,
    KeyEventRelationship,
)
from backend.model.schemas.associations import (
    GeneAssociation,
    CompoundAssociation,
    ComponentAssociation,
    OrganAssociation,
    GeneExpressionAssociation,
)

from backend.model.constants import NodeType

from backend.model.cytoscape.elements import CytoscapeNode, CytoscapeEdge

logger = logging.getLogger(__name__)

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

            # Process organ associations for both upstream and downstream KEs
            for ke in ["upstream", "downstream"]:
                ke_uri = binding.get(f"KE_{ke}", {}).get("value", "")
                organ_uri = binding.get(f"KE_{ke}_organ", {}).get("value", "")
                organ_name = binding.get(f"KE_{ke}_organ_name", {}).get("value", "")
                if ke_uri and organ_uri:
                    self._process_organ_association(ke_uri, organ_uri, organ_name)
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

    def _process_organ_association(self, ke_uri: str, organ_uri: str, organ_name: str):
        """Process an organ association"""
        if not ke_uri or not organ_uri:
            return

        organ_node = CytoscapeNode(
            id=organ_uri,
            label=organ_name if organ_name else organ_uri.split("/")[-1],
            node_type=NodeType.ORGAN.value,
            classes="organ-node",
            properties={"anatomical_id": organ_uri, "anatomical_name": organ_name},
        )

        edge = CytoscapeEdge(
            id=f"{ke_uri}_{organ_uri}",
            source=ke_uri,
            target=organ_uri,
            label="associated with",
            properties={"type": "associated_with"},
        )

        association = OrganAssociation(
            ke_uri=ke_uri, organ_data=organ_node, edge_data=edge
        )

        self.network.add_organ_association(association)

    def add_gene_associations(
        self, gene_bindings: List[Dict], include_proteins: bool = True
    ):
        """Add gene associations from SPARQL bindings"""
        for binding in gene_bindings:
            try:
                ke_uri = binding.get("ke", {}).get("value", "")
                ensembl_id = binding.get("ensembl", {}).get("value", "")

                if include_proteins:
                    uniprot_id = binding.get("uniprot", {}).get("value", "")
                else:
                    uniprot_id = None

                if ke_uri and ensembl_id:
                    gene_assoc = GeneAssociation(
                        ke_uri=ke_uri,
                        ensembl_id=ensembl_id,
                        uniprot_id=uniprot_id if include_proteins else None,
                    )
                    self.network.gene_associations.append(gene_assoc)

            except Exception as e:
                logger.warning(f"Failed to process gene binding: {e}")
                continue

    def add_compound_associations(self, compound_sparql_results: List[Dict[str, Any]]):
        """Add compound associations from compound SPARQL results"""
        for result in compound_sparql_results:
            aop_uri = result.get("aop", {}).get("value", "")
            chemical_uri = result.get("chemical", {}).get("value", "")
            pubchem_compound = result.get("pubchem_compound", {}).get("value", "")
            compound_name = result.get("compound_name", {}).get("value", "")
            cid = result.get("cid", {}).get("value", "")
            mie_uri = result.get("mie", {}).get("value", "")

            if aop_uri and chemical_uri and pubchem_compound:
                association = CompoundAssociation(
                    aop_uri=aop_uri,
                    mie_uri=mie_uri,
                    chemical_uri=chemical_uri,
                    chemical_label=compound_name,
                    pubchem_compound=pubchem_compound,
                    compound_name=compound_name,
                    cas_id=cid if cid else None,
                )

                self.network.add_compound_association(association)

    def add_component_associations(
        self, component_sparql_results: List[Dict[str, Any]]
    ):
        """Add component associations from compound SPARQL results"""
        for result in component_sparql_results:
            process_iri = result.get("process", {}).get("value", "")
            if not process_iri:
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

    def add_gene_expression_association(
        self, gene_expression_results: List[Dict[str, Any]]
    ):
        """Add bgee gene expression associations from biodatafuse query results"""
        for result in gene_expression_results:
            ensembl_id = result.get("ensembl_id", {}).get("value", "")
            if not ensembl_id:
                continue
            association = GeneExpressionAssociation(
                ensembl_id=ensembl_id,
                anatomical_id=result.get("anatomical_entity_id", {}).get("value", ""),
                anatomical_name=result.get("anatomical_entity_name", {}).get(
                    "value", ""
                ),
                expression_level=result.get("expression_level", {}).get("value", ""),
                confidence_id=result.get("confidence_level_id", {}).get("value", ""),
                confidence_level_name=result.get("confidence_level_name", {}).get(
                    "value", ""
                ),
                developmental_id=result.get("developmental_stage_id", {}).get(
                    "value", ""
                ),
                developmental_stage_name=result.get("developmental_stage_name", {}).get(
                    "value", ""
                ),
                expr=result.get("expr", {}).get("value", ""),
            )
            self.network.add_gene_expression_association(association)

    def add_organ_associations_from_sparql(self, sparql_results: List[Dict[str, Any]]):
        """Add organ associations from SPARQL results"""
        for result in sparql_results:
            ke_uri = result.get("ke", {}).get("value", "")
            organ_uri = result.get("organ", {}).get("value", "")
            organ_name = result.get("organ_name", {}).get("value", "")

            if ke_uri and organ_uri:
                organ_node = CytoscapeNode(
                    id=f"organ_{organ_uri.split('/')[-1] if '/' in organ_uri else organ_uri}",
                    label=organ_name if organ_name else organ_uri.split("/")[-1],
                    node_type=NodeType.ORGAN.value,
                    classes="organ-node",
                    properties={
                        "anatomical_id": (
                            organ_uri.split("/")[-1] if "/" in organ_uri else organ_uri
                        ),
                        "anatomical_name": organ_name,
                        "organ_uri": organ_uri,
                    },
                )

                edge = CytoscapeEdge(
                    id=f"{ke_uri}_{organ_node.id}",
                    source=ke_uri,
                    target=organ_node.id,
                    label="associated with",
                    properties={
                        "type": "associated_with",
                        "edge_type": "ke_organ_association",
                    },
                )

                association = OrganAssociation(
                    ke_uri=ke_uri, organ_data=organ_node, edge_data=edge
                )

                self.network.add_organ_association(association)

    def build(self) -> AOPNetwork:
        """Return the constructed network"""
        return self.network
