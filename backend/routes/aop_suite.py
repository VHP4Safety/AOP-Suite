from flask import Blueprint, request, jsonify, make_response
import logging

from backend.service.aop_network_service import AOPNetworkService
from backend.service.aop_suite_logger_manager import logger_manager

# Set up logging
logger = logging.getLogger(__name__)


aop_app = Blueprint("aop_app", __name__)

# AOP Wiki RDF API-related routes
## Query the AOP Wiki RDF for KE, AOP, and MIE data
@aop_app.route("/add_aop_network_data", methods=["POST"])
def get_aop_network_data():
    aop_service = AOPNetworkService()
    result, status_code = aop_service.add_aop_network_data(request)
    return jsonify(result), status_code

## Get genes associated with a specific KE
@aop_app.route("/load_and_show_genes", methods=["POST"])
def load_and_show_genes():
    aop_service = AOPNetworkService()
    result, status_code = aop_service.load_and_show_genes(request)
    return jsonify(result), status_code

# General routes for AOP Network Builder
## Network state TODO fix implementation
## Save network state
@aop_app.route("/save_network_state", methods=["POST"])
def save_network_state():
    aop_service = AOPNetworkService()
    result, status_code = aop_service.save_network_state(request)
    return jsonify(result), status_code

## Load network state
@aop_app.route("/load_network_state", methods=["GET"])
def load_network_state():
    aop_service = AOPNetworkService()
    return jsonify(aop_service.load_network_state()), 200


## Get compounds associated with a specific AOP
@aop_app.route("/load_and_show_compounds", methods=["POST"])
def load_and_show_compounds():
    aop_service = AOPNetworkService()
    return aop_service.load_and_show_compounds(request)


## Get gene expressions associated with genes
@aop_app.route("/query_bgee_expression", methods=["POST"])
def load_and_show_gene_expressions():
    aop_service = AOPNetworkService()
    result, status_code = aop_service.query_bgee_expression(request)
    return jsonify(result), status_code

## Get components associated with a specific KE
@aop_app.route("/load_and_show_components", methods=["POST"])
def load_and_show_components():
    aop_service = AOPNetworkService()
    return aop_service.load_and_show_components(request)

# Organs query
@aop_app.route("/load_and_show_organs", methods=["POST"])
def load_and_show_organs():
    """Load and show organ data for Key Events"""
    aop_service = AOPNetworkService()
    return aop_service.load_and_show_organs(request)

# Session management routes
@aop_app.route("/session/start", methods=["POST"])
def start_project_session():
    """Start a new project session"""
    data = request.get_json()
    project_name = data.get('project_name', '').strip()
    
    if not project_name:
        return jsonify({"error": "Project name is required"}), 400
    
    # Validate project name (alphanumeric, spaces, hyphens, underscores only)
    import re
    if not re.match(r'^[a-zA-Z0-9\s\-_]+$', project_name):
        return jsonify({"error": "Project name contains invalid characters"}), 400
    
    session_id = logger_manager.start_project_session(project_name)
    return jsonify({
        "success": True, 
        "session_id": session_id, 
        "project_name": project_name,
        "message": f"Project '{project_name}' started"
    }), 200

@aop_app.route("/session/status", methods=["GET"])
def get_session_status():
    """Get current session status"""
    session_id = logger_manager.get_session_id()
    project_name = logger_manager.get_project_name()
    
    if session_id:
        return jsonify({
            "active": True,
            "session_id": session_id,
            "project_name": project_name
        }), 200
    else:
        return jsonify({"active": False}), 200

@aop_app.route("/session/end", methods=["POST"])
def end_session():
    """End current session"""
    logger_manager.end_session()
    return jsonify({"success": True, "message": "Session ended"}), 200

# Operation logging routes (updated to check for active session)
@aop_app.route("/operation_log/summary", methods=["GET"])
def get_operation_log_summary():
    """Get summary of logged operations"""
    aop_service = AOPNetworkService()
    if not aop_service.has_active_session():
        return jsonify({"error": "No active session"}), 400
    return jsonify(aop_service.get_operation_log()), 200

@aop_app.route("/operation_log/script", methods=["GET"])
def download_python_script():
    """Download Python script of logged operations"""
    aop_service = AOPNetworkService()
    if not aop_service.has_active_session():
        return jsonify({"error": "No active session"}), 400
    
    script_content = aop_service.generate_python_script()
    project_name = logger_manager.get_project_name() or "aop_project"
    
    response = make_response(script_content)
    response.headers['Content-Type'] = 'text/x-python'
    response.headers['Content-Disposition'] = f'attachment; filename={project_name}_operations.py'
    
    return response

@aop_app.route("/operation_log/json", methods=["GET"])
def download_operation_log_json():
    """Download operation log as JSON"""
    aop_service = AOPNetworkService()
    if not aop_service.has_active_session():
        return jsonify({"error": "No active session"}), 400
        
    json_content = aop_service.export_log_json()
    project_name = logger_manager.get_project_name() or "aop_project"
    
    response = make_response(json_content)
    response.headers['Content-Type'] = 'application/json'
    response.headers['Content-Disposition'] = f'attachment; filename={project_name}_log.json'
    
    return response

@aop_app.route("/operation_log/clear", methods=["POST"])
def clear_operation_log():
    """Clear the operation log"""
    aop_service = AOPNetworkService()
    if not aop_service.has_active_session():
        return jsonify({"error": "No active session"}), 400
        
    aop_service.clear_operation_log()
    return jsonify({"success": True, "message": "Operation log cleared"}), 200

# Exports

@aop_app.route('/ndex/to_ndex_network', methods=['POST'])
def to_ndex_network():
    """Accept Cytoscape elements and optional name/description, return CX2 JSON."""
    aop_service = AOPNetworkService()
    result, status_code = aop_service.export_to_cx2(request)
    return jsonify(result), status_code

