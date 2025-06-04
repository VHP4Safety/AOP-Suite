from flask import Blueprint, request, jsonify, send_file
import requests
from wikidataintegrator import wdi_core
import json
import re
from urllib.parse import quote, unquote
import pandas as pd
import csv
import os
from pyBiodatafuse import id_mapper
from pyBiodatafuse.annotators import opentargets, bgee

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
        compound_dat = wdi_core.WDFunctionsEngine.execute_sparql_query(
            sparqlquery_full, endpoint=compoundwikiEP, as_dataframe=True
        )
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    compound_list = []
    for _, row in compound_dat.iterrows():
        cid = row.iloc[3] if row.iloc[3] else ""
        compound_list.append({
            "ID": row.iloc[1] if pd.notnull(row.iloc[1]) else "NA",
            "Term": row.iloc[2] if pd.notnull(row.iloc[2]) else "NA",
            "SMILES": row.iloc[0] if pd.notnull(row.iloc[0]) else "NA",
            "cid": str(cid) if pd.notnull(cid) else "NA"
        })
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
        compound_dat = wdi_core.WDFunctionsEngine.execute_sparql_query(
            sparqlquery, endpoint=compoundwikiEP, as_dataframe=True
        )
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    compound_list = []
    for _, row in compound_dat.iterrows():
        compound_list.append(
            {"propertyLabel": row["propertyLabel"], "value": str(row["value"])}
        )
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
        compound_dat = wdi_core.WDFunctionsEngine.execute_sparql_query(
            sparqlquery, endpoint=compoundwikiEP, as_dataframe=True
        )
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    compound_list = []
    for _, row in compound_dat.iterrows():
        compound_list.append(
            {
                "propEntityLabel": row["propEntityLabel"],
                "value": row["value"],
                "unitsLabel": row["unitsLabel"],
                "source": row["source"],
                "doi": row["doi"],
            }
        )
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
        compound_dat = wdi_core.WDFunctionsEngine.execute_sparql_query(
            sparqlquery, endpoint=compoundwikiEP, as_dataframe=True
        )
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    if compound_dat.empty:
        return jsonify({"error": "No data found"}), 404
    compound_list = [
        {
            "wcid": compound_dat.at[0, "cmp"],
            "label": compound_dat.at[0, "cmpLabel"],
            "inchikey": compound_dat.at[0, "inchiKey"],
            "SMILES": compound_dat.at[0, "SMILES"],
        }
    ]
    return jsonify(compound_list), 200


