from typing import Dict, List, Any
from backend.models.cytoscape.elements import CytoscapeNode, CytoscapeEdge
import logging
from backend.models.constants import NodeType, EdgeType

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
    
    def get_nodes_by_type(self, node_type: NodeType) -> List[CytoscapeNode]:
        """Get nodes of a specific type"""
        return [node for node in self.nodes if node.is_instance_of(node_type)]

    def get_edges_by_type(self, edge_type: EdgeType) -> List[CytoscapeEdge]:
        """Get edges of a specific type"""
        return [edge for edge in self.edges if edge.is_instance_of(edge_type)]
