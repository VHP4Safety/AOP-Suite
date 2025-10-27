from enum import Enum
from typing import Set
import logging

logger = logging.getLogger(__name__)

class NodeType(Enum):
    MIE = "mie"
    KE = "ke"
    AO = "ao"
    CHEMICAL = "chemical"
    PROTEIN = "protein"
    GENE = "gene"
    ORGAN = "organ"
    COMPONENT_PROCESS = "component_process" # TODO get actual types
    COMPONENT_OBJECT = "component_object" # To group component object types
    CUSTOM = "custom"
    CELL = "cell"
    QUALITY = "quality"
    CELLULAR_COMPONENT = "cellular_component"


class EdgeType(Enum):
    KER = "ker"
    INTERACTION = "interaction"
    PART_OF = "part_of"
    TRANSLATES_TO = "translates_to"
    EXPRESSION_IN = "expression_in"
    CUSTOM = "custom"
    IS_STRESSOR_OF = "is stressor of"
    HAS_PROCESS = "has process"
    INVOLVES = "involves"
    NA = "na"

    # Component action edge types
    INCREASED = "increased process quality"
    DECREASED = "decreased process quality"
    DELAYED = "delayed"
    OCCURRENCE = "occurrence"
    ABNORMAL = "abnormal"
    PREMATURE = "premature"
    DISRUPTED = "disrupted"
    FUNCTIONAL_CHANGE = "functional change"
    MORPHOLOGICAL_CHANGE = "morphological change"
    PATHOLOGICAL = "pathological"
    ARRESTED = "arrested"
    ASSOCIATED_WITH = "involves"
    HAS_OBJECT = "has object"

    @classmethod
    def get_component_actions(cls) -> Set[str]:
        """Get all component action labels"""
        return {
            cls.INCREASED.value,
            cls.DECREASED.value,
            cls.DELAYED.value,
            cls.OCCURRENCE.value,
            cls.ABNORMAL.value,
            cls.PREMATURE.value,
            cls.DISRUPTED.value,
            cls.FUNCTIONAL_CHANGE.value,
            cls.MORPHOLOGICAL_CHANGE.value,
            cls.PATHOLOGICAL.value,
            cls.ARRESTED.value,
        }

    @classmethod
    def get_iri(cls) -> Set[str]:
        return {
            item.value["iri"]
            for item in cls
            if isinstance(item.value, dict) and "iri" in item.value
        }

    @classmethod
    def get_label(cls) -> Set[str]:
        # For component actions, return the action labels directly
        component_actions = cls.get_component_actions()
        return {
            item.value["label"]
            for item in cls
            if isinstance(item.value, dict) and "label" in item.value
        } | component_actions


class DataSourceType(Enum):
    AOPWIKI = "aopwiki"
    QSPRPRED = "qsprpred"
    BGEE = "bgee"
    OPENTARGETS = "opentargets"
    CUSTOM_TABLE = "custom_table"
    MANUAL = "manual"
