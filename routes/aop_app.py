from flask import Blueprint, request, jsonify, send_file
from urllib.parse import quote, unquote
from pyBiodatafuse import id_mapper
from pyBiodatafuse.annotators import opentargets, bgee
from bioregistry import get_iri
import requests
import json
import pandas as pd
import os
import csv
import re
import traceback

from datetime import datetime
from services.aop_network_service import aop_service

# Add this constant for network state persistence
NETWORK_STATES_DIR = os.path.join(os.path.dirname(__file__), "../saved_networks")

aop_app = Blueprint("aop_app", __name__)

@aop_app.route("/get_dummy_data", methods=["GET"])
def get_dummy_data():
    """
    Get dummy data for testing purposes.
    
    Returns:
        tuple: JSON response with dummy compound data and status code 200
    """
    results = [
        {"Compound": "Compound1", "SMILES": "Smile 1"},
        {"Compound": "Compound1", "SMILES": "Smile 1"},
        {"Compound": "Compound1", "SMILES": "Smile 1"},
    ]
    return jsonify(results), 200

def is_valid_qid(qid):
    return re.fullmatch(r"Q\d+", qid) is not None

def get_compounds_q(q):
    if not is_valid_qid(q):
        return jsonify({"error": "Invalid identifier format"}), 400
    
    compoundwikiEP = "https://compoundcloud.wikibase.cloud/query/sparql"
    sparqlquery_full = (
        "PREFIX wd: <https://compoundcloud.wikibase.cloud/entity/>\n"
        "PREFIX wdt: <https://compoundcloud.wikibase.cloud/prop/direct/>\n\n"
        "SELECT DISTINCT (substr(str(?cmp), 45) as ?ID) (?cmpLabel AS ?Term) ?SMILES ?cid\n"
        "WHERE {\n"
        "  { ?parent wdt:P21 wd:"
        + q
        + " ; wdt:P29 ?cmp . } UNION { ?cmp wdt:P21 wd:"
        + q
        + " . }\n"
        "  ?cmp wdt:P1 ?type ; rdfs:label ?cmpLabel . FILTER(lang(?cmpLabel) = 'en')\n"
        "  ?type rdfs:label ?typeLabel . FILTER(lang(?typeLabel) = 'en')\n"
        "  OPTIONAL { ?cmp wdt:P7 ?chiralSMILES }\n"
        "  OPTIONAL { ?cmp wdt:P12 ?nonchiralSMILES }\n"
        "  OPTIONAL {?cmp wdt:P13 ?cid . }\n"
        '  BIND (COALESCE(IF(BOUND(?chiralSMILES), ?chiralSMILES, 1/0), IF(BOUND(?nonchiralSMILES), ?nonchiralSMILES, 1/0), "") AS ?SMILES)\n'
        '  SERVICE wikibase:label { bd:serviceParam wikibase:language "[AUTO_LANGUAGE],en". }\n'
        "}"
    )
    
    try:
        response = requests.get(compoundwikiEP, params={"query": sparqlquery_full, "format": "json"})
        if response.status_code != 200:
            return jsonify({"error": "SPARQL query failed"}), 500
        
        data = response.json()
        compound_list = []
        
        for result in data.get("results", {}).get("bindings", []):
            compound_list.append({
                "ID": result.get("ID", {}).get("value", "NA"),
                "Term": result.get("Term", {}).get("value", "NA"),
                "SMILES": result.get("SMILES", {}).get("value", "NA"),
                "cid": result.get("cid", {}).get("value", "NA")
            })
            
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    
    return jsonify(compound_list), 200

@aop_app.route("/get_compounds", methods=["GET"])
def get_compounds_VHP():
    """
    Get compounds related to VHP (Q2059).
    
    Returns:
        tuple: JSON response with compound data and status code
    """
    return get_compounds_q("Q2059")

@aop_app.route("/get_compound_identifiers/<cwid>")
def show_compounds_identifiers_as_json(cwid):
    """
    Get compound identifiers for a specific compound.
    
    Args:
        cwid (str): Compound Wikibase ID (must be valid QID format)
        
    Returns:
        tuple: JSON response with property labels and values, or error message
    """
    if not is_valid_qid(cwid):
        return jsonify({"error": "Invalid compound identifier"}), 400
    
    compoundwikiEP = "https://compoundcloud.wikibase.cloud/query/sparql"
    sparqlquery = (
        "PREFIX wd: <https://compoundcloud.wikibase.cloud/entity/>\n"
        "PREFIX wdt: <https://compoundcloud.wikibase.cloud/prop/direct/>\n\n"
        "SELECT ?propertyLabel ?value\n"
        "WHERE {\n"
        "  VALUES ?property { wd:P3 wd:P2 wd:P32 }\n"
        "  ?property wikibase:directClaim ?valueProp .\n"
        "  OPTIONAL { wd:" + cwid + " ?valueProp ?value }\n"
        '  SERVICE wikibase:label { bd:serviceParam wikibase:language "[AUTO_LANGUAGE],en". }\n'
        "}"
    )
    
    try:
        response = requests.get(compoundwikiEP, params={"query": sparqlquery, "format": "json"})
        if response.status_code != 200:
            return jsonify({"error": "SPARQL query failed"}), 500
        
        data = response.json()
        compound_list = []
        
        for result in data.get("results", {}).get("bindings", []):
            compound_list.append({
                "propertyLabel": result.get("propertyLabel", {}).get("value", ""),
                "value": result.get("value", {}).get("value", "")
            })
            
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    
    return jsonify(compound_list), 200

