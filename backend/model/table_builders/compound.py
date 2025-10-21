from backend.model.parsers.cytoscape import CytoscapeNetworkParser
from backend.model.cytoscape.elements import CytoscapeNode
import logging
from typing import List, Dict

logger = logging.getLogger(__name__)

class CompoundTableBuilder:
    """Builds compound table data from Cytoscape network"""

    def __init__(self, parser: CytoscapeNetworkParser):
        self.parser = parser
        self.chemical_nodes = {node.id: node for node in self._get_chemical_nodes()}

    def _get_chemical_nodes(self) -> List[CytoscapeNode]:
        """Get all chemical nodes from the network"""
        return [
            node
            for node in self.parser.nodes
            if (
                node.classes == "chemical-node"
                or node.node_type == "chemical"
                or node.id.startswith("chemical_")
            )
        ]

    def build_compound_table(self) -> List[Dict[str, str]]:
        """Build compound table from network chemical nodes"""
        table_entries = []
        seen_compounds = set()

        for node in self.chemical_nodes.values():
            compound_name = (
                node.properties.get("compound_name")
                or node.properties.get("chemical_label")
                or node.label
            )

            pubchem_id = node.properties.get("pubchem_id", "")
            pubchem_compound = node.properties.get("pubchem_compound", "")
            cas_id = node.properties.get("cas_id", "N/A")

            compound_key = f"{compound_name}_{pubchem_id}"
            if compound_key not in seen_compounds:
                entry = {
                    "compound_name": compound_name,
                    "chemical_label": node.properties.get(
                        "chemical_label", compound_name
                    ),
                    "pubchem_id": pubchem_id,
                    "pubchem_compound": pubchem_compound,
                    "cas_id": cas_id,
                    "chemical_uri": node.properties.get("chemical_uri", ""),
                    "smiles": node.properties.get("smiles", ""),
                    "node_id": node.id,
                }
                table_entries.append(entry)
                seen_compounds.add(compound_key)

        logger.info(f"Built compound table with {len(table_entries)} entries")
        return table_entries
