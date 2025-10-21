from typing import Dict, Any, List, Optional
import logging

logger = logging.getLogger(__name__)


class AOPStyleManager:
    """Manages base Cytoscape styles for AOP networks"""
    
    def __init__(self):
        self.base_styles = self._create_base_styles()
    
    def _create_base_styles(self) -> List[Dict[str, Any]]:
        """Create the base Cytoscape styles (without font size multipliers)"""
        return [
            # Default node styles
            {
                "selector": "node",
                "style": {
                    "width": "350px",
                    "height": "350px",
                    "background-color": "#ffff99",  # Default yellow
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
                    "transition-timing-function": "ease-out"
                }
            },
            
            # MIE nodes - use type selector
            {
                "selector": "node[type='mie']",
                "style": {
                    "background-color": "#ccffcc"
                }
            },
            
            # AO nodes - use type selector  
            {
                "selector": "node[type='ao']",
                "style": {
                    "background-color": "#ffe6e6"
                }
            },
            
            # UniProt nodes - use type selector
            {
                "selector": "node[type='uniprot']",
                "style": {
                    "background-color": "#ffff99"
                }
            },
            
            # Ensembl nodes - use type selector
            {
                "selector": "node[type='ensembl']", 
                "style": {
                    "background-color": "#ffcc99"
                }
            },
            
            # Chemical nodes
            {
                "selector": ".chemical-node",
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
                    "transition-timing-function": "ease-out"
                }
            },
            
            # KER edges
            {
                "selector": "edge[ker_label]",
                "style": {
                    "curve-style": "unbundled-bezier",
                    "width": "40px",
                    "line-color": "#93d5f6",
                    "opacity": 0.8,
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
                    "transition-timing-function": "ease-out"
                }
            },
            
            # UniProt nodes
            {
                "selector": ".uniprot-node",
                "style": {
                    "shape": "rectangle",
                    "opacity": 0.6,
                    "label": "data(label)",
                    "background-color": "#f2f2f2",
                    "text-valign": "center",
                    "text-halign": "center",
                    "color": "#000000",
                    "font-size": "45px",
                    "font-weight": "bold",
                    "border-width": 0,
                    "transition-property": "font-size",
                    "transition-duration": "0.3s",
                    "transition-timing-function": "ease-out"
                }
            },
            
            # Ensembl nodes
            {
                "selector": ".ensembl-node",
                "style": {
                    "shape": "ellipse",
                    "background-opacity": 0,
                    "label": "data(label)",
                    "text-valign": "center",
                    "text-halign": "center",
                    "color": "#000000",
                    "font-size": "45px",
                    "font-weight": "bold",
                    "border-width": 0,
                    "border-color": "transparent",
                    "transition-property": "font-size",
                    "transition-duration": "0.3s",
                    "transition-timing-function": "ease-out"
                }
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
                    "transition-timing-function": "ease-out"
                }
            },
            
            # Interaction edges
            {
                "selector": "edge[type='interaction']",
                "style": {
                    "width": "40px",
                    "line-color": "#ceafc0",
                    "opacity": 0.5,
                    "target-arrow-shape": "triangle",
                    "target-arrow-color": "#ceafc0",
                    "text-margin-y": 1,
                    "text-rotation": "autorotate",
                    "font-size": "40px",
                    "font-weight": "bold",
                    "color": "#000",
                    "transition-property": "width, font-size",
                    "transition-duration": "0.3s",
                    "transition-timing-function": "ease-out"
                }
            },
            
            # QSPR prediction edges
            {
                "selector": ".qspr-prediction-edge",
                "style": {
                    "width": "35px",
                    "line-color": "#ff6b6b",
                    "opacity": 0.7,
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
                    "transition-timing-function": "ease-out"
                }
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
                    "transition-timing-function": "ease-out"
                }
            },
            
            # Process nodes
            {
                "selector": ".process-node",
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
                    "transition-timing-function": "ease-out"
                }
            },
            
            # Object nodes
            {
                "selector": ".object-node",
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
                    "transition-timing-function": "ease-out"
                }
            },
            
            # Has process edges
            {
                "selector": "edge[type='has process']",
                "style": {
                    "curve-style": "bezier",
                    "width": "4px",
                    "line-color": "#4caf50",
                    "opacity": 0.7,
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
                    "transition-timing-function": "ease-out"
                }
            },
            
            # Has object edges
            {
                "selector": "edge[type='has object']",
                "style": {
                    "curve-style": "bezier",
                    "width": "3px",
                    "line-color": "#9c27b0",
                    "opacity": 0.8,
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
                    "transition-timing-function": "ease-out"
                }
            },
            
            # Component action edges
            {
                "selector": "edge[label='increased process quality'], edge[label='decreased process quality'], edge[label='delayed'], edge[label='occurrence'], edge[label='abnormal'], edge[label='premature'], edge[label='disrupted'], edge[label='functional change'], edge[label='morphological change'], edge[label='pathological'], edge[label='arrested']",
                "style": {
                    "curve-style": "bezier",
                    "width": "5px",
                    "line-color": "#4caf50",
                    "opacity": 0.6,
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
                    "text-background-opacity": 0.8,
                    "text-background-padding": "2px",
                    "transition-property": "width, font-size, text-margin-y, text-background-padding",
                    "transition-duration": "0.3s",
                    "transition-timing-function": "ease-out"
                }
            },
            
            # Organ nodes
            {
                "selector": "node[type='organ'], .organ-node",
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
                    "opacity": 0.9,
                    "transition-property": "width, height, font-size, text-max-width, border-width, padding",
                    "transition-duration": "0.3s",
                    "transition-timing-function": "ease-out"
                }
            },
            
            # Selected nodes
            {
                "selector": "node:selected",
                "style": {
                    "border-width": "14px",
                    "border-color": "#1976d2",
                    "z-index": 9999
                }
            },
            
            # Associated with edges
            {
                "selector": "edge[type='associated_with'], edge[type='expression_in']",
                "style": {
                    "curve-style": "straight",
                    "width": "2px",
                    "line-color": "#b19cd9",
                    "opacity": 0.7,
                    "target-arrow-shape": "triangle",
                    "target-arrow-color": "#b19cd9",
                    "arrow-scale": 1.2,
                    "line-style": "dashed",
                    "line-dash-pattern": [6, 3],
                    "source-endpoint": "outside-to-node",
                    "target-endpoint": "outside-to-node",
                    "transition-property": "width",
                    "transition-duration": "0.3s",
                    "transition-timing-function": "ease-out"
                }
            },
            
            # Selected associated edges
            {
                "selector": "edge[type='associated_with']:selected, edge[type='expression_in']:selected",
                "style": {
                    "line-color": "#8e7cc3",
                    "target-arrow-color": "#8e7cc3",
                    "width": "3px",
                    "opacity": 1
                }
            }
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