@aop_app.route("/get_compound_expdata/<cwid>")
def show_compounds_expdata_as_json(cwid):
    """
    Get experimental data for a specific compound from Wikidata.
    
    Args:
        cwid (str): Compound Wikibase ID (must be valid QID format)
        
    Returns:
        tuple: JSON response with experimental property data including values, units, sources, and DOIs
    """
    if not is_valid_qid(cwid):
        return jsonify({"error": "Invalid compound identifier"}), 400
    
    compoundwikiEP = "https://compoundcloud.wikibase.cloud/query/sparql"
    sparqlquery = (
        "PREFIX wd: <https://compoundcloud.wikibase.cloud/entity/>\n"
        "PREFIX wdt: <https://compoundcloud.wikibase.cloud/prop/direct/>\n"
        "PREFIX wid: <http://www.wikidata.org/entity/>\n"
        "PREFIX widt: <http://www.wikidata.org/prop/direct/>\n"
        "PREFIX prov: <http://www.w3.org/ns/prov#>\n\n"
        "SELECT ?propEntityLabel ?value ?unitsLabel ?source ?doi\n"
        "WHERE {\n"
        "  wd:P5 wikibase:directClaim ?identifierProp .\n"
        "  wd:" + cwid + " ?identifierProp ?wikidata .\n"
        '  BIND (iri(CONCAT("http://www.wikidata.org/entity/", ?wikidata)) AS ?qid)\n'
        "  SERVICE <https://query.wikidata.org/sparql> {\n"
        "    ?qid ?propp ?statement .\n"
        "    ?statement a wikibase:BestRank ;\n"
        "      ?proppsv [ wikibase:quantityAmount ?value ; wikibase:quantityUnit ?units ] .\n"
        "    OPTIONAL { ?statement prov:wasDerivedFrom/pr:P248 ?source . OPTIONAL { ?source wdt:P356 ?doi . } }\n"
        "    ?property wikibase:claim ?propp ; wikibase:statementValue ?proppsv ; widt:P1629 ?propEntity ; widt:P31 wid:Q21077852 .\n"
        "    ?propEntity rdfs:label ?propEntityLabel . FILTER ( lang(?propEntityLabel) = 'en' )\n"
        "    ?units rdfs:label ?unitsLabel . FILTER ( lang(?unitsLabel) = 'en' )\n"
        '    BIND (COALESCE(IF(BOUND(?source), ?source, 1/0), "") AS ?source)\n'
        '    BIND (COALESCE(IF(BOUND(?doi), ?doi, 1/0), "") AS ?doi)\n'
        "  }\n"
        '  SERVICE wikibase:label { bd:serviceParam wikibase:language "[AUTO_LANGUAGE],en". }\n'
        "}"
    )
    
    try:
        response = requests.get(compoundwikiEP, params={"query": sparqlquery, "format": "json"})
        if response.status_code != 200:
            return jsonify({"error": "SPARQL query failed"}), 500
        
        data = response.json()
        compound_list = []
        
        for result in data.get("results", {}).get("bindings", []):
            compound_list.append({
                "propEntityLabel": result.get("propEntityLabel", {}).get("value", ""),
                "value": result.get("value", {}).get("value", ""),
                "unitsLabel": result.get("unitsLabel", {}).get("value", ""),
                "source": result.get("source", {}).get("value", ""),
                "doi": result.get("doi", {}).get("value", "")
            })
            
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    
    return jsonify(compound_list), 200

@aop_app.route("/get_compound_properties/<cwid>")
def show_compounds_properties_as_json(cwid):
    """
    Get basic properties for a specific compound including InChI key and SMILES.
    
    Args:
        cwid (str): Compound Wikibase ID (must be valid QID format)
        
    Returns:
        tuple: JSON response with compound properties or error message
    """
    if not is_valid_qid(cwid):
        return jsonify({"error": "Invalid compound identifier"}), 400
    
    compoundwikiEP = "https://compoundcloud.wikibase.cloud/query/sparql"
    sparqlquery = (
        "PREFIX wd: <https://compoundcloud.wikibase.cloud/entity/>\n"
        "PREFIX wdt: <https://compoundcloud.wikibase.cloud/prop/direct/>\n\n"
        "SELECT ?cmp ?cmpLabel ?inchiKey ?SMILES WHERE {\n"
        "  VALUES ?cmp { wd:" + cwid + " }\n"
        "  ?cmp wdt:P10 ?inchiKey .\n"
        "  OPTIONAL { ?cmp wdt:P7 ?chiralSMILES }\n"
        "  OPTIONAL { ?cmp wdt:P12 ?nonchiralSMILES }\n"
        '  BIND (COALESCE(IF(BOUND(?chiralSMILES), ?chiralSMILES, 1/0), IF(BOUND(?nonchiralSMILES), ?nonchiralSMILES, 1/0), "") AS ?SMILES)\n'
        '  SERVICE wikibase:label { bd:serviceParam wikibase:language "[AUTO_LANGUAGE],en". }\n'
        "}"
    )
    
    try:
        response = requests.get(compoundwikiEP, params={"query": sparqlquery, "format": "json"})
        if response.status_code != 200:
            return jsonify({"error": "SPARQL query failed"}), 500
        
        data = response.json()
        bindings = data.get("results", {}).get("bindings", [])
        
        if not bindings:
            return jsonify({"error": "No data found"}), 404
        
        result = bindings[0]
        compound_list = [{
            "wcid": result.get("cmp", {}).get("value", ""),
            "label": result.get("cmpLabel", {}).get("value", ""),
            "inchikey": result.get("inchiKey", {}).get("value", ""),
            "SMILES": result.get("SMILES", {}).get("value", "")
        }]
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    
    return jsonify(compound_list), 200

@aop_app.route("/get_compounds_parkinson", methods=["GET"])
def get_compounds_VHP_CS2():
    """
    Get compounds related to Parkinson's disease (Q5050).
    
    Returns:
        tuple: JSON response with compound data and status code
    """
    return get_compounds_q("Q5050")