@aop_app.route("/get_compounds_parkinson", methods=["GET"])
def get_compounds_VHP_CS2():
    """
    Get compounds related to Parkinson's disease (Q5050).
    
    Returns:
        tuple: JSON response with compound data and status code
    """
    return get_compounds_q("Q5050")


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
    
    Expected JSON payload:
        smiles (list): List of SMILES strings
        models (list): List of model names
        metadata (dict): Model metadata
        threshold (float, optional): Prediction threshold (default: 6.5)
        
    Returns:
        tuple: JSON response with filtered predictions above threshold
    """
    data = request.get_json(silent=True)
    if not data:
        return jsonify({"error": "Invalid JSON input"}), 400
    smiles = [i for i in data.get("smiles", []) if i!= '']
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
    try:
        response = requests.get(
            AOPWIKISPARQL_ENDPOINT,
            params={"query": query, "format": "json"},
            timeout=10,
        )
    except Exception as e:
        return {"error": str(e)}
    if response.status_code != 200:
        return {"error": "Failed to fetch SPARQL data"}
    try:
        data = response.json()
    except Exception as e:
        return {"error": str(e)}
    cytoscape_elements = []
    node_dict = {}
    for result in data.get("results", {}).get("bindings", []):
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
    return list(node_dict.values()) + cytoscape_elements


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
    """
    Load and return gene data (UniProt and Ensembl) for specified MIEs.
    
    Query Parameters:
        mies (str): Comma or space-separated list of MIE identifiers 
                   Supports formats: "aop.events:1656", "https://identifiers.org/aop.events/1656", "1656"
        
    Returns:
        tuple: JSON response with Cytoscape-formatted gene elements and edges
    """
    mies = request.args.get("mies", "")
    print(f"Received mies parameter: {mies}")
    if not mies:
        return jsonify({"error": "mies parameter is required"}), 400
    
    # Parse comma or space-separated MIE identifiers and extract numeric IDs
    mie_ids = []
    # Split by comma or space
    raw_mies = mies.replace(",", " ").split()
    
    for mie in raw_mies:
        mie = mie.strip()
        if not mie:
            continue
            
        # Handle different formats:
        # 1. https://identifiers.org/aop.events/1656
        # 2. aop.events:1656  
        # 3. 1656
        if "https://identifiers.org/aop.events/" in mie:
            numeric_id = mie.split("https://identifiers.org/aop.events/")[-1]
        elif "aop.events:" in mie:
            numeric_id = mie.split("aop.events:")[-1]
        else:
            # Assume it's already a numeric ID
            numeric_id = mie
            
        # Validate that we have a numeric ID
        if numeric_id and numeric_id.isdigit():
            mie_ids.append(numeric_id)
        else:
            print(f"Warning: Could not extract numeric ID from: {mie}")
    
    print(f"Extracted MIE IDs: {mie_ids}")
    
    if not mie_ids:
        return jsonify({"error": "No valid MIE identifiers found"}), 400
    
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
                
                # Check if this row's MIE ID matches any of our requested IDs
                if csv_mie_id in mie_ids and uniprot_id and ensembl_id:
                    full_mie_id = f"https://identifiers.org/aop.events/{csv_mie_id}"
                    uniprot_node_id = f"uniprot_{uniprot_id}"
                    ensembl_node_id = f"ensembl_{ensembl_id}"
                    
                    gene_elements.append(
                        {
                            "data": {
                                "id": uniprot_node_id,
                                "label": uniprot_id,
                                "type": "uniprot",
                            },
                            "classes": "uniprot-node",
                        }
                    )
                    gene_elements.append(
                        {
                            "data": {
                                "id": ensembl_node_id,
                                "label": ensembl_id,
                                "type": "ensembl",
                            },
                            "classes": "ensembl-node",
                        }
                    )
                    gene_elements.append(
                        {
                            "data": {
                                "id": f"edge_{full_mie_id}_{uniprot_node_id}",
                                "source": uniprot_node_id,
                                "target": full_mie_id,
                                "label": "part of",
                            }
                        }
                    )
                    gene_elements.append(
                        {
                            "data": {
                                "id": f"edge_{uniprot_node_id}_{ensembl_node_id}",
                                "source": uniprot_node_id,
                                "target": ensembl_node_id,
                                "label": "translates to",
                            }
                        }
                    )
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    
    print(f"Generated {len(gene_elements)} gene elements")
    return jsonify(gene_elements)


@aop_app.route("/add_qsprpred_compounds", methods=["POST"])
def add_qsprpred_compounds():
    """
    Add QSPR prediction compounds to Cytoscape network.
    
    Expected JSON payload:
        compound_mapping (dict): Mapping of SMILES to compound data
        model_to_protein_info (dict): Model to protein information mapping
        model_to_mie (dict): Model to MIE mapping
        response (list): Prediction response data
        cy_elements (list): Current Cytoscape elements
        
    Returns:
        tuple: JSON response with updated Cytoscape elements
    """
    data = request.get_json(silent=True)
    if not data:
        return jsonify({"error": "Invalid JSON input"}), 400
    compound_mapping = data.get("compound_mapping", {})
    model_to_protein_info = data.get("model_to_protein_info", {})
    model_to_mie = data.get("model_to_mie", {})
    response_data = data.get("response", [])
    cy_elements = data.get("cy_elements", [])
    
    # Track added compounds to avoid duplicates
    added_compounds = set()
    
    if isinstance(response_data, list):
        grouped = {}
        for pred in response_data:
            smiles = pred.get("smiles")
            if not smiles:
                continue
            if smiles not in grouped:
                grouped[smiles] = []
            grouped[smiles].append(pred)
            
        for smiles, predictions in grouped.items():
            compound = compound_mapping.get(smiles)
            compound_id = (
                compound.get("term") if compound and "term" in compound else smiles
            )
            
            # Add compound node only once
            if compound_id not in added_compounds:
                cy_elements.append(
                    {
                        "data": {
                            "id": compound_id,
                            "label": compound_id,
                            "type": "chemical",
                            "smiles": smiles,
                        },
                        "classes": "chemical-node",
                    }
                )
                added_compounds.add(compound_id)
            
            for prediction in predictions:
                for model, value in prediction.items():
                    if model != "smiles":
                        try:
                            if float(value) >= 6.5:
                                protein_info = model_to_protein_info.get(
                                    model,
                                    {"proteinName": "Unknown Protein", "uniprotId": ""},
                                )
                                uniprot_target = f"uniprot_{protein_info.get('uniprotId', '')}"
                                
                                # Ensure the edge has a unique ID
                                edge_id = f"{compound_id}-{uniprot_target}-{model}"
                                cy_elements.append(
                                    {
                                        "data": {
                                            "id": edge_id,
                                            "source": compound_id,
                                            "target": uniprot_target,
                                            "value": value,
                                            "type": "interaction",
                                            "label": f"pChEMBL: {value} ({model})",
                                        }
                                    }
                                )
                        except Exception:
                            continue
    return jsonify(cy_elements), 200


@aop_app.route("/add_aop_bounding_box", methods=["POST"])
def add_aop_bounding_box():
    """
    Add AOP bounding boxes to group related nodes in Cytoscape network.
    
    Query Parameters:
        aop (str): AOP parameter flag
        
    Expected JSON payload:
        cy_elements (list): Current Cytoscape elements
        
    Returns:
        tuple: JSON response with elements including bounding boxes
    """
    data = request.json
    aop = request.args.get('aop', '')
    cy_elements = data.get("cy_elements", [])
    bounding_boxes = []
    if not aop:
        return jsonify({"error": "AOP parameter is required"}), 400

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


## BioDatafuse
@aop_app.route("/get_bridgedb_xref", methods=["POST"])
def get_bridgedb_xref():
    """
    Get cross-references using BridgeDb service.
    
    Expected JSON payload:
        identifiers (list): List of identifiers to map
        input_species (str, optional): Input species (default: "Human")
        input_datasource (str, optional): Input datasource (default: "PubChem Compound")
        output_datasource (str, optional): Output datasource (default: "All")
        
    Returns:
        tuple: JSON response with BridgeDb mapping results and metadata
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
    
    Query Parameters:
        bridgedb_data (str): JSON string of BridgeDb DataFrame data
        
    Returns:
        tuple: JSON response with OpenTargets interaction data
    """
    try:
        bridgedb_data = request.args.get("bridgedb_data", "")
        if not bridgedb_data:
            return jsonify({"error": "BridgeDb data is required"}), 400

        bridgedb_df = pd.DataFrame(json.loads(bridgedb_data))
        ot_df, ot_metadata = opentargets.get_compound_disease_interactions(bridgedb_df=bridgedb_df)

        # Replace NaN with None (null in JSON)
        ot_df = ot_df.where(pd.notnull(ot_df), None)

        return jsonify(ot_df.to_dict(orient="records")), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@aop_app.route("/add_bdf_bgee", methods=["POST"])
def add_bdf_bgee():
    """
    Get gene expression data from Bgee using BridgeDb data.
    
    Expected JSON payload:
        bridgedb_data (list): BridgeDb DataFrame data as list of dictionaries
        
    Returns:
        tuple: JSON response with Bgee gene expression data
    """
    data = request.get_json(silent=True)
    if not data or "bridgedb_data" not in data:
        return jsonify({"error": "BridgeDb data is required"}), 400

    bridgedb_df = pd.DataFrame(data["bridgedb_data"])
    try:
        bgee_df, bgee_metadata = bgee.get_gene_expression(bridgedb_df=bridgedb_df)

        # Replace NaN with None (null in JSON)
        bgee_df = bgee_df.where(pd.notnull(bgee_df), None)

        result = bgee_df.to_dict(orient="records")

        # Log the result to the server log
        print("Result of /add_bdf_bgee:", result)

        return jsonify(result), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@aop_app.route("/populate_compound_table/<qid>", methods=["GET"])
def populate_compound_table(qid):
    """
    Populate compound table with formatted data for a specific QID.
    
    Args:
        qid (str): Wikibase QID identifier
        
    Returns:
        tuple: JSON response with compound mapping and formatted table data
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

