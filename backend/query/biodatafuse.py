from pyBiodatafuse import id_mapper
from pyBiodatafuse.annotators import opentargets, bgee
import pandas as pd


def get_bridgedb_xref(identifiers, input_species="Human", input_datasource="PubChem Compound", output_datasource="All"):
    """
        identifiers (list): List of identifiers to map
        input_species (str, optional): Input species (default: "Human")
        input_datasource (str, optional): Input datasource (default: "PubChem Compound")
        output_datasource (str, optional): Output datasource (default: "All")

    """
    data_input = pd.DataFrame(identifiers)
    try:        
        bridgedb_df, bridgedb_metadata = id_mapper.bridgedb_xref(
            identifiers=data_input,
            input_species=input_species,
            input_datasource=input_datasource,
            output_datasource=output_datasource,
        )
        return bridgedb_df, bridgedb_metadata
    except Exception as e:
        return {"error": str(e)}

def add_bdf_opentargets(bridgedb_df):
    try:
        ot_df, ot_metadata = opentargets.get_compound_disease_interactions(
            bridgedb_df=bridgedb_df
        )
        return ot_df, ot_metadata
    except Exception as e:
        return {"error": str(e)}, 500

def add_bdf_bgee(bridgedb_df):
    try:
        bgee_df, bgee_metadata = bgee.get_gene_expression(
            bridgedb_df=bridgedb_df
            )
        return bgee_df, bgee_metadata
    except Exception as e:
        return {"error": str(e)}