@aop_app.route("/get_compounds/<qid>", methods=["GET"])
def get_compounds_by_qid(qid):
    """
    Get compounds for a specific QID.
    
    Args:
        qid (str): Wikibase QID identifier
        
    Returns:
        tuple: JSON response with compound data or error message
    """
    if not is_valid_qid(qid):
        return jsonify({"error": "Invalid identifier format"}), 400
    return get_compounds_q(qid)

def fetch_predictions(smiles, models, metadata, threshold=6.5):
    url = "https://qsprpred.cloud.vhp4safety.nl/api"
    headers = {
        "User-Agent": "Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:135.0) Gecko/20100101 Firefox/135.0",
        "Accept": "*/*",
        "Accept-Language": "en-US,en;q=0.5",
        "Content-Type": "application/json",
        "Sec-Fetch-Dest": "empty",
        "Sec-Fetch-Mode": "cors",
        "Sec-Fetch-Site": "cross-site",
        "Priority": "u=0",
    }
    body = {"smiles": smiles, "models": models, "format": "json"}
    try:
        response = requests.post(
            url, headers=headers, data=json.dumps(body), timeout=20
        )
    except Exception as e:
        return {"error": str(e)}
    if response.status_code == 200:
        try:
            predictions = response.json()
        except Exception as e:
            return {"error": str(e)}
        filtered_predictions = []
        for prediction in predictions:
            try:
                filtered_prediction = {"smiles": prediction["smiles"]}
                for key, value in prediction.items():
                    if key != "smiles":
                        try:
                            val = float(value)
                        except Exception:
                            continue
                        if val >= threshold:
                            new_key = re.sub(r"prediction \((.+)\)", r"\1", key)
                            filtered_prediction[new_key] = value
                if models and models[0] in metadata:
                    filtered_prediction.update(metadata.get(models[0], {}))
                filtered_predictions.append(filtered_prediction)
            except Exception:
                continue
        return filtered_predictions
    else:
        return {"error": response.text}

@aop_app.route("/get_predictions", methods=["POST"])
def get_predictions():
    """
    Get QSPR predictions for compounds using specified models.
    """
    data = request.get_json(silent=True)
    if not data:
        return jsonify({"error": "Invalid JSON input"}), 400
    smiles = [i for i in data.get("smiles", []) if i != '']
    models = data.get("models", [])
    metadata = data.get("metadata", {})
    try:
        threshold = float(data.get("threshold", 6.5))
    except Exception:
        threshold = 6.5
    results = fetch_predictions(smiles, models, metadata, threshold)
    return jsonify(results)

AOPWIKISPARQL_ENDPOINT = "https://aopwiki.rdf.bigcat-bioinformatics.org/sparql/"

def extract_ker_id(ker_uri):
    return ker_uri.split("/")[-1] if ker_uri else "Unknown"

