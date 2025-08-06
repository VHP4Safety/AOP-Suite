import requests
import logging
from typing import Dict, List, Any, Optional, Tuple

from backend.model.aop_data_model import (
    AOPNetworkBuilder, 
    AOPNetwork, 
    AOPKeyEvent, 
    NodeType,
    GeneAssociation
)

# Set up logger
logger = logging.getLogger(__name__)

AOPWIKISPARQL_ENDPOINT = "https://aopwiki.rdf.bigcat-bioinformatics.org/sparql/"

class SPARQLQueryError(Exception):
    """Custom exception for SPARQL query errors"""
    pass

class AOPDataError(Exception):
    """Custom exception for AOP data processing errors"""
    pass

class AOPQueryService:
    """Service for querying AOP data from SPARQL endpoint"""

    def __init__(self):
        self.endpoint = AOPWIKISPARQL_ENDPOINT

    def query_aop_network(self, query_type: str, values: str) -> AOPNetwork:
        """Query AOP network data and return structured model"""
        try:
            # Build and execute SPARQL query
            sparql_query = self._build_aop_sparql_query(query_type, values)
            if not sparql_query:
                raise AOPDataError(f"Invalid query type: {query_type}")

            sparql_results = self._execute_sparql_query(sparql_query)

            # Build network from results using the data model
            builder = AOPNetworkBuilder()
            for binding in sparql_results.get("results", {}).get("bindings", []):
                builder.process_sparql_binding(binding)

            network = builder.build()
            logger.info(f"Built AOP network: {network.get_summary()}")

            return network

        except Exception as e:
            logger.error(f"Failed to query AOP network: {e}")
            raise AOPDataError(str(e))

    def query_genes_for_network(self, network: AOPNetwork) -> AOPNetwork:
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
            builder.add_gene_associations(gene_results.get("results", {}).get("bindings", []))

            updated_network = builder.build()
            logger.info(f"Added gene associations: {len(updated_network.gene_associations)} genes")

            return updated_network

        except Exception as e:
            logger.error(f"Failed to query genes for network: {e}")
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
            builder.add_compound_associations(compound_results.get("results", {}).get("bindings", []))

            updated_network = builder.build()
            logger.info(f"Added compound associations: {len(updated_network.compound_associations)} compounds")

            return updated_network

        except Exception as e:
            logger.error(f"Failed to query compounds for network: {e}")
            # Return original network if compound query fails
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
        values_clause_map = {
            "mie": f"VALUES ?MIE {{ {formatted_values} }}",
            "aop": f"VALUES ?aop {{ {formatted_values} }}",
            "ke_upstream": f"VALUES ?KE_upstream {{ {formatted_values} }}",
            "ke_downstream": f"VALUES ?KE_downstream {{ {formatted_values} }}"
        }

        values_clause = values_clause_map.get(query_type)
        if not values_clause:
            logger.warning(f"Invalid query type: {query_type}")
            return ""

        final_query = base_query.replace("%VALUES_CLAUSE%", values_clause)
        logger.debug(f"Generated SPARQL query length: {len(final_query)}")

        return final_query

    def _build_gene_sparql_query(self, ke_uris: str) -> str:
        """Build SPARQL query for gene data"""
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

# Public API functions that use the data model
def get_aop_network_data(query_type: str, values: str) -> Dict[str, Any]:
    """Get AOP network data using the data model"""
    try:
        network = aop_query_service.query_aop_network(query_type, values)
        summary = network.get_summary()
        
        response_data = {
            "success": True,
            "elements": network.to_cytoscape_elements(),
            "elements_count": len(network.to_cytoscape_elements()),
            "report": summary,
        }
        
        # Generate warnings if incomplete
        warnings = []
        if summary.get("mie_count", 0) == 0:
            warnings.append("No Molecular Initiating Events (MIEs) found")
        if summary.get("ao_count", 0) == 0:
            warnings.append("No Adverse Outcomes (AOs) found")
        if summary.get("ker_count", 0) == 0:
            if summary.get("mie_count", 0) > 0 or summary.get("ao_count", 0) > 0:
                warnings.append("No Key Event Relationships (KERs) found")
        
        if warnings:
            response_data["warning"] = {
                "type": "incomplete_aop_data",
                "message": f"Warnings: {'; '.join(warnings)}",
                "details": f"Found: {summary.get('mie_count', 0)} MIEs, {summary.get('ao_count', 0)} AOs, {summary.get('ke_count', 0)} intermediate KEs, {summary.get('ker_count', 0)} KERs",
                "specific_issues": warnings,
            }
        
        return response_data
        
    except Exception as e:
        logger.error(f"AOP network query failed: {e}")
        return {"error": str(e)}, 500

def load_and_show_genes(kes: str) -> List[Dict[str, Any]]:
    """Load genes for KEs using the data model"""
    try:
        # Create temporary network with KEs
        temp_network = AOPNetwork()
        ke_uris = [uri.strip('<>') for uri in kes.split()]
        
        for ke_uri in ke_uris:
            ke_id = ke_uri.split("/")[-1] if "/" in ke_uri else ke_uri
            key_event = AOPKeyEvent(
                ke_id=ke_id,
                uri=ke_uri,
                title="Temporary KE",
                ke_type=NodeType.KE
            )
            temp_network.add_key_event(key_event)
        
        # Query genes using the data model
        enriched_network = aop_query_service.query_genes_for_network(temp_network)
        
        # Convert to Cytoscape elements
        cytoscape_elements = []
        for association in enriched_network.gene_associations:
            cytoscape_elements.extend(association.to_cytoscape_elements())
        
        logger.info(f"Generated {len(cytoscape_elements)} gene elements using data model")
        return cytoscape_elements
        
    except Exception as e:
        logger.error(f"Gene query failed: {e}")
        return []

def load_and_show_compounds(aops: str) -> List[Dict[str, Any]]:
    """Load compounds for AOPs using the data model"""
    try:
        # Create temporary network with AOPs
        temp_network = AOPNetwork()
        aop_uris = [uri.strip('<>') for uri in aops.split()]
        
        for aop_uri in aop_uris:
            aop_id = aop_uri.split("/")[-1] if "/" in aop_uri else aop_uri
            # Add basic AOP info to network
            temp_network.aop_info[aop_uri] = {
                "aop_id": aop_id,
                "title": "Temporary AOP"
            }
        
        # Query compounds using the data model
        enriched_network = aop_query_service.query_compounds_for_network(temp_network)
        
        # Convert to Cytoscape elements
        cytoscape_elements = []
        for association in enriched_network.compound_associations:
            cytoscape_elements.extend(association.to_cytoscape_elements())
        
        logger.info(f"Generated {len(cytoscape_elements)} compound elements using data model")
        return cytoscape_elements
        
    except Exception as e:
        logger.error(f"Compound query failed: {e}")
        return []

def populate_aop_table(cy_elements):
    """Populate AOP table using data model - should be called via service layer"""
    logger.warning("populate_aop_table called directly - should use service layer")
    
    # Import here to avoid circular dependency
    from backend.service.aop_network_service import AOPTableBuilder
    builder = AOPTableBuilder(cy_elements)
    return builder.build_aop_table()
