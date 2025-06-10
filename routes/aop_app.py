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
    print(f"Query preview (first 200 chars): {query[:200]}...")
    
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
    
    for i, result in enumerate(data.get("results", {}).get("bindings", [])):
        if i < 3:  # Debug first few results
            print(f"Processing result {i}: {result}")
        
        ke_upstream = result.get("KE_upstream", {}).get("value", "")
        ke_upstream_title = result.get("KE_upstream_title", {}).get("value", "")
        ke_downstream = result.get("KE_downstream", {}).get("value", "")
        ke_downstream_title = result.get("KE_downstream_title", {}).get("value", "")
        mie = result.get("MIE", {}).get("value", "")
        ao = result.get("ao", {}).get("value", "")
        ker_uri = result.get("KER", {}).get("value", "")
        ker_id = extract_ker_id(ker_uri)
        aop = result.get("aop", {}).get("value", "")
        aop_title = result.get("aop_title", {}).get("value", "")
        
        # Process nodes (existing logic)
        if ke_upstream not in node_dict:
            node_dict[ke_upstream] = {
                "data": {
                    "id": ke_upstream,
                    "label": ke_upstream_title,
                    "KEupTitle": ke_upstream_title,
                    "is_mie": ke_upstream == mie,
                    "uniprot_id": result.get("uniprot_id", {}).get("value", ""),
                    "protein_name": result.get("protein_name", {}).get("value", ""),
                    "organ": result.get("KE_upstream_organ", {}).get("value", ""),
                    "aop": [aop] if aop else [],
                    "aop_title": [aop_title] if aop_title else [],
                }
            }
        else:
            if aop and aop not in node_dict[ke_upstream]["data"]["aop"]:
                node_dict[ke_upstream]["data"]["aop"].append(aop)
            if (
                aop_title
                and aop_title not in node_dict[ke_upstream]["data"]["aop_title"]
            ):
                node_dict[ke_upstream]["data"]["aop_title"].append(aop_title)
        if ke_upstream == mie:
            node_dict[ke_upstream]["data"]["is_mie"] = True
        if ke_downstream not in node_dict:
            node_dict[ke_downstream] = {
                "data": {
                    "id": ke_downstream,
                    "label": ke_downstream_title,
                    "is_ao": ke_downstream == ao,
                    "uniprot_id": result.get("uniprot_id", {}).get("value", ""),
                    "protein_name": result.get("protein_name", {}).get("value", ""),
                    "organ": result.get("KE_downstream_organ", {}).get("value", ""),
                    "aop": [aop] if aop else [],
                    "aop_title": [aop_title] if aop_title else [],
                }
            }
        else:
            if aop and aop not in node_dict[ke_downstream]["data"]["aop"]:
                node_dict[ke_downstream]["data"]["aop"].append(aop)
            if (
                aop_title
                and aop_title not in node_dict[ke_downstream]["data"]["aop_title"]
            ):
                node_dict[ke_downstream]["data"]["aop_title"].append(aop_title)
        if ke_downstream == ao:
            node_dict[ke_downstream]["data"]["is_ao"] = True
        edge_id = f"{ke_upstream}_{ke_downstream}"
        cytoscape_elements.append(
            {
                "data": {
                    "id": edge_id,
                    "source": ke_upstream,
                    "target": ke_downstream,
                    "curie": f"aop.relationships:{ker_id}",
                    "ker_label": ker_id,
                }
            }
        )
    
    final_elements = list(node_dict.values()) + cytoscape_elements
    print(f"Created {len(node_dict)} nodes and {len(cytoscape_elements)} edges")
    print(f"Total elements to return: {len(final_elements)}")
    
    return final_elements

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
                        "expression_cell": "No expression data"
                    })
        
        return jsonify({"gene_data": gene_data}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@aop_app.route("/populate_qaop_table", methods=["POST"])
def populate_qaop_table():
    """Populate QAOP (Quantitative AOP) table from Cytoscape elements."""
    try:
        data = request.get_json(silent=True)
        if not data or "cy_elements" not in data:
            return jsonify({"error": "Cytoscape elements required"}), 400
        
        cy_elements = data["cy_elements"]
        qaop_data = []
        
        # Create a lookup for node labels
        node_labels = {}
        for element in cy_elements:
            if element.get("group") != "edges" and element.get("classes") != "bounding-box":
                element_data = element.get("data", {})
                node_id = element_data.get("id")
                node_label = element_data.get("label")
                if node_id and node_label:
                    node_labels[node_id] = node_label
        
        # Process edges with KER labels
        for element in cy_elements:
            if (element.get("group") == "edges" and 
                element.get("data", {}).get("ker_label") and
                element.get("data", {}).get("curie")):
                
                edge_data = element["data"]
                source_id = edge_data.get("source", "")
                target_id = edge_data.get("target", "")
                ker_label = edge_data.get("ker_label", "")
                curie = edge_data.get("curie", "")
                
                # Get labels from lookup
                source_label = node_labels.get(source_id, source_id)
                target_label = node_labels.get(target_id, target_id)
                
                qaop_data.append({
                    "source_id": source_id,
                    "source_label": source_label,
                    "curie": curie,
                    "target_id": target_id,
                    "target_label": target_label
                })
        
        return jsonify({"qaop_data": qaop_data}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@aop_app.route("/toggle_genes", methods=["POST"])
def toggle_genes():
    """Toggle gene visibility in the network."""
    try:
        data = request.get_json(silent=True)
        if not data or "action" not in data:
            return jsonify({"error": "Invalid input"}), 400
        
        action = data["action"]
        
        if action == "show":
            cy_elements = data.get("cy_elements", [])
            # Extract MIE node IDs from existing network
            mie_node_ids = []
            for element in cy_elements:
                element_data = element.get("data", {})
                if element_data.get("is_mie"):
                    mie_node_ids.append(element_data["id"])
            
            if mie_node_ids:
                # Extract numeric IDs from MIE node IDs
                mie_ids = []
                for mie_node_id in mie_node_ids:
                    if "https://identifiers.org/aop.events/" in mie_node_id:
                        numeric_id = mie_node_id.split("https://identifiers.org/aop.events/")[-1]
                        if numeric_id.isdigit():
                            mie_ids.append(numeric_id)
                
                if mie_ids:
                    # Load genes using existing logic but avoid duplicates
                    gene_elements = []
                    existing_element_ids = {element.get("data", {}).get("id") for element in cy_elements}
                    
                    csv_path = os.path.join(os.path.dirname(__file__), "../static/data/caseMieModel.csv")
                    
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
                                
                                # Only add elements that don't already exist
                                if uniprot_node_id not in existing_element_ids:
                                    gene_elements.append({
                                        "data": {
                                            "id": uniprot_node_id,
                                            "label": protein_name or uniprot_id,
                                            "type": "uniprot",
                                            "uniprot_id": uniprot_id
                                        },
                                        "classes": "uniprot-node"
                                    })
                                    existing_element_ids.add(uniprot_node_id)
                                
                                if ensembl_node_id not in existing_element_ids:
                                    gene_elements.append({
                                        "data": {
                                            "id": ensembl_node_id,
                                            "label": ensembl_id,
                                            "type": "ensembl",
                                            "ensembl_id": ensembl_id
                                        },
                                        "classes": "ensembl-node"
                                    })
                                    existing_element_ids.add(ensembl_node_id)
                                
                                # Only add edges if source and target exist and edge doesn't exist
                                edge_id = f"{mie_node_id}_{uniprot_node_id}"
                                if (mie_node_id in {e.get("data", {}).get("id") for e in cy_elements} and 
                                    edge_id not in existing_element_ids):
                                    gene_elements.append({
                                        "data": {
                                            "id": edge_id,
                                            "source": uniprot_node_id,
                                            "target": mie_node_id,
                                            "label": "part of"
                                        }
                                    })
                                    existing_element_ids.add(edge_id)
                                
                                edge_id2 = f"{uniprot_node_id}_{ensembl_node_id}"
                                if edge_id2 not in existing_element_ids:
                                    gene_elements.append({
                                        "data": {
                                            "id": edge_id2,
                                            "source": uniprot_node_id,
                                            "target": ensembl_node_id,
                                            "label": "translates to"
                                        }
                                    })
                                    existing_element_ids.add(edge_id2)
                    
                    return jsonify({"gene_elements": gene_elements}), 200
            
            return jsonify({"gene_elements": []}), 200
        elif action == "hide":
            # For hide action, just return success - let frontend handle the hiding
            return jsonify({"success": True}), 200
        else:
            return jsonify({"error": "Invalid action"}), 400
    except Exception as e:
        return jsonify({"error": str(e)}), 500

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
        jsonify({"error": str(e)}), 500

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
                if gene_label and gene_label not in genes:
                    genes.append(gene_label)
        
        return jsonify({"genes": genes}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# Network state storage
NETWORK_STATES_DIR = os.path.join(os.path.dirname(__file__), "../static/data/network_states")

@aop_app.route("/save_network_state", methods=["POST"])
def save_network_state():
    """Save current network state to persistent storage."""
    try:
        data = request.get_json(silent=True)
        if not data:
            return jsonify({"error": "Invalid JSON input"}), 400
        
        # Ensure network states directory exists
        os.makedirs(NETWORK_STATES_DIR, exist_ok=True)
        
        # Generate filename with timestamp
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"network_state_{timestamp}.json"
        filepath = os.path.join(NETWORK_STATES_DIR, filename)
        
        # Add server-side metadata
        data["server_metadata"] = {
            "saved_at": datetime.now().isoformat(),
            "filename": filename,
            "server_version": "1.0"
        }
        
        # Save to file
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        
        # Also save as latest (for quick loading)
        latest_filepath = os.path.join(NETWORK_STATES_DIR, "latest_network_state.json")
        with open(latest_filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        
        return jsonify({
            "success": True,
            "message": "Network state saved successfully",
            "filename": filename,
            "timestamp": data["server_metadata"]["saved_at"]
        }), 200
        
    except Exception as e:
        print(f"Error saving network state: {str(e)}")
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500

@aop_app.route("/load_network_state", methods=["GET"])
def load_network_state():
    """Load the latest network state from persistent storage."""
    try:
        latest_filepath = os.path.join(NETWORK_STATES_DIR, "latest_network_state.json")
        
        if not os.path.exists(latest_filepath):
            return jsonify({"error": "No saved network state found"}), 404
        
        with open(latest_filepath, 'r', encoding='utf-8') as f:
            network_data = json.load(f)
        
        return jsonify(network_data), 200
        
    except Exception as e:
        print(f"Error loading network state: {str(e)}")
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500

## BioDatafuse
@aop_app.route("/get_bridgedb_xref", methods=["POST"])
def get_bridgedb_xref():
    """
    Get cross-references using BridgeDb service.
    """
    data = request.get_json(silent=True)
    if not data or "identifiers" not in data:
        return jsonify({"error": "Invalid input"}), 400

    data_input = pd.DataFrame(data["identifiers"], columns=["identifier"])
    input_species = data.get("input_species", "Human")
    input_datasource = data.get("input_datasource", "PubChem Compound")
    output_datasource = data.get("output_datasource", "All")

    try:
        bridgedb_df, bridgedb_metadata = id_mapper.bridgedb_xref(
            identifiers=data_input,
            input_species=input_species,
            input_datasource=input_datasource,
            output_datasource=output_datasource,
        )
        return jsonify({
            "bridgedb_df": bridgedb_df.fillna("NaN").to_dict(orient="records"),
            "bridgedb_metadata": bridgedb_metadata
        }), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@aop_app.route("/add_bdf_opentargets", methods=["GET"])
def add_bdf_opentargets():
    """
    Get compound-disease interactions from OpenTargets using BridgeDb data.
    """
    try:
        bridgedb_data = request.args.get("bridgedb_data", "")
        if not bridgedb_data:
            return jsonify({"error": "BridgeDb data is required"}), 400

        # Parse the JSON string
        bridgedb_list = json.loads(bridgedb_data)
        
        # Convert to DataFrame
        if not bridgedb_list:
            return jsonify([]), 200
            
        bridgedb_df = pd.DataFrame(bridgedb_list)
        
        # Get OpenTargets data
        ot_df, ot_metadata = opentargets.get_compound_disease_interactions(bridgedb_df=bridgedb_df)

        # Replace NaN with None (null in JSON)
        ot_df = ot_df.where(pd.notnull(ot_df), None)

        return jsonify(ot_df.to_dict(orient="records")), 200
    except Exception as e:
        print(f"OpenTargets error: {str(e)}")
        return jsonify({"error": str(e)}), 500

@aop_app.route("/add_bdf_bgee", methods=["POST"])
def add_bdf_bgee():
    """
    Get gene expression data from Bgee using BridgeDb data.
    """
    try:
        data = request.get_json(silent=True)
        if not data or "bridgedb_data" not in data:
            return jsonify({"error": "BridgeDb data is required"}), 400

        # Convert to DataFrame
        bridgedb_list = data["bridgedb_data"]
        if not bridgedb_list:
            return jsonify({}), 200
            
        bridgedb_df = pd.DataFrame(bridgedb_list)
        
        # Get Bgee data
        bgee_df, bgee_metadata = bgee.get_gene_expression(bridgedb_df=bridgedb_df)

        # Replace NaN with None (null in JSON)
        bgee_df = bgee_df.where(pd.notnull(bgee_df), None)

        result = bgee_df.to_dict(orient="records")

        # Log the result to the server log
        print("Result of /add_bdf_bgee:", result)

        return jsonify(result), 200
    except Exception as e:
        print(f"Bgee error: {str(e)}")
        return jsonify({"error": str(e)}), 500

@aop_app.route("/populate_compound_table/<qid>", methods=["GET"])
def populate_compound_table(qid):
    """
    Populate compound table with formatted data for a specific QID.
    """
    try:
        compound_data, status = get_compounds_q(qid)
        if status != 200:
            return compound_data, status
        
        compounds = compound_data.get_json()
        compound_mapping = {}
        table_data = []
        
        for compound in compounds:
            smiles = compound.get("SMILES", "")
            cid = compound.get("cid", "")
            term = compound.get("Term", "")
            compound_id = compound.get("ID", "")
            
            compound_mapping[smiles] = {
                "term": term,
                "url": f"/compound/{compound_id}",
                "target": "_blank"
            }
            
            if cid and cid != "nan":
                pubchem_url = f"https://pubchem.ncbi.nlm.nih.gov/compound/{cid}"
                pubchem_cell = f'<a href="{pubchem_url}" class="cid-link" target="_blank">{cid}</a>'
            else:
                pubchem_cell = f'<span class="cid-link">{cid}</span>'
            
            encoded_smiles = quote(smiles, safe="")
            img_url = f"https://cdkdepict.cloud.vhp4safety.nl/depict/bot/svg?w=-1&h=-1&abbr=off&hdisp=bridgehead&showtitle=false&zoom=0.5&annotate=cip&r=0&smi={encoded_smiles}"
            
            table_data.append({
                "smiles": smiles,
                "term": term,
                "cid": cid,
                "compound_id": compound_id,
                "img_url": img_url,
                "compound_cell": f'<a href="/compound/{compound_id}" class="compound-link" target="_blank">{term}</a>',
                "pubchem_cell": pubchem_cell
            })
        
        return jsonify({
            "compound_mapping": compound_mapping,
            "table_data": table_data
        }), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

def convert_curie_to_iri(curie_or_namespace, local_id=None):
    """
    Convert CURIE to proper IRI using bioregistry.
    
    Args:
        curie_or_namespace: Either a full CURIE like "chebi:24867" or namespace like "chebi"
        local_id: Local identifier if namespace is provided separately
        
    Returns:
        str: Proper IRI URL or original string if conversion fails
    """
    try:
        if local_id:
            # Namespace and local_id provided separately
            iri = get_iri(curie_or_namespace, local_id)
        else:
            # Full CURIE provided
            iri = get_iri(curie_or_namespace)
        
        if iri:
            return iri
        else:
            # Fallback to original if bioregistry can't resolve
            print(f"Warning: Could not resolve CURIE {curie_or_namespace}:{local_id if local_id else ''}")
            return curie_or_namespace
    except Exception as e:
        print(f"Error converting CURIE {curie_or_namespace}: {str(e)}")
        return curie_or_namespace

@aop_app.route("/convert_therapeutic_areas", methods=["POST"])
def convert_therapeutic_areas():
    """
    Convert therapeutic areas with proper CURIE to IRI conversion.
    """
    try:
        data = request.get_json(silent=True)
        if not data or "therapeutic_areas" not in data:
            return jsonify({"error": "Invalid input"}), 400
        
        therapeutic_areas = data["therapeutic_areas"]
        converted_areas = []
        
        for area_string in therapeutic_areas:
            # Parse the format "ID:name, ID:name"
            areas = area_string.split(",")
            for area in areas:
                parts = area.split(":", 1)  # Split only on first colon
                if len(parts) == 2:
                    namespace_id = parts[0].strip()
                    name = parts[1].strip()
                    
                    # Try to convert using bioregistry
                    # Handle formats like "EFO_0000319" -> "efo:0000319"
                    if "_" in namespace_id:
                        namespace, local_id = namespace_id.split("_", 1)
                        namespace = namespace.lower()
                        curie = f"{namespace}:{local_id}"
                    else:
                        curie = namespace_id.lower()
                    
                    iri = convert_curie_to_iri(curie)
                    
                    converted_areas.append({
                        "original": area_string,
                        "namespace_id": namespace_id,
                        "name": name,
                        "curie": curie,
                        "iri": iri,
                        "link": f'<a href="{iri}" title="{name}" target="_blank" style="position: relative; z-index: 10;">{name}</a>'
                    })
        
        return jsonify({"converted_areas": converted_areas}), 200
        
    except Exception as e:
        print(f"Error converting therapeutic areas: {str(e)}")
        return jsonify({"error": str(e)}), 500

@aop_app.route("/add_aop_network_data", methods=["POST"])
def add_aop_network_data():
    """
    Add more AOP network data using flexible SPARQL queries.
    
    Request JSON:
        query_type (str): Type of query - 'mie', 'aop', 'ke_upstream', 'ke_downstream'
        values (str): Space-separated list of URIs or identifiers
        
    Returns:
        tuple: JSON response with new network elements or error message
    """
    try:
        print("=== AOP Network Data Request ===")
        data = request.get_json(silent=True)
        print(f"Request data: {data}")
        
        if not data or "query_type" not in data or "values" not in data:
            print("ERROR: Missing required fields in request")
            return jsonify({"error": "Query type and values are required"}), 400
        
        query_type = data["query_type"]
        values = data["values"].strip()
        
        print(f"Query type: {query_type}")
        print(f"Values: {values}")
        
        if not values:
            print("ERROR: Empty values provided")
            return jsonify({"error": "Values cannot be empty"}), 400
        
        # Build the SPARQL query based on type
        print("Building SPARQL query...")
        sparql_query = build_flexible_aop_sparql_query(query_type, values)
        
        if not sparql_query:
            print("ERROR: Failed to build SPARQL query")
            return jsonify({"error": "Invalid query type"}), 400
        
        print(f"Generated SPARQL query:\n{sparql_query}")
        
        # Execute the query
        print("Executing SPARQL query...")
        elements = fetch_sparql_data(sparql_query)
        
        print(f"SPARQL query result type: {type(elements)}")
        if isinstance(elements, dict) and "error" in elements:
            print(f"SPARQL query error: {elements}")
            return jsonify(elements), 500
        
        print(f"Number of elements returned: {len(elements) if isinstance(elements, list) else 'N/A'}")
        
        result = {
            "success": True,
            "elements": elements,
            "query_type": query_type,
            "values_used": values,
            "elements_count": len(elements) if isinstance(elements, list) else 0
        }
        
        print(f"Returning successful result with {result['elements_count']} elements")
        return jsonify(result), 200
        
    except Exception as e:
        print(f"ERROR in add_aop_network_data: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500

def build_flexible_aop_sparql_query(query_type: str, values: str) -> str:
    """
    Build SPARQL query based on query type and values.
    
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
        value = value.strip()
        if value:
            # If it looks like a full URI, wrap in angle brackets
            if value.startswith('http://') or value.startswith('https://'):
                processed_values.append(f"<{value}>")
            # If it's a prefixed identifier, keep as is
            elif ':' in value:
                processed_values.append(value)
            # If it's just a number, construct the appropriate URI based on query type
            elif value.isdigit():
                if query_type == 'aop':
                    processed_values.append(f"<https://identifiers.org/aop/{value}>")
                else:  # mie, ke_upstream, ke_downstream
                    processed_values.append(f"<https://identifiers.org/aop.events/{value}>")
            else:
                # For other formats, try to determine the appropriate URI
                if query_type == 'aop':
                    processed_values.append(f"<https://identifiers.org/aop/{value}>")
                else:  # mie, ke_upstream, ke_downstream
                    processed_values.append(f"<https://identifiers.org/aop.events/{value}>")
    
    formatted_values = " ".join(processed_values)
    print(f"Processed values: {formatted_values}")
    
    # Base query
    base_query = """SELECT DISTINCT ?aop ?aop_title ?MIEtitle ?MIE ?KE_downstream ?KE_downstream_title ?KER ?ao ?KE_upstream ?KE_upstream_title ?KE_upstream_organ ?KE_downstream_organ
WHERE {
  %VALUES_CLAUSE%
  ?aop a aopo:AdverseOutcomePathway ;
       dc:title ?aop_title ;
       aopo:has_adverse_outcome ?ao ;
       aopo:has_molecular_initiating_event ?MIE .
  ?MIE dc:title ?MIEtitle .
  ?aop aopo:has_key_event_relationship ?KER .
  ?KER a aopo:KeyEventRelationship ;
       aopo:has_upstream_key_event ?KE_upstream ;
       aopo:has_downstream_key_event ?KE_downstream .
  ?KE_upstream dc:title ?KE_upstream_title .
  ?KE_downstream dc:title ?KE_downstream_title .
  OPTIONAL { ?KE_upstream aopo:OrganContext ?KE_upstream_organ . ?KE_downstream aopo:OrganContext ?KE_downstream_organ . }
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
        print(f"ERROR: Invalid query type: {query_type}")
        return ""
    
    print(f"Generated VALUES clause: {values_clause}")
    
    final_query = base_query.replace("%VALUES_CLAUSE%", values_clause)
    print(f"Final query length: {len(final_query)} characters")
    print(f"Final query:\n{final_query}")
    
    return final_query