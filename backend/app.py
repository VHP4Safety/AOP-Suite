@app.route("/load_and_show_genes")
def load_and_show_genes():
    try:
        kes = request.args.get("kes", "")
        include_proteins = request.args.get("include_proteins", "true").lower() == "true"
        
        if not kes:
            return jsonify({"error": "No Key Events provided"}), 400

        # Query genes for the network
        query_service = AOPQueryService()
        network = AOPNetwork()  # Empty network to start with
        network.key_events = {ke.strip('<>'): KeyEvent(uri=ke.strip('<>'), title="") 
                             for ke in kes.split() if ke.strip()}
        
        updated_network, sparql_query = query_service.query_genes_for_network(network, include_proteins)
        
        # Convert to Cytoscape elements
        gene_elements = []
        for gene_assoc in updated_network.gene_associations:
            gene_elements.extend(gene_assoc.to_cytoscape_elements(include_proteins))
        
        return jsonify({
            "gene_elements": gene_elements,
            "sparql_query": sparql_query,
            "include_proteins": include_proteins
        })
        
    except Exception as e:
        logger.error(f"Error in load_and_show_genes: {e}")
        return jsonify({"error": str(e)}), 500