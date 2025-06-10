from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, Union
from enum import Enum
import json
import uuid
from datetime import datetime

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

class DataSourceType(Enum):
    AOPWIKI = "aopwiki"
    QSPRPRED = "qsprpred"
    BGEE = "bgee"
    OPENTARGETS = "opentargets"
    CUSTOM_TABLE = "custom_table"
    MANUAL = "manual"

@dataclass
class AOPNode:
    id: str
    label: str
    node_type: NodeType
    source: DataSourceType
    properties: Dict[str, Any] = field(default_factory=dict)
    position: Optional[Dict[str, float]] = None
    visible: bool = True
    created_at: datetime = field(default_factory=datetime.now)
    
    def to_cytoscape(self) -> Dict[str, Any]:
        """Convert to Cytoscape.js format"""
        return {
            "data": {
                "id": self.id,
                "label": self.label,
                "type": self.node_type.value,
                "source": self.source.value,
                **self.properties
            },
            "classes": f"{self.node_type.value}-node",
            "position": self.position or {}
        }

@dataclass
class AOPEdge:
    id: str
    source: str
    target: str
    edge_type: EdgeType
    source_type: DataSourceType
    label: Optional[str] = None
    properties: Dict[str, Any] = field(default_factory=dict)
    visible: bool = True
    created_at: datetime = field(default_factory=datetime.now)
    
    def to_cytoscape(self) -> Dict[str, Any]:
        """Convert to Cytoscape.js format"""
        return {
            "data": {
                "id": self.id,
                "source": self.source,
                "target": self.target,
                "type": self.edge_type.value,
                "source_type": self.source_type.value,
                "label": self.label,
                **self.properties
            }
        }

@dataclass
class CustomDataTable:  # Still a placeholder, TODO decide how to upload/type in data
    id: str
    name: str
    description: str
    columns: List[Dict[str, str]]  # [{"name": "col1", "type": "string", "description": "..."}]
    data: List[Dict[str, Any]]
    mapping_config: Dict[str, Any]  # How to map this data to network
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)

@dataclass
class AOPNetwork:
    id: str
    name: str
    description: str
    nodes: Dict[str, AOPNode] = field(default_factory=dict)
    edges: Dict[str, AOPEdge] = field(default_factory=dict)
    custom_tables: Dict[str, CustomDataTable] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    
    def add_node(self, node: AOPNode) -> None:
        """Add node to network"""
        self.nodes[node.id] = node
        self.updated_at = datetime.now()
    
    def add_edge(self, edge: AOPEdge) -> None:
        """Add edge to network"""
        self.edges[edge.id] = edge
        self.updated_at = datetime.now()
    
    def add_custom_table(self, table: CustomDataTable) -> None:
        """Add custom data table"""
        self.custom_tables[table.id] = table
        self.updated_at = datetime.now()
    
    def to_cytoscape(self) -> List[Dict[str, Any]]:
        """Convert entire network to Cytoscape.js format"""
        elements = []
        
        # Add visible nodes
        for node in self.nodes.values():
            if node.visible:
                elements.append(node.to_cytoscape())
        
        # Add visible edges (only if both source and target are visible)
        for edge in self.edges.values():
            if (edge.visible and 
                edge.source in self.nodes and self.nodes[edge.source].visible and
                edge.target in self.nodes and self.nodes[edge.target].visible):
                elements.append(edge.to_cytoscape())
        
        return elements
    
    def get_nodes_by_type(self, node_type: NodeType) -> List[AOPNode]:
        """Get all nodes of a specific type"""
        return [node for node in self.nodes.values() if node.node_type == node_type]
    
    def get_nodes_by_source(self, source: DataSourceType) -> List[AOPNode]:
        """Get all nodes from a specific data source"""
        return [node for node in self.nodes.values() if node.source == source]
