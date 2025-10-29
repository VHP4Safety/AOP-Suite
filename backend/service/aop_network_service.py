import json
import logging
from typing import Dict, Optional, Any, Tuple
from dataclasses import dataclass
from datetime import datetime
import os

from pyaop.aop.builder import AOPNetworkBuilder
from .aop_suite_logger_manager import logger_manager

logger = logging.getLogger(__name__)

NETWORK_STATES_DIR = os.path.join(os.path.dirname(__file__), "../../saved_networks")


class AOPNetworkService:
    """Main service for AOP network operations using the AOP data model"""

    def __init__(self):
        self.state_manager = NetworkStateManager()
        self.builder = AOPNetworkBuilder()
        # Use session-based logger
        self.logger = logger_manager.get_current_logger()

    def add_aop_network_data(self, request_data) -> Tuple[Dict[str, Any], int]:
        """Add AOP network data using the proper data model"""
        try:
            data = request_data.get_json(silent=True)
            if not data:
                return {"error": "JSON payload required"}, 400

            # Extract parameters from JSON payload
            query_type = data.get("query_type", None)
            values = data.get("values", "")
            status = data.get("status", "")
            cy_elements = data.get("cy_elements", {"elements": []})
            stype = type(status)
            logger.debug(f"Status {stype}")
            self.builder.update_from_json(cy_elements)

            # Log the operation
            self._log_aop_query_operation(query_type, values, status)

            # Use the AOP data model via the query service
            network, query = self.builder.query_by_identifier(query_type, values, status)

            # Get summary and elements
            summary = network.get_summary()
            elements = network.to_cytoscape_elements()

            # Log the result
            self._log_operation_result("aop_query", summary)

            response_data = {
                "success": True,
                "elements": elements,
                "aop_table": network.aop_table(),
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

    def load_and_show_components(self, request_data) -> Tuple[Dict[str, Any], int]:
        """Load components for KEs using the AOP data model"""
        try:
            data = request_data.get_json(silent=True)
            if not data or "cy_elements" not in data:
                return {"error": "Cytoscape elements required"}, 400

            # Extract parameters from JSON payload
            kes = data.get("kes", "")
            go_only = data.get("go_only", False)
            cy_elements = data.get("cy_elements", {"elements": []})

            # Handle both old format (list) and new format (dict with elements key)
            if isinstance(cy_elements, list):
                cy_elements = {"elements": cy_elements}

            self.builder.update_from_json(cy_elements)

            # Log the operation
            self._log_component_query_operation(go_only)

            logger.info(f"Loading components for KEs: Gene Ontology only={go_only}")
            _, query = self.builder.query_components_for_network(go_only=go_only)

            # Get updated network elements - return as list, not wrapped in object
            component_elements = self.builder.network.to_cytoscape_elements()

            # Log the result
            component_count = len([el for el in component_elements["elements"] if el.get('data', {}).get('type') in ['component_process', 'component_object']])
            self._log_operation_result("component_query", {"component_count": component_count})

            return {
                "component_elements": component_elements,
                "component_table": self.builder.network.component_table(),
                "sparql_query": query
            }, 200

        except Exception as e:
            logger.error(f"Error in load_and_show_components: {e}")
            return {"error": str(e)}, 500

    def load_and_show_genes(self, request_data) -> Tuple[Dict[str, Any], int]:
        """Load genes for KEs using the AOP data model"""
        try:
            data = request_data.get_json(silent=True)
            if not data or "cy_elements" not in data:
                return {"error": "Cytoscape elements required"}, 400

            # Extract parameters from JSON payload
            include_proteins = data.get("include_proteins", True)
            cy_elements = data.get("cy_elements", {"elements": []})

            # Handle both old format (list) and new format (dict with elements key)
            if isinstance(cy_elements, list):
                cy_elements = {"elements": cy_elements}

            self.builder.update_from_json(cy_elements)

            # Log the operation
            self._log_gene_query_operation(include_proteins)

            # Query genes for this network with include_proteins parameter
            _, query = self.builder.query_genes_for_ke(include_proteins)

            # Get updated network elements - return as list, not wrapped in object
            gene_elements = self.builder.network.to_cytoscape_elements()

            # Log the result
            gene_count = len([el for el in gene_elements['elements'] if el.get('data', {}).get('type') in ['gene', 'protein']])
            self._log_operation_result("gene_query", {"gene_count": gene_count})

            return {
                "gene_elements": gene_elements,
                "gene_table": self.builder.network.gene_table(),
                "sparql_query": query
            }, 200

        except Exception as e:
            logger.error(f"Error in load_and_show_genes: {e}")
            return {"error": str(e)}, 500

    def load_and_show_compounds(self, request_data) -> Tuple[Dict[str, Any], int]:
        """Load compounds for AOPs using the AOP data model"""
        try:
            data = request_data.get_json(silent=True)
            if not data or "cy_elements" not in data:
                return {"error": "Cytoscape elements required"}, 400

            # Extract parameters from JSON payload
            cy_elements = data.get("cy_elements", {"elements": []})

            self.builder.update_from_json(cy_elements)

            # Log the operation
            self._log_compound_query_operation()

            # Query compounds for this network
            _, query = self.builder.query_compounds_for_network()

            # Get updated network elements - return as list, not wrapped in object
            compound_elements = self.builder.network.to_cytoscape_elements()

            # Log the result
            compound_count = len([el for el in compound_elements["elements"] if el.get('data', {}).get('type') == 'chemical'])
            self._log_operation_result("compound_query", {"compound_count": compound_count})

            return {"compound_elements": compound_elements,
                    "compound_table": self.builder.network.compound_table(),
                    "sparql_query": query}, 200

        except Exception as e:
            logger.error(f"Error in load_and_show_compounds: {e}")
            return {"error": str(e)}, 500

    def load_and_show_organs(self, request_data) -> Tuple[Dict[str, Any], int]:
        """Load organs for KEs using the AOP data model"""
        try:
            data = request_data.get_json(silent=True)
            if not data or "cy_elements" not in data:
                return {"error": "Cytoscape elements required"}, 400

            # Extract parameters from JSON payload
            kes = data.get("kes", "")
            cy_elements = data.get("cy_elements", {"elements": []})

            # Handle both old format (list) and new format (dict with elements key)
            if isinstance(cy_elements, list):
                cy_elements = {"elements": cy_elements}

            self.builder.update_from_json(cy_elements)

            # Log the operation
            self._log_organ_query_operation()

            # Query organs for this network
            _, query = self.builder.query_organs_for_kes()

            # Get updated network elements - return as list, not wrapped in object
            organ_elements = self.builder.network.to_cytoscape_elements()

            # Log the result
            organ_count = len([el for el in organ_elements["elements"] if el.get('data', {}).get('type') == 'organ'])
            self._log_operation_result("organ_query", {"organ_count": organ_count})

            return {
                "organ_elements": organ_elements,
                "organ_table": self.builder.network.component_table(),
                "sparql_query": query
            }, 200

        except Exception as e:
            logger.error(f"Error in load_and_show_organs: {e}")
            return {"error": str(e)}, 500

    def query_bgee_expression(self, request_data) -> Tuple[Dict[str, Any], int]:
        """Query Bgee for gene expression data from Cytoscape elements"""
        try:
            data = request_data.get_json(silent=True)
            if not data or "cy_elements" not in data:
                return {"error": "Cytoscape elements required"}, 400

            # Extract parameters from JSON payload
            confidence_level = data.get("confidence_level", 80)
            cy_elements = data.get("cy_elements", {"elements": []})

            # Handle both old format (list) and new format (dict with elements key)
            if isinstance(cy_elements, list):
                cy_elements = {"elements": cy_elements}

            self.builder.update_from_json(cy_elements)

            # Log the operation
            self._log_bgee_query_operation(confidence_level)

            _, query = self.builder.query_gene_expression(confidence_level)

            # Get updated network elements - return as list, not wrapped in object
            expression_elements = self.builder.network.to_cytoscape_elements()

            # Log the result
            expression_count = len(self.builder.network.gene_expression_table())
            self._log_operation_result("bgee_query", {"expression_count": expression_count})

            return {
                "expression_elements": expression_elements,
                "expression_data": self.builder.network.gene_expression_table(),
                "gene_table": self.builder.network.gene_table(),  # Add gene table like other methods
                "sparql_query": query or "# Query failed",
            }, 200

        except Exception as e:
            logger.error(f"Error in query_bgee_expression: {e}", exc_info=True)
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

    def export_to_cx2(self, request_data) -> Tuple[Dict[str, Any], int]:
        """Export network to CX2 format using the data model"""
        try:
            self.builder.update_from_json(request_data.args.get("network", "")) #TODO fix api call structure
            cx2_json = self.builder.network.to_cx2
            return cx2_json, 200

        except Exception as e:
            logger.error(f"Error in export_to_cx2: {e}", exc_info=True)
            return {"error": f"Failed to export to CX2: {str(e)}"}, 500

    def populate_aop_table(self, request_data) -> Tuple[Dict[str, Any], int]:
        """Populate AOP table from current network elements"""
        try:
            data = request_data.get_json(silent=True)
            if not data or "cy_elements" not in data:
                return {"error": "Cytoscape elements required"}, 400

            cy_elements = data.get("cy_elements", {"elements": []})
            self.builder.update_from_json(cy_elements)

            # Get AOP table data
            aop_table = self.builder.network.aop_table()

            return {
                "aop_data": aop_table
            }, 200

        except Exception as e:
            logger.error(f"Error in populate_aop_table: {e}")
            return {"error": str(e)}, 500

    def get_operation_log(self) -> Dict[str, Any]:
        """Get the current operation log summary"""
        if not self.logger:
            return {"total_operations": 0, "session_id": None, "project_name": None}
        
        summary = self.logger.get_operation_summary()
        summary["project_name"] = logger_manager.get_project_name()
        return summary

    def generate_python_script(self) -> str:
        """Generate Python script from logged operations"""
        if not self.logger:
            return "# No active session - please start a project first\n"
        return self.logger.generate_python_script()

    def clear_operation_log(self) -> None:
        """Clear the operation log"""
        logger_manager.clear_current_session_log()

    def export_log_json(self) -> str:
        """Export operation log as JSON"""
        if not self.logger:
            return '{"error": "No active session"}'
        return self.logger.export_log_json()

    def has_active_session(self) -> bool:
        """Check if there's an active session"""
        return self.logger is not None

    # Private logging methods
    def _log_aop_query_operation(self, query_type: str, values: str, status: str):
        """Log AOP query operation"""
        # Clean up values for Python code
        values_list = [v.strip() for v in values.split() if v.strip()]
        values_repr = repr(' '.join(values_list))
        
        python_code = f"""# Query AOP network by {query_type}
network, query = builder.query_by_identifier('{query_type}', {values_repr}, {repr(status)})"""
        
        self.logger.log_operation(
            operation_type="aop_query",
            description=f"Query AOP network by {query_type}",
            python_code=python_code,
            comment=f"Query AOP-Wiki RDF for {query_type} using values: {values_list}",
            parameters={
                "query_type": query_type,
                "values": values_list,
                "status": status
            }
        )

    def _log_gene_query_operation(self, include_proteins: bool):
        """Log gene query operation"""
        python_code = f"""# Query genes for Key Events in the network
_, query = builder.query_genes_for_ke(include_proteins={include_proteins})"""
        
        self.logger.log_operation(
            operation_type="gene_query",
            description="Query genes for Key Events",
            python_code=python_code,
            comment=f"Query genes associated with KEs, include proteins: {include_proteins}",
            parameters={"include_proteins": include_proteins}
        )

    def _log_compound_query_operation(self):
        """Log compound query operation"""
        python_code = """# Query compounds for AOPs in the network
_, query = builder.query_compounds_for_network()"""
        
        self.logger.log_operation(
            operation_type="compound_query",
            description="Query compounds for AOPs",
            python_code=python_code,
            comment="Query chemical compounds associated with AOPs in the network"
        )

    def _log_component_query_operation(self, go_only: bool):
        """Log component query operation"""
        python_code = f"""# Query components for the network
_, query = builder.query_components_for_network(go_only={go_only})"""
        
        self.logger.log_operation(
            operation_type="component_query",
            description="Query components for KEs",
            python_code=python_code,
            comment=f"Query GO components for Key Events, GO only: {go_only}",
            parameters={"go_only": go_only}
        )

    def _log_organ_query_operation(self):
        """Log organ query operation"""
        python_code = """# Query organs for Key Events in the network
_, query = builder.query_organs_for_kes()"""
        
        self.logger.log_operation(
            operation_type="organ_query",
            description="Query organs for Key Events",
            python_code=python_code,
            comment="Query organ/tissue information for Key Events"
        )

    def _log_bgee_query_operation(self, confidence_level: int):
        """Log Bgee query operation"""
        python_code = f"""# Query gene expression data from Bgee
_, query = builder.query_gene_expression(confidence_level={confidence_level})"""
        
        self.logger.log_operation(
            operation_type="bgee_query",
            description="Query Bgee gene expression",
            python_code=python_code,
            comment=f"Query gene expression data from Bgee with confidence level {confidence_level}",
            parameters={"confidence_level": confidence_level}
        )

    def _log_operation_result(self, operation_type: str, result_summary: Dict[str, Any]):
        """Update the last log entry with result information"""
        if self.logger.entries and self.logger.entries[-1].operation_type == operation_type:
            self.logger.entries[-1].result_summary = str(result_summary)

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
