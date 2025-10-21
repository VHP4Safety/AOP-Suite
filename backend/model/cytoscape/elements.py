from dataclasses import dataclass
from typing import Dict, Any, Optional
import logging

logger = logging.getLogger(__name__)

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

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary format for Cytoscape"""
        return {
            "id": self.id,
            "source": self.source,
            "target": self.target,
            "label": self.label,
            **self.properties,
        }

    def is_gene_relationship(self) -> bool:
        """Check if this is a gene-related relationship"""
        return self.label in ["translates to", "part of"]


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

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary format for Cytoscape"""
        return {
            "id": self.id,
            "label": self.label,
            "type": self.node_type,
            **self.properties,
        }

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

    def is_organ_node(self) -> bool:
        """Check if this is an organ node"""
        return (
            self.classes == "organ-node"
            or self.node_type == "organ"
            or self.id.startswith("organ_")
        )
