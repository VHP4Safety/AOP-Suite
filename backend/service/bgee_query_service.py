import logging
from typing import List, Dict
from backend.models.schemas.base_model import CytoscapeNode
from backend.query.bgee.bgee_query import query_bgee_anatomical_expression

logger = logging.getLogger(__name__)

def query_gene_expression_data(gene_nodes: List[CytoscapeNode]) -> List[Dict[str, str]]:
    """Query Bgee for basic gene expression data"""
    try:
        # Extract Ensembl IDs from nodes
        gene_ids = []
        for node in gene_nodes:
            gene_id = node.properties.get("gene_id", node.id)
            if gene_id.startswith("gene_"):
                gene_id = gene_id.replace("gene_", "")
            gene_ids.append(gene_id)

        if not gene_ids:
            return []

        logger.info(f"Querying Bgee expression for {len(gene_ids)} genes")
        expression_data = query_bgee_gene_expression(gene_ids)

        logger.info(f"Retrieved expression data for {len(expression_data)} genes")
        return expression_data

    except Exception as e:
        logger.error(f"Error querying Bgee expression: {e}")
        return []

def query_anatomical_expression_data(gene_nodes: List[CytoscapeNode]) -> List[Dict[str, str]]:
    """Query Bgee for organ-specific expression data"""
    try:
        gene_ids = []
        for node in gene_nodes:
            gene_id = node.properties.get("gene_id", node.id)
            if gene_id.startswith("gene_"):
                gene_id = gene_id.replace("gene_", "")
            gene_ids.append(gene_id)

        if not gene_ids:
            return []

        logger.info(f"Querying Bgee anatomical for {len(gene_ids)} genes")
        anatomical_data = query_bgee_anatomical_expression(gene_ids)

        logger.info(f"Retrieved anatomical data for {len(anatomical_data)} entries")
        return anatomical_data

    except Exception as e:
        logger.error(f"Error querying Bgee anatomical: {e}")
        return []

def query_developmental_expression_data(gene_nodes: List[CytoscapeNode]) -> List[Dict[str, str]]:
    """Query Bgee for developmental stage expression data"""
    try:
        gene_ids = []
        for node in gene_nodes:
            gene_id = node.properties.get("gene_id", node.id)
            if gene_id.startswith("gene_"):
                gene_id = gene_id.replace("gene_", "")
            gene_ids.append(gene_id)

        if not gene_ids:
            return []

        logger.info(f"Querying Bgee developmental for {len(gene_ids)} genes")
        developmental_data = query_bgee_developmental_expression(gene_ids)

        logger.info(f"Retrieved developmental data for {len(developmental_data)} entries")
        return developmental_data

    except Exception as e:
        logger.error(f"Error querying Bgee developmental: {e}")
        return []
