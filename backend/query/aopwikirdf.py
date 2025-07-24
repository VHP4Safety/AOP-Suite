import requests


AOPWIKISPARQL_ENDPOINT = "https://aopwiki.rdf.bigcat-bioinformatics.org/sparql/"


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
        print(
            f"Response structure: {list(data.keys()) if isinstance(data, dict) else type(data)}"
        )

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
        ao_title = result.get("ao_title", {}).get("value", "")
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
                        "label": (
                            ke_upstream_title if ke_upstream_title != "NA" else "NA"
                        ),
                        "KEupTitle": (
                            ke_upstream_title if ke_upstream_title != "NA" else "NA"
                        ),
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
                if (
                    aop_title
                    and aop_title not in node_dict[ke_upstream]["data"]["aop_title"]
                ):
                    node_dict[ke_upstream]["data"]["aop_title"].append(aop_title)

        if ke_downstream != "NA" and ke_downstream not in [mie, ao]:
            if ke_downstream not in node_dict:
                node_dict[ke_downstream] = {
                    "data": {
                        "id": ke_downstream,
                        "label": (
                            ke_downstream_title if ke_downstream_title != "NA" else "NA"
                        ),
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
                if (
                    aop_title
                    and aop_title not in node_dict[ke_downstream]["data"]["aop_title"]
                ):
                    node_dict[ke_downstream]["data"]["aop_title"].append(aop_title)

        # Only create edges if we have actual KER data (not "NA")
        if ker_uri != "NA" and ke_upstream != "NA" and ke_downstream != "NA":
            edge_id = f"{ke_upstream}_{ke_downstream}"
            # Check if edge already exists
            edge_exists = any(
                edge["data"]["id"] == edge_id for edge in cytoscape_elements
            )
            if not edge_exists:
                cytoscape_elements.append(
                    {
                        "data": {
                            "id": edge_id,
                            "source": ke_upstream,
                            "target": ke_downstream,
                            "curie": f"aop.relationships:{ker_id}",
                            "ker_label": ker_id,
                            "type": "key_event_relationship",
                        }
                    }
                )
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
        "has_complete_pathways": ker_count > 0,
    }

    return {"elements": final_elements, "report": report}


def get_case_mie_model(request_data):
    """
    Get model to MIE mapping for case studies.

    Query Parameters:
        mie_query (str): MIE query string containing AOP event identifiers

    Returns:
        tuple: JSON response with model to MIE mapping dictionary
    """
    mie_query = request_data.args.get("mie_query", "")
    if not mie_query:
        return {"error": "mie_query parameter is required"}, 400
    try:
        filtered_df = load_case_mie_model(mie_query)
    except Exception as e:
        return {"error": str(e)}, 500
    model_to_mie = filtered_df.set_index("qsprpred_model")[
        "MIE/KE identifier in AOP wiki"
    ].to_dict()
    return model_to_mie, 200


def load_and_show_genes(kes):
    """Load and return gene data (UniProt and Ensembl) for specified KEs."""
    sparqlquery = (
        """
            SELECT DISTINCT ?ke ?ensembl ?uniprot WHERE {
                VALUES ?ke { """
        + kes
        + """ }
                ?ke a aopo:KeyEvent; edam:data_1025 ?object .
                ?object skos:exactMatch ?id .
                ?id a edam:data_1033; edam:data_1033 ?ensembl .
                OPTIONAL {     ?object skos:exactMatch ?prot.
        					   ?prot a edam:data_2291; 
                                       edam:data_2291 ?uniprot.
    						}
                }
            """
    )
    print(sparqlquery)
    try:
        response = requests.get(
            AOPWIKISPARQL_ENDPOINT, 
            params={"query": sparqlquery, "format": "json"},
            timeout=10
        )
        response.raise_for_status()  # Raise HTTPError for bad responses (4xx and 5xx)

        data = response.json()
        cytoscape_elements = []

        for i, result in enumerate(data.get("results", {}).get("bindings", [])):
            ke = result.get("ke", {}).get("value", "")
            ensembl = result.get("ensembl", {}).get("value", "")
            uniprot = result.get("uniprot", {}).get("value", "")
            protein_name = result.get("uniprot", {}).get("value", "")

            if ke and ensembl:
                # Create Ensembl gene node
                ensembl_node_id = f"ensembl_{ensembl}"
                cytoscape_elements.append(
                    {
                        "data": {
                            "id": ensembl_node_id,
                            "label": ensembl,
                            "type": "ensembl",
                            "ensembl_id": ensembl,
                        },
                        "classes": "ensembl-node",
                    }
                )

                # Always create UniProt node (use NA values if not available)
                uniprot_id = uniprot if uniprot else "NA"
                uniprot_label = protein_name if protein_name else "NA"
                uniprot_node_id = uniprot

                cytoscape_elements.append(
                    {
                        "data": {
                            "id": uniprot_node_id,
                            "label": uniprot_label,
                            "type": "uniprot",
                            "uniprot_id": uniprot_id,
                        },
                        "classes": "uniprot-node",
                    }
                )

                # Create edge from Ensembl to UniProt (translates to)
                cytoscape_elements.append(
                    {
                        "data": {
                            "id": f"{ensembl_node_id}_{uniprot_node_id}",
                            "source": ensembl_node_id,
                            "target": uniprot_node_id,
                            "label": "translates to",
                        }
                    }
                )

                # Create edge from UniProt to KE (part of)
                cytoscape_elements.append(
                    {
                        "data": {
                            "id": f"{uniprot_node_id}_{ke}",
                            "source": uniprot_node_id,
                            "target": ke,
                            "label": "part of",
                        }
                    }
                )

        return cytoscape_elements
    except requests.exceptions.Timeout as e:
        print(f"Timeout error: {str(e)}")
    except requests.exceptions.ConnectionError as e:
        print(f"Connection error: {str(e)}")
    except requests.exceptions.HTTPError as e:
        print(f"HTTP error: {str(e)}")
    except requests.exceptions.RequestException as e:
        print(f"Request exception: {str(e)}")


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
        if value.startswith("http"):
            processed_values.append(f"<{value}>")
        else:
            processed_values.append(f"<{value}>")

    formatted_values = " ".join(processed_values)
    print(f"Processed values: {formatted_values}")

    # Base query with all KER relationships as OPTIONAL
    base_query = """SELECT DISTINCT ?aop ?aop_title ?MIEtitle ?MIE ?KE_downstream ?KE_downstream_title ?KER ?ao ?ao_title ?KE_upstream ?KE_upstream_title ?KE_upstream_organ ?KE_downstream_organ
WHERE {
  %VALUES_CLAUSE%
  ?aop a aopo:AdverseOutcomePathway ;
       dc:title ?aop_title ;
       aopo:has_adverse_outcome ?ao ;
       aopo:has_molecular_initiating_event ?MIE .
  ?ao dc:title ?ao_title .
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


def get_aop_network_data(query_type, values):
    try:
        # Build SPARQL query
        try:
            sparql_query = build_flexible_aop_sparql_query(query_type, values)
            if not sparql_query:
                return {"error": "Invalid query type"}, 400
        except Exception as e:
            return {"error": f"SPARQL query build error: {str(e)}"}, 500

        # Execute query
        print("=== Executing SPARQL query ===")
        try:
            result = fetch_sparql_data(sparql_query)
        except requests.exceptions.RequestException as e:
            return {"error": f"SPARQL request error: {str(e)}"}, 500
        except Exception as e:
            return {"error": f"SPARQL fetch error: {str(e)}"}, 500

        # Check for errors
        if isinstance(result, dict) and "error" in result:
            return {"error": result["error"]}, 500

        # Extract elements and report
        try:
            elements = result.get("elements", [])
            report = result.get("report", {})
        except Exception as e:
            return {"error": f"Result parsing error: {str(e)}"}, 500

        # Prepare response
        response_data = {
            "success": True,
            "elements": elements,
            "elements_count": len(elements),
            "report": report,
        }

        # Generate specific warning message based on what was found
        warnings = []
        if report.get("mie_count", 0) == 0:
            warnings.append("No Molecular Initiating Events (MIEs) found")
        if report.get("ao_count", 0) == 0:
            warnings.append("No Adverse Outcomes (AOs) found")
        if report.get("ker_count", 0) == 0:
            if report.get("mie_count", 0) > 0 or report.get("ao_count", 0) > 0:
                warnings.append("No Key Event Relationships (KERs) found")
            else:
                warnings.append("No pathway relationships found")
        if report.get("ke_count", 0) == 0 and report.get("ker_count", 0) > 0:
            warnings.append("No intermediate Key Events found - only direct relationships")
        if warnings:
            response_data["warning"] = {
                "type": "incomplete_aop_data",
                "message": f"Warnings: {'; '.join(warnings)}",
                "details": (
                    f"Found: {report.get('mie_count', 0)} MIEs, "
                    f"{report.get('ao_count', 0)} AOs, "
                    f"{report.get('ke_count', 0)} intermediate KEs, "
                    f"{report.get('ker_count', 0)} KERs"
                ),
                "specific_issues": warnings,
            }
        return response_data
    except Exception as e:
        return {"error": f"Unexpected error: {str(e)}"}, 500
    
def populate_aop_table(cy_elements):
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
                    iri_part = (
                        node_id.split("/")[-1] if "/" in node_id else node_id
                    )
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
    return aop_data

