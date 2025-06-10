import json
import pandas as pd
from typing import Dict, List, Optional, Any
from models.aop_data_model import *
import uuid
from datetime import datetime
import os

class AOPNetworkService:
    def __init__(self):
        self.networks: Dict[str, AOPNetwork] = {}
        self.current_network_id: Optional[str] = None
    
    def create_network(self, name: str, description: str = "") -> str:
        """Create a new AOP network"""
        network_id = str(uuid.uuid4())
        network = AOPNetwork(
            id=network_id,
            name=name,
            description=description
        )
        self.networks[network_id] = network
        self.current_network_id = network_id
        return network_id
    
    def get_current_network(self) -> Optional[AOPNetwork]:
        """Get the currently active network"""
        if self.current_network_id:
            return self.networks.get(self.current_network_id)
        return None
    
    def load_aopwiki_data(self, mie_query: str) -> List[Dict[str, Any]]:
        """Load data from AOP Wiki and convert to network nodes/edges"""
        network = self.get_current_network()
        if not network:
            raise ValueError("No active network")
        
        # Parse MIE query and fetch from AOP Wiki
        # This would use your existing SPARQL query logic
        elements = self._fetch_aopwiki_sparql(mie_query)
        
        for element in elements:
            if 'source' in element['data'] and 'target' in element['data']:
                # It's an edge
                edge = AOPEdge(
                    id=element['data']['id'],
                    source=element['data']['source'],
                    target=element['data']['target'],
                    edge_type=EdgeType.KER,
                    source_type=DataSourceType.AOPWIKI,
                    label=element['data'].get('ker_label'),
                    properties=element['data']
                )
                network.add_edge(edge)
            else:
                # It's a node
                node_type = self._determine_node_type(element['data'])
                node = AOPNode(
                    id=element['data']['id'],
                    label=element['data']['label'],
                    node_type=node_type,
                    source=DataSourceType.AOPWIKI,
                    properties=element['data']
                )
                network.add_node(node)
        
        return network.to_cytoscape()
    
    def add_bgee_data(self, genes: List[str]) -> Dict[str, Any]:
        """Add Bgee gene expression data to network"""
        network = self.get_current_network()
        if not network:
            raise ValueError("No active network")
        
        # Fetch Bgee data (using your existing logic)
        bgee_data = self._fetch_bgee_data(genes)
        
        # Create organ nodes and expression edges
        organ_nodes_created = set()
        
        for gene_id, gene_data in bgee_data.items():
            if 'Bgee_gene_expression_levels' in gene_data:
                for expression in gene_data['Bgee_gene_expression_levels']:
                    organ_id = f"organ_{expression.get('anatomical_entity_id', 'unknown')}"
                    organ_name = expression.get('anatomical_entity_name', 'Unknown Organ')
                    
                    # Create organ node if not exists
                    if organ_id not in organ_nodes_created:
                        organ_node = AOPNode(
                            id=organ_id,
                            label=organ_name,
                            node_type=NodeType.ORGAN,
                            source=DataSourceType.BGEE,
                            properties={
                                'anatomical_entity_id': expression.get('anatomical_entity_id'),
                                'anatomical_entity_name': organ_name
                            }
                        )
                        network.add_node(organ_node)
                        organ_nodes_created.add(organ_id)
                    
                    # Create expression edge from gene to organ
                    edge_id = f"expression_{gene_id}_{organ_id}"
                    expression_edge = AOPEdge(
                        id=edge_id,
                        source=gene_id,
                        target=organ_id,
                        edge_type=EdgeType.EXPRESSION_IN,
                        source_type=DataSourceType.BGEE,
                        label=f"Expression: {expression.get('expression_level', 'N/A')}",
                        properties={
                            'expression_level': expression.get('expression_level'),
                            'confidence_level': expression.get('confidence_level_name'),
                            'developmental_stage': expression.get('developmental_stage_name')
                        }
                    )
                    network.add_edge(expression_edge)
        
        return {
            'nodes_added': len(organ_nodes_created),
            'edges_added': len([e for e in network.edges.values() if e.edge_type == EdgeType.EXPRESSION_IN])
        }
    
    def create_custom_table(self, table_data: Dict[str, Any]) -> str: # Still a placeholder, TODO
        """Create a custom data table"""
        network = self.get_current_network()
        if not network:
            raise ValueError("No active network")
        
        table = CustomDataTable(
            id=str(uuid.uuid4()),
            name=table_data['name'],
            description=table_data.get('description', ''),
            columns=table_data['columns'],
            data=table_data['data'],
            mapping_config=table_data.get('mapping_config', {})
        )
        
        network.add_custom_table(table)
        return table.id
    
    def apply_custom_table_to_network(self, table_id: str, mapping_config: Dict[str, Any]) -> Dict[str, Any]:
        """Apply custom table data to network based on mapping configuration"""
        network = self.get_current_network()
        if not network or table_id not in network.custom_tables:
            raise ValueError("Table not found")
        
        table = network.custom_tables[table_id]
        results = {'nodes_created': 0, 'edges_created': 0, 'properties_updated': 0}
        
        for row in table.data:
            if mapping_config.get('create_nodes'):
                # Create nodes based on mapping
                node_config = mapping_config['create_nodes']
                node_id = self._generate_node_id(row, node_config)
                
                if node_id not in network.nodes:
                    node = AOPNode(
                        id=node_id,
                        label=row.get(node_config['label_column'], node_id),
                        node_type=NodeType(node_config['node_type']),
                        source=DataSourceType.CUSTOM_TABLE,
                        properties=self._extract_properties(row, node_config.get('property_columns', []))
                    )
                    network.add_node(node)
                    results['nodes_created'] += 1
            
            if mapping_config.get('create_edges'):
                # Create edges based on mapping
                edge_config = mapping_config['create_edges']
                source_id = row.get(edge_config['source_column'])
                target_id = row.get(edge_config['target_column'])
                
                if source_id and target_id:
                    edge_id = f"{source_id}_{target_id}_{table_id}"
                    edge = AOPEdge(
                        id=edge_id,
                        source=source_id,
                        target=target_id,
                        edge_type=EdgeType(edge_config.get('edge_type', 'custom')),
                        source_type=DataSourceType.CUSTOM_TABLE,
                        label=row.get(edge_config.get('label_column')),
                        properties=self._extract_properties(row, edge_config.get('property_columns', []))
                    )
                    network.add_edge(edge)
                    results['edges_created'] += 1
            
            if mapping_config.get('update_properties'):
                # Update existing node properties
                prop_config = mapping_config['update_properties']
                node_id = row.get(prop_config['node_id_column'])
                
                if node_id in network.nodes:
                    node = network.nodes[node_id]
                    for col in prop_config.get('property_columns', []):
                        if col in row:
                            node.properties[col] = row[col]
                    results['properties_updated'] += 1
        
        return results
    
    def _fetch_aopwiki_sparql(self, mie_query: str) -> List[Dict[str, Any]]:
        """Fetch data from AOP Wiki SPARQL endpoint"""
        # Use your existing SPARQL logic here
        pass
    
    def _fetch_bgee_data(self, genes: List[str]) -> Dict[str, Any]:
        """Fetch Bgee gene expression data"""
        # Use your existing Bgee fetching logic here
        pass
    
    def _determine_node_type(self, data: Dict[str, Any]) -> NodeType:
        """Determine node type from AOP Wiki data"""
        if data.get('is_mie'):
            return NodeType.MIE
        elif data.get('is_ao'):
            return NodeType.AO
        else:
            return NodeType.KE
    
    def _generate_node_id(self, row: Dict[str, Any], config: Dict[str, Any]) -> str:
        """Generate node ID from row data"""
        if 'id_column' in config:
            return str(row[config['id_column']])
        return str(uuid.uuid4())
    
    def _extract_properties(self, row: Dict[str, Any], property_columns: List[str]) -> Dict[str, Any]:
        """Extract properties from row data"""
        return {col: row[col] for col in property_columns if col in row}

# Global service instance
aop_service = AOPNetworkService()