def fetch_sparql_data(query):
    print("=== Fetching SPARQL Data ===")
    print(f"SPARQL endpoint: {AOPWIKISPARQL_ENDPOINT}")
    print(f"Query preview: {query}...")
    
    try:
        print("Making HTTP request to SPARQL endpoint...")
        response = requests.get(
            AOPWIKISPARQL_ENDPOINT,
            params={"query": query, "format": "json"},
            timeout=10,
        )
        print(f"HTTP response status: {response.status_code}")
        print(f"Response headers: {dict(response.headers)}")
        
    except Exception as e:
        print(f"ERROR: HTTP request failed: {str(e)}")
        return {"error": str(e)}
    
    if response.status_code != 200:
        print(f"ERROR: SPARQL endpoint returned status {response.status_code}")
        print(f"Response text: {response.text[:500]}...")
        return {"error": "Failed to fetch SPARQL data"}
    
    try:
        print("Parsing JSON response...")
        data = response.json()
        print(f"JSON parsing successful")
        print(f"Response structure: {list(data.keys()) if isinstance(data, dict) else type(data)}")
        
        if isinstance(data, dict) and "results" in data:
            bindings = data.get("results", {}).get("bindings", [])
            print(f"Number of SPARQL result bindings: {len(bindings)}")
        
    except Exception as e:
        print(f"ERROR: JSON parsing failed: {str(e)}")
        print(f"Response text (first 500 chars): {response.text[:500]}")
        return {"error": str(e)}
    
    print("Processing SPARQL results into Cytoscape elements...")
    cytoscape_elements = []
    node_dict = {}
    
    # Track what we found for reporting
    mie_count = 0
    ao_count = 0
    ke_count = 0
    ker_count = 0
    
    for i, result in enumerate(data.get("results", {}).get("bindings", [])):
        if i < 3:  # Debug first few results
            print(f"Processing result {i}: {result}")
        
        # Extract all values, using "NA" for missing ones
        ke_upstream = result.get("KE_upstream", {}).get("value", "NA")
        ke_upstream_title = result.get("KE_upstream_title", {}).get("value", "NA")
        ke_downstream = result.get("KE_downstream", {}).get("value", "NA")
        ke_downstream_title = result.get("KE_downstream_title", {}).get("value", "NA")
        mie = result.get("MIE", {}).get("value", "")
        mie_title = result.get("MIEtitle", {}).get("value", "")
        ao = result.get("ao", {}).get("value", "")
        ao_title = result.get("AOtitle", {}).get("value", "")
        ker_uri = result.get("KER", {}).get("value", "NA")
        ker_id = extract_ker_id(ker_uri) if ker_uri != "NA" else "NA"
        aop = result.get("aop", {}).get("value", "")
        aop_title = result.get("aop_title", {}).get("value", "")
        
        # Always process MIE node if it exists
        if mie:
            if mie not in node_dict:
                node_dict[mie] = {
                    "data": {
                        "id": mie,
                        "label": mie_title if mie_title else "NA",
                        "KEupTitle": mie_title if mie_title else "NA",
                        "is_mie": True,
                        "type": "mie",
                        "uniprot_id": result.get("uniprot_id", {}).get("value", ""),
                        "protein_name": result.get("protein_name", {}).get("value", ""),
                        "organ": result.get("KE_upstream_organ", {}).get("value", ""),
                        "aop": [aop] if aop else [],
                        "aop_title": [aop_title] if aop_title else [],
                    }
                }
                mie_count += 1
            else:
                # Update existing MIE with additional AOP info
                if aop and aop not in node_dict[mie]["data"]["aop"]:
                    node_dict[mie]["data"]["aop"].append(aop)
                if aop_title and aop_title not in node_dict[mie]["data"]["aop_title"]:
                    node_dict[mie]["data"]["aop_title"].append(aop_title)

        # Always process AO node if it exists
        if ao:
            if ao not in node_dict:
                node_dict[ao] = {
                    "data": {
                        "id": ao,
                        "label": ao_title if ao_title else "NA",
                        "is_ao": True,
                        "type": "ao",
                        "uniprot_id": result.get("uniprot_id", {}).get("value", ""),
                        "protein_name": result.get("protein_name", {}).get("value", ""),
                        "organ": result.get("KE_downstream_organ", {}).get("value", ""),
                        "aop": [aop] if aop else [],
                        "aop_title": [aop_title] if aop_title else [],
                    }
                }
                ao_count += 1
            else:
                # Update existing AO with additional AOP info
                if aop and aop not in node_dict[ao]["data"]["aop"]:
                    node_dict[ao]["data"]["aop"].append(aop)
                if aop_title and aop_title not in node_dict[ao]["data"]["aop_title"]:
                    node_dict[ao]["data"]["aop_title"].append(aop_title)

        # Process intermediate KE nodes only if they exist and are different from MIE/AO
        if ke_upstream != "NA" and ke_upstream not in [mie, ao]:
            if ke_upstream not in node_dict:
                node_dict[ke_upstream] = {
                    "data": {
                        "id": ke_upstream,
                        "label": ke_upstream_title if ke_upstream_title != "NA" else "NA",
                        "KEupTitle": ke_upstream_title if ke_upstream_title != "NA" else "NA",
                        "is_mie": False,
                        "is_ao": False,
                        "type": "key_event",
                        "uniprot_id": result.get("uniprot_id", {}).get("value", ""),
                        "protein_name": result.get("protein_name", {}).get("value", ""),
                        "organ": result.get("KE_upstream_organ", {}).get("value", ""),
                        "aop": [aop] if aop else [],
                        "aop_title": [aop_title] if aop_title else [],
                    }
                }
                ke_count += 1
            else:
                # Update existing KE with additional AOP info
                if aop and aop not in node_dict[ke_upstream]["data"]["aop"]:
                    node_dict[ke_upstream]["data"]["aop"].append(aop)
                if aop_title and aop_title not in node_dict[ke_upstream]["data"]["aop_title"]:
                    node_dict[ke_upstream]["data"]["aop_title"].append(aop_title)
                
        if ke_downstream != "NA" and ke_downstream not in [mie, ao]:
            if ke_downstream not in node_dict:
                node_dict[ke_downstream] = {
                    "data": {
                        "id": ke_downstream,
                        "label": ke_downstream_title if ke_downstream_title != "NA" else "NA",
                        "is_mie": False,
                        "is_ao": False,
                        "type": "key_event",
                        "uniprot_id": result.get("uniprot_id", {}).get("value", ""),
                        "protein_name": result.get("protein_name", {}).get("value", ""),
                        "organ": result.get("KE_downstream_organ", {}).get("value", ""),
                        "aop": [aop] if aop else [],
                        "aop_title": [aop_title] if aop_title else [],
                    }
                }
                ke_count += 1
            else:
                # Update existing KE with additional AOP info
                if aop and aop not in node_dict[ke_downstream]["data"]["aop"]:
                    node_dict[ke_downstream]["data"]["aop"].append(aop)
                if aop_title and aop_title not in node_dict[ke_downstream]["data"]["aop_title"]:
                    node_dict[ke_downstream]["data"]["aop_title"].append(aop_title)

        # Only create edges if we have actual KER data (not "NA")
        if (ker_uri != "NA" and ke_upstream != "NA" and ke_downstream != "NA"):
            edge_id = f"{ke_upstream}_{ke_downstream}"
            # Check if edge already exists
            edge_exists = any(edge["data"]["id"] == edge_id for edge in cytoscape_elements)
            if not edge_exists:
                cytoscape_elements.append({
                    "data": {
                        "id": edge_id,
                        "source": ke_upstream,
                        "target": ke_downstream,
                        "curie": f"aop.relationships:{ker_id}",
                        "ker_label": ker_id,
                        "type": "key_event_relationship"
                    }
                })
                ker_count += 1
    
    final_elements = list(node_dict.values()) + cytoscape_elements
    print(f"Created {len(node_dict)} nodes and {len(cytoscape_elements)} edges")
    print(f"MIEs: {mie_count}, AOs: {ao_count}, KEs: {ke_count}, KERs: {ker_count}")
    
    # Prepare detailed report
    report = {
        "total_nodes": len(node_dict),
        "total_edges": len(cytoscape_elements),
        "mie_count": mie_count,
        "ao_count": ao_count,
        "ke_count": ke_count,
        "ker_count": ker_count,
        "has_complete_pathways": ker_count > 0
    }
    
    return {
        "elements": final_elements,
        "report": report
    }

@aop_app.route("/get_aop_network")
def get_aop_network():
    """
    Get AOP (Adverse Outcome Pathway) network data for specified MIEs.
    
    Query Parameters:
        mies (str): Space-separated list of MIE identifiers
        
    Returns:
        tuple: JSON response with Cytoscape-formatted network elements
    """
    mies = request.args.get("mies", "")
    return get_aop_network_by_mies(mies)

