from typing import List, Dict, Any, Optional
import logging
from dataclasses import dataclass

from backend.model.parsers.cytoscape import CytoscapeNetworkParser
from backend.model.cytoscape.elements import CytoscapeNode, CytoscapeEdge

logger = logging.getLogger(__name__)


@dataclass
class AOPRelationshipEntry:
    """Represents an AOP relationship entry for the table"""

    source_node: "CytoscapeNode"
    target_node: "CytoscapeNode"
    edge: "CytoscapeEdge"

    def to_table_entry(self) -> Dict[str, str]:
        """Convert to AOP table entry format"""
        source_aop_info = self._extract_node_aop_info(self.source_node)
        target_aop_info = self._extract_node_aop_info(self.target_node)

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

        aop_ids = []
        for aop_uri in aop_uris:
            if aop_uri and "aop/" in aop_uri:
                aop_id = aop_uri.split("aop/")[-1]
                aop_ids.append(f"AOP:{aop_id}")

        return {"aop_ids": aop_ids, "aop_titles": aop_titles}

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

        logger.info(
            f"Built AOP table with {len(table_entries)} entries using data model"
        )
        return table_entries

    def _extract_aop_relationships(self) -> List[AOPRelationshipEntry]:
        """Extract AOP relationships from parsed network"""
        relationships = []

        for edge in self.parser.edges:
            if edge.properties.get("ker_label") and edge.properties.get("curie"):

                source_node = self._find_node_by_id(edge.source)
                target_node = self._find_node_by_id(edge.target)

                if source_node and target_node:
                    relationship = AOPRelationshipEntry(
                        source_node=source_node, target_node=target_node, edge=edge
                    )
                    relationships.append(relationship)

        return relationships

    def _extract_disconnected_nodes(self) -> List[Dict[str, str]]:
        """Extract disconnected nodes"""
        connected_node_ids = set()

        for edge in self.parser.edges:
            connected_node_ids.add(edge.source)
            connected_node_ids.add(edge.target)

        disconnected_entries = []
        for node in self.parser.nodes:
            if node.id not in connected_node_ids:
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

    def _find_node_by_id(self, node_id: str) -> Optional["CytoscapeNode"]:
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

        aop_ids = []
        for aop_uri in aop_uris:
            if aop_uri and "aop/" in aop_uri:
                aop_id = aop_uri.split("aop/")[-1]
                aop_ids.append(f"AOP:{aop_id}")

        aop_string = ",".join(sorted(aop_ids)) if aop_ids else "N/A"
        aop_titles_string = "; ".join(sorted(aop_titles)) if aop_titles else "N/A"

        return {"aop_string": aop_string, "aop_titles_string": aop_titles_string}
