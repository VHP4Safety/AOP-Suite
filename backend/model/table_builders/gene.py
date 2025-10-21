from typing import List, Dict, Optional
import logging
from dataclasses import dataclass, field

from backend.model.parsers.cytoscape import CytoscapeNetworkParser
from backend.model.cytoscape.elements import CytoscapeNode, CytoscapeEdge

logger = logging.getLogger(__name__)


@dataclass
class GeneProteinPair:
    """Represents a gene-protein relationship"""

    gene_id: str
    gene_label: str
    protein_id: str
    protein_label: str
    uniprot_id: str
    ensembl_node_id: str
    uniprot_node_id: str

    def to_table_entry(self) -> Dict[str, str]:
        """Convert to gene table entry format"""
        return {
            "gene": self.gene_label if self.gene_label != "N/A" else "N/A",
            "protein": self.protein_label if self.protein_label != "N/A" else "N/A",
            "uniprot_id": self.uniprot_id if self.uniprot_id != "N/A" else "N/A",
            "ensembl_id": (
                self.ensembl_node_id if self.ensembl_node_id != "N/A" else "N/A"
            ),
            "uniprot_node_id": (
                self.uniprot_node_id if self.uniprot_node_id != "N/A" else "N/A"
            ),
        }

class GeneTableBuilder:
    """Builds gene table data from Cytoscape network"""

    def __init__(self, parser: CytoscapeNetworkParser):
        self.parser = parser
        self.ensembl_nodes = {node.id: node for node in parser.get_ensembl_nodes()}
        self.uniprot_nodes = {node.id: node for node in parser.get_uniprot_nodes()}
        self.gene_relationships = parser.get_gene_relationships()
        self.expression_edges = self._get_expression_edges()

    def _get_expression_edges(self) -> List[CytoscapeEdge]:
        """Get all expression edges from the network"""
        return [
            edge
            for edge in self.parser.edges
            if edge.properties.get("type") == "expression_in"
        ]

    def build_gene_table(self) -> List[Dict[str, str]]:
        """Build complete gene table with expression data"""
        gene_pairs = self._create_gene_protein_pairs()
        orphaned_genes = self._get_orphaned_genes(gene_pairs)
        orphaned_proteins = self._get_orphaned_proteins(gene_pairs)

        all_pairs = gene_pairs + orphaned_genes + orphaned_proteins

        table_entries = []
        seen_pairs = set()

        for pair in all_pairs:
            entry = pair.to_table_entry()

            expression_data = self._get_expression_data_for_gene(pair.ensembl_node_id)
            if expression_data:
                entry.update(
                    {
                        "expression_organs": "; ".join(
                            [exp["organ"] for exp in expression_data]
                        ),
                        "expression_levels": "; ".join(
                            [exp["level"] for exp in expression_data]
                        ),
                        "expression_confidence": "; ".join(
                            [exp["confidence"] for exp in expression_data]
                        ),
                        "expression_ids": "; ".join(
                            [exp["expr_id"] for exp in expression_data]
                        ),
                    }
                )
            else:
                entry.update(
                    {
                        "expression_organs": "N/A",
                        "expression_levels": "N/A",
                        "expression_confidence": "N/A",
                        "expression_ids": "N/A",
                    }
                )

            pair_key = f"{entry['gene']}_{entry['protein']}_{entry['uniprot_id']}"

            if pair_key not in seen_pairs:
                table_entries.append(entry)
                seen_pairs.add(pair_key)

        logger.info(f"Built gene table with {len(table_entries)} entries")
        return table_entries

    def _get_expression_data_for_gene(self, gene_node_id: str) -> List[Dict[str, str]]:
        """Get expression data for a specific gene"""
        expression_data = []

        for edge in self.expression_edges:
            if edge.source == gene_node_id:
                target_node = None
                for node in self.parser.nodes:
                    if node.id == edge.target:
                        target_node = node
                        break

                if target_node:
                    expression_data.append(
                        {
                            "organ": target_node.label,
                            "level": edge.properties.get("expression_level", "N/A"),
                            "confidence": edge.properties.get(
                                "confidence_level", "N/A"
                            ),
                            "expr_id": edge.properties.get("expr", "N/A"),
                        }
                    )

        return expression_data

    def _create_gene_protein_pairs(self) -> List[GeneProteinPair]:
        """Create gene-protein pairs from relationships"""
        pairs = []

        for edge in self.gene_relationships:
            if edge.label != "translates to":
                continue

            ensembl_node = None
            uniprot_node = None

            source_node = self.ensembl_nodes.get(edge.source) or self.uniprot_nodes.get(
                edge.source
            )
            target_node = self.ensembl_nodes.get(edge.target) or self.uniprot_nodes.get(
                edge.target
            )

            if source_node and source_node.is_ensembl_node():
                ensembl_node = source_node
                uniprot_node = target_node
            elif target_node and target_node.is_ensembl_node():
                ensembl_node = target_node
                uniprot_node = source_node

            if ensembl_node and uniprot_node:
                pair = self._create_pair_from_nodes(ensembl_node, uniprot_node)
                if pair:
                    pairs.append(pair)

        logger.debug(f"Created {len(pairs)} gene-protein pairs from relationships")
        return pairs

    def _create_pair_from_nodes(
        self, ensembl_node: CytoscapeNode, uniprot_node: CytoscapeNode
    ) -> Optional[GeneProteinPair]:
        """Create a gene-protein pair from two nodes"""
        try:
            gene_label = ensembl_node.label
            ensembl_id = ensembl_node.properties.get("ensembl_id", ensembl_node.id)
            if ensembl_id.startswith("ensembl_"):
                ensembl_id = ensembl_id.replace("ensembl_", "")

            protein_label = uniprot_node.label
            uniprot_id = uniprot_node.properties.get("uniprot_id", uniprot_node.id)
            if uniprot_id.startswith("uniprot_"):
                uniprot_id = uniprot_id.replace("uniprot_", "")

            if len(protein_label) <= 10 and not protein_label.startswith("uniprot_"):
                if uniprot_id == "NA" or uniprot_id == uniprot_node.id:
                    uniprot_id = protein_label

            return GeneProteinPair(
                gene_id=ensembl_id,
                gene_label=gene_label,
                protein_id=uniprot_id,
                protein_label=protein_label,
                uniprot_id=uniprot_id,
                ensembl_node_id=ensembl_node.id,
                uniprot_node_id=uniprot_node.id,
            )
        except Exception as e:
            logger.warning(
                f"Failed to create pair from nodes {ensembl_node.id}, {uniprot_node.id}: {e}"
            )
            return None

    def _get_orphaned_genes(
        self, existing_pairs: List[GeneProteinPair]
    ) -> List[GeneProteinPair]:
        """Get genes without protein connections"""
        connected_gene_ids = {pair.ensembl_node_id for pair in existing_pairs}
        orphaned = []

        for node_id, node in self.ensembl_nodes.items():
            if node_id not in connected_gene_ids:
                ensembl_id = node.properties.get("ensembl_id", node.id)
                if ensembl_id.startswith("ensembl_"):
                    ensembl_id = ensembl_id.replace("ensembl_", "")

                pair = GeneProteinPair(
                    gene_id=ensembl_id,
                    gene_label=node.label,
                    protein_id="N/A",
                    protein_label="N/A",
                    uniprot_id="N/A",
                    ensembl_node_id=node.id,
                    uniprot_node_id="N/A",
                )
                orphaned.append(pair)

        logger.debug(f"Found {len(orphaned)} orphaned genes")
        return orphaned

    def _get_orphaned_proteins(
        self, existing_pairs: List[GeneProteinPair]
    ) -> List[GeneProteinPair]:
        """Get proteins without gene connections"""
        connected_protein_ids = {pair.uniprot_node_id for pair in existing_pairs}
        orphaned = []

        for node_id, node in self.uniprot_nodes.items():
            if node_id not in connected_protein_ids:
                uniprot_id = node.properties.get("uniprot_id", node.id)
                if uniprot_id.startswith("uniprot_"):
                    uniprot_id = uniprot_id.replace("uniprot_", "")

                if len(node.label) <= 10 and not node.label.startswith("uniprot_"):
                    if uniprot_id == "NA" or uniprot_id == node.id:
                        uniprot_id = node.label

                pair = GeneProteinPair(
                    gene_id="N/A",
                    gene_label="N/A",
                    protein_id=uniprot_id,
                    protein_label=node.label,
                    uniprot_id=uniprot_id,
                    ensembl_node_id="N/A",
                    uniprot_node_id=node.id,
                )
                orphaned.append(pair)

        logger.debug(f"Found {len(orphaned)} orphaned proteins")
        return orphaned


