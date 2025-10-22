from typing import List, Dict, Any, Optional
import logging

logger = logging.getLogger(__name__)

class ComponentTableBuilder:
    """Builds component table data from component elements"""

    def __init__(self, component_elements: List[Dict[str, Any]]):
        self.component_elements = component_elements
        self.component_nodes = self._get_component_nodes()
        self.component_edges = self._get_component_edges()

    def _get_component_nodes(self) -> List[Dict[str, Any]]:
        """Get all component nodes (process and object nodes)"""
        return [
            element
            for element in self.component_elements
            if element.get("data", {}).get("type")
            in ("component_process", "component_object")
        ]

    def _get_component_edges(self) -> List[Dict[str, Any]]:
        """Get all component edges"""
        return [
            element
            for element in self.component_elements
            if "source" in element.get("data", {})
            and "target" in element.get("data", {})
        ]

    def build_component_table(self) -> List[Dict[str, str]]:
        """Build component table from component elements"""
        table_entries = []
        seen_components = set()

        ke_components = self._group_by_ke()

        for ke_id, components in ke_components.items():
            processes = components.get("processes", [])
            objects = components.get("objects", [])
            actions = components.get("actions", [])
            ke_name = self._get_ke_name(ke_id)

            for process in processes:
                if not process.get("iri"):
                    continue
                process_objects = self._find_objects_for_process(
                    process["id"], objects, actions
                )

                if process_objects:
                    for obj_data in process_objects:
                        entry = self._create_component_entry(
                            ke_id, process, obj_data, ke_name
                        )
                        component_key = f"{ke_id}_{process['id']}_{obj_data.get('object_id', 'no_object')}"

                        if component_key not in seen_components:
                            table_entries.append(entry)
                            seen_components.add(component_key)
                else:
                    entry = self._create_component_entry(ke_id, process, {}, ke_name)
                    component_key = f"{ke_id}_{process['id']}_no_object"

                    if component_key not in seen_components:
                        table_entries.append(entry)
                        seen_components.add(component_key)

        logger.info(f"Built component table with {len(table_entries)} entries")
        return table_entries

    def _group_by_ke(self) -> Dict[str, Dict[str, List[Dict[str, Any]]]]:
        """Group component elements by KE"""
        ke_components = {}

        for edge in self.component_edges:
            edge_data = edge.get("data", {})
            source = edge_data.get("source", "")
            target = edge_data.get("target", "")

            ke_id = self._normalize_ke_id(source)
            if ke_id and target.startswith("process_"):
                if ke_id not in ke_components:
                    ke_components[ke_id] = {
                        "processes": [],
                        "objects": [],
                        "actions": [],
                    }

        for edge in self.component_edges:
            edge_data = edge.get("data", {})
            source = edge_data.get("source", "")
            target = edge_data.get("target", "")
            label = edge_data.get("label", "")

            ke_id = self._normalize_ke_id(source)
            if ke_id and target.startswith("process_") and ke_id in ke_components:
                process_node = None
                for node in self.component_nodes:
                    if node.get("data", {}).get("id") == target:
                        process_node = node
                        break

                if process_node:
                    node_data = process_node.get("data", {})
                    process_info = {
                        "id": target,
                        "name": node_data.get(
                            "process_name", node_data.get("label", "")
                        ),
                        "iri": node_data.get("process_iri", ""),
                        "action": label,
                    }

                    existing_process = None
                    for p in ke_components[ke_id]["processes"]:
                        if p["id"] == target:
                            existing_process = p
                            break

                    if not existing_process:
                        ke_components[ke_id]["processes"].append(process_info)

        process_object_relationships = {}

        for edge in self.component_edges:
            edge_data = edge.get("data", {})
            source = edge_data.get("source", "")
            target = edge_data.get("target", "")
            label = edge_data.get("label", "")

            if source.startswith("process_") and target.startswith("object_"):
                if source not in process_object_relationships:
                    process_object_relationships[source] = []

                object_node = None
                for node in self.component_nodes:
                    if node.get("data", {}).get("id") == target:
                        object_node = node
                        break

                if object_node:
                    node_data = object_node.get("data", {})
                    full_object_iri = node_data.get("object_iri", "")
                    object_info = {
                        "object_id": target,
                        "object_name": node_data.get(
                            "object_name", node_data.get("label", "")
                        ),
                        "object_iri": full_object_iri,
                        "object_iri_short": (
                            target.replace("object_", "")
                            if target.startswith("object_")
                            else target
                        ),
                        "relationship": label,
                    }
                    process_object_relationships[source].append(object_info)

        self._process_object_relationships = process_object_relationships

        return ke_components

    def _normalize_ke_id(self, source: str) -> Optional[str]:
        """Convert KE URI to normalized aop.events_ format"""
        if source.startswith("aop.events_"):
            return source
        elif "aop.events/" in source:
            ke_number = source.split("aop.events/")[-1]
            return f"aop.events_{ke_number}"
        return None

    def _find_objects_for_process(
        self,
        process_id: str,
        objects: List[Dict[str, Any]],
        actions: List[Dict[str, Any]],
    ) -> List[Dict[str, Any]]:
        """Find objects associated with a process"""
        if hasattr(self, "_process_object_relationships"):
            return self._process_object_relationships.get(process_id, [])
        return []

    def _create_component_entry(
        self,
        ke_id: str,
        process: Dict[str, Any],
        object_data: Dict[str, Any],
        ke_name: str = "",
    ) -> Dict[str, str]:
        """Create a component table entry"""
        ke_number = (
            ke_id.replace("aop.events_", "")
            if ke_id.startswith("aop.events_")
            else ke_id
        )

        process_id = (
            process["id"].replace("process_", "")
            if process["id"].startswith("process_")
            else process["id"]
        )

        object_id = "N/A"
        object_iri = "N/A"
        if object_data.get("object_id"):
            object_id = object_data.get(
                "object_iri_short", object_data["object_id"].replace("object_", "")
            )
            object_iri = object_data.get("object_iri", "N/A")

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
            "object_iri": object_iri,
            "action": process.get("action", "N/A"),
            "relationship": object_data.get("relationship", "N/A"),
            "node_id": process["id"],
        }

    def _get_ke_name(self, ke_id: str) -> str:
        """Attempt to resolve the KE name (label) from provided elements"""
        candidates = {ke_id}
        if ke_id.startswith("aop.events_"):
            number = ke_id.replace("aop.events_", "")
            candidates.add(f"https://identifiers.org/aop.events/{number}")
        for element in self.component_elements:
            data = element.get("data", {})
            if data.get("id") in candidates:
                return data.get("label") or data.get("ke_label") or ""
        return ""
