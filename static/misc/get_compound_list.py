
# Importing the required modules.
import requests
from wikidataintegrator import wdi_core

# Setting up the url for sparql endpoint.
compoundwikiEP = "https://compoundcloud.wikibase.cloud/query/sparql"

# Setting up the sparql query for the full list of compounds.
sparqlquery_full = '''
PREFIX wd: <https://compoundcloud.wikibase.cloud/entity/>
PREFIX wdt: <https://compoundcloud.wikibase.cloud/prop/direct/>

SELECT (substr(str(?cmp), 45) as ?ID) (?cmpLabel AS ?Term)
  ?SMILES (?cmp AS ?ref)
WHERE{
  { ?parent wdt:P21 wd:Q2059 ; wdt:P29 ?cmp . } UNION { ?cmp wdt:P21 wd:Q2059 . }
  ?cmp wdt:P1 ?type ; rdfs:label ?cmpLabel . FILTER(lang(?cmpLabel) = 'en')
  ?type rdfs:label ?typeLabel . FILTER(lang(?typeLabel) = 'en')
  OPTIONAL { ?cmp wdt:P7 ?chiralSMILES }
  OPTIONAL { ?cmp wdt:P12 ?nonchiralSMILES }
  BIND (COALESCE(IF(BOUND(?chiralSMILES), ?chiralSMILES, 1/0), IF(BOUND(?nonchiralSMILES), ?nonchiralSMILES, 1/0),"") AS ?SMILES)
  SERVICE wikibase:label { bd:serviceParam wikibase:language "[AUTO_LANGUAGE],en". }
}
'''

# Setting up the spaqrl query for the vhp subset of the compounds. 
sparqlquery_vhp = '''
PREFIX wd: <https://compoundcloud.wikibase.cloud/entity/>
PREFIX wdt: <https://compoundcloud.wikibase.cloud/prop/direct/>

SELECT ?cmp ?cmpLabel ?typeLabel ?pubchem ?cas ?wikidata ?toxbank
       (GROUP_CONCAT(DISTINCT ?roleLabel; separator=", ") AS ?roles)
WHERE {
  ?cmp wdt:P21 wd:Q2059 ; wdt:P1 ?type .
  OPTIONAL { ?cmp wdt:P13 ?pubchem }
  OPTIONAL { ?cmp wdt:P4 ?toxbank }
  OPTIONAL { ?cmp wdt:P5 ?wikidata }
  OPTIONAL { ?cmp wdt:P23 ?cas }
  OPTIONAL { ?cmp wdt:P17 ?role . ?role rdfs:label ?roleLabel }
  SERVICE wikibase:label { bd:serviceParam wikibase:language "[AUTO_LANGUAGE],en". }
} GROUP BY ?typeLabel ?cmp ?cmpLabel ?pubchem ?wikidata ?toxbank ?cas
'''


compound_dat = wdi_core.WDFunctionsEngine.execute_sparql_query(sparqlquery_full, endpoint=compoundwikiEP, as_dataframe=True)
compound_dat = wdi_core.WDFunctionsEngine.execute_sparql_query(sparqlquery_vhp, endpoint=compoundwikiEP, as_dataframe=True)

compound_dat.loc[:, "Term"]
compound_dat.loc[:,["Term", "SMILES", "ID", "ref"]]