class GeneExpressionTableBuilder:
    """Builds gene expression table data from Cytoscape network"""

    def __init__(self, parser: CytoscapeNetworkParser):
        self.parser = parser
        self.ensembl_nodes = {node.id: node for node in parser.get_ensembl_nodes()}
        self.gene_expression_edges = self._get_gene_expression_edges()
        self.organ_nodes = self.parser.get_organ_nodes()

    def _get_gene_expression_edges(self) -> List[CytoscapeEdge]:
        """Get all gene expression edges from the network"""
        return [
            edge
            for edge in self.parser.edges
            if edge.properties.get("type") == "expression_in"
        ]

    def build_gene_expression_table(self) -> List[Dict[str, str]]:
        """Build gene expression table from gene expression edges"""
        table_entries = []
        seen_entries = set()

        for edge in self.gene_expression_edges:
            source_node = self.ensembl_nodes.get(edge.source)

            # Find target organ node
            target_node = None
            for node in self.parser.nodes:
                if node.id == edge.target and node.is_organ_node():
                    target_node = node
                    break

            if source_node and target_node:
                entry_key = f"{source_node.id}_{target_node.id}"
                if entry_key not in seen_entries:
                    # Extract gene ID from node
                    gene_id = source_node.properties.get("ensembl_id", source_node.id)
                    if gene_id.startswith("ensembl_"):
                        gene_id = gene_id.replace("ensembl_", "")

                    entry = {
                        "gene_id": gene_id,
                        "gene_label": source_node.label,
                        "organ": target_node.label,
                        "organ_id": target_node.properties.get(
                            "anatomical_id", target_node.id
                        ),
                        "expression_level": edge.properties.get(
                            "expression_level", "N/A"
                        ),
                        "confidence": edge.properties.get("confidence_level", "N/A"),
                        "developmental_stage": edge.properties.get(
                            "developmental_stage", "N/A"
                        ),
                        "expr_id": edge.properties.get("expr", "N/A"),
                    }
                    table_entries.append(entry)
                    seen_entries.add(entry_key)

        logger.info(f"Built gene expression table with {len(table_entries)} entries")
        return table_entries
