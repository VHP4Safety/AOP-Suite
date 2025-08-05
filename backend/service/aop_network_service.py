import json
import logging
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass

from backend.query.aopwikirdf import aop_query_service
from backend.model.aop_data_model import (
    CytoscapeNetworkParser, 
    GeneTableBuilder,
    AOPNetwork,
    AOPKeyEvent,
    NodeType,
    AOPRelationshipEntry
)

from datetime import datetime
import os

logger = logging.getLogger(__name__)

NETWORK_STATES_DIR = os.path.join(os.path.dirname(__file__), "../saved_networks")

@dataclass
class ServiceResponse:
    """Standardized service response"""
    success: bool
    data: Optional[Any] = None
    error: Optional[str] = None
    status_code: int = 200

class NetworkStateManager:
    """Handles network state persistence"""
    
    def __init__(self, states_dir: str = NETWORK_STATES_DIR):
        self.states_dir = states_dir
        os.makedirs(states_dir, exist_ok=True)
    
    def save_state(self, data: Dict[str, Any]) -> ServiceResponse:
        """Save network state to file"""
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"network_state_{timestamp}.json"
            filepath = os.path.join(self.states_dir, filename)
            
            with open(filepath, "w") as f:
                json.dump(data, f, indent=2)
            
            logger.info(f"Network state saved to {filename}")
            return ServiceResponse(
                success=True, 
                data={"filename": filename}
            )
        except Exception as e:
            logger.error(f"Failed to save network state: {e}")
            return ServiceResponse(
                success=False, 
                error=f"Failed to save state: {str(e)}",
                status_code=500
            )
    
    def load_latest_state(self) -> ServiceResponse:
        """Load the most recent network state"""
        try:
            if not os.path.exists(self.states_dir):
                return ServiceResponse(
                    success=False, 
                    error="No saved states found",
                    status_code=404
                )
            
            files = sorted(
                [f for f in os.listdir(self.states_dir) 
                 if f.startswith("network_state_") and f.endswith(".json")],
                reverse=True
            )
            
            if not files:
                return ServiceResponse(
                    success=False, 
                    error="No saved states found",
                    status_code=404
                )
            
            filepath = os.path.join(self.states_dir, files[0])
            with open(filepath, "r") as f:
                data = json.load(f)
            
            logger.info(f"Loaded network state from {files[0]}")
            return ServiceResponse(success=True, data=data)
            
        except Exception as e:
            logger.error(f"Failed to load network state: {e}")
            return ServiceResponse(
                success=False, 
                error=f"Failed to load state: {str(e)}",
                status_code=500
            )