def get_aop_network_by_mies(mies):
    if not mies:
        return jsonify({"error": "MIEs parameter is required"}), 400
    AOPWIKIPARKINSONSPARQL_QUERY = (
        "SELECT DISTINCT ?aop ?aop_title ?MIEtitle ?MIE ?KE_downstream ?KE_downstream_title  ?KER ?ao ?AOtitle ?KE_upstream ?KE_upstream_title ?KE_upstream_organ ?KE_downstream_organ\n"
        "WHERE {\n"
        "  VALUES ?MIE { " + mies + " }\n"
        "  ?aop a aopo:AdverseOutcomePathway ;\n"
        "       dc:title ?aop_title ;\n"
        "       aopo:has_adverse_outcome ?ao ;\n"
        "       aopo:has_molecular_initiating_event ?MIE .\n"
        "  ?MIE dc:title ?MIEtitle .\n"
        "  ?aop aopo:has_key_event_relationship ?KER .\n"
        "  ?KER a aopo:KeyEventRelationship ;\n"
        "       aopo:has_upstream_key_event ?KE_upstream ;\n"
        "       aopo:has_downstream_key_event ?KE_downstream .\n"
        "  ?KE_upstream dc:title ?KE_upstream_title .\n"
        "  ?KE_downstream dc:title ?KE_downstream_title .\n"
        "  OPTIONAL { ?KE_upstream aopo:OrganContext ?KE_upstream_organ . ?KE_downstream aopo:OrganContext ?KE_downstream_organ . }\n"
        "}"
    )
    data = fetch_sparql_data(AOPWIKIPARKINSONSPARQL_QUERY)
    return jsonify(data)

@aop_app.route("/js/aop_app/populate_qsprpred.js")
def serve_populate_qsprpred_js():
    """
    Serve the populate_qsprpred.js JavaScript file.
    
    Returns:
        File response or error JSON
    """
    try:
        return send_file("js/aop_app/populate_qsprpred.js")
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@aop_app.route("/js/aop_app/populate_aop_network.js")
def serve_populate_aop_network_js():
    """
    Serve the populate_aop_network.js JavaScript file.
    
    Returns:
        File response or error JSON
    """
    try:
        return send_file("js/aop_app/populate_aop_network.js")
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@aop_app.route("/js/aop_app/predict_qspr.js")
def serve_predict_qspr_js():
    """
    Serve the predict_qspr.js JavaScript file.
    
    Returns:
        File response or error JSON
    """
    try:
        return send_file("js/aop_app/predict_qspr.js")
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# Gene-related functions - SINGLE DEFINITION
def load_case_mie_model(mie_query):
    try:
        df = pd.read_csv(
            os.path.join(os.path.dirname(__file__), "../static/data/caseMieModel.csv"),
            dtype=str,
        )
    except Exception as e:
        raise Exception("CSV load error: " + str(e))
    mie_ids = []
    for mie in mie_query.split():
        if "aop.events:" in mie:
            parts = mie.split("aop.events:")
            if len(parts) > 1 and parts[1]:
                mie_ids.append(parts[1])
    df["MIE/KE identifier in AOP wiki"] = df["MIE/KE identifier in AOP wiki"].astype(
        str
    )
    filtered_df = df[df["MIE/KE identifier in AOP wiki"].isin(mie_ids)]
    return filtered_df

@aop_app.route("/get_case_mie_model", methods=["GET"])
def get_case_mie_model():
    """
    Get model to MIE mapping for case studies.
    
    Query Parameters:
        mie_query (str): MIE query string containing AOP event identifiers
        
    Returns:
        tuple: JSON response with model to MIE mapping dictionary
    """
    mie_query = request.args.get("mie_query", "")
    if not mie_query:
        return jsonify({"error": "mie_query parameter is required"}), 400
    try:
        filtered_df = load_case_mie_model(mie_query)
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    model_to_mie = filtered_df.set_index("qsprpred_model")[
        "MIE/KE identifier in AOP wiki"
    ].to_dict()
    return jsonify(model_to_mie), 200

@aop_app.route("/load_and_show_genes", methods=["GET"])
def load_and_show_genes():
    """Load and return gene data (UniProt and Ensembl) for specified MIEs."""
    mies = request.args.get("mies", "")
    if not mies:
        return jsonify({"error": "mies parameter is required"}), 400
    
    # Parse MIE identifiers more robustly
    mie_ids = []
    raw_mies = mies.replace(",", " ").split()
    
    for mie in raw_mies:
        mie = mie.strip()
        if not mie:
            continue
            
        # Extract numeric ID from various formats
        if "https://identifiers.org/aop.events/" in mie:
            numeric_id = mie.split("https://identifiers.org/aop.events/")[-1]
        elif "aop.events:" in mie:
            numeric_id = mie.split("aop.events:")[-1]
        else:
            numeric_id = mie
            
        if numeric_id and numeric_id.isdigit():
            mie_ids.append(numeric_id)
    
    if not mie_ids:
        return jsonify({"error": "No valid MIE identifiers found"}), 400
    
    gene_elements = []
    csv_path = os.path.join(os.path.dirname(__file__), "../static/data/caseMieModel.csv")
    
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
                    gene_elements.append({
                        "data": {
                            "id": uniprot_node_id,
                            "label": protein_name or uniprot_id,
                            "type": "uniprot",
                            "uniprot_id": uniprot_id
                        },
                        "classes": "uniprot-node"
                    })
                    
                    # Add Ensembl node  
                    gene_elements.append({
                        "data": {
                            "id": ensembl_node_id,
                            "label": ensembl_id,
                            "type": "ensembl",
                            "ensembl_id": ensembl_id
                        },
                        "classes": "ensembl-node"
                    })
                    
                    # Add edge from MIE to UniProt - check that MIE node exists first
                    gene_elements.append({
                        "data": {
                            "id": f"{mie_node_id}_{uniprot_node_id}",
                            "source": uniprot_node_id,
                            "target": mie_node_id,
                            "label": "part of"
                        }
                    })
                    
                    # Add edge from UniProt to Ensembl
                    gene_elements.append({
                        "data": {
                            "id": f"{uniprot_node_id}_{ensembl_node_id}",
                            "source": uniprot_node_id,
                            "target": ensembl_node_id,
                            "label": "translates to"
                        }
                    })
                    
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    
    return jsonify(gene_elements), 200

