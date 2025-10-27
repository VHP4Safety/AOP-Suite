import json
import logging
from typing import Dict, Optional, Any, Tuple
from dataclasses import dataclass
from datetime import datetime
import os

from backend.query.aopwikirdf import aop_query_service
from backend.query.bgee import bgee_query_service

from backend.models.core.aop import AOPNetwork, AOPKeyEvent, AOPInfo

from backend.models.constants import NodeType

from backend.models.converters.cy_to_aop import CytoscapeNetworkParser

from backend.models.data_tables.gene import (
    GeneTableBuilder, GeneExpressionTableBuilder)
from backend.models.data_tables.aop import AOPTableBuilder
from backend.models.data_tables.compound import CompoundTableBuilder
from backend.models.data_tables.component import ComponentTableBuilder

logger = logging.getLogger(__name__)

NETWORK_STATES_DIR = os.path.join(os.path.dirname(__file__), "../../saved_networks")


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
            include_proteins = request_data.args.get("include_proteins", "true").lower() == "true"

            if not kes:
                return {"error": "kes parameter is required"}, 400

            logger.info(f"Loading genes for KEs (include_proteins={include_proteins})")

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

            # Query genes for this network with include_proteins parameter
            enriched_network, query = aop_query_service.query_genes_for_network(temp_network, include_proteins)

            # Convert gene associations to Cytoscape elements
            gene_elements = []
            for association in enriched_network.gene_associations:
                gene_elements.extend(association.to_cytoscape_elements())

            logger.info(f"Retrieved {len(gene_elements)} gene elements using data model (proteins included: {include_proteins})")
            return {"gene_elements": gene_elements, "sparql_query": query}, 200

        except Exception as e:
            logger.error(f"Error in load_and_show_genes: {e}")
            return {"error": str(e)}, 500

    def query_bgee_expression(self, request_data) -> Tuple[Dict[str, Any], int]:
        """Query Bgee for gene expression data from Cytoscape elements"""
        try:
            data = request_data.get_json(silent=True)
            if not data or "cy_elements" not in data:
                return {"error": "Cytoscape elements required"}, 400

            query_by = "both"  # Always query by both genes and organs
            confidence_level = data.get("confidence_level", None)
            logger.info(f"Querying Bgee by {query_by} with confidence {confidence_level}")

            # Parse elements and build network
            parser = CytoscapeNetworkParser(data["cy_elements"])
            temp_network = AOPNetwork()

            # Add both genes and organs (required for "both" query)
            gene_nodes = parser.get_nodes_by_type(NodeType.GENE)
            organ_nodes = parser.get_nodes_by_type(NodeType.ORGAN)

            logger.info(f"Found {len(gene_nodes)} Ensembl nodes and {len(organ_nodes)} organ nodes")

            # Validate that we have both genes and organs
            if len(gene_nodes) == 0 and len(organ_nodes) == 0:
                return {
                    "expression_data": [],
                    "expression_elements": [],
                    "sparql_query": "# No genes or organs found in network",
                    "message": "Network must contain both genes (Ensembl nodes) and organs to query Bgee"
                }, 200
            elif len(gene_nodes) == 0:
                return {
                    "expression_data": [],
                    "expression_elements": [],
                    "sparql_query": "# No genes found in network", 
                    "message": "Network must contain genes (Ensembl nodes) to query Bgee"
                }, 200
            elif len(organ_nodes) == 0:
                return {
                    "expression_data": [],
                    "expression_elements": [],
                    "sparql_query": "# No organs found in network",
                    "message": "Network must contain organs to query Bgee"
                }, 200

            # Add nodes to temp network
            temp_network.node_list.extend(gene_nodes)
            temp_network.node_list.extend(organ_nodes)

            # Query Bgee directly
            enriched_network, query_used = bgee_query_service.query_gene_expressions_for_network(
                temp_network, query_by, confidence_level
            )

            # Convert results
            expression_elements = []
            expression_data = []

            if enriched_network and enriched_network.gene_expression_associations:
                for association in enriched_network.gene_expression_associations:
                    expression_elements.extend(association.to_cytoscape_elements())
                    expression_data.append(association.to_table_entry())

            logger.info(f"Retrieved {len(expression_data)} expression associations")
            return {
                "expression_data": expression_data,
                "expression_elements": expression_elements,
                "sparql_query": query_used or "# Query failed"
            }, 200

        except Exception as e:
            logger.error(f"Error in query_bgee_expression: {e}", exc_info=True)
            return {"error": str(e)}, 500

    def query_bgee_anatomical(self, request_data) -> Tuple[Dict[str, Any], int]:
        """Query Bgee for anatomical expression data"""
        try:
            data = request_data.get_json(silent=True)
            if not data:
                return {"error": "No JSON data provided"}, 400

            # Set query_by to organs for anatomical queries
            data["query_by"] = "organs"

            # Create mock request object with the modified data
            class MockRequest:
                def get_json(self, silent=True):
                    return data

            return self.query_bgee_expression(MockRequest())

        except Exception as e:
            logger.error(f"Error in query_bgee_anatomical: {e}")
            return {"error": str(e)}, 500

    def query_bgee_developmental(self, request_data) -> Tuple[Dict[str, Any], int]:
        """Query Bgee for developmental expression data"""
        try:
            # For now, redirect to the main expression query
            return self.query_bgee_expression(request_data)

        except Exception as e:
            logger.error(f"Error in query_bgee_developmental: {e}")
            return {"error": str(e)}, 500

    def populate_gene_expression_table(self, request_data) -> Tuple[Dict[str, Any], int]:
        """Populate gene expression table from network elements"""
        try:
            data = request_data.get_json(silent=True)
            if not data or "cy_elements" not in data:
                return {"error": "Cytoscape elements required"}, 400

            logger.info(f"Populating gene expression table from {len(data['cy_elements'])} elements")

            parser = CytoscapeNetworkParser(data["cy_elements"])
            builder = GeneExpressionTableBuilder(parser)
            expression_data = builder.build_gene_expression_table()

            logger.info(f"Generated {len(expression_data)} gene expression entries")
            return {"expression_data": expression_data}, 200

        except Exception as e:
            logger.error(f"Error in populate_gene_expression_table: {e}")
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

    def load_and_show_components(self, request_data) -> Tuple[Dict[str, Any], int]:
        """Load components for KEs using the AOP data model"""
        try:
            kes = request_data.args.get("kes", "")
            if not kes:
                return {"error": "kes parameter is required"}, 400
            go_only = True if request_data.args.get("go_only") == "true" else False
            logger.info(f"Loading components for KEs: Gene Ontology only={go_only}")

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
            enriched_network, query = aop_query_service.query_components_for_network(temp_network, go_only=go_only)

            # Convert gene associations to Cytoscape elements
            component_elements = []
            for association in enriched_network.component_associations:
                component_elements.extend(association.to_cytoscape_elements())

            logger.info(f"Retrieved {len(component_elements)} gene elements using data model")
            return {"component_elements": component_elements, "sparql_query": query}, 200
        except Exception as e:
            logger.error(f"Error in load_and_show_components: {e}")
            return {"error": str(e)}, 500

    def populate_component_table(self, request_data) -> Tuple[Dict[str, Any], int]:
        """Populate component table from component elements"""
        try:
            data = request_data.get_json(silent=True)
            if not data or "cy_elements" not in data:
                return {"error": "Component elements required"}, 400

            logger.info(
                f"Populating component table from {len(data['cy_elements'])} elements using data model"
            )

            builder = ComponentTableBuilder(data["cy_elements"])
            component_data = builder.build_component_table()

            logger.info(f"Extracted {len(component_data)} component entries using data model")
            return {"component_data": component_data}, 200

        except Exception as e:
            logger.error(f"Error in populate_component_table: {e}")
            return {"error": str(e)}, 500

    def load_and_show_organs(self, request_data) -> Tuple[Dict[str, Any], int]:
        """Load organs for KEs using the AOP data model"""
        try:
            kes = request_data.args.get("kes", "")
            if not kes:
                return {"error": "kes parameter is required"}, 400

            logger.info(f"Loading organs for KEs")

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

            # Query organs for this network
            enriched_network, query = aop_query_service.query_organs_for_network(temp_network)

            # Convert organ associations to Cytoscape elements
            organ_elements = []
            for association in enriched_network.organ_associations:
                organ_elements.extend(association.to_cytoscape_elements())

            logger.info(f"Retrieved {len(organ_elements)} organ elements using data model")
            return {"organ_elements": organ_elements, "sparql_query": query}, 200

        except Exception as e:
            logger.error(f"Error in load_and_show_organs: {e}")
            return {"error": str(e)}, 500

    def export_to_cx2(self, request_data) -> Tuple[Dict[str, Any], int]:
        """Export network to CX2 format using the data model"""
        try:
            data = request_data.get_json(silent=True)
            if not data:
                return {"error": "No data provided"}, 400

            elements = data.get("elements", [])
            if not elements:
                return {"error": "No network elements provided"}, 400

            # Extract metadata
            name = data.get("name", "AOP Network")
            description = data.get("description", "Exported from AOP Network Builder")
            cytoscape_styles = data.get("styles")  # Extract Cytoscape styles

            logger.info(f"Exporting network to CX2: {name} with {len(elements)} elements")
            if cytoscape_styles:
                logger.info(f"Received Cytoscape styles with {len(cytoscape_styles)} style rules")

            # Create AOPNetwork from Cytoscape elements - let the model handle everything
            network = AOPNetwork.from_cytoscape_elements(elements)
            
            # Pass the Cytoscape styles to the conversion method
            cx2_network = network.to_ndx_network(name=name, description=description, cytoscape_styles=cytoscape_styles)
            
            # Convert to JSON format
            cx2_json = cx2_network.to_cx2()

            logger.info(f"Successfully exported network to CX2 format")
            
            return cx2_json, 200

        except Exception as e:
            logger.error(f"Error in export_to_cx2: {e}", exc_info=True)
            return {"error": f"Failed to export to CX2: {str(e)}"}, 500

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
