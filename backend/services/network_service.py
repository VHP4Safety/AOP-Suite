    def process_aop_network_query(self, aop_ids: List[str]) -> Dict[str, Any]:
        """Process full AOP network query with all associations"""
        try:
            logger.info(f"Processing AOP network query for AOPs: {aop_ids}")

            # Build network from SPARQL results
            builder = AOPNetworkBuilder()

            # Get main AOP network
            network_results = self.sparql_service.query_aop_network(aop_ids)
            for result in network_results:
                builder.process_sparql_binding(result)

            # Get gene associations
            gene_results = self.sparql_service.query_genes_for_kes(
                builder.network.get_ke_uris()
            )
            builder.add_gene_associations(gene_results)

            # Get component associations
            component_results = self.sparql_service.query_components_for_kes(
                builder.network.get_ke_uris()
            )
            builder.add_component_associations(component_results)

            # Get compound associations
            compound_results = self.sparql_service.query_compounds_for_aops(aop_ids)
            builder.add_compound_associations(compound_results)

            # Get organ associations from SPARQL
            organ_results = self.sparql_service.query_organs_for_kes(
                builder.network.get_ke_uris()
            )
            builder.add_organ_associations_from_sparql(organ_results)

            # Build complete network
            network = builder.build()

            # Generate Cytoscape elements
            cytoscape_elements = network.to_cytoscape_elements()

            # Add organ elements to cytoscape
            for organ_assoc in network.organ_associations:
                cytoscape_elements.extend(organ_assoc.to_cytoscape_elements())

            # Generate tables
            tables = self._generate_tables(cytoscape_elements, network)

            # Generate summary with organ counts
            summary = self._generate_summary(network, tables)

            logger.info(f"Successfully processed AOP network with {len(cytoscape_elements)} elements")

            return {
                "cytoscape_elements": cytoscape_elements,
                "tables": tables,
                "summary": summary,
                "network": network,
            }

        except Exception as e:
            logger.error(f"Failed to process AOP network query: {e}")
            raise

    def _generate_summary(self, network: AOPNetwork, tables: Dict[str, Any]) -> Dict[str, Any]:
        """Generate comprehensive summary statistics"""
        network_summary = network.get_summary()
        
        # Count elements from tables and network
        summary = {
            "network": {
                "key_events": network_summary["total_key_events"],
                "mie_count": network_summary["mie_count"], 
                "ke_count": network_summary["ke_count"],
                "ao_count": network_summary["ao_count"],
                "relationships": network_summary["ker_count"],
                "total_aops": network_summary["total_aops"],
            },
            "associations": {
                "genes": len(tables.get("gene_table", [])),
                "compounds": len(tables.get("compound_table", [])),
                "components": len(tables.get("component_table", [])),
                "organs": len(network.organ_associations),  # Count organ associations
                "gene_expression": len(network.gene_expression_associations),
            },
            "elements": {
                "total_nodes": (
                    network_summary["total_key_events"] + 
                    len(set(pair.ensembl_node_id for pair in self._extract_gene_pairs(tables.get("gene_table", [])))) +
                    len(set(pair.uniprot_node_id for pair in self._extract_gene_pairs(tables.get("gene_table", [])) if pair.uniprot_node_id != "N/A")) +
                    len(tables.get("compound_table", [])) +
                    len([comp for comp in tables.get("component_table", []) if comp.get("process_id") != "N/A"]) +
                    len([comp for comp in tables.get("component_table", []) if comp.get("object_id") != "N/A"]) +
                    len(network.organ_associations)  # Add organ nodes to total count
                ),
                "total_edges": (
                    network_summary["ker_count"] + 
                    len([pair for pair in self._extract_gene_pairs(tables.get("gene_table", [])) if pair.uniprot_node_id != "N/A"]) +  # translates_to edges
                    len(tables.get("gene_table", [])) +  # part_of edges
                    len(tables.get("compound_table", [])) +  # stressor edges
                    len(tables.get("component_table", [])) * 2 +  # component edges (KE->process, process->object)
                    len(network.organ_associations) +  # organ association edges
                    len(network.gene_expression_associations)  # expression edges
                ),
            },
            "tables": {
                "aop_table_rows": len(tables.get("aop_table", [])),
                "gene_table_rows": len(tables.get("gene_table", [])),
                "compound_table_rows": len(tables.get("compound_table", [])),
                "component_table_rows": len(tables.get("component_table", [])),
            }
        }
        
        return summary

    def _extract_gene_pairs(self, gene_table: List[Dict[str, str]]) -> List[Any]:
        """Extract gene pairs for counting purposes"""
        # This is a helper method to extract gene pairs from the table
        # Implementation depends on the structure of your gene table
        pairs = []
        for row in gene_table:
            class GenePair:
                def __init__(self, ensembl_id, uniprot_id):
                    self.ensembl_node_id = ensembl_id
                    self.uniprot_node_id = uniprot_id
            
            pairs.append(GenePair(
                row.get("ensembl_id", "N/A"),
                row.get("uniprot_id", "N/A")
            ))
        return pairs