@aop_app.route("/toggle_genes", methods=["POST"])
def toggle_genes():
    """Toggle gene visibility in the network using proper data models."""
    try:
        data = request.get_json(silent=True)
        if not data or "action" not in data:
            return jsonify({"error": "Action parameter required"}), 400
        
        action = data["action"]
        
        if action == "show":
            cy_elements = data.get("cy_elements", [])
            # Extract MIE node IDs from existing network
            mie_node_ids = []
            for element in cy_elements:
                element_data = element.get("data", {})
                element_id = element_data.get("id", "")
                if "aop.events" in element_id and element_data.get("is_mie"):
                    mie_node_ids.append(element_id)
            
            if mie_node_ids:
                gene_elements = load_and_show_genes_for_mies(mie_node_ids)
                if isinstance(gene_elements, tuple):
                    gene_data = gene_elements[0].get_json()["gene_elements"]
                else:
                    gene_data = gene_elements.get("gene_elements", [])
                
                # Add gene data using proper service method
                if aop_service.get_current_network():
                    result = aop_service.add_gene_data(gene_data)
                    # Return updated network
                    updated_network = aop_service.get_network_cytoscape()
                    return jsonify({"gene_elements": updated_network}), 200
                else:
                    return jsonify({"gene_elements": gene_data}), 200
            else:
                return jsonify({"gene_elements": []}), 200

        elif action == "hide":
            # Filter out gene nodes from current network
            if aop_service.get_current_network():
                filtered_elements = []
                for element in aop_service.get_network_cytoscape():
                    element_data = element.get("data", {})
                    element_type = element_data.get("type", "")
                    if element_type not in ["uniprot", "ensembl"]:
                        filtered_elements.append(element)
                return jsonify(filtered_elements), 200
            return jsonify({"success": True}), 200
        else:
            return jsonify({"error": "Invalid action"}), 400
            
    except Exception as e:
        return jsonify({"error": str(e)}), 500

def load_and_show_genes_for_mies(mie_node_ids):
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
        return jsonify({"gene_elements": []}), 200
    
    gene_elements = []
    csv_path = os.path.join(os.path.dirname(__file__), "../static/data/caseMieModel.csv")
    
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
                    gene_elements.append({
                        "data": {
                            "id": uniprot_node_id,
                            "label": protein_name or uniprot_id,
                            "type": "uniprot",
                            "uniprot_id": uniprot_id
                        },
                        "classes": "uniprot-node"
                    })
                    
                    # Add Ensembl node  
                    gene_elements.append({
                        "data": {
                            "id": ensembl_node_id,
                            "label": ensembl_id,
                            "type": "ensembl",
                            "ensembl_id": ensembl_id
                        },
                        "classes": "ensembl-node"
                    })
                    
                    # Add edge from MIE to UniProt
                    gene_elements.append({
                        "data": {
                            "id": f"{mie_node_id}_{uniprot_node_id}",
                            "source": uniprot_node_id,
                            "target": mie_node_id,
                            "label": "part of"
                        }
                    })
                    
                    # Add edge from UniProt to Ensembl
                    gene_elements.append({
                        "data": {
                            "id": f"{uniprot_node_id}_{ensembl_node_id}",
                            "source": uniprot_node_id,
                            "target": ensembl_node_id,
                            "label": "translates to"
                        }
                    })
                    
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    
    return jsonify({"gene_elements": gene_elements}), 200

