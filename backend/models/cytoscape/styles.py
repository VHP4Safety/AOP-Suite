from typing import Dict, Any, List, Optional
import logging

from backend.models.constants import NodeType, EdgeType
logger = logging.getLogger(__name__)


class AOPStyleManager:
    """Manages base Cytoscape styles for AOP networks"""

    def __init__(self):
        self.base_styles = self._create_base_styles()

    def _create_base_styles(self) -> List[Dict[str, Any]]:
        """Create the base Cytoscape styles"""
        return [
            # Default node styles
            {
                "selector": "node",
                "style": {
                    "width": "350px",
                    "height": "350px",
                    "background-color": "#ffff99",
                    "label": "data(label)",
                    "text-wrap": "wrap",
                    "text-max-width": "235px",
                    "text-valign": "center",
                    "text-halign": "center",
                    "color": "#000",
                    "font-size": "40px",
                    "border-width": "2px",
                    "border-color": "#000",
                    "transition-property": "width, height, font-size, text-max-width",
                    "transition-duration": "0.3s",
                    "transition-timing-function": "ease-out",
                },
            },
            # MIE nodes - use type selector
            {"selector": f"node[type='{NodeType.MIE.value}']", "style": {"background-color": "#ccffcc"}},
            # AO nodes - use type selector
            {"selector": f"node[type='{NodeType.AO.value}']", "style": {"background-color": "#ffe6e6"}},
            # UniProt nodes - use type selector
            {
                "selector": f"node[type='{NodeType.PROTEIN.value}']",
                "style": {"background-color": "#ffff99"},
            },
            # Ensembl nodes - use type selector
            {"selector": f"node[type='{NodeType.GENE.value}']", "style": {"background-color": "#ffcc99"}},
            # Chemical nodes
            {
                "selector": f"node[type='{NodeType.CHEMICAL.value}'], .chemical-node",
                "style": {
                    "width": "270px",
                    "height": "200px",
                    "shape": "triangle",
                    "background-color": "#93d5f6",
                    "label": "data(label)",
                    "text-wrap": "wrap",
                    "text-max-width": "190px",
                    "text-valign": "top",
                    "text-halign": "center",
                    "color": "#000",
                    "font-size": "90px",
                    "border-width": 2,
                    "border-color": "#000",
                    "text-margin-y": 3,
                    "transition-property": "width, height, font-size, text-max-width",
                    "transition-duration": "0.3s",
                    "transition-timing-function": "ease-out",
                },
            },
            # KER edges
            {
                "selector": f"edge[type='{EdgeType.KER.value}'], edge[ker_label]",
                "style": {
                    "curve-style": "unbundled-bezier",
                    "width": "40px",
                    "line-color": "#93d5f6",
                    "opacity": 1,
                    "target-arrow-shape": "triangle",
                    "target-arrow-color": "#93d5f6",
                    "label": "data(ker_label)",
                    "text-margin-y": 1,
                    "text-rotation": "autorotate",
                    "font-size": "40px",
                    "font-weight": "bold",
                    "color": "#000",
                    "transition-property": "width, font-size",
                    "transition-duration": "0.3s",
                    "transition-timing-function": "ease-out",
                },
            },
            # UniProt nodes
            {
                "selector": f"node[type='{NodeType.PROTEIN.value}'], .protein-node",
                "style": {
                    "shape": "round-rectangle",
                    "width": "400px",
                    "height": "200px",
                    "opacity": 1,
                    "label": "data(label)",
                    "background-color": "#e3f2fd",
                    "background-gradient-direction": "to-bottom-right",
                    "background-gradient-stop-colors": "#e3f2fd #bbdefb",
                    "text-valign": "center",
                    "text-halign": "center",
                    "color": "#0d47a1",
                    "font-size": "36px",
                    "font-weight": "600",
                    "font-family": "Arial, sans-serif",
                    "font-color": "#000000",
                    "text-wrap": "wrap",
                    "text-max-width": "180px",
                    "border-width": "2px",
                    "border-color": "#1976d2",
                    "border-style": "solid",
                    "box-shadow": "0px 4px 8px rgba(0,0,0,0.2)",
                    "padding": "4px",
                    "transition-property": "font-size, width, height, border-width, box-shadow",
                    "transition-duration": "0.3s",
                    "transition-timing-function": "ease-out",
                },
            },
            # Ensembl nodes
            {
                "selector": f"node[type='{NodeType.GENE.value}'], .gene-node",
                "style": {
                    "shape": "ellipse",
                    "width": "200px",
                    "height": "100px",
                    "background-opacity": 0,
                    "label": "data(label)",
                    "text-valign": "center",
                    "text-halign": "center",
                    "text-wrap": "wrap",
                    "text-max-width": "180px",
                    "color": "#000000",
                    "font-size": "45px",
                    "font-weight": "bold",
                    "border-width": 0,
                    "border-color": "transparent",
                    "transition-property": "font-size, width, height, text-max-width",
                    "transition-duration": "0.3s",
                    "transition-timing-function": "ease-out",
                },
            },
            # Generic edge labels
            {
                "selector": "edge[label]",
                "style": {
                    "label": "data(label)",
                    "text-rotation": "autorotate",
                    "text-margin-y": -15,
                    "font-size": "40px",
                    "curve-style": "unbundled-bezier",
                    "transition-property": "font-size",
                    "transition-duration": "0.3s",
                    "transition-timing-function": "ease-out",
                },
            },
            # Interaction edges
            {
                "selector": f"edge[type='{EdgeType.INTERACTION.value}']",
                "style": {
                    "width": "40px",
                    "line-color": "#ceafc0",
                    "opacity": 1,
                    "target-arrow-shape": "triangle",
                    "target-arrow-color": "#ceafc0",
                    "text-margin-y": 1,
                    "text-rotation": "autorotate",
                    "font-size": "40px",
                    "font-weight": "bold",
                    "color": "#000",
                    "transition-property": "width, font-size",
                    "transition-duration": "0.3s",
                    "transition-timing-function": "ease-out",
                },
            },
            # QSPR prediction edges
            {
                "selector": ".qspr-prediction-edge",
                "style": {
                    "width": "35px",
                    "line-color": "#ff6b6b",
                    "opacity": 1,
                    "target-arrow-shape": "triangle",
                    "target-arrow-color": "#ff6b6b",
                    "text-margin-y": 1,
                    "text-rotation": "autorotate",
                    "font-size": "35px",
                    "font-weight": "bold",
                    "color": "#000",
                    "line-style": "dashed",
                    "transition-property": "width, font-size",
                    "transition-duration": "0.3s",
                    "transition-timing-function": "ease-out",
                },
            },
            # Bounding box
            {
                "selector": ".bounding-box",
                "style": {
                    "shape": "roundrectangle",
                    "background-opacity": 0.1,
                    "border-width": 2,
                    "border-color": "#000",
                    "label": "data(label)",
                    "text-valign": "top",
                    "text-halign": "center",
                    "font-size": "50px",
                    "text-wrap": "wrap",
                    "font-weight": "bold",
                    "text-max-width": "1400px",
                    "transition-property": "font-size, text-max-width",
                    "transition-duration": "0.3s",
                    "transition-timing-function": "ease-out",
                },
            },
            # Process nodes
            {
                "selector": f"node[type='{NodeType.COMPONENT_PROCESS.value}'], .process-node",
                "style": {
                    "shape": "roundrectangle",
                    "width": "320px",
                    "height": "140px",
                    "background-color": "#ffffff",
                    "border-width": "1px",
                    "border-color": "#000000",
                    "label": "data(label)",
                    "text-valign": "center",
                    "text-halign": "center",
                    "font-size": "32px",
                    "font-weight": "normal",
                    "color": "#2196f3",
                    "text-wrap": "wrap",
                    "text-max-width": "300px",
                    "transition-property": "width, height, font-size, text-max-width, border-width",
                    "transition-duration": "0.3s",
                    "transition-timing-function": "ease-out",
                },
            },
            # Object nodes
            {
                "selector": f"node[type='{NodeType.COMPONENT_OBJECT.value}'], .object-node",
                "style": {
                    "shape": "roundrectangle",
                    "width": "280px",
                    "height": "280px",
                    "background-color": "#f3e5f5",
                    "border-width": "2px",
                    "border-color": "#9c27b0",
                    "label": "data(label)",
                    "text-valign": "center",
                    "text-halign": "center",
                    "font-size": "36px",
                    "font-weight": "bold",
                    "color": "#4a148c",
                    "text-wrap": "wrap",
                    "text-max-width": "260px",
                    "transition-property": "width, height, font-size, text-max-width, border-width",
                    "transition-duration": "0.3s",
                    "transition-timing-function": "ease-out",
                },
            },
            # Has process edges
            {
                "selector": f"edge[type='{EdgeType.HAS_PROCESS.value}']",
                "style": {
                    "curve-style": "bezier",
                    "width": "20px",
                    "line-color": "#4caf50",
                    "opacity": 1,
                    "target-arrow-shape": "triangle",
                    "target-arrow-color": "#4caf50",
                    "arrow-scale": 1.5,
                    "label": "data(label)",
                    "text-rotation": "autorotate",
                    "text-margin-y": "-5px",
                    "font-size": "30px",
                    "font-weight": "bold",
                    "color": "#2e7d32",
                    "transition-property": "width, font-size, text-margin-y",
                    "transition-duration": "0.3s",
                    "transition-timing-function": "ease-out",
                },
            },
            # Has object edges
            {
                "selector": f"edge[type='{EdgeType.HAS_OBJECT.value}']",
                "style": {
                    "curve-style": "bezier",
                    "width": "20px",
                    "line-color": "#9c27b0",
                    "opacity": 1,
                    "target-arrow-shape": "triangle",
                    "target-arrow-color": "#9c27b0",
                    "arrow-scale": 1.2,
                    "line-style": "dashed",
                    "label": "data(label)",
                    "text-rotation": "autorotate",
                    "text-margin-y": "-5px",
                    "font-size": "26px",
                    "color": "#4a148c",
                    "transition-property": "width, font-size, text-margin-y",
                    "transition-duration": "0.3s",
                    "transition-timing-function": "ease-out",
                },
            },
            # Component action edges
            {
                "selector": f"edge[label='{EdgeType.INCREASED.value}'], edge[label='{EdgeType.DECREASED.value}'], edge[label='{EdgeType.DELAYED.value}'], edge[label='{EdgeType.OCCURRENCE.value}'], edge[label='{EdgeType.ABNORMAL.value}'], edge[label='{EdgeType.PREMATURE.value}'], edge[label='{EdgeType.DISRUPTED.value}'], edge[label='{EdgeType.FUNCTIONAL_CHANGE.value}'], edge[label='{EdgeType.MORPHOLOGICAL_CHANGE.value}'], edge[label='{EdgeType.PATHOLOGICAL.value}'], edge[label='{EdgeType.ARRESTED.value}']",
                "style": {
                    "curve-style": "bezier",
                    "width": "20px",
                    "line-color": "#4caf50",
                    "opacity": 1,
                    "target-arrow-shape": "triangle",
                    "target-arrow-color": "#4caf50",
                    "arrow-scale": 1.8,
                    "label": "data(label)",
                    "text-rotation": "autorotate",
                    "text-margin-y": "-8px",
                    "font-size": "28px",
                    "font-weight": "bold",
                    "color": "#1b5e20",
                    "text-background-color": "#e8f5e8",
                    "text-background-opacity": 1,
                    "text-background-padding": "2px",
                    "transition-property": "width, font-size, text-margin-y, text-background-padding",
                    "transition-duration": "0.3s",
                    "transition-timing-function": "ease-out",
                },
            },
            # Organ nodes
            {
                "selector": f"node[type='{NodeType.ORGAN.value}'], .organ-node",
                "style": {
                    "shape": "round-rectangle",
                    "width": "150px",
                    "height": "150px",
                    "background-color": "#8e7cc3",
                    "border-width": "2px",
                    "border-color": "#6a5acd",
                    "label": "data(label)",
                    "text-valign": "center",
                    "text-halign": "center",
                    "font-size": "40px",
                    "font-weight": "bold",
                    "color": "#ffffff",
                    "text-outline-color": "#6a5acd",
                    "text-outline-width": 1,
                    "text-wrap": "wrap",
                    "text-max-width": "50px",
                    "padding": "8px",
                    "opacity": 1,
                    "transition-property": "width, height, font-size, text-max-width, border-width, padding",
                    "transition-duration": "0.3s",
                    "transition-timing-function": "ease-out",
                },
            },
            # Cell nodes
            {
                "selector": f"node[type='{NodeType.CELL.value}'], .cell-node",
                "style": {
                    "shape": "octagon",
                    "width": "180px",
                    "height": "180px",
                    "background-color": "#9b59b6",
                    "border-width": "3px",
                    "border-color": "#7d3c98",
                    "label": "data(label)",
                    "text-valign": "center",
                    "text-halign": "center",
                    "font-size": "38px",
                    "font-weight": "bold",
                    "color": "#ffffff",
                    "text-outline-color": "#7d3c98",
                    "text-outline-width": 1,
                    "text-wrap": "wrap",
                    "text-max-width": "160px",
                    "padding": "6px",
                    "opacity": 15,
                    "transition-property": "width, height, font-size, text-max-width, border-width, padding",
                    "transition-duration": "0.3s",
                    "transition-timing-function": "ease-out",
                },
            },
            # Quality nodes
            {
                "selector": f"node[type='{NodeType.QUALITY.value}'], .quality-node",
                "style": {
                    "shape": "diamond",
                    "width": "160px",
                    "height": "160px",
                    "background-color": "#f39c12",
                    "border-width": "2px",
                    "border-color": "#e67e22",
                    "label": "data(label)",
                    "text-valign": "center",
                    "text-halign": "center",
                    "font-size": "35px",
                    "font-weight": "bold",
                    "color": "#ffffff",
                    "text-outline-color": "#e67e22",
                    "text-outline-width": 1,
                    "text-wrap": "wrap",
                    "text-max-width": "140px",
                    "padding": "4px",
                    "opacity": 1,
                    "transition-property": "width, height, font-size, text-max-width, border-width, padding",
                    "transition-duration": "0.3s",
                    "transition-timing-function": "ease-out",
                },
            },
            # Selected nodes
            {
                "selector": "node:selected",
                "style": {
                    "border-width": "14px",
                    "border-color": "#1976d2",
                    "z-index": 9999,
                },
            },
            # Associated with edges
            {
                "selector": f"edge[type='{EdgeType.ASSOCIATED_WITH.value}'], edge[type='{EdgeType.EXPRESSION_IN.value}']",
                "style": {
                    "curve-style": "straight",
                    "width": "20px",
                    "line-color": "#b19cd9",
                    "opacity": 1,
                    "target-arrow-shape": "triangle",
                    "target-arrow-color": "#b19cd9",
                    "arrow-scale": 1.2,
                    # "line-style": "dashed",
                    # "line-dash-pattern": [6, 3],
                    "source-endpoint": "outside-to-node",
                    "target-endpoint": "outside-to-node",
                    "transition-property": "width",
                    "transition-duration": "0.3s",
                    "transition-timing-function": "ease-out",
                },
            },
            # Selected associated edges
            {
                "selector": f"edge[type='{EdgeType.ASSOCIATED_WITH.value}']:selected, edge[type='{EdgeType.EXPRESSION_IN.value}']:selected",
                "style": {
                    "line-color": "#8e7cc3",
                    "target-arrow-color": "#8e7cc3",
                    "width": "3px",
                    "opacity": 1,
                },
            },
        ]

    def get_styles(self) -> List[Dict[str, Any]]:
        """Get base styles"""
        return self.base_styles

    def get_layout_config(self) -> Dict[str, Any]:
        """Get default layout configuration"""
        return {
            "name": "breadthfirst",
            "directed": True,
            "padding": 30
        }


# Global style manager instance
default_style_manager = AOPStyleManager()


def get_default_styles() -> List[Dict[str, Any]]:
    """Get default AOP styles"""
    return default_style_manager.get_styles()


def get_layout_config() -> Dict[str, Any]:
    """Get default layout configuration"""
    return default_style_manager.get_layout_config()
