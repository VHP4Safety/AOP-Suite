from typing import Dict, List, Any
from backend.model.cytoscape.elements import CytoscapeNode, CytoscapeEdge
import logging

logger = logging.getLogger(__name__)

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

    def get_organ_nodes(self) -> List[CytoscapeNode]:
        """Extract organ nodes from Cytoscape elements"""
        organ_nodes = []

        for element in self.elements:
            if element.get("group") == "nodes":
                node_data = element.get("data", {})
                node_type = node_data.get("type", "").lower()

                if (
                    node_type == "organ"
                    or "anatomical_id" in node_data
                    or "anatomical_name" in node_data
                    or node_data.get("id", "").startswith(
                        "http://purl.obolibrary.org/obo/UBERON_"
                    )
                ):

                    organ_node = CytoscapeNode(
                        id=node_data.get("id", ""),
                        label=node_data.get(
                            "label", node_data.get("anatomical_name", "")
                        ),
                        node_type="organ",
                        classes="organ-node",
                        properties={
                            "anatomical_id": node_data.get(
                                "anatomical_id", node_data.get("id", "")
                            ),
                            "anatomical_name": node_data.get(
                                "anatomical_name", node_data.get("label", "")
                            ),
                            "uberon_id": node_data.get(
                                "anatomical_id", node_data.get("id", "")
                            ),
                            "type": "organ",
                        },
                    )
                    organ_nodes.append(organ_node)

        return organ_nodes
