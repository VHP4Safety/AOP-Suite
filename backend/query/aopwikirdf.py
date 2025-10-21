import requests
import logging
from typing import Dict, Any


from backend.model.parsers.builder import AOPNetworkBuilder

from backend.model.schemas.base import AOPNetwork


# Set up logger
logger = logging.getLogger(__name__)

AOPWIKISPARQL_ENDPOINT = "https://aopwiki.rdf.bigcat-bioinformatics.org/sparql/"


class SPARQLQueryError(Exception):
    """Custom exception for SPARQL query errors"""

    pass  # TODO


class AOPDataError(Exception):
    """Custom exception for AOP data processing errors"""

    pass  # TODO


class AOPQueryService:
    """Service for querying AOP data from SPARQL endpoint"""

    def __init__(self):
        self.endpoint = AOPWIKISPARQL_ENDPOINT

    def query_aop_network(self, query_type: str, values: str) -> AOPNetwork:
        """Query AOP network data and return structured model"""
        try:
            # Build and execute SPARQL query
            network_query = self._build_aop_sparql_query(query_type, values)
            if not network_query:
                raise AOPDataError(f"Invalid query type: {query_type}")

            sparql_results = self._execute_sparql_query(network_query)

            # Build network from results using the data model
            builder = AOPNetworkBuilder()
            for binding in sparql_results.get("results", {}).get("bindings", []):
                builder.process_sparql_binding(binding)

            network = builder.build()
            logger.info(f"Built AOP network: {network.get_summary()}")

            return network, network_query

        except Exception as e:
            logger.error(f"Failed to query AOP network: {e}")
            raise AOPDataError(str(e))

    def query_genes_for_network(self, network: AOPNetwork, include_proteins: bool = True) -> AOPNetwork:
        """Query gene associations for all KEs in the network"""
        try:
            ke_uris = network.get_ke_uris()
            if not ke_uris:
                logger.warning("No Key Events found for gene querying")
                return network

            # Format KE URIs for SPARQL
            formatted_uris = " ".join([f"<{uri}>" for uri in ke_uris])
            gene_query = self._build_gene_sparql_query(formatted_uris)

            gene_results = self._execute_sparql_query(gene_query)

            # Add gene associations to network using the builder
            builder = AOPNetworkBuilder()
            builder.network = network  # Use existing network
            builder.add_gene_associations(
                gene_results.get("results", {}).get("bindings", []), include_proteins
            )

            updated_network = builder.build()
            logger.info(
                f"Added gene associations: {len(updated_network.gene_associations)} genes (include_proteins: {include_proteins})"
            )

            return updated_network, gene_query

        except Exception as e:
            logger.error(f"Failed to query genes for network: {e}")
            # Return original network if gene query fails
            return network

    def query_organs_for_network(self, network: AOPNetwork) -> AOPNetwork:
        """Query gene associations for all KEs in the network"""
        try:
            ke_uris = network.get_ke_uris()
            if not ke_uris:
                logger.warning("No Key Events found for gene querying")
                return network

            # Format KE URIs for SPARQL
            formatted_uris = " ".join([f"<{uri}>" for uri in ke_uris])
            organ_query = self._build_organ_sparql_query(formatted_uris)

            organ_results = self._execute_sparql_query(organ_query)

            # Add gene associations to network using the builder
            builder = AOPNetworkBuilder()
            builder.network = network  # Use existing network
            builder.add_organ_associations(
                organ_results.get("results", {}).get("bindings", [])
            )

            updated_network = builder.build()
            logger.info(
                f"Added organ associations: {len(updated_network.organ_associations)} components"
            )

            return updated_network, organ_query
        except Exception as e:
            logger.error(f"Failed to query components for network: {e}")
            # Return original network if gene query fails
            return network

    def query_compounds_for_network(self, network: AOPNetwork) -> AOPNetwork:
        """Query compound associations for all AOPs in the network"""
        try:
            aop_uris = network.get_aop_uris()
            if not aop_uris:
                logger.warning("No AOPs found for compound querying")
                return network

            # Format AOP URIs for SPARQL
            formatted_uris = " ".join([f"<{uri}>" for uri in aop_uris])
            compound_query = self._build_compound_sparql_query(formatted_uris)
            print(compound_query)
            compound_results = self._execute_sparql_query(compound_query)

            # Add compound associations to network using the builder
            builder = AOPNetworkBuilder()
            builder.network = network  # Use existing network
            builder.add_compound_associations(
                compound_results.get("results", {}).get("bindings", [])
            )

            updated_network = builder.build()
            logger.info(
                f"Added compound associations: {len(updated_network.compound_associations)} compounds"
            )

            return updated_network, compound_query

        except Exception as e:
            logger.error(f"Failed to query compounds for network: {e}")
            # Return original network if compound query fails
            return network

    def query_components_for_network(self, network: AOPNetwork, go_only: bool = False) -> AOPNetwork:
        """Query gene associations for all KEs in the network"""
        try:
            ke_uris = network.get_ke_uris()
            if not ke_uris:
                logger.warning("No Key Events found for gene querying")
                return network

            # Format KE URIs for SPARQL
            formatted_uris = " ".join([f"<{uri}>" for uri in ke_uris])
            component_query = self._build_components_sparql_query(go_only, formatted_uris)

            component_results = self._execute_sparql_query(component_query)

            # Add gene associations to network using the builder
            builder = AOPNetworkBuilder()
            builder.network = network  # Use existing network
            builder.add_component_associations(
                component_results.get("results", {}).get("bindings", [])
            )

            updated_network = builder.build()
            logger.info(
                f"Added component associations: {len(updated_network.component_associations)} components"
            )

            return updated_network, component_query

        except Exception as e:
            logger.error(f"Failed to query components for network: {e}")
            # Return original network if gene query fails
            return network

    def _build_aop_sparql_query(self, query_type: str, values: str) -> str:
        """Build SPARQL query for AOP data"""
        logger.info(f"Building AOP SPARQL query: {query_type}, values: {values}")

        # Process values to ensure proper URI formatting
        processed_values = []
        for value in values.split():
            if value.startswith("http"):
                processed_values.append(f"<{value}>")
            else:
                processed_values.append(f"<{value}>")

        formatted_values = " ".join(processed_values)

        # Base query template
        base_query = """SELECT DISTINCT ?aop ?aop_title ?MIEtitle ?MIE ?KE_downstream ?KE_downstream_title ?KER ?ao ?ao_title ?KE_upstream ?KE_upstream_title
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
          }
        }"""

        # Build VALUES clause based on query type
        values_clause_map = {
            "mie": f"VALUES ?MIE {{ {formatted_values} }}",
            "aop": f"VALUES ?aop {{ {formatted_values} }}",
            "ke_upstream": f"VALUES ?KE_upstream {{ {formatted_values} }}",
            "ke_downstream": f"VALUES ?KE_downstream {{ {formatted_values} }}",
        }

        values_clause = values_clause_map.get(query_type)
        if not values_clause:
            logger.warning(f"Invalid query type: {query_type}")
            return ""

        final_query = base_query.replace("%VALUES_CLAUSE%", values_clause)
        logger.debug(f"Generated SPARQL query length: {len(final_query)}")

        return final_query

    def _build_gene_sparql_query(self, ke_uris: str, include_proteins: bool = True) -> str:
        """Build SPARQL query for gene data"""
        if include_proteins:
            return f"""
                SELECT DISTINCT ?ke ?ensembl ?uniprot WHERE {{
                    VALUES ?ke {{ {ke_uris} }}
                    ?ke a aopo:KeyEvent; edam:data_1025 ?object .
                    ?object skos:exactMatch ?id .
                    ?id a edam:data_1033; edam:data_1033 ?ensembl .
                    OPTIONAL {{
                        ?object skos:exactMatch ?prot .
                        ?prot a edam:data_2291 ;
                              edam:data_2291 ?uniprot .
                    }}
                }}
            """
        else:
            return f"""
                SELECT DISTINCT ?ke ?ensembl WHERE {{
                    VALUES ?ke {{ {ke_uris} }}
                    ?ke a aopo:KeyEvent; edam:data_1025 ?object .
                    ?object skos:exactMatch ?id .
                    ?id a edam:data_1033; edam:data_1033 ?ensembl .
                }}
            """

    def _build_compound_sparql_query(self, aop_uris: str) -> str:
        """Build SPARQL query for compound data"""
        return f"""
            SELECT DISTINCT ?aop ?compound_name ?cid ?pubchem_compound ?mie ?chemical
            WHERE {{
                VALUES ?aop {{ {aop_uris} }}
                FILTER(STRSTARTS(STR(?pubchem_compound), "https://identifiers.org/pubchem.compound/"))

                ?aop a aopo:AdverseOutcomePathway ; nci:C54571 ?stressor ; aopo:has_molecular_initiating_event ?mie .
                ?chemical skos:exactMatch ?pubchem_compound ; dc:title ?compound_name.
                ?stressor a nci:C54571 ; aopo:has_chemical_entity ?chemical .
                ?pubchem_compound cheminf:000140 ?cid .
            }}
            ORDER BY ?compound_name
        """

    def _build_organ_sparql_query(self, ke_uris: str) -> str:
        """Build SPARQL query for organ data"""
        return f"""
        SELECT DISTINCT ?ke ?organ ?organ_name WHERE {{
                    VALUES ?ke {{ {ke_uris} }}
                    ?ke a aopo:KeyEvent; aopo:OrganContext ?organ .
                    ?organ dc:title ?organ_name .
        }}
        """

    def _build_components_sparql_query(self, go_only: bool, ke_uris: str) -> str:
        """Build SPARQL query for GO process data"""
        if go_only:
            go_filter = 'FILTER(STRSTARTS(STR(?process), "http://purl.obolibrary.org/obo/GO_"))'
        else:
            go_filter = ""
        return f"""
            SELECT DISTINCT ?ke ?keTitle ?bioEvent ?process ?processName ?object ?objectName ?action
            WHERE {{
                {go_filter}
                VALUES ?ke {{ {ke_uris } }}
                ?ke a aopo:KeyEvent ;
                    dc:title ?keTitle .
                OPTIONAL {{ ?ke aopo:hasBiologicalEvent ?bioEvent. ?bioEvent aopo:hasProcess ?process . ?process dc:title ?processName.}}
                OPTIONAL {{ ?ke aopo:hasBiologicalEvent ?bioEvent. ?bioEvent aopo:hasObject ?object . ?object dc:title ?objectName.}}
                OPTIONAL {{ ?ke aopo:hasBiologicalEvent ?bioEvent. ?bioEvent aopo:hasAction ?action . }}
            }}
            ORDER BY ?ke
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


# Global service instance
aop_query_service = AOPQueryService()
