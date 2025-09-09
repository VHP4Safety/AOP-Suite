import requests
import logging
from typing import Dict, List, Any, Optional, Tuple

from backend.model.aop_data_model import (
    AOPNetworkBuilder,
    AOPNetwork,
    AOPKeyEvent,
    NodeType,
    GeneAssociation,
)

# Set up logger
logger = logging.getLogger(__name__)

BGEE_SPARQL_ENDPOINT = "https://www.bgee.org/sparql/"


class BgeeQueryService:
    """Service for querying bgee data from SPARQL endpoint"""

    def __init__(self):
        self.endpoint = BGEE_SPARQL_ENDPOINT

    def query_bgee(self, query_type: str, values: str) -> AOPNetwork:
        """Query bgee network data and return structured model"""
        try:
            # Build and execute SPARQL query
            network_query = self._build_bgee_sparql_query(query_type, values)
            if not network_query:
                raise bgeeDataError(f"Invalid query type: {query_type}")

            sparql_results = self._execute_sparql_query(network_query)

            # Build network from results using the data model
            builder = AOPNetworkBuilder()
            for binding in sparql_results.get("results", {}).get("bindings", []):
                builder.process_sparql_binding(binding)

            network = builder.build()
            logger.info(f"Built bgee network: {network.get_summary()}")

            return network, network_query

        except Exception as e:
            logger.error(f"Failed to query bgee network: {e}")
            raise bgeeDataError(str(e))

    def query_gene_expressions_for_network(self, network: AOPNetwork) -> AOPNetwork:
        """Query bgee for genes in the network"""
        try:
            gene_ids = network.get_ensembl_ids()
            organ_ids = network.get_organ_ids()
            if not gene_ids:
                logger.warning("No Key Events found for gene querying")
                return network

            # Format KE URIs for SPARQL
            gene_expression_query = self._build_bgee_sparql_query(gene_ids, organ_ids)

            gene_expression_results = self._execute_sparql_query(gene_expression_query)

            # Add gene associations to network using the builder
            builder = AOPNetworkBuilder()
            builder.network = network  # Use existing network
            builder.add_gene_expression_associations(
                gene_expression_results.get("results", {}).get("bindings", [])
            )

            updated_network = builder.build()
            logger.info(
                f"Added gene associations: {len(updated_network.component_associations)} genes"
            )

            return updated_network, gene_expression_query

        except Exception as e:
            logger.error(f"Failed to query genes for network: {e}")
            # Return original network if gene query fails
            return network

    def query_gene_expression_data(self, ensembl_nodes: List, confidence_level: int = None) -> List[Dict[str, str]]:
        """Query Bgee for basic gene expression data with optional confidence filtering"""
        try:
            # Extract Ensembl IDs from nodes
            ensembl_ids = []
            for node in ensembl_nodes:
                ensembl_id = node.properties.get("ensembl_id", node.id)
                if ensembl_id.startswith("ensembl_"):
                    ensembl_id = ensembl_id.replace("ensembl_", "")
                ensembl_ids.append(f'"{ensembl_id}"')

            if not ensembl_ids:
                return []

            logger.info(f"Querying Bgee expression for {len(ensembl_ids)} genes with confidence level {confidence_level}")

            # Build and execute SPARQL query with confidence level
            query = self._build_bgee_sparql_query(True, ensembl_ids, [], confidence_level)
            results = self._execute_sparql_query(query)

            # Process results
            expression_data = []
            for binding in results.get("results", {}).get("bindings", []):
                expression_data.append({
                    "gene_id": f"ensembl_{binding.get('ensembl_id', {}).get('value', '')}",
                    "ensembl_id": binding.get('ensembl_id', {}).get('value', ''),
                    "gene_symbol": binding.get('ensembl_id', {}).get('value', ''),  # Use as symbol for now
                    "expression_level": binding.get('expression_level', {}).get('value', ''),
                    "anatomical_entity": binding.get('anatomical_entity_name', {}).get('value', ''),
                    "anatomical_entity_id": binding.get('anatomical_entity_id', {}).get('value', '').split('/')[-1],
                    "organ": binding.get('anatomical_entity_name', {}).get('value', ''),
                    "organ_id": binding.get('anatomical_entity_id', {}).get('value', '').split('/')[-1],
                    "developmental_stage": binding.get('developmental_stage_name', {}).get('value', ''),
                    "confidence": binding.get('confidence_level_name', {}).get('value', ''),
                    "confidence_level": binding.get('confidence_level_name', {}).get('value', ''),
                    "expression_score": binding.get('expression_level', {}).get('value', '0'),
                    "expr": binding.get('expr', {}).get('value', '')  # Add expr field
                })

            logger.info(f"Retrieved expression data for {len(expression_data)} entries")
            return expression_data

        except Exception as e:
            logger.error(f"Error querying Bgee expression: {e}")
            return []

    def query_anatomical_expression_data(self, ensembl_nodes: List, confidence_level: int = None) -> List[Dict[str, str]]:
        """Query Bgee for organ-specific expression data with confidence filtering"""
        try:
            ensembl_ids = []
            for node in ensembl_nodes:
                ensembl_id = node.properties.get("ensembl_id", node.id)
                if ensembl_id.startswith("ensembl_"):
                    ensembl_id = ensembl_id.replace("ensembl_", "")
                ensembl_ids.append(f'"{ensembl_id}"')

            if not ensembl_ids:
                return []

            logger.info(f"Querying Bgee anatomical for {len(ensembl_ids)} genes with confidence level {confidence_level}")

            # Build and execute SPARQL query with confidence level
            query = self._build_bgee_sparql_query(True, ensembl_ids, [], confidence_level)
            results = self._execute_sparql_query(query)

            # Process results
            anatomical_data = []
            for binding in results.get("results", {}).get("bindings", []):
                anatomical_data.append({
                    "gene_id": f"ensembl_{binding.get('ensembl_id', {}).get('value', '')}",
                    "ensembl_id": binding.get('ensembl_id', {}).get('value', ''),
                    "gene_symbol": binding.get('ensembl_id', {}).get('value', ''),
                    "organ": binding.get('anatomical_entity_name', {}).get('value', ''),
                    "organ_name": binding.get('anatomical_entity_name', {}).get('value', ''),
                    "organ_id": binding.get('anatomical_entity_id', {}).get('value', '').split('/')[-1],
                    "expression_level": binding.get('expression_level', {}).get('value', ''),
                    "confidence": binding.get('confidence_level_name', {}).get('value', ''),
                    "developmental_stage": binding.get('developmental_stage_name', {}).get('value', ''),
                    "expression_score": binding.get('expression_level', {}).get('value', '0'),
                    "expr": binding.get('expr', {}).get('value', '')  # Add expr field
                })

            logger.info(f"Retrieved anatomical data for {len(anatomical_data)} entries")
            return anatomical_data

        except Exception as e:
            logger.error(f"Error querying Bgee anatomical: {e}")
            return []

    def _build_bgee_sparql_query(self, bool, ensembl_ids: list, anatomical_entities: list, confidence_level: int = None) -> str:
        anatomical_entities_clause = f"VALUES ?anatomical_entity_name {{ {' '.join(anatomical_entities)} }}" if len(anatomical_entities) > 0 else ""
        
        # Build confidence level filter - use actual Bgee confidence level URIs
        confidence_filter = ""
        if confidence_level is not None:
            # Map confidence level percentage to actual Bgee confidence URIs
            if confidence_level >= 80:
                # High confidence only
                confidence_filter = "?expr genex:hasConfidenceLevel obo:CIO_0000029 . # high confidence level"
            elif confidence_level >= 50:
                # High and medium confidence
                confidence_filter = """
                {
                    ?expr genex:hasConfidenceLevel obo:CIO_0000029 . # high confidence
                } UNION {
                    ?expr genex:hasConfidenceLevel obo:CIO_0000031 . # medium confidence
                }
                """
            elif confidence_level >= 20:
                # All confidence levels except low
                confidence_filter = """
                {
                    ?expr genex:hasConfidenceLevel obo:CIO_0000029 . # high confidence
                } UNION {
                    ?expr genex:hasConfidenceLevel obo:CIO_0000031 . # medium confidence
                } UNION {
                    ?expr genex:hasConfidenceLevel obo:CIO_0000030 . # low confidence
                }
                """
            # For levels below 20, no filter (include all confidence levels)
        
        return f"""
            PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
            PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
            PREFIX orth: <http://purl.org/net/orth#>
            PREFIX lscr: <http://purl.org/lscr#>
            PREFIX genex: <http://purl.org/genex#>
            PREFIX obo: <http://purl.obolibrary.org/obo/>
            PREFIX dcterms: <http://purl.org/dc/terms/>

            SELECT ?gene_id ?ensembl_id ?anatomical_entity_id ?anatomical_entity_name ?developmental_stage_id ?developmental_stage_name ?expression_level ?confidence_level_id ?confidence_level_name ?expr
            WHERE {{
              VALUES ?ensembl_id {{ {" ".join(ensembl_ids)} }}
              {anatomical_entities_clause if anatomical_entities else ""}
              ?gene_id a orth:Gene .
              ?gene_id dcterms:identifier ?ensembl_id .
              ?expr genex:hasSequenceUnit ?gene_id.
              ?expr a genex:Expression .
              {confidence_filter}
              ?expr genex:hasConfidenceLevel ?confidence_level_id .
              ?confidence_level_id rdfs:label ?confidence_level_label.
              BIND(str(?confidence_level_label) as ?confidence_level_name)
              ?expr genex:hasExpressionLevel ?expression_level .
              ?expr genex:hasExpressionCondition ?cond .
              ?cond genex:hasDevelopmentalStage ?developmental_stage_id.
              ?developmental_stage_id rdfs:label ?developmental_stage_name.
              ?cond genex:hasAnatomicalEntity ?anatomical_entity_id . # tissue
              ?anatomical_entity_id rdfs:label ?anatomical_entity_name.
            }}
        """

    def _execute_sparql_query(self, query: str) -> Dict[str, Any]:
        """Execute SPARQL query with standardized error handling"""
        logger.info(f"Executing SPARQL query (length: {len(query)})")

        try:
            response = requests.get(
                self.endpoint,
                params={"query": query, "format": "json"},
                timeout=10,
            )
            logger.debug(f"SPARQL response status: {response.status_code}")
            response.raise_for_status()

            data = response.json()
            bindings = data.get("results", {}).get("bindings", [])
            logger.info(f"Retrieved {len(bindings)} SPARQL result bindings")

            return data

        except requests.exceptions.Timeout:
            raise SPARQLQueryError("SPARQL query timeout")
        except requests.exceptions.ConnectionError:
            raise SPARQLQueryError("Failed to connect to SPARQL endpoint")
        except requests.exceptions.HTTPError as e:
            raise SPARQLQueryError(f"HTTP error {e.response.status_code}: {e}")
        except requests.exceptions.RequestException as e:
            raise SPARQLQueryError(f"Request error: {str(e)}")
        except ValueError as e:
            raise SPARQLQueryError(f"Invalid JSON response: {str(e)}")


# Add missing exception classes
class bgeeDataError(Exception):
    """Exception raised for Bgee data errors"""
    pass

class SPARQLQueryError(Exception):
    """Exception raised for SPARQL query errors"""
    pass

# Global service instance
bgee_query_service = BgeeQueryService()
