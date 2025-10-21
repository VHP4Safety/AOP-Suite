import logging
from typing import List, Dict
from backend.model.aop_data_model import CytoscapeNode

logger = logging.getLogger(__name__)

def query_gene_expression_data(ensembl_nodes: List[CytoscapeNode]) -> List[Dict[str, str]]:
    """Query Bgee for basic gene expression data"""
    try:
        # Extract Ensembl IDs from nodes
        ensembl_ids = []
        for node in ensembl_nodes:
            ensembl_id = node.properties.get("ensembl_id", node.id)
            if ensembl_id.startswith("ensembl_"):
                ensembl_id = ensembl_id.replace("ensembl_", "")
            ensembl_ids.append(ensembl_id)

        if not ensembl_ids:
            return []

        logger.info(f"Querying Bgee expression for {len(ensembl_ids)} genes")

        # Use existing Bgee query implementation
        from backend.query.bgee.bgee_query import query_bgee_gene_expression
        expression_data = query_bgee_gene_expression(ensembl_ids)

        logger.info(f"Retrieved expression data for {len(expression_data)} genes")
        return expression_data

    except Exception as e:
        logger.error(f"Error querying Bgee expression: {e}")
        return []

def query_anatomical_expression_data(ensembl_nodes: List[CytoscapeNode]) -> List[Dict[str, str]]:
    """Query Bgee for organ-specific expression data"""
    try:
        ensembl_ids = []
        for node in ensembl_nodes:
            ensembl_id = node.properties.get("ensembl_id", node.id)
            if ensembl_id.startswith("ensembl_"):
                ensembl_id = ensembl_id.replace("ensembl_", "")
            ensembl_ids.append(ensembl_id)

        if not ensembl_ids:
            return []

        logger.info(f"Querying Bgee anatomical for {len(ensembl_ids)} genes")

        # Use existing Bgee query implementation
        from backend.query.bgee.bgee_query import query_bgee_anatomical_expression
        anatomical_data = query_bgee_anatomical_expression(ensembl_ids)

        logger.info(f"Retrieved anatomical data for {len(anatomical_data)} entries")
        return anatomical_data

    except Exception as e:
        logger.error(f"Error querying Bgee anatomical: {e}")
        return []

def query_developmental_expression_data(ensembl_nodes: List[CytoscapeNode]) -> List[Dict[str, str]]:
    """Query Bgee for developmental stage expression data"""
    try:
        ensembl_ids = []
        for node in ensembl_nodes:
            ensembl_id = node.properties.get("ensembl_id", node.id)
            if ensembl_id.startswith("ensembl_"):
                ensembl_id = ensembl_id.replace("ensembl_", "")
            ensembl_ids.append(ensembl_id)

        if not ensembl_ids:
            return []

        logger.info(f"Querying Bgee developmental for {len(ensembl_ids)} genes")

        # Use existing Bgee query implementation
        from backend.query.bgee.bgee_query import query_bgee_developmental_expression
        developmental_data = query_bgee_developmental_expression(ensembl_ids)

        logger.info(f"Retrieved developmental data for {len(developmental_data)} entries")
        return developmental_data

    except Exception as e:
        logger.error(f"Error querying Bgee developmental: {e}")
        return []