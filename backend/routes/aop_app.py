from flask import Blueprint, request, jsonify

from backend.service import aop_network_service

# Instantiate the service class
aop_service = aop_network_service.AOPNetworkService()

aop_app = Blueprint("aop_app", __name__)

# AOP Wiki RDF API-related routes
## Query the AOP Wiki RDF for KE, AOP, and MIE data
@aop_app.route("/add_aop_network_data", methods=["POST"])
def get_aop_network_data():
    return aop_service.add_aop_network_data(request)

## Populate the AOP table
@aop_app.route("/populate_aop_table", methods=["POST"])
def populate_aop_table():
    return aop_service.populate_aop_table(request)

## Get genes associated with a specific KE
@aop_app.route("/load_and_show_genes", methods=["GET"])
def load_and_show_genes():
    return aop_service.load_and_show_genes(request)

## Populate the gene table
@aop_app.route("/populate_gene_table", methods=["POST"])
def populate_gene_table():
    return aop_service.populate_gene_table(request)

# General routes for AOP Network Builder
## Network state TODO fix implementation
## Save network state
@aop_app.route("/save_network_state", methods=["POST"])
def save_network_state():
    return jsonify(aop_service.save_network_state(request)), 200

## Load network state
@aop_app.route("/load_network_state", methods=["GET"])
def load_network_state():
    return jsonify(aop_service.load_network_state()), 200


## Get compounds associated with a specific AOP
@aop_app.route("/load_and_show_compounds", methods=["GET"])
def load_and_show_compounds():
    return aop_service.load_and_show_compounds(request)

## Get gene expressions associated with genes
@aop_app.route("/load_and_show_gene_expressions", methods=["POST"])
def load_and_show_gene_expressions():
    return aop_service.get_gene_expressions_for_current_network(request)

### Populate the compound table
@aop_app.route("/populate_compound_table", methods=["POST"])
def populate_compound_table():
    return jsonify(aop_service.populate_compound_table(request)), 200


## Get components associated with a specific KE
@aop_app.route("/load_and_show_components", methods=["GET"])
def load_and_show_components():
    return aop_service.load_and_show_components(request)

@aop_app.route("/populate_component_table", methods=["POST"])
def populate_component_table():
    return jsonify(aop_service.populate_component_table(request)), 200

@aop_app.route("/load_and_show_organs", methods=["GET"])
def load_and_show_organs():
    return aop_service.load_and_show_organs(request)

# Bgee Expression Routes
@aop_app.route("/query_bgee_expression", methods=["POST"])
def query_bgee_expression():
    """Query Bgee for gene expression data"""
    try:
        result, status_code = aop_service.query_bgee_expression(request)
        return jsonify(result), status_code
    except Exception as e:
        return jsonify({"error": "Internal server error"}), 500

@aop_app.route("/query_bgee_anatomical", methods=["POST"])
def query_bgee_anatomical():
    """Query Bgee for anatomical expression data"""
    try:
        result, status_code = aop_service.query_bgee_anatomical(request)
        return jsonify(result), status_code
    except Exception as e:
        return jsonify({"error": "Internal server error"}), 500

@aop_app.route("/query_bgee_developmental", methods=["POST"])
def query_bgee_developmental():
    """Query Bgee for developmental expression data"""
    try:
        result, status_code = aop_service.query_bgee_developmental(request)
        return jsonify(result), status_code
    except Exception as e:
        return jsonify({"error": "Internal server error"}), 500

@aop_app.route("/populate_gene_expression_table", methods=["POST"])
def populate_gene_expression_table():
    """Populate gene expression table from network elements"""
    try:
        result, status_code = aop_service.populate_gene_expression_table(request)
        return jsonify(result), status_code
    except Exception as e:
        return jsonify({"error": "Internal server error"}), 500
