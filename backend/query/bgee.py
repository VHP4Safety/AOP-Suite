import requests
import logging
from typing import Dict, List, Any, Tuple

from backend.model.parsers.builder import AOPNetworkBuilder
from backend.model.schemas.base import AOPNetwork


# Set up logger
logger = logging.getLogger(__name__)

BGEE_SPARQL_ENDPOINT = "https://www.bgee.org/sparql/"


class BgeeQueryService:
    """Service for querying Bgee gene expression data from SPARQL endpoint"""

    def __init__(self):
        self.endpoint = BGEE_SPARQL_ENDPOINT

    def query_gene_expressions_for_network(self, network: AOPNetwork, query_by: str = "genes", confidence_level: int = None) -> Tuple[AOPNetwork, str]:
        """
        Query Bgee for gene expression data based on network content
        
        Args:
            network: AOPNetwork containing genes and/or organs
            query_by: "genes", "organs", or "both" - determines what to use for querying
            confidence_level: Optional confidence level filter (20-100)
        
        Returns:
            Tuple of updated network and SPARQL query used
        """
        try:
            ensembl_ids = []
            organ_ids = []

            # Get genes from network if needed
            if query_by in ["genes", "both"]:
                ensembl_ids = network.get_ensembl_ids()
                logger.info(f"Raw ensembl_ids from network: {ensembl_ids}")
                # Format for SPARQL query
                ensembl_ids = [f'"{eid}"' for eid in ensembl_ids if eid]
                logger.info(f"Formatted ensembl_ids for SPARQL: {ensembl_ids}")

                organ_ids = network.get_organ_ids()
                logger.info(f"Raw organ_ids from network: {organ_ids}")
                # Format for SPARQL query
                organ_ids = [f'"{oid}"' for oid in organ_ids if oid]
                logger.info(f"Formatted organ_ids for SPARQL: {organ_ids}")

            if not ensembl_ids and not organ_ids:
                logger.warning(f"No elements found in network for Bgee querying")
                return network, ""

            logger.info(f"Querying Bgee by {query_by}: {len(ensembl_ids)} genes, {len(organ_ids)} organs, confidence: {confidence_level}")

            # Build and execute SPARQL query
            gene_expression_query = self._build_bgee_sparql_query(ensembl_ids, organ_ids, confidence_level)

            # LOG THE COMPLETE QUERY
            logger.info("="*80)
            logger.info("GENERATED BGEE SPARQL QUERY:")
            logger.info("="*80)
            logger.info(gene_expression_query)
            logger.info("="*80)

            gene_expression_results = self._execute_sparql_query(gene_expression_query)

            # Add gene expression associations to network using the builder
            builder = AOPNetworkBuilder()
            builder.network = network  # Use existing network
            builder.add_gene_expression_association(
                gene_expression_results.get("results", {}).get("bindings", [])
            )

            updated_network = builder.build()
            logger.info(f"Added {len(updated_network.gene_expression_associations)} gene expression associations")

            return updated_network, gene_expression_query

        except Exception as e:
            logger.error(f"Failed to query Bgee for network: {e}")
            # Return original network if query fails
            return network, ""

    def _build_bgee_sparql_query(self, ensembl_ids: List[str], organ_ids: List[str], confidence_level: int = None) -> str:
        """Build SPARQL query for Bgee gene expression data"""
        
        # Build genes clause
        genes_clause = ""
        if ensembl_ids:
            genes_clause = f"VALUES ?ensembl_id {{ {' '.join(ensembl_ids)} }}"
        
        # Build anatomical entities clause - use organ names directly
        anatomical_entities_clause = ""
        if organ_ids:
            # Remove quotes from organ names and use them directly
            clean_organ_names = [oid.strip('"') for oid in organ_ids]
            organ_values = ' '.join(f'"{name}"' for name in clean_organ_names)
            anatomical_entities_clause = f"VALUES ?anatomical_entity_name {{ {organ_values} }}"
        
        # Build confidence level filter
        confidence_filter = ""
        if confidence_level is not None:
            if confidence_level >= 80:
                confidence_filter = "?expr genex:hasConfidenceLevel obo:CIO_0000029 . # high confidence"
            elif confidence_level >= 50:
                confidence_filter = """
                {
                    ?expr genex:hasConfidenceLevel obo:CIO_0000029 . # high confidence
                } UNION {
                    ?expr genex:hasConfidenceLevel obo:CIO_0000031 . # medium confidence
                }
                """
            elif confidence_level >= 20:
                confidence_filter = """
                {
                    ?expr genex:hasConfidenceLevel obo:CIO_0000029 . # high confidence
                } UNION {
                    ?expr genex:hasConfidenceLevel obo:CIO_0000031 . # medium confidence
                } UNION {
                    ?expr genex:hasConfidenceLevel obo:CIO_0000030 . # low confidence
                }
                """
        
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
              {genes_clause}
              {anatomical_entities_clause}
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
        logger.info(f"Executing Bgee SPARQL query (length: {len(query)})")

        try:
            response = requests.get(
                self.endpoint,
                params={"query": query, "format": "json"},
                timeout=30,
            )
            logger.debug(f"Bgee SPARQL response status: {response.status_code}")
            response.raise_for_status()

            data = response.json()
            bindings = data.get("results", {}).get("bindings", [])
            logger.info(f"Retrieved {len(bindings)} Bgee result bindings")

            return data

        except requests.exceptions.Timeout:
            raise BgeeDataError("Bgee SPARQL query timeout")
        except requests.exceptions.ConnectionError:
            raise BgeeDataError("Failed to connect to Bgee SPARQL endpoint")
        except requests.exceptions.HTTPError as e:
            raise BgeeDataError(f"Bgee HTTP error {e.response.status_code}: {e}")
        except requests.exceptions.RequestException as e:
            raise BgeeDataError(f"Bgee request error: {str(e)}")
        except ValueError as e:
            raise BgeeDataError(f"Invalid JSON response from Bgee: {str(e)}")


# Exception classes
class BgeeDataError(Exception):
    """Exception raised for Bgee data errors"""
    pass


# Global service instance
bgee_query_service = BgeeQueryService()