class AOPNetworkService:
    """Main service for AOP network operations using the AOP data model"""
    
    def __init__(self):
        self.state_manager = NetworkStateManager()
        self.current_network: Optional[AOPNetwork] = None

    def add_aop_network_data(self, request_data) -> Tuple[Dict[str, Any], int]:
        """Add AOP network data using the proper data model"""
        try:
            data = request_data.get_json(silent=True)
            if not data:
                return {"error": "No data provided"}, 400

            query_type = data.get("query_type", "")
            values = data.get("values", "")
            
            if not query_type or not values:
                return {"error": "query_type and values are required"}, 400

            logger.info(f"Building AOP network: {query_type}, {len(values.split())} values")
            
            # Use the AOP data model via the query service
            network = aop_query_service.query_aop_network(query_type, values)
            self.current_network = network
            
            # Get summary and elements
            summary = network.get_summary()
            elements = network.to_cytoscape_elements()
            
            response_data = {
                "success": True,
                "elements": elements,
                "elements_count": len(elements),
                "report": summary,
            }
            
            # Generate warnings if incomplete
            warnings = []
            if summary.get("mie_count", 0) == 0:
                warnings.append("No Molecular Initiating Events (MIEs) found")
            if summary.get("ao_count", 0) == 0:
                warnings.append("No Adverse Outcomes (AOs) found")
            if summary.get("ker_count", 0) == 0:
                if summary.get("mie_count", 0) > 0 or summary.get("ao_count", 0) > 0:
                    warnings.append("No Key Event Relationships (KERs) found")
            
            if warnings:
                response_data["warning"] = {
                    "type": "incomplete_aop_data",
                    "message": f"Warnings: {'; '.join(warnings)}",
                    "details": f"Found: {summary.get('mie_count', 0)} MIEs, {summary.get('ao_count', 0)} AOs, {summary.get('ke_count', 0)} intermediate KEs, {summary.get('ker_count', 0)} KERs",
                    "specific_issues": warnings,
                }
            
            logger.info(f"Successfully built AOP network with {len(elements)} elements")
            return response_data, 200
            
        except Exception as e:
            logger.error(f"Error in add_aop_network_data: {e}")
            return {"error": str(e)}, 500

    def load_and_show_genes(self, request_data) -> Tuple[Dict[str, Any], int]:
        """Load genes for KEs using the AOP data model"""
        try:
            kes = request_data.args.get("kes", "")
            if not kes:
                return {"error": "kes parameter is required"}, 400

            logger.info(f"Loading genes for KEs using AOP data model")
            
            # Create a temporary network with the provided KEs
            temp_network = AOPNetwork()
            
            # Parse KE URIs and add them as key events
            ke_uris = [uri.strip('<>') for uri in kes.split()]
            for ke_uri in ke_uris:
                ke_id = ke_uri.split("/")[-1] if "/" in ke_uri else ke_uri
                key_event = AOPKeyEvent(
                    ke_id=ke_id,
                    uri=ke_uri,
                    title="Temporary KE",
                    ke_type=NodeType.KE
                )
                temp_network.add_key_event(key_event)
            
            # Query genes for this network
            enriched_network = aop_query_service.query_genes_for_network(temp_network)
            
            # Convert gene associations to Cytoscape elements
            gene_elements = []
            for association in enriched_network.gene_associations:
                gene_elements.extend(association.to_cytoscape_elements())

            logger.info(f"Retrieved {len(gene_elements)} gene elements using data model")
            return {"gene_elements": gene_elements}, 200
            
        except Exception as e:
            logger.error(f"Error in load_and_show_genes: {e}")
            return {"error": str(e)}, 500

    def populate_gene_table(self, request_data) -> Tuple[Dict[str, Any], int]:
        """Populate gene table from Cytoscape elements using clean OOP approach"""
        try:
            data = request_data.get_json(silent=True)
            if not data or "cy_elements" not in data:
                return {"error": "Cytoscape elements required"}, 400

            logger.info(f"Populating gene table from {len(data['cy_elements'])} elements using data model")

            # Use the clean OOP approach with proper data model
            parser = CytoscapeNetworkParser(data["cy_elements"])
            builder = GeneTableBuilder(parser)
            gene_data = builder.build_gene_table()
            
            logger.info(f"Extracted {len(gene_data)} gene entries using data model")
            return {"gene_data": gene_data}, 200
            
        except Exception as e:
            logger.error(f"Error in populate_gene_table: {e}")
            return {"error": str(e)}, 500

    def populate_aop_table(self, request_data) -> Tuple[Dict[str, Any], int]:
        """Populate AOP table using the AOP data model"""
        try:
            data = request_data.get_json(silent=True)
            if not data or "cy_elements" not in data:
                return {"error": "Cytoscape elements required"}, 400

            logger.info(f"Populating AOP table from {len(data['cy_elements'])} elements using data model")
            
            # Parse Cytoscape elements into AOP network structure
            aop_table_builder = AOPTableBuilder(data["cy_elements"])
            aop_data = aop_table_builder.build_aop_table()
            
            logger.info(f"Generated {len(aop_data)} AOP table entries using data model")
            return {"aop_data": aop_data}, 200
            
        except Exception as e:
            logger.error(f"Error in populate_aop_table: {e}")
            return {"error": str(e)}, 500

    def save_network_state(self, request_data) -> Tuple[Dict[str, Any], int]:
        """Save current network state to persistent storage"""
        try:
            data = request_data.get_json(silent=True)
            if not data:
                return {"error": "No data provided"}, 400

            response = self.state_manager.save_state(data)
            return ({"success": True, "filename": response.data["filename"]} 
                   if response.success else {"error": response.error}), response.status_code
                   
        except Exception as e:
            logger.error(f"Error in save_network_state: {e}")
            return {"error": str(e)}, 500

    def load_network_state(self) -> Tuple[Dict[str, Any], int]:
        """Load the most recent network state"""
        try:
            response = self.state_manager.load_latest_state()
            return (response.data if response.success else {"error": response.error}), response.status_code
            
        except Exception as e:
            logger.error(f"Error in load_network_state: {e}")
            return {"error": str(e)}, 500

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
        
        logger.info(f"Built AOP table with {len(table_entries)} entries using data model")
        return table_entries
    
    def _extract_aop_relationships(self) -> List['AOPRelationshipEntry']:
        """Extract AOP relationships from parsed network"""
        relationships = []
        
        for edge in self.parser.edges:
            # Only process edges with KER data
            if (edge.properties.get("ker_label") and 
                edge.properties.get("curie")):
                
                source_node = self._find_node_by_id(edge.source)
                target_node = self._find_node_by_id(edge.target)
                
                if source_node and target_node:
                    relationship = AOPRelationshipEntry(
                        source_node=source_node,
                        target_node=target_node,
                        edge=edge
                    )
                    relationships.append(relationship)
        
        return relationships
    
    def _extract_disconnected_nodes(self) -> List[Dict[str, str]]:
        """Extract disconnected nodes"""
        connected_node_ids = set()
        
        # Get all connected node IDs
        for edge in self.parser.edges:
            connected_node_ids.add(edge.source)
            connected_node_ids.add(edge.target)
        
        disconnected_entries = []
        for node in self.parser.nodes:
            if node.id not in connected_node_ids:
                # Extract AOP information
                aop_info = self._extract_aop_info_from_node(node)
                
                entry = {
                    "source_id": node.id,
                    "source_label": node.label or node.id,
                    "source_type": node.node_type or "unknown",
                    "ker_label": "N/A (disconnected)",
                    "curie": "N/A",
                    "target_id": "N/A",
                    "target_label": "N/A",
                    "target_type": "N/A",
                    "aop_list": aop_info["aop_string"],
                    "aop_titles": aop_info["aop_titles_string"],
                    "is_connected": False,
                }
                disconnected_entries.append(entry)
        
        return disconnected_entries
    
    def _find_node_by_id(self, node_id: str) -> Optional['CytoscapeNode']:
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
        
        # Convert URIs to AOP IDs
        aop_ids = []
        for aop_uri in aop_uris:
            if aop_uri and "aop/" in aop_uri:
                aop_id = aop_uri.split("aop/")[-1]
                aop_ids.append(f"AOP:{aop_id}")
        
        aop_string = ",".join(sorted(aop_ids)) if aop_ids else "N/A"
        aop_titles_string = "; ".join(sorted(aop_titles)) if aop_titles else "N/A"
        
        return {
            "aop_string": aop_string,
            "aop_titles_string": aop_titles_string
        }
