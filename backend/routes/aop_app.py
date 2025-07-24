from flask import Blueprint, request, jsonify, send_file

import requests
import json
import pandas as pd
import os
import csv
import re
import traceback
from datetime import datetime

from backend.service import aop_network_service
from backend.query import aopwikirdf, qsprpred

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


#TODO## Get compounds associated with a specific KE
#@aop_app.route("/load_and_show_compounds", methods=["GET"])
#def load_and_show_compounds():
#    return aop_service.load_and_show_compounds(request)
#
### Populate the compound table
#@aop_app.route("/populate_compound_table", methods=["POST"])
#def populate_compound_table():
#    return jsonify(aop_service.populate_compound_table(request)), 200


# General routes for AOP Network Builder
## Network state TODO fix implementation
@aop_app.route("/save_network_state", methods=["POST"])
def save_network_state():
    return jsonify(aop_service.save_network_state(request)), 200


@aop_app.route("/load_network_state", methods=["GET"])
def load_network_state():
    return jsonify(aop_service.load_network_state()), 200


##Old routes
#@aop_app.route("/get_case_mie_model", methods=["GET"])
#def get_case_mie_model():
#   return aop_service.get_case_mie_model(request), 200
#@aop_app.route("/toggle_bounding_boxes", methods=["POST"])
#def toggle_bounding_boxes():
#    """Toggle visibility of bounding boxes in Cytoscape elements."""
#    return jsonify(aop_service.toggle_bounding_boxes(request)), 200
