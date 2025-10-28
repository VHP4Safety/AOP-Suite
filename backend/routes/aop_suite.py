from flask import Blueprint, request, jsonify
import logging

from backend.service.aop_network_service import AOPNetworkService

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

# Exports

@aop_app.route('/ndex/to_ndex_network', methods=['POST'])
def to_ndex_network():
    """Accept Cytoscape elements and optional name/description, return CX2 JSON."""
    aop_service = AOPNetworkService()
    result, status_code = aop_service.export_to_cx2(request)
    return jsonify(result), status_code

