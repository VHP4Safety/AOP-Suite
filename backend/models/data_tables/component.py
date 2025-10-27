from typing import List, Dict, Any, Optional, Set
import logging

from backend.models.constants import NodeType, EdgeType

logger = logging.getLogger(__name__)


class ComponentTableBuilder:
    """Builds component table data from component elements - one row per KE"""

    def __init__(self, component_elements: List[Dict[str, Any]]):
        self.component_elements = component_elements
        self.nodes = [
            el for el in component_elements if "source" not in el.get("data", {})
        ]
        self.edges = [el for el in component_elements if "source" in el.get("data", {})]

        self.process_nodes = self._get_nodes_by_type("component_process")
        logger.debug(f"Found {len(self.process_nodes)} process nodes.")
        self.object_nodes = self._get_nodes_by_type("component_object")
        self.organ_nodes = self._get_organ_nodes()
        self.ke_nodes = self._get_ke_nodes()

    def _get_nodes_by_type(self, node_type: str) -> List[Dict[str, Any]]:
        """Get all nodes of a specific type"""
        return [
            element
            for element in self.nodes
            if element.get("classes", "") == node_type
        ]

    def _get_organ_nodes(self) -> List[Dict[str, Any]]:
        """Get all organ nodes (from components or other sources)"""
        organ_nodes = []
        for element in self.nodes:
            node_data = element.get("data", {})
            node_type = node_data.get("type", "")
            # Include organ nodes and component objects that are organs
            if (
                node_type == "organ"
                or "organ" in node_data.get("classes", "").lower()
                or any(
                    substring in node_data.get("id", "")
                    for substring in ["FMA", "UBERON"]
                )
            ):
                organ_nodes.append(element)
        return organ_nodes

    def _get_ke_nodes(self) -> List[Dict[str, Any]]:
        """Get all KE nodes"""
        return [
            element
            for element in self.nodes
            if element.get("data", {}).get("id", "").startswith("aop.events")
            or element.get("data", {}).get("type") in ("key_event", "mie", "ao")
        ]

    def _find_node_by_id(self, node_id: str) -> Optional[Dict[str, Any]]:
        """Find a node by its ID"""
        for node in self.nodes:
            if node.get("data", {}).get("id") == node_id:
                return node
        return None

    def _normalize_ke_id(self, source: str) -> Optional[str]:
        """Convert KE URI to normalized aop.events_ format"""
        if not source:
            return None
        if source.startswith("aop.events_"):
            return source
        elif "aop.events/" in source:
            ke_number = source.split("aop.events/")[-1]
            return f"aop.events_{ke_number}"
        elif source.startswith("aop.events"):
            return source
        return None

    def _get_ke_action_processes(self, ke_id: str) -> List[Dict[str, Any]]:
        """Get all action-process pairs for a KE using EdgeType component actions"""
        action_processes = []
        # edges that have this KE as source
        ke_edges = []
        for edge in self.edges:
            edge_data = edge.get("data", {})
            source = edge_data.get("source", "")
            normalized_source = self._normalize_ke_id(source)
            if normalized_source == ke_id:
                ke_edges.append(edge_data)
        # Now filter for process edges
        for edge in self.edges:
            edge_data = edge.get("data", {})
            source = edge_data.get("source", "")
            target = edge_data.get("target", "")
            normalized_source = self._normalize_ke_id(source)
            
            # Check if source matches and target is a process
            if normalized_source == ke_id and target.startswith("process_"):
                edge_label = edge_data.get("label", "")
                edge_type = edge_data.get("type", "")
                process_node = self._find_node_by_id(target)
                if process_node:
                    process_data = process_node.get("data", {})
                    # Use edge_label, fall back to edge_type, fall back to "has_process"
                    action_label = edge_label or edge_type or "has_process"
                    
                    action_processes.append({
                        "action": action_label,
                        "process_id": target,
                        "process_name": process_data.get("process_name", process_data.get("label", "")),
                        "process_iri": process_data.get("process_iri", "")
                    })
                    
                else:
                    logger.warning(f"Process node not found: {target}")
        
        
        return action_processes

    def _get_ke_organs(self, ke_id: str) -> List[Dict[str, Any]]:
        """Get all organs linked to a KE via any edge"""
        organs = []
        organ_ids_seen: Set[str] = set()

        for edge in self.edges:
            edge_data = edge.get("data", {})
            source = edge_data.get("source", "")
            target = edge_data.get("target", "")

            # Check KE -> Organ edges
            if self._normalize_ke_id(source) == ke_id:
                organ_node = self._find_node_by_id(target)
                if organ_node and self._is_organ_node(organ_node):
                    organ_data = organ_node.get("data", {})
                    organ_id = organ_data.get("id", "")
                    if organ_id not in organ_ids_seen:
                        organs.append(
                            {
                                "organ_id": organ_id,
                                "organ_name": organ_data.get("anatomical_name")
                                or organ_data.get("object_name")
                                or organ_data.get("label", ""),
                                "organ_iri": organ_data.get("anatomical_id")
                                or organ_data.get("object_iri", ""),
                            }
                        )
                        organ_ids_seen.add(organ_id)

            # Check Organ -> KE edges (reverse direction)
            elif self._normalize_ke_id(target) == ke_id:
                organ_node = self._find_node_by_id(source)
                if organ_node and self._is_organ_node(organ_node):
                    organ_data = organ_node.get("data", {})
                    organ_id = organ_data.get("id", "")
                    if organ_id not in organ_ids_seen:
                        organs.append(
                            {
                                "organ_id": organ_id,
                                "organ_name": organ_data.get("anatomical_name")
                                or organ_data.get("object_name")
                                or organ_data.get("label", ""),
                                "organ_iri": organ_data.get("anatomical_id")
                                or organ_data.get("object_iri", ""),
                            }
                        )
                        organ_ids_seen.add(organ_id)

        return organs

    def _is_organ_node(self, node: Dict[str, Any]) -> bool:
        """Check if a node represents an organ"""
        node_data = node.get("data", {})
        node_type = node_data.get("type", "")
        node_classes = node_data.get("classes", "")
        node_id = node_data.get("id", "")

        return (
            node_type == "organ"
            or "organ" in node_classes.lower()
            or any(substring in node_id for substring in ["FMA", "UBERON"])
            or node_data.get("anatomical_name") is not None
        )

    def build_component_table(self) -> List[Dict[str, Any]]:
        """Build component table with one row per Key Event that has component associations"""
        table_entries = []

        for ke_node in self.ke_nodes:
            ke_data = ke_node.get("data", {})
            ke_id = self._normalize_ke_id(ke_data.get("id", ""))

            if not ke_id:
                continue

            # Get action-processes and organs for this KE
            action_processes = self._get_ke_action_processes(ke_id)
            organs = self._get_ke_organs(ke_id)

            # Only include KEs that have component associations (either processes or organs)
            if not action_processes and not organs:
                continue

            ke_name = ke_data.get("label", ke_data.get("ke_label", ""))
            ke_number = (
                ke_id.replace("aop.events_", "")
                if ke_id.startswith("aop.events_")
                else ke_id
            )

            # Create table entry
            entry = {
                "ke_id": ke_id,
                "ke_number": ke_number,
                "ke_uri": f"https://identifiers.org/aop.events/{ke_number}",
                "ke_name": ke_name or "N/A",
                "action_processes": action_processes,
                "organs": organs,
                "action_process_count": len(action_processes),
                "organ_count": len(organs),
            }

            table_entries.append(entry)
        return table_entries
