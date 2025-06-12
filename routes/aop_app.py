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

@aop_app.route("/toggle_genes", methods=["POST"])
def toggle_genes():
    """Toggle gene visibility in the network."""
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
                return load_and_show_genes_for_mies(mie_node_ids)
            else:
                return jsonify({"gene_elements": []}), 200

        elif action == "hide":
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
    """Toggle bounding boxes in the network visualization."""
    try:
        data = request.get_json(silent=True)
        if not data or "action" not in data:
            return jsonify({"error": "Action parameter required"}), 400
        
        action = data["action"]
        cy_elements = data.get("cy_elements", [])
        
        if action == "add":
            # Add bounding boxes logic here
            # For now, return the elements unchanged
            return jsonify(cy_elements)
        elif action == "remove":
            # Remove bounding boxes logic here
            # For now, return the elements unchanged
            return jsonify(cy_elements)
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
        
        # Mock GO processes data - in a real implementation, you would query GO database
        # For now, return some example processes based on the KE titles
        go_processes = []
        
        # Simple mapping of some common KE terms to GO processes
        go_mappings = {
            'gene expression': [
                {'id': 'GO:0010468', 'label': 'regulation of gene expression', 'uri': 'http://purl.obolibrary.org/obo/GO_0010468'},
                {'id': 'GO:0006355', 'label': 'regulation of transcription, DNA-templated', 'uri': 'http://purl.obolibrary.org/obo/GO_0006355'}
            ],
            'thyroid': [
                {'id': 'GO:0006590', 'label': 'thyroid hormone generation', 'uri': 'http://purl.obolibrary.org/obo/GO_0006590'},
                {'id': 'GO:0070324', 'label': 'thyroid hormone binding', 'uri': 'http://purl.obolibrary.org/obo/GO_0070324'}
            ],
            'cognitive': [
                {'id': 'GO:0050890', 'label': 'cognition', 'uri': 'http://purl.obolibrary.org/obo/GO_0050890'},
                {'id': 'GO:0007611', 'label': 'learning or memory', 'uri': 'http://purl.obolibrary.org/obo/GO_0007611'}
            ],
            'hippocampal': [
                {'id': 'GO:0021766', 'label': 'hippocampus development', 'uri': 'http://purl.obolibrary.org/obo/GO_0021766'},
                {'id': 'GO:0048854', 'label': 'brain morphogenesis', 'uri': 'http://purl.obolibrary.org/obo/GO_0048854'}
            ]
        }
        
        # Find relevant GO processes based on KE labels
        added_processes = set()
        for ke in ke_nodes:
            ke_label = ke['label'].lower()
            ke_title = ke['title'].lower()
            search_text = f"{ke_label} {ke_title}"
            
            for keyword, processes in go_mappings.items():
                if keyword in search_text:
                    for process in processes:
                        if process['id'] not in added_processes:
                            go_processes.append(process)
                            added_processes.add(process['id'])
        
        # If no specific matches, add some general developmental processes
        if not go_processes:
            go_processes = [
                {'id': 'GO:0032502', 'label': 'developmental process', 'uri': 'http://purl.obolibrary.org/obo/GO_0032502'},
                {'id': 'GO:0048856', 'label': 'anatomical structure development', 'uri': 'http://purl.obolibrary.org/obo/GO_0048856'}
            ]
        
        result = {'processes': go_processes}
        
        # Add hierarchy relationships if requested
        if include_hierarchy and go_processes:
            edges = []
            # Simple parent-child relationships (this would come from GO database in real implementation)
            hierarchy_map = {
                'GO:0010468': 'GO:0065007',  # regulation of gene expression -> biological regulation
                'GO:0006355': 'GO:0010468',  # regulation of transcription -> regulation of gene expression
                'GO:0006590': 'GO:0008152',  # thyroid hormone generation -> metabolic process
                'GO:0050890': 'GO:0008150',  # cognition -> biological process
                'GO:0007611': 'GO:0050890',  # learning or memory -> cognition
                'GO:0021766': 'GO:0048856',  # hippocampus development -> anatomical structure development
                'GO:0048854': 'GO:0048856'   # brain morphogenesis -> anatomical structure development
            }
            
            for child_id, parent_id in hierarchy_map.items():
                if any(p['id'] == child_id for p in go_processes):
                    # Add parent process if not already present
                    if not any(p['id'] == parent_id for p in go_processes):
                        parent_labels = {
                            'GO:0065007': 'biological regulation',
                            'GO:0008152': 'metabolic process',
                            'GO:0008150': 'biological process',
                            'GO:0048856': 'anatomical structure development'
                        }
                        if parent_id in parent_labels:
                            go_processes.append({
                                'id': parent_id,
                                'label': parent_labels[parent_id],
                                'uri': f'http://purl.obolibrary.org/obo/{parent_id.replace(":", "_")}'
                            })
                    
                    # Add edge
                    edges.append({
                        'id': f'{parent_id}_{child_id}',
                        'source': parent_id,
                        'target': child_id,
                        'type': 'go_hierarchy',
                        'label': 'is_a'
                    })
            
            result['processes'] = {
                'nodes': go_processes,
                'edges': edges
            }
        return jsonify(result)
        
    except json.JSONDecodeError as e:
        return jsonify({'error': f'Invalid JSON in cy_elements: {str(e)}'}), 400
    except Exception as e:
        return jsonify({'error': f'Server error: {str(e)}'}), 500