@aop_app.route("/toggle_bounding_boxes", methods=["POST"])
def toggle_bounding_boxes():
    """Toggle bounding boxes on/off in the network."""
    try:
        data = request.get_json(silent=True)
        if not data or "action" not in data or "cy_elements" not in data:
            return jsonify({"error": "Invalid input"}), 400
        
        action = data["action"]
        cy_elements = data["cy_elements"]
        
        if action == "remove":
            # Remove bounding boxes and unparent nodes
            filtered_elements = []
            for element in cy_elements:
                if not element.get("classes") == "bounding-box":
                    # Remove parent property
                    if "parent" in element.get("data", {}):
                        del element["data"]["parent"]
                    filtered_elements.append(element)
            return jsonify(filtered_elements), 200
        elif action == "add":
            # Use existing add_aop_bounding_box logic
            bounding_boxes = []
            seen = set()
            
            # Only process nodes with valid AOP data
            for element in cy_elements:
                if element.get("group") == "edges" or element.get("classes") == "bounding-box":
                    continue
                    
                element_data = element.get('data', {})
                node_aop = element_data.get('aop', [])
                aop_titles = element_data.get('aop_title', [])
                
                # Skip elements without AOP data
                if not node_aop or not aop_titles:
                    continue
                    
                if not isinstance(node_aop, list):
                    node_aop = [node_aop]
                if not isinstance(aop_titles, list):
                    aop_titles = [aop_titles]
                    
                for aop_item, aop_title in zip(node_aop, aop_titles):
                    if aop_item and aop_item not in seen:
                        bounding_boxes.append({
                            "group": "nodes",
                            "data": {
                                "id": f"bounding-box-{aop_item}",
                                "label": f"{aop_title} (aop:{aop_item.replace('https://identifiers.org/aop/', '')})"},
                            "classes": "bounding-box"
                        })
                        seen.add(aop_item)

            # Only assign parent to elements with valid AOP data
            for element in cy_elements:
                if element.get("group") == "edges" or element.get("classes") == "bounding-box":
                    continue
                    
                element_data = element.get('data', {})
                node_aop = element_data.get('aop', [])
                
                if not node_aop:
                    continue
                    
                if not isinstance(node_aop, list):
                    node_aop = [node_aop]
                for aop_item in node_aop:
                    if aop_item:
                        element['data']['parent'] = f"bounding-box-{aop_item}"
                        break  # Only assign to first valid AOP
                        
            return jsonify(cy_elements + bounding_boxes), 200
        else:
            return jsonify({"error": "Invalid action"}), 400
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@aop_app.route("/get_all_genes", methods=["POST"])
def get_all_genes():
    """Get all genes from Cytoscape elements."""
    try:
        data = request.get_json(silent=True)
        if not data or "cy_elements" not in data:
            return jsonify({"error": "Cytoscape elements required"}), 400
        
        cy_elements = data["cy_elements"]
        genes = []
        
        for element in cy_elements:
            element_data = element.get("data", element)
            element_classes = element.get("classes", "")
            element_type = element_data.get("type", "")
            element_id = element_data.get("id", "")
            
            # Check for Ensembl nodes
            if (element_classes == "ensembl-node" or 
                element_type == "ensembl" or
                element_id.startswith("ensembl_")):
                
                gene_label = element_data.get("label", "")
                if gene_label:
                    genes.append(gene_label)
        
        return jsonify({"genes": genes}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@aop_app.route("/get_go_processes", methods=["GET"])
def get_go_processes():
    """
    Get GO biological processes for Key Events in the network.
    
    Query Parameters:
        cy_elements (str): JSON string of Cytoscape elements
        include_hierarchy (str): 'true' to include GO hierarchy relationships
        
    Returns:
        JSON response with GO processes and optionally hierarchy relationships
    """
    try:
        cy_elements_str = request.args.get('cy_elements', '[]')
        include_hierarchy = request.args.get('include_hierarchy', 'false').lower() == 'true'
        
        # Parse the cytoscape elements
        cy_elements = json.loads(cy_elements_str)

        # Extract Key Event nodes
        ke_nodes = []
        for element in cy_elements:
            if element.get('group') == 'nodes' or 'group' not in element:
                data = element.get('data', {})
                element_id = data.get('id', '')
                
                # Check if it's a Key Event (AOP event)
                if 'aop.events' in element_id or element_id.startswith('https://identifiers.org/aop.events/'):
                    ke_nodes.append({
                        'id': element_id,
                        'label': data.get('label', ''),
                        'title': data.get('KEupTitle', data.get('label', ''))
                    })

        if not ke_nodes:
            return jsonify({
                'error': False,
                'message': 'No Key Events found in current network',
                'processes': []
            })
        result = {}  #TODO Implement querying
        return jsonify(result)
        
    except json.JSONDecodeError as e:
        return jsonify({'error': f'Invalid JSON in cy_elements: {str(e)}'}), 400
    except Exception as e:
        return jsonify({'error': f'Server error: {str(e)}'}), 500

@aop_app.route("/populate_aop_table", methods=["POST"])
def populate_aop_table():
    """Populate AOP table from Cytoscape elements with enhanced data."""
    try:
        data = request.get_json(silent=True)
        if not data or "cy_elements" not in data:
            return jsonify({"error": "Cytoscape elements required"}), 400
        
        cy_elements = data["cy_elements"]
        aop_data = []
        
        # Create a lookup for node labels and AOP data
        node_data = {}
        connected_nodes = set()
        
        for element in cy_elements:
            if element.get("group") != "edges" and element.get("classes") != "bounding-box":
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
                        "aop_title": element_data.get("aop_title", [])
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
                        source_aop_titles = [source_aop_titles] if source_aop_titles else []
                    
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
                        target_aop_titles = [target_aop_titles] if target_aop_titles else []
                    
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
                    aop_titles_string = "; ".join(sorted(list(aop_titles))) if aop_titles else "N/A"

                    aop_data.append({
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
                        "is_connected": True
                    })
        
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
                aop_titles_string = "; ".join(sorted(node_aop_titles)) if node_aop_titles else "N/A"
                
                aop_data.append({
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
                    "is_connected": False
                })
        
        return jsonify({"aop_data": aop_data}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@aop_app.route("/save_network_state", methods=["POST"])
def save_network_state():
    """Save current network state to persistent storage."""
    try:
        data = request.get_json(silent=True)
        if not data:
            return jsonify({"error": "No data provided"}), 400
        
        # Create directory if it doesn't exist
        os.makedirs(NETWORK_STATES_DIR, exist_ok=True)
        
        # Save with timestamp
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"network_state_{timestamp}.json"
        filepath = os.path.join(NETWORK_STATES_DIR, filename)
        
        with open(filepath, 'w') as f:
            json.dump(data, f, indent=2)
        
        return jsonify({"success": True, "filename": filename}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@aop_app.route("/load_network_state", methods=["GET"])
def load_network_state():
    """Load the most recent network state."""
    try:
        if not os.path.exists(NETWORK_STATES_DIR):
            return jsonify({"error": "No saved states found"}), 404
        
        # Find most recent file
        files = [f for f in os.listdir(NETWORK_STATES_DIR) if f.startswith("network_state_") and f.endswith(".json")]
        if not files:
            return jsonify({"error": "No saved states found"}), 404
        
        files.sort(reverse=True)  # Most recent first
        latest_file = files[0]
        filepath = os.path.join(NETWORK_STATES_DIR, latest_file)
        
        with open(filepath, 'r') as f:
            data = json.load(f)
        
        return jsonify(data), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@aop_app.route("/populate_gene_table", methods=["POST"])
def populate_gene_table():
    """Populate gene table from Cytoscape elements."""
    try:
        data = request.get_json(silent=True)
        if not data or "cy_elements" not in data:
            return jsonify({"error": "Cytoscape elements required"}), 400
        
        cy_elements = data["cy_elements"]
        gene_data = []
        
        for element in cy_elements:
            element_data = element.get("data", element)
            element_classes = element.get("classes", "")
            element_type = element_data.get("type", "")
            element_id = element_data.get("id", "")
            
            # Check for Ensembl nodes
            if (element_classes == "ensembl-node" or 
                element_type == "ensembl" or
                element_id.startswith("ensembl_")):
                
                gene_label = element_data.get("label", "")
                if gene_label and gene_label not in [g["gene"] for g in gene_data]:
                    gene_data.append({
                        "gene": gene_label,
                        "expression_cell": "Normal"  # Default value
                    })
        
        return jsonify({"gene_data": gene_data}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

def build_flexible_aop_sparql_query(query_type: str, values: str) -> str:
    """
    Build SPARQL query with OPTIONAL KER relationships.
    
    Args:
        query_type: Type of query ('mie', 'aop', 'ke_upstream', 'ke_downstream')
        values: Space-separated list of URIs or identifiers
        
    Returns:
        str: Complete SPARQL query or empty string if invalid type
    """
    
    print(f"=== Building SPARQL Query ===")
    print(f"Query type: {query_type}")
    print(f"Values: {values}")
    
    # Process values to ensure proper URI formatting
    processed_values = []
    for value in values.split():
        if value.startswith('http'):
            processed_values.append(f"<{value}>")
        else:
            processed_values.append(f"<{value}>")
    
    formatted_values = " ".join(processed_values)
    print(f"Processed values: {formatted_values}")
    
    # Base query with all KER relationships as OPTIONAL
    base_query = """SELECT DISTINCT ?aop ?aop_title ?MIEtitle ?MIE ?KE_downstream ?KE_downstream_title ?KER ?ao ?KE_upstream ?KE_upstream_title ?KE_upstream_organ ?KE_downstream_organ
WHERE {
  %VALUES_CLAUSE%
  ?aop a aopo:AdverseOutcomePathway ;
       dc:title ?aop_title ;
       aopo:has_adverse_outcome ?ao ;
       aopo:has_molecular_initiating_event ?MIE .
  ?MIE dc:title ?MIEtitle .
  OPTIONAL {
    ?aop aopo:has_key_event_relationship ?KER .
    ?KER a aopo:KeyEventRelationship ;
         aopo:has_upstream_key_event ?KE_upstream ;
         aopo:has_downstream_key_event ?KE_downstream .
    ?KE_upstream dc:title ?KE_upstream_title .
    ?KE_downstream dc:title ?KE_downstream_title .
    OPTIONAL { ?KE_upstream aopo:OrganContext ?KE_upstream_organ . ?KE_downstream aopo:OrganContext ?KE_downstream_organ . }
  }
}"""
    
    # Build VALUES clause based on query type
    values_clause = ""
    
    if query_type == "mie":
        values_clause = f"VALUES ?MIE {{ {formatted_values} }}"
    elif query_type == "aop":
        values_clause = f"VALUES ?aop {{ {formatted_values} }}"
    elif query_type == "ke_upstream":
        values_clause = f"VALUES ?KE_upstream {{ {formatted_values} }}"
    elif query_type == "ke_downstream":
        values_clause = f"VALUES ?KE_downstream {{ {formatted_values} }}"
    else:
        print(f"Invalid query type: {query_type}")
        return ""
    
    print(f"Generated VALUES clause: {values_clause}")
    
    final_query = base_query.replace("%VALUES_CLAUSE%", values_clause)
    print(f"Final query length: {len(final_query)} characters")
    print(f"Final query:\n{final_query}")
    
    return final_query

@aop_app.route("/add_aop_network_data", methods=["POST"])
def add_aop_network_data():
    """Add AOP network data based on query type and values."""
    try:
        data = request.get_json(silent=True)
        if not data:
            return jsonify({"error": "No data provided"}), 400
        
        query_type = data.get("query_type", "")
        values = data.get("values", "")
        
        if not query_type or not values:
            return jsonify({"error": "Query type and values are required"}), 400
        
        # Build SPARQL query
        sparql_query = build_flexible_aop_sparql_query(query_type, values)
        
        if not sparql_query:
            return jsonify({"error": "Invalid query type"}), 400
        
        # Execute query
        print("=== Executing SPARQL query ===")
        result = fetch_sparql_data(sparql_query)
        
        # Check for errors
        if isinstance(result, dict) and "error" in result:
            return jsonify({"error": result["error"]}), 500
        
        # Extract elements and report
        elements = result.get("elements", [])
        report = result.get("report", {})
        
        # Prepare response
        response_data = {
            "success": True,
            "elements": elements,
            "elements_count": len(elements),
            "report": report
        }
        
        # Generate specific warning message based on what was found
        warnings = []
        
        if report.get("mie_count", 0) == 0:
            warnings.append("No Molecular Initiating Events (MIEs) found")
        
        if report.get("ao_count", 0) == 0:
            warnings.append("No Adverse Outcomes (AOs) found")
            
        if report.get("ker_count", 0) == 0:
            if report.get("mie_count", 0) > 0 or report.get("ao_count", 0) > 0:
                warnings.append("No Key Event Relationships (KERs) found - only basic AOP structure available")
            else:
                warnings.append("No pathway relationships found")
        
        if report.get("ke_count", 0) == 0 and report.get("ker_count", 0) > 0:
            warnings.append("No intermediate Key Events found - only direct relationships")
        
        if warnings:
            response_data["warning"] = {
                "type": "incomplete_aop_data",
                "message": f"AOP data retrieved with limitations: {'; '.join(warnings)}",
                "details": f"Found: {report.get('mie_count', 0)} MIEs, {report.get('ao_count', 0)} AOs, {report.get('ke_count', 0)} intermediate KEs, {report.get('ker_count', 0)} KERs",
                "specific_issues": warnings
            }
        
        return jsonify(response_data), 200
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500

def convert_curie_to_iri(curie_or_namespace, local_id=None):
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
            return get_iri(curie_or_namespace, local_id) or f"{curie_or_namespace}:{local_id}"
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
