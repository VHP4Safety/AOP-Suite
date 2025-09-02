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
    AOPTableBuilder,
    AOPInfo,
    CompoundTableBuilder
)

from datetime import datetime
import os

logger = logging.getLogger(__name__)

NETWORK_STATES_DIR = os.path.join(os.path.dirname(__file__), "../saved_networks")


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
            network, query = aop_query_service.query_aop_network(query_type, values)
            self.current_network = network
            
            # Get summary and elements
            summary = network.get_summary()
            elements = network.to_cytoscape_elements()
            
            response_data = {
                "success": True,
                "elements": elements,
                "elements_count": len(elements),
                "report": summary,
                "sparql_query": query
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

            logger.info(f"Loading genes for KEs")
            
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
            enriched_network, query = aop_query_service.query_genes_for_network(temp_network)
            
            # Convert gene associations to Cytoscape elements
            gene_elements = []
            for association in enriched_network.gene_associations:
                gene_elements.extend(association.to_cytoscape_elements())

            logger.info(f"Retrieved {len(gene_elements)} gene elements using data model")
            return {"gene_elements": gene_elements, "sparql_query": query}, 200
            
        except Exception as e:
            logger.error(f"Error in load_and_show_genes: {e}")
            return {"error": str(e)}, 500

    def populate_gene_table(self, request_data) -> Tuple[Dict[str, Any], int]:
        """Populate gene table from Cytoscape elements"""
        try:
            data = request_data.get_json(silent=True)
            if not data or "cy_elements" not in data:
                return {"error": "Cytoscape elements required"}, 400

            logger.info(f"Populating gene table from {len(data['cy_elements'])} elements using data model")

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

    def load_and_show_compounds(self, request_data) -> Tuple[Dict[str, Any], int]:
        """Load compounds for AOPs using the AOP data model"""
        try:
            aops = request_data.args.get("aops", "")
            if not aops:
                return {"error": "aops parameter is required"}, 400

            logger.info(f"Loading compounds for AOPs: {aops}")
            
            # Parse AOP URIs
            aop_uris = [uri.strip('<>') for uri in aops.split()]
            logger.info(f"Parsed AOP URIs: {aop_uris}")
            
            # Create a temporary network with the provided AOPs
            temp_network = AOPNetwork()
            
            # Add minimal AOP info to the network
            for aop_uri in aop_uris:
                aop_id = aop_uri.split("/")[-1] if "/" in aop_uri else aop_uri
                
                aop_info = AOPInfo(
                    aop_id=aop_id,
                    title=f"AOP {aop_id}",
                    uri=aop_uri
                )
                temp_network.aop_info[aop_uri] = aop_info
            
            # Query compounds for this network
            enriched_network, query = aop_query_service.query_compounds_for_network(temp_network)
            
            # Convert compound associations to Cytoscape elements
            compound_elements = []
            for association in enriched_network.compound_associations:
                compound_elements.extend(association.to_cytoscape_elements())

            logger.info(f"Retrieved {len(compound_elements)} compound elements")
            return {"compound_elements": compound_elements, "sparql_query": query}, 200
            
        except Exception as e:
            logger.error(f"Error in load_and_show_compounds: {e}")
            return {"error": str(e)}, 500

    def populate_compound_table(self, request_data) -> Tuple[Dict[str, Any], int]:
        """Populate compound table using the compound data model"""
        try:
            data = request_data.get_json(silent=True)
            if not data or "cy_elements" not in data:
                return {"error": "Cytoscape elements required"}, 400

            logger.info(f"Populating compound table from {len(data['cy_elements'])} elements using data model")
            
            # Parse Cytoscape elements into compound table structure
            parser = CytoscapeNetworkParser(data["cy_elements"])
            compound_table_builder = CompoundTableBuilder(parser)
            compound_data = compound_table_builder.build_compound_table()
            
            logger.info(f"Generated {len(compound_data)} compound table entries")
            return {"compound_data": compound_data}, 200
            
        except Exception as e:
            logger.error(f"Error in populate_compound_table: {e}")
            return {"error": f"Failed to populate compound table: {str(e)}"}, 500


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
            return ServiceResponse(success=True, data={"filename": filename})
        except Exception as e:
            logger.error(f"Failed to save network state: {e}")
            return ServiceResponse(
                success=False, error=f"Failed to save state: {str(e)}", status_code=500
            )

    def load_latest_state(self) -> ServiceResponse:
        """Load the most recent network state"""
        try:
            if not os.path.exists(self.states_dir):
                return ServiceResponse(
                    success=False, error="No saved states found", status_code=404
                )

            files = sorted(
                [
                    f
                    for f in os.listdir(self.states_dir)
                    if f.startswith("network_state_") and f.endswith(".json")
                ],
                reverse=True,
            )

            if not files:
                return ServiceResponse(
                    success=False, error="No saved states found", status_code=404
                )

            filepath = os.path.join(self.states_dir, files[0])
            with open(filepath, "r") as f:
                data = json.load(f)

            logger.info(f"Loaded network state from {files[0]}")
            return ServiceResponse(success=True, data=data)

        except Exception as e:
            logger.error(f"Failed to load network state: {e}")
            return ServiceResponse(
                success=False, error=f"Failed to load state: {str(e)}", status_code=500
            )