@aop_app.route("/populate_gene_table", methods=["POST"])
def populate_gene_table():
    """
    Populate gene table from Cytoscape elements.
    
    Expected JSON payload:
        cy_elements (list): Current Cytoscape elements
        
    Returns:
        tuple: JSON response with gene data for table population
    """
    try:
        data = request.get_json(silent=True)
        if not data or "cy_elements" not in data:
            return jsonify({"error": "Cytoscape elements required"}), 400
        
        cy_elements = data["cy_elements"]
        gene_data = []
        
        for element in cy_elements:
            # Handle both direct element structure and nested data structure
            element_data = element.get("data", element)
            element_classes = element.get("classes", "")
            element_type = element_data.get("type", "")
            element_id = element_data.get("id", "")
            
            # Check for Ensembl nodes using multiple criteria
            if (element_classes == "ensembl-node" or 
                element_type == "ensembl" or
                element_id.startswith("ensembl_")):
                
                gene_label = element_data.get("label", "")
                if gene_label and gene_label not in [g["gene"] for g in gene_data]:
                    gene_data.append({
                        "gene": gene_label,
                        "expression_cell": ""
                    })
        
        return jsonify({"gene_data": gene_data}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@aop_app.route("/populate_qaop_table", methods=["POST"])
def populate_qaop_table():
    """
    Populate QAOP (Quantitative AOP) table from Cytoscape elements.
    
    Expected JSON payload:
        cy_elements (list): Current Cytoscape elements
        
    Returns:
        tuple: JSON response with QAOP relationship data
    """
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

@aop_app.route("/initialize_gene_view", methods=["POST"])
def initialize_gene_view():
    """
    Initialize gene view by loading genes for MIE nodes.
    
    Expected JSON payload:
        cy_elements (list): Current Cytoscape elements
        
    Returns:
        tuple: JSON response with gene elements to add
    """
    try:
        data = request.get_json(silent=True)
        if not data or "cy_elements" not in data:
            return jsonify({"error": "Cytoscape elements required"}), 400
        
        cy_elements = data["cy_elements"]
        
        # Extract MIE node IDs
        mie_node_ids = []
        for element in cy_elements:
            if element.get("data", {}).get("is_mie"):
                node_id = element["data"]["id"]
                mie_node_ids.append(node_id)
        
        if not mie_node_ids:
            return jsonify({"gene_elements": []}), 200
        
        # Extract numeric IDs from MIE node IDs
        mie_ids = []
        for mie_node_id in mie_node_ids:
            if "https://identifiers.org/aop.events/" in mie_node_id:
                numeric_id = mie_node_id.split("https://identifiers.org/aop.events/")[-1]
                if numeric_id.isdigit():
                    mie_ids.append(numeric_id)
        
        if not mie_ids:
            return jsonify({"gene_elements": []}), 200
        
        # Use existing load_and_show_genes logic
        gene_elements = []
        
        csv_path = os.path.join(os.path.dirname(__file__), "../static/data/caseMieModel.csv")
        try:
            with open(csv_path, "r", encoding="utf-8") as csvfile:
                reader = csv.DictReader(csvfile)
                for row in reader:
                    csv_mie_id = row.get("MIE/KE identifier in AOP wiki", "").strip()
                    uniprot_id = row.get("uniprot ID inferred from qspred name", "").strip()
                    ensembl_id = row.get("Ensembl", "").strip()
                    
                    # Check if this row's MIE ID matches any requested
                    if csv_mie_id in mie_ids and uniprot_id and ensembl_id:
                        full_mie_id = f"https://identifiers.org/aop.events/{csv_mie_id}"
                        uniprot_node_id = f"uniprot_{uniprot_id}"
                        ensembl_node_id = f"ensembl_{ensembl_id}"
                        
                        gene_elements.extend([
                            {
                                "data": {
                                    "id": uniprot_node_id,
                                    "label": uniprot_id,
                                    "type": "uniprot",
                                },
                                "classes": "uniprot-node",
                            },
                            {
                                "data": {
                                    "id": ensembl_node_id,
                                    "label": ensembl_id,
                                    "type": "ensembl",
                                },
                                "classes": "ensembl-node",
                            },
                            {
                                "data": {
                                    "id": f"edge_{full_mie_id}_{uniprot_node_id}",
                                    "source": uniprot_node_id,
                                    "target": full_mie_id,
                                    "label": "part of",
                                }
                            },
                            {
                                "data": {
                                    "id": f"edge_{uniprot_node_id}_{ensembl_node_id}",
                                    "source": uniprot_node_id,
                                    "target": ensembl_node_id,
                                    "label": "translates to",
                                }
                            }
                        ])
        except Exception as e:
            return jsonify({"error": str(e)}), 500
        
        return jsonify({"gene_elements": gene_elements}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@aop_app.route("/toggle_genes", methods=["POST"])
def toggle_genes():
    """
    Toggle gene visibility in the network.
    
    Expected JSON payload:
        action (str): 'show' or 'hide'
        cy_elements (list): Current Cytoscape elements
        
    Returns:
        tuple: JSON response with gene elements (for show) or success message (for hide)
    """
    try:
        data = request.get_json(silent=True)
        if not data or "action" not in data:
            return jsonify({"error": "Invalid input"}), 400
        
        action = data["action"]
        
        if action == "show":
            cy_elements = data.get("cy_elements", [])
            # Extract MIE node IDs and load genes
            mie_node_ids = []
            for element in cy_elements:
                element_data = element.get("data", {})
                if element_data.get("is_mie"):
                    node_id = element_data["id"]
                    mie_node_ids.append(node_id)
            
            if mie_node_ids:
                # Extract numeric IDs from MIE node IDs
                mie_ids = []
                for mie_node_id in mie_node_ids:
                    if "https://identifiers.org/aop.events/" in mie_node_id:
                        numeric_id = mie_node_id.split("https://identifiers.org/aop.events/")[-1]
                        if numeric_id.isdigit():
                            mie_ids.append(numeric_id)
                
                if mie_ids:
                    gene_elements = []
                    csv_path = os.path.join(os.path.dirname(__file__), "../static/data/caseMieModel.csv")
                    try:
                        with open(csv_path, "r", encoding="utf-8") as csvfile:
                            reader = csv.DictReader(csvfile)
                            for row in reader:
                                csv_mie_id = row.get("MIE/KE identifier in AOP wiki", "").strip()
                                uniprot_id = row.get("uniprot ID inferred from qspred name", "").strip()
                                ensembl_id = row.get("Ensembl", "").strip()
                                
                                if csv_mie_id in mie_ids and uniprot_id and ensembl_id:
                                    full_mie_id = f"https://identifiers.org/aop.events/{csv_mie_id}"
                                    uniprot_node_id = f"uniprot_{uniprot_id}"
                                    ensembl_node_id = f"ensembl_{ensembl_id}"
                                    
                                    gene_elements.extend([
                                        {
                                            "data": {
                                                "id": uniprot_node_id,
                                                "label": uniprot_id,
                                                "type": "uniprot",
                                            },
                                            "classes": "uniprot-node",
                                        },
                                        {
                                            "data": {
                                                "id": ensembl_node_id,
                                                "label": ensembl_id,
                                                "type": "ensembl",
                                            },
                                            "classes": "ensembl-node",
                                        },
                                        {
                                            "data": {
                                                "id": f"edge_{full_mie_id}_{uniprot_node_id}",
                                                "source": uniprot_node_id,
                                                "target": full_mie_id,
                                                "label": "part of",
                                            }
                                        },
                                        {
                                            "data": {
                                                "id": f"edge_{uniprot_node_id}_{ensembl_node_id}",
                                                "source": uniprot_node_id,
                                                "target": ensembl_node_id,
                                                "label": "translates to",
                                            }
                                        }
                                    ])
                    except Exception as e:
                        return jsonify({"error": str(e)}), 500
                    
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
    """
    Toggle bounding boxes on/off in the network.
    
    Expected JSON payload:
        action (str): 'add' or 'remove'
        cy_elements (list): Current Cytoscape elements
        
    Returns:
        tuple: JSON response with updated elements
    """
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
                    # Remove parent relationship
                    if "parent" in element.get("data", {}):
                        del element["data"]["parent"]
                    filtered_elements.append(element)
            return jsonify(filtered_elements), 200
        elif action == "add":
            # Use existing add_aop_bounding_box logic but with proper parameter handling
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

import json
import os
from datetime import datetime

# Network state storage (in production, use database)
NETWORK_STATES_DIR = os.path.join(os.path.dirname(__file__), "../static/data/network_states")

@aop_app.route("/save_network_state", methods=["POST"])
def save_network_state():
    """
    Save current network state to persistent storage.
    
    Expected JSON payload:
        elements (list): Cytoscape elements
        style (list): Cytoscape styles
        layout (dict): Node positions
        metadata (dict): Additional metadata
        
    Returns:
        tuple: JSON response with save confirmation
    """
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
        import traceback
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500

@aop_app.route("/load_network_state", methods=["GET"])
def load_network_state():
    """
    Load the latest network state from persistent storage.
    
    Returns:
        tuple: JSON response with network state data
    """
    try:
        latest_filepath = os.path.join(NETWORK_STATES_DIR, "latest_network_state.json")
        
        if not os.path.exists(latest_filepath):
            return jsonify({"error": "No saved network state found"}), 404
        
        with open(latest_filepath, 'r', encoding='utf-8') as f:
            network_data = json.load(f)
        
        return jsonify(network_data), 200
        
    except Exception as e:
        print(f"Error loading network state: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500

@aop_app.route("/list_network_states", methods=["GET"])
def list_network_states():
    """
    List all saved network states.
    
    Returns:
        tuple: JSON response with list of saved states
    """
    try:
        if not os.path.exists(NETWORK_STATES_DIR):
            return jsonify({"states": []}), 200
        
        states = []
        for filename in os.listdir(NETWORK_STATES_DIR):
            if filename.endswith('.json') and filename != 'latest_network_state.json':
                filepath = os.path.join(NETWORK_STATES_DIR, filename)
                stat = os.stat(filepath)
                states.append({
                    "filename": filename,
                    "created_at": datetime.fromtimestamp(stat.st_ctime).isoformat(),
                    "modified_at": datetime.fromtimestamp(stat.st_mtime).isoformat(),
                    "size": stat.st_size
                })
        
        # Sort by creation time, newest first
        states.sort(key=lambda x: x["created_at"], reverse=True)
        
        return jsonify({"states": states}), 200
        
    except Exception as e:
        print(f"Error listing network states: {str(e)}")
        return jsonify({"error": str(e)}), 500

@aop_app.route("/delete_network_state/<filename>", methods=["DELETE"])
def delete_network_state(filename):
    """
    Delete a specific network state file.
    
    Args:
        filename (str): Name of the file to delete
        
    Returns:
        tuple: JSON response with deletion confirmation
    """
    try:
        # Validate filename to prevent directory traversal
        if not filename.endswith('.json') or '/' in filename or '\\' in filename:
            return jsonify({"error": "Invalid filename"}), 400
        
        filepath = os.path.join(NETWORK_STATES_DIR, filename)
        
        if not os.path.exists(filepath):
            return jsonify({"error": "File not found"}), 404
        
        os.remove(filepath)
        
        return jsonify({
            "success": True,
            "message": f"Network state {filename} deleted successfully"
        }), 200
        
    except Exception as e:
        print(f"Error deleting network state: {str(e)}")
        return jsonify({"error": str(e)}), 500