@aop_app.route("/query_opentargets_compounds", methods=["POST"])
def query_opentargets_compounds():
    """
    Query OpenTargets for compound data based on current network elements.
    
    Returns:
        JSON response with compound data from OpenTargets
    """
    try:
        data = request.get_json(silent=True)
        if not data or 'cy_elements' not in data:
            return jsonify({'error': 'Cytoscape elements required'}), 400
        
        cy_elements = data['cy_elements']
        
        # Extract existing compounds and targets from network
        compounds = []
        targets = []
        
        for element in cy_elements:
            if element.get('group') == 'nodes' or 'group' not in element:
                element_data = element.get('data', {})
                element_type = element_data.get('type', '')
                
                if element_type == 'chemical':
                    compounds.append(element_data)
                elif element_type in ['uniprot', 'protein']:
                    targets.append(element_data)
        
        # Mock OpenTargets response - in real implementation, query OpenTargets API
        mock_compounds = [
            {
                'id': 'compound_ot_1',
                'label': 'OpenTargets Compound 1',
                'smiles': 'CCO',
                'chembl_id': 'CHEMBL123',
                'targets': ['P10827', 'P10828']
            },
            {
                'id': 'compound_ot_2', 
                'label': 'OpenTargets Compound 2',
                'smiles': 'CCC',
                'chembl_id': 'CHEMBL456',
                'targets': ['P10827']
            }
        ]
        
        mock_relationships = [
            {
                'id': 'rel_ot_1',
                'source': 'compound_ot_1',
                'target': 'uniprot_P10827',
                'confidence': 0.8
            },
            {
                'id': 'rel_ot_2',
                'source': 'compound_ot_2',
                'target': 'uniprot_P10828',
                'confidence': 0.7
            }
        ]
        
        return jsonify({
            'compounds': mock_compounds,
            'relationships': mock_relationships
        })
        
    except Exception as e:
        return jsonify({'error': f'Server error: {str(e)}'}), 500

@aop_app.route("/query_opentargets_targets", methods=["POST"])
def query_opentargets_targets():
    """
    Query OpenTargets for target data based on current network elements.
    
    Returns:
        JSON response with target data from OpenTargets
    """
    try:
        data = request.get_json(silent=True)
        if not data or 'cy_elements' not in data:
            return jsonify({'error': 'Cytoscape elements required'}), 400
        
        # Mock OpenTargets targets response
        mock_targets = [
            {
                'id': 'target_ot_1',
                'label': 'OpenTargets Target 1',
                'uniprot_id': 'P12345',
                'ensembl_id': 'ENSG00000123456',
                'target_class': 'Enzyme'
            },
            {
                'id': 'target_ot_2',
                'label': 'OpenTargets Target 2', 
                'uniprot_id': 'P67890',
                'ensembl_id': 'ENSG00000789012',
                'target_class': 'Receptor'
            }
        ]
        
        return jsonify({'targets': mock_targets})
        
    except Exception as e:
        return jsonify({'error': f'Server error: {str(e)}'}), 500

@aop_app.route("/query_opentargets_diseases", methods=["POST"])
def query_opentargets_diseases():
    """
    Query OpenTargets for disease association data.
    
    Returns:
        JSON response with disease association data from OpenTargets
    """
    try:
        data = request.get_json(silent=True)
        if not data or 'cy_elements' not in data:
            return jsonify({'error': 'Cytoscape elements required'}), 400
        
        # Mock disease associations
        mock_associations = [
            {
                'target_id': 'uniprot_P10827',
                'disease_id': 'EFO_0000311',
                'disease_name': 'cardiovascular disease',
                'score': 0.85
            },
            {
                'target_id': 'uniprot_P10828',
                'disease_id': 'EFO_0000618',
                'disease_name': 'nervous system disease',
                'score': 0.72
            }
        ]
        
        return jsonify({'associations': mock_associations})
        
    except Exception as e:
        return jsonify({'error': f'Server error: {str(e)}'}), 500

@aop_app.route("/query_bgee_expression", methods=["POST"])
def query_bgee_expression():
    """
    Query Bgee for gene expression data based on current network elements.
    
    Returns:
        JSON response with gene expression data from Bgee
    """
    try:
        data = request.get_json(silent=True)
        if not data or 'cy_elements' not in data:
            return jsonify({'error': 'Cytoscape elements required'}), 400
        
        cy_elements = data['cy_elements']
        
        # Extract gene nodes from network
        gene_nodes = []
        for element in cy_elements:
            if element.get('group') == 'nodes' or 'group' not in element:
                element_data = element.get('data', {})
                element_type = element_data.get('type', '')
                
                if element_type in ['ensembl', 'uniprot']:
                    gene_nodes.append(element_data)
        
        # Mock Bgee expression data
        mock_expression_data = []
        for gene in gene_nodes:
            gene_id = gene.get('id', '')
            mock_expression_data.append({
                'gene_id': gene_id,
                'expression_level': 'high',
                'anatomical_entity': 'brain',
                'developmental_stage': 'adult',
                'expression_score': 0.9
            })
        
        return jsonify({'expression_data': mock_expression_data})
        
    except Exception as e:
        return jsonify({'error': f'Server error: {str(e)}'}), 500

