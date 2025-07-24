from flask import Blueprint, request, jsonify, send_file

import json
import requests
from typing import Dict, List, Optional, Any

from backend.model.aop_data_model import (
    AOPNetwork,
    AOPNode,
    AOPEdge,
    NodeType,
    EdgeType,
    DataSourceType,
)
from backend.query import aopwikirdf

import uuid
from datetime import datetime
import os

import pandas as pd
from bioregistry import get_iri

NETWORK_STATES_DIR = os.path.join(os.path.dirname(__file__), "../saved_networks")
AOPWIKISPARQL_ENDPOINT = "https://aopwiki.rdf.bigcat-bioinformatics.org/sparql/"


class AOPNetworkService:
    # Initialization and network management
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

    # Querying AOP Wiki RDF

    def get_all_genes(self, request_data):
        """Get all genes from Cytoscape elements."""
        try:
            data = request_data.get_json(silent=True)
            if not data or "cy_elements" not in data:
                return {"error": "Cytoscape elements required"}, 400

            cy_elements = data["cy_elements"]
            genes = []

            for element in cy_elements:
                element_data = element.get("data", element)
                element_classes = element.get("classes", "")
                element_type = element_data.get("type", "")
                element_id = element_data.get("id", "")

                # Check for Ensembl nodes
                if (
                    element_classes == "ensembl-node"
                    or element_type == "ensembl"
                    or element_id.startswith("ensembl_")
                ):

                    gene_label = element_data.get("label", "")
                    if gene_label:
                        genes.append(gene_label)

            return {"genes": genes}, 200
        except Exception as e:
            return {"error": str(e)}, 500

    def add_aop_network_data(self, request_data):
        """Add AOP network data based on query type and values."""
        try:
            data = request_data.get_json(silent=True)
            if not data:
                return {"error": "No data provided"}, 400
            query_type = data.get("query_type", "")
            values = data.get("values", "")
            if not query_type or not values:
                return jsonify({"error": "query_type and values are required"}), 400
            aop_network_data = aopwikirdf.get_aop_network_data(query_type, values)
            return jsonify(aop_network_data), 200
        except Exception as e:
            return jsonify({"error": str(e)}), 500

    def load_and_show_genes(self, request_data):
        try:
            kes = request_data.args.get("kes", "")
            if not kes:
                return jsonify({"error": "kes parameter is required"}), 400
            else:
                cytoscape_elements = aopwikirdf.load_and_show_genes(kes)
                return jsonify({"gene_elements": cytoscape_elements}), 200
        except Exception as e:
            return jsonify({"error": str(e)}), 500

    def populate_gene_table(self, request_data):
        """Populate gene table from Cytoscape elements."""
        try:
            data = request_data.get_json(silent=True)
            if not data or "cy_elements" not in data:
                return {"error": "Cytoscape elements required"}, 400

            cy_elements = data["cy_elements"]
            gene_data = []

            for element in cy_elements:
                element_data = element.get("data", element)
                element_classes = element.get("classes", "")
                element_type = element_data.get("type", "")
                element_id = element_data.get("id", "")

                # Check for Ensembl nodes
                if (
                    element_classes == "ensembl-node"
                    or element_type == "ensembl"
                    or element_id.startswith("ensembl_")
                ):
                    gene_label = element_data.get("label", "")

                    # Find corresponding UniProt node
                    uniprot_protein = "N/A"
                    uniprot_id = "N/A"
                    uniprot_node_id = "N/A"

                    # Look for connected UniProt nodes
                    for other_element in cy_elements:
                        other_data = other_element.get("data", {})
                        other_classes = other_element.get("classes", "")
                        other_type = other_data.get("type", "")

                        if other_classes == "uniprot-node" or other_type == "uniprot":
                            # Check if there's an edge connecting this Ensembl to UniProt
                            for edge_element in cy_elements:
                                if edge_element.get("group") == "edges":
                                    edge_data = edge_element.get("data", {})
                                    source = edge_data.get("source", "")
                                    target = edge_data.get("target", "")

                                    if (
                                        source == element_id
                                        and target == other_data.get("id", "")
                                    ) or (
                                        target == element_id
                                        and source == other_data.get("id", "")
                                    ):
                                        uniprot_protein = other_data.get("label", "N/A")
                                        uniprot_id = other_data.get(
                                            "uniprot_id",
                                            other_data.get("id", "").replace(
                                                "uniprot_", ""
                                            ),
                                        )
                                        uniprot_node_id = other_data.get("id", "N/A")
                                        break

                            if uniprot_protein != "N/A":
                                break

                    if gene_label and gene_label not in [g["gene"] for g in gene_data]:
                        gene_data.append(
                            {
                                "gene": gene_label,
                                "protein": uniprot_protein,
                                "uniprot_id": uniprot_id,
                                "ensembl_id": element_id,
                                "uniprot_node_id": uniprot_node_id,
                            }
                        )

            return jsonify({"gene_data": gene_data}), 200
        except Exception as e:
            return jsonify({"error": str(e)}), 500

    # Populate app tables
    def populate_aop_table(self, request_data):
        """Populate AOP table from Cytoscape elements with enhanced data."""
        try:
            data = request_data.get_json(silent=True)
            if not data or "cy_elements" not in data:
                raise ValueError("Cytoscape elements required")
            cy_elements = data["cy_elements"]
            aop_data = aopwikirdf.populate_aop_table(cy_elements)
            return {"aop_data": aop_data}
        except Exception as e:
            return {"error": str(e)}

    # BioDataFuse
    def add_bgee_data(self, request_data):
        return

    def add_opentargets_data(self, request_data):
        return

    # Network state management
    def save_network_state(self, request_data):
        """Save current network state to persistent storage."""
        try:
            data = request_data.get_json(silent=True)
            if not data:
                return {"error": "No data provided"}, 400

            # Create directory if it doesn't exist
            os.makedirs(NETWORK_STATES_DIR, exist_ok=True)

            # Save with timestamp
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"network_state_{timestamp}.json"
            filepath = os.path.join(NETWORK_STATES_DIR, filename)

            with open(filepath, "w") as f:
                json.dump(data, f, indent=2)

            return {"success": True, "filename": filename}, 200
        except Exception as e:
            return {"error": str(e)}, 500

    def load_network_state(self):
        """Load the most recent network state."""
        try:
            if not os.path.exists(NETWORK_STATES_DIR):
                return {"error": "No saved states found"}, 404

            # Find most recent file
            files = [
                f
                for f in os.listdir(NETWORK_STATES_DIR)
                if f.startswith("network_state_") and f.endswith(".json")
            ]
            if not files:
                return {"error": "No saved states found"}, 404

            files.sort(reverse=True)  # Most recent first
            latest_file = files[0]
            filepath = os.path.join(NETWORK_STATES_DIR, latest_file)

            with open(filepath, "r") as f:
                data = json.load(f)

            return data, 200
        except Exception as e:
            return {"error": str(e)}, 500
