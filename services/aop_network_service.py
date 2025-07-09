import json
import pandas as pd
from typing import Dict, List, Optional, Any
from models.aop_data_model import *
import uuid
from datetime import datetime
import os
import traceback

class AOPNetworkService:
    def __init__(self):
        self.networks: Dict[str, AOPNetwork] = {}
        self.current_network_id: Optional[str] = None
        # Initialize with a default network for the main application
        self.initialize_default_network()
    
    def initialize_default_network(self):
        """Initialize a default network for the main application"""
        default_id = self.create_network("Main AOP Network", "Primary network for AOP analysis")
        self.current_network_id = default_id
        return default_id
    
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
    
    def load_aopwiki_data(self, elements_data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Load data from AOP Wiki and convert to network nodes/edges using proper data models"""
        network = self.get_current_network()
        if not network:
            raise ValueError("No active network")
        
        # Process elements using proper data model classes
        for element in elements_data:
            element_data = element.get('data', {})
            
            # Check if it's an edge (has source and target)
            if 'source' in element_data and 'target' in element_data:
                edge = AOPEdge(
                    id=element_data.get('id', str(uuid.uuid4())),
                    source=element_data['source'],
                    target=element_data['target'],
                    edge_type=EdgeType.KER,
                    source_type=DataSourceType.AOPWIKI,
                    label=element_data.get('ker_label'),
                    properties=element_data
                )
                network.add_edge(edge)
            else:
                # It's a node
                node_type = self._determine_node_type(element_data)
                node = AOPNode(
                    id=element_data.get('id', str(uuid.uuid4())),
                    label=element_data.get('label', 'Unknown'),
                    node_type=node_type,
                    source=DataSourceType.AOPWIKI,
                    properties=element_data
                )
                network.add_node(node)
        
        # Use the proper data model method to convert to Cytoscape format
        return network.to_cytoscape()
    
    def add_gene_data(self, gene_elements: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Add gene data (UniProt/Ensembl) to network using proper data models"""
        network = self.get_current_network()
        if not network:
            raise ValueError("No active network")
        
        nodes_added = 0
        edges_added = 0
        
        for element in gene_elements:
            element_data = element.get('data', {})
            
            if 'source' in element_data and 'target' in element_data:
                # It's an edge
                edge_type = EdgeType.PART_OF if element_data.get('label') == 'part of' else EdgeType.TRANSLATES_TO
                edge = AOPEdge(
                    id=element_data['id'],
                    source=element_data['source'],
                    target=element_data['target'],
                    edge_type=edge_type,
                    source_type=DataSourceType.MANUAL,
                    label=element_data.get('label'),
                    properties=element_data
                )
                network.add_edge(edge)
                edges_added += 1
            else:
                # It's a node
                node_type = NodeType.UNIPROT if element_data.get('type') == 'uniprot' else NodeType.ENSEMBL
                node = AOPNode(
                    id=element_data['id'],
                    label=element_data.get('label', element_data['id']),
                    node_type=node_type,
                    source=DataSourceType.MANUAL,
                    properties=element_data
                )
                network.add_node(node)
                nodes_added += 1
        
        return {'nodes_added': nodes_added, 'edges_added': edges_added}
    
    def add_bgee_data(self, genes: List[str]) -> Dict[str, Any]:
        """Add Bgee gene expression data to network using proper data models"""
        network = self.get_current_network()
        if not network:
            raise ValueError("No active network")
        
        # Fetch Bgee data (using your existing logic)
        bgee_data = self._fetch_bgee_data(genes)
        
        # Create organ nodes and expression edges using proper data models
        organ_nodes_created = set()
        edges_created = 0
        
        for gene_id, gene_data in bgee_data.items():
            if 'Bgee_gene_expression_levels' in gene_data:
                for expression in gene_data['Bgee_gene_expression_levels']:
                    organ_id = f"organ_{expression.get('anatomical_entity_id', 'unknown')}"
                    organ_name = expression.get('anatomical_entity_name', 'Unknown Organ')
                    
                    # Create organ node if not exists
                    if organ_id not in organ_nodes_created and organ_id not in network.nodes:
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
                    if edge_id not in network.edges:
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
                        edges_created += 1
        
        return {
            'nodes_added': len(organ_nodes_created),
            'edges_added': edges_created
        }
    
    def add_opentargets_data(self, ot_data: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Add OpenTargets compound-disease data using proper data models"""
        network = self.get_current_network()
        if not network:
            return {"error": "No active network"}
            
        nodes_added = 0
        edges_added = 0
        
        try:
            for entry in ot_data:
                # Create disease nodes
                disease_id = entry.get('disease_id')
                if disease_id and f"disease_{disease_id}" not in network.nodes:
                    disease_node = AOPNode(
                        id=f"disease_{disease_id}",
                        label=entry.get('disease_name', disease_id),
                        node_type=NodeType.CUSTOM,
                        source=DataSourceType.OPENTARGETS,
                        properties={
                            'disease_id': disease_id,
                            'disease_name': entry.get('disease_name'),
                            'therapeutic_areas': entry.get('therapeutic_areas')
                        }
                    )
                    network.add_node(disease_node)
                    nodes_added += 1
                
                # Create compound-disease interaction edges
                compound_id = entry.get('identifier')
                if compound_id and disease_id:
                    edge_id = f"compound_disease_{compound_id}_{disease_id}"
                    if edge_id not in network.edges:
                        interaction_edge = AOPEdge(
                            id=edge_id,
                            source=compound_id,
                            target=f"disease_{disease_id}",
                            edge_type=EdgeType.INTERACTION,
                            source_type=DataSourceType.OPENTARGETS,
                            label="compound-disease interaction",
                            properties={
                                'interaction_score': entry.get('interaction_score'),
                                'evidence_count': entry.get('evidence_count')
                            }
                        )
                        network.add_edge(interaction_edge)
                        edges_added += 1
                        
            return {
                "success": True,
                "nodes_added": nodes_added,
                "edges_added": edges_added
            }

        except Exception as e:
            return {"error": str(e)}
    
    def get_network_cytoscape(self) -> List[Dict[str, Any]]:
        """Get current network in Cytoscape format using proper data model method"""
        network = self.get_current_network()
        if not network:
            return []
        return network.to_cytoscape()
    
    def filter_nodes_by_type(self, node_type: NodeType) -> List[Dict[str, Any]]:
        """Get nodes of specific type in Cytoscape format"""
        network = self.get_current_network()
        if not network:
            return []
        
        filtered_nodes = network.get_nodes_by_type(node_type)
        return [node.to_cytoscape() for node in filtered_nodes]
    
    def filter_nodes_by_source(self, source: DataSourceType) -> List[Dict[str, Any]]:
        """Get nodes from specific data source in Cytoscape format"""
        network = self.get_current_network()
        if not network:
            return []
        
        filtered_nodes = network.get_nodes_by_source(source)
        return [node.to_cytoscape() for node in filtered_nodes]
    
    
    def _determine_node_type(self, data: Dict[str, Any]) -> NodeType:
        """Determine node type from AOP Wiki data"""
        if data.get('is_mie'):
            return NodeType.MIE
        elif data.get('is_ao'):
            return NodeType.AO
        elif data.get('type') == 'uniprot':
            return NodeType.UNIPROT
        elif data.get('type') == 'ensembl':
            return NodeType.ENSEMBL
        else:
            return NodeType.KE
    
    def _fetch_bgee_data(self, genes: List[str]) -> Dict[str, Any]:
        """Fetch Bgee gene expression data - placeholder implementation"""
        # This should be implemented to actually fetch from Bgee
        # For now, return empty dict to avoid errors
        print(f"_fetch_bgee_data called with genes: {genes}")
        return {}
    
    def _fetch_aopwiki_sparql(self, mie_query: str) -> List[Dict[str, Any]]:
        """Fetch data from AOP Wiki SPARQL endpoint - placeholder implementation"""
        # This should be implemented to actually fetch from AOP Wiki
        # For now, return empty list to avoid errors
        print(f"_fetch_aopwiki_sparql called with query: {mie_query}")
        return []

    def get_network_for_route(self, route_params: Dict[str, Any]) -> str:
        """Get or create network based on route parameters"""
        mie_query = route_params.get('mie_query', '')
        qid = route_params.get('qid', '')
        qid_wd = route_params.get('qid_wd', '')
        
        # Create a unique network ID based on parameters
        if mie_query:
            network_name = f"AOP Network - {mie_query}"
            network_id = f"mie_{mie_query.replace(' ', '_')}"
        elif qid or qid_wd:
            network_name = f"AOP Network - {qid}_{qid_wd}"
            network_id = f"id_{qid}_{qid_wd}"
        else:
            # Use default network
            return self.current_network_id
        
        # Create network if it doesn't exist
        if network_id not in self.networks:
            self.networks[network_id] = AOPNetwork(
                id=network_id,
                name=network_name,
                description=f"Network for parameters: mie={mie_query}, qid={qid}, qid_wd={qid_wd}"
            )
        
        self.current_network_id = network_id
        return network_id

# Global service instance
aop_service = AOPNetworkService()