@aop_app.route("/query_bgee_developmental", methods=["POST"])
def query_bgee_developmental():
    """
    Query Bgee for developmental stage expression data.
    
    Returns:
        JSON response with developmental stage data from Bgee
    """
    try:
        data = request.get_json(silent=True)
        if not data or 'cy_elements' not in data:
            return jsonify({'error': 'Cytoscape elements required'}), 400
        
        # Mock developmental data
        mock_developmental_data = [
            {
                'gene_id': 'ensembl_ENSG00000126351',
                'stage': 'HsapDv:0000087',
                'stage_name': 'embryonic stage',
                'expression_score': 0.8
            },
            {
                'gene_id': 'ensembl_ENSG00000151090',
                'stage': 'HsapDv:0000174',
                'stage_name': 'adult stage',
                'expression_score': 0.95
            }
        ]
        
        return jsonify({'developmental_data': mock_developmental_data})
        
    except Exception as e:
        return jsonify({'error': f'Server error: {str(e)}'}), 500

@aop_app.route("/query_bgee_anatomical", methods=["POST"])
def query_bgee_anatomical():
    """
    Query Bgee for organ-specific expression data.
    
    Returns:
        JSON response with anatomical expression data from Bgee
    """
    try:
        data = request.get_json(silent=True)
        if not data or 'cy_elements' not in data:
            return jsonify({'error': 'Cytoscape elements required'}), 400
        
        # Mock anatomical expression data
        mock_anatomical_data = [
            {
                'gene_id': 'ensembl_ENSG00000126351',
                'organ': 'UBERON:0000955',
                'organ_name': 'brain',
                'expression_level': 'high',
                'confidence': 'high'
            },
            {
                'gene_id': 'ensembl_ENSG00000151090',
                'organ': 'UBERON:0000948',
                'organ_name': 'heart',
                'expression_level': 'medium',
                'confidence': 'medium'
            }
        ]
        
        return jsonify({'anatomical_data': mock_anatomical_data})
        
    except Exception as e:
        return jsonify({'error': f'Server error: {str(e)}'}), 500

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
        
        # Fetch data using existing function
        elements = fetch_sparql_data(sparql_query)
        
        if isinstance(elements, dict) and "error" in elements:
            return jsonify({"error": elements["error"]}), 500
        
        return jsonify({
            "success": True,
            "elements": elements,
            "elements_count": len(elements) if isinstance(elements, list) else 0
        }), 200
        
    except Exception as e:
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
        if value.startswith('http'):
            processed_values.append(f"<{value}>")
        else:
            processed_values.append(f"<{value}>")
    
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
        print(f"Invalid query type: {query_type}")
        return ""
    
    print(f"Generated VALUES clause: {values_clause}")
    
    final_query = base_query.replace("%VALUES_CLAUSE%", values_clause)
    print(f"Final query length: {len(final_query)} characters")
    print(f"Final query:\n{final_query}")
    
    return final_query

# Network state storage
NETWORK_STATES_DIR = os.path.join(os.path.dirname(__file__), "../static/data/network_states")

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

@aop_app.route("/convert_therapeutic_areas", methods=["POST"])
def convert_therapeutic_areas():
    """Convert therapeutic areas to proper IRIs."""
    try:
        data = request.get_json(silent=True)
        if not data or "therapeutic_areas" not in data:
            return jsonify({"error": "No therapeutic areas provided"}), 400
        
        converted_areas = []
        for area_string in data["therapeutic_areas"]:
            # Split comma-separated CURIEs and process each individually
            individual_curies = [curie.strip() for curie in area_string.split(',')]
            
            converted_links = []
            for curie in individual_curies:
                if curie:  # Skip empty strings
                    # Split on colon to get namespace and id for proper conversion
                    if ':' in curie:
                        namespace, local_id = curie.split(':', 1)
                        # Try to get proper IRI using bioregistry
                        proper_iri = get_iri(namespace, local_id)
                        if proper_iri:
                            converted_links.append(f'<a href="{proper_iri}" target="_blank">{curie}</a>')
                        else:
                            # Fallback to original curie
                            converted_links.append(f'<a href="#" target="_blank">{curie}</a>')
                    else:
                        # No colon found, treat as plain text
                        converted_links.append(f'<a href="#" target="_blank">{curie}</a>')
            
            converted_areas.append({
                "namespace_id": area_string,
                "link": ', '.join(converted_links)
            })
        
        return jsonify({"converted_areas": converted_areas}), 200
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