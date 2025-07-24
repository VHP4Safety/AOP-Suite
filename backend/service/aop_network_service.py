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

    def load_and_show_genes_for_mies(self, mie_node_ids):
        """Load genes for specific MIE node IDs."""
        # Extract numeric IDs from MIE node IDs
        mie_ids = []
        for mie_id in mie_node_ids:
            if "https://identifiers.org/aop.events/" in mie_id:
                numeric_id = mie_id.split("https://identifiers.org/aop.events/")[-1]
            elif "aop.events:" in mie_id:
                numeric_id = mie_id.split("aop.events:")[-1]
            else:
                numeric_id = mie_id

            if numeric_id and numeric_id.isdigit():
                mie_ids.append(numeric_id)

        if not mie_ids:
            return {"gene_elements": []}, 200

        gene_elements = []
        csv_path = os.path.join(
            os.path.dirname(__file__), "../static/data/caseMieModel.csv"
        )

        try:
            with open(csv_path, "r", encoding="utf-8") as csvfile:
                reader = csv.DictReader(csvfile)
                for row in reader:
                    csv_mie_id = row.get("MIE/KE identifier in AOP wiki", "").strip()
                    uniprot_id = row.get("uniprot ID inferred from qspred name", "").strip()
                    ensembl_id = row.get("Ensembl", "").strip()
                    protein_name = row.get("protein name uniprot", "").strip()

                    if csv_mie_id in mie_ids and uniprot_id and ensembl_id:
                        mie_node_id = f"https://identifiers.org/aop.events/{csv_mie_id}"
                        uniprot_node_id = f"uniprot_{uniprot_id}"
                        ensembl_node_id = f"ensembl_{ensembl_id}"

                        # Add UniProt node
                        gene_elements.append(
                            {
                                "data": {
                                    "id": uniprot_node_id,
                                    "label": protein_name or uniprot_id,
                                    "type": "uniprot",
                                    "uniprot_id": uniprot_id,
                                },
                                "classes": "uniprot-node",
                            }
                        )

                        # Add Ensembl node
                        gene_elements.append(
                            {
                                "data": {
                                    "id": ensembl_node_id,
                                    "label": ensembl_id,
                                    "type": "ensembl",
                                    "ensembl_id": ensembl_id,
                                },
                                "classes": "ensembl-node",
                            }
                        )

                        # Add edge from MIE to UniProt
                        gene_elements.append(
                            {
                                "data": {
                                    "id": f"{mie_node_id}_{uniprot_node_id}",
                                    "source": uniprot_node_id,
                                    "target": mie_node_id,
                                    "label": "part of",
                                }
                            }
                        )

                        # Add edge from UniProt to Ensembl
                        gene_elements.append(
                            {
                                "data": {
                                    "id": f"{uniprot_node_id}_{ensembl_node_id}",
                                    "source": uniprot_node_id,
                                    "target": ensembl_node_id,
                                    "label": "translates to",
                                }
                            }
                        )

        except Exception as e:
            return {"error": str(e)}, 500

        return {"gene_elements": gene_elements}, 200

    def populate_aop_table(self, request_data):
        """Populate AOP table from Cytoscape elements with enhanced data."""
        try:
            data = request_data.get_json(silent=True)
            if not data or "cy_elements" not in data:
                return {"error": "Cytoscape elements required"}, 400

            cy_elements = data["cy_elements"]
            aop_data = []

            # Create a lookup for node labels and AOP data
            node_data = {}
            connected_nodes = set()

            for element in cy_elements:
                if (
                    element.get("group") != "edges"
                    and element.get("classes") != "bounding-box"
                ):
                    element_data = element.get("data", {})
                    node_id = element_data.get("id")
                    if node_id:
                        # Format label with fallback to IRI if missing
                        label = element_data.get("label", "")
                        if not label or label == "NA":
                            # Extract readable part from IRI
                            iri_part = node_id.split("/")[-1] if "/" in node_id else node_id
                            label = f"{iri_part} (missing label)"

                        node_data[node_id] = {
                            "label": label,
                            "type": element_data.get("type", "unknown"),
                            "is_mie": element_data.get("is_mie", False),
                            "is_ao": element_data.get("is_ao", False),
                            "aop": element_data.get("aop", []),
                            "aop_title": element_data.get("aop_title", []),
                        }

            # Process edges with KER labels and track connected nodes
            for element in cy_elements:
                if element.get("group") == "edges":
                    edge_data = element.get("data", {})
                    source_id = edge_data.get("source", "")
                    target_id = edge_data.get("target", "")

                    # Track connected nodes
                    if source_id:
                        connected_nodes.add(source_id)
                    if target_id:
                        connected_nodes.add(target_id)

                    # Only process edges with KER data
                    if edge_data.get("ker_label") and edge_data.get("curie"):
                        ker_label = edge_data.get("ker_label", "")
                        curie = edge_data.get("curie", "")

                        # Get source and target data
                        source_data = node_data.get(source_id, {})
                        target_data = node_data.get(target_id, {})

                        source_label = source_data.get("label", source_id)
                        target_label = target_data.get("label", target_id)
                        source_type = source_data.get("type", "unknown")
                        target_type = target_data.get("type", "unknown")

                        # Collect all AOPs from both source and target nodes
                        all_aops = set()
                        aop_titles = set()

                        # Add AOPs from source
                        source_aops = source_data.get("aop", [])
                        source_aop_titles = source_data.get("aop_title", [])
                        if not isinstance(source_aops, list):
                            source_aops = [source_aops] if source_aops else []
                        if not isinstance(source_aop_titles, list):
                            source_aop_titles = (
                                [source_aop_titles] if source_aop_titles else []
                            )

                        for aop in source_aops:
                            if aop and "aop/" in aop:
                                aop_id = aop.split("aop/")[-1]
                                all_aops.add(f"AOP:{aop_id}")

                        for title in source_aop_titles:
                            if title:
                                aop_titles.add(title)

                        # Add AOPs from target
                        target_aops = target_data.get("aop", [])
                        target_aop_titles = target_data.get("aop_title", [])
                        if not isinstance(target_aops, list):
                            target_aops = [target_aops] if target_aops else []
                        if not isinstance(target_aop_titles, list):
                            target_aop_titles = (
                                [target_aop_titles] if target_aop_titles else []
                            )

                        for aop in target_aops:
                            if aop and "aop/" in aop:
                                aop_id = aop.split("aop/")[-1]
                                all_aops.add(f"AOP:{aop_id}")

                        for title in target_aop_titles:
                            if title:
                                aop_titles.add(title)

                        # Convert to sorted lists for consistent display
                        aop_list = sorted(list(all_aops))
                        aop_string = ",".join(aop_list) if aop_list else "N/A"
                        aop_titles_string = (
                            "; ".join(sorted(list(aop_titles))) if aop_titles else "N/A"
                        )

                        aop_data.append(
                            {
                                "source_id": source_id,
                                "source_label": source_label,
                                "source_type": source_type,
                                "ker_label": ker_label,
                                "curie": curie,
                                "target_id": target_id,
                                "target_label": target_label,
                                "target_type": target_type,
                                "aop_list": aop_string,
                                "aop_titles": aop_titles_string,
                                "is_connected": True,
                            }
                        )

            # Add disconnected nodes as separate entries
            for node_id, node_info in node_data.items():
                if node_id not in connected_nodes:
                    # Get AOP information for disconnected nodes
                    node_aops = node_info.get("aop", [])
                    node_aop_titles = node_info.get("aop_title", [])

                    if not isinstance(node_aops, list):
                        node_aops = [node_aops] if node_aops else []
                    if not isinstance(node_aop_titles, list):
                        node_aop_titles = [node_aop_titles] if node_aop_titles else []

                    aop_ids = []
                    for aop in node_aops:
                        if aop and "aop/" in aop:
                            aop_id = aop.split("aop/")[-1]
                            aop_ids.append(f"AOP:{aop_id}")

                    aop_string = ",".join(sorted(aop_ids)) if aop_ids else "N/A"
                    aop_titles_string = (
                        "; ".join(sorted(node_aop_titles)) if node_aop_titles else "N/A"
                    )

                    aop_data.append(
                        {
                            "source_id": node_id,
                            "source_label": node_info.get("label", node_id),
                            "source_type": node_info.get("type", "unknown"),
                            "ker_label": "N/A (disconnected)",
                            "curie": "N/A",
                            "target_id": "N/A",
                            "target_label": "N/A",
                            "target_type": "N/A",
                            "aop_list": aop_string,
                            "aop_titles": aop_titles_string,
                            "is_connected": False,
                        }
                    )

            return jsonify({"aop_data": aop_data}), 200
        except Exception as e:
            return jsonify({"error": str(e)}), 500

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

    def convert_curie_to_iri(self, curie_or_namespace, local_id=None):
        """
        Convert CURIE to proper IRI using bioregistry.

        Args:
            curie_or_namespace: Either a full CURIE like "chebi:24867" or namespace like "chebi"
            local_id: Local identifier if namespace is provided

        Returns:
            str: Proper IRI URL or original string if conversion fails
        """
        try:
            if local_id:
                # Namespace and local_id provided separately
                return (
                    get_iri(curie_or_namespace, local_id)
                    or f"{curie_or_namespace}:{local_id}"
                )
            else:
                # Full CURIE provided
                if ":" in curie_or_namespace:
                    namespace, lid = curie_or_namespace.split(":", 1)
                    return get_iri(namespace, lid) or curie_or_namespace
                else:
                    return curie_or_namespace
        except Exception as e:
            print(f"Error converting CURIE {curie_or_namespace}: {e}")
            return curie_or_namespace

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
