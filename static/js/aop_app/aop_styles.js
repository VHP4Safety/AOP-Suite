function positionNodes(cy, fontSizeMultiplier = 1) {
    if (!cy || !cy.elements) {
        console.warn("Invalid Cytoscape instance passed to positionNodes");
        return;
    }

    cy.layout({
        //animate: true,
        name: 'breadthfirst',
        directed: true,
        padding: 30,
        //rankDir: "RL"
    }).run();
    cy.style([
        {
            selector: "node",
            style: {
                "width": `${270 * fontSizeMultiplier}px`,
                "height": `${200 * fontSizeMultiplier}px`,
                "background-color": ele =>
                    ele.data("is_mie") ? "#ccffcc" :
                        ele.data("is_ao") ? "#ffe6e6" :
                            ele.data("is_uniprot") ? "#ffff99" :
                                ele.data("is_ensembl") ? "#ffcc99" : "#ffff99",
                "label": "data(label)",
                "text-wrap": "wrap",
                "text-max-width": `${235 * fontSizeMultiplier}px`,
                "text-valign": "center",
                "text-halign": "center",
                "color": "#000",
                "font-size": `${40 * fontSizeMultiplier}px`,
                "border-width": "2px",
                "border-color": "#000"
            }
        },
        {
            selector: ".chemical-node",
            style: {
                "width": `${270 * fontSizeMultiplier}px`,
                "height": `${200 * fontSizeMultiplier}px`,
                "shape": "triangle",
                "background-color": "#93d5f6",
                "label": "data(label)",
                "text-wrap": "wrap",
                "text-max-width": `${190 * fontSizeMultiplier}px`,
                "text-valign": "top",
                "text-halign": "center",
                "color": "#000",
                "font-size": `${90 * fontSizeMultiplier}px`,
                "border-width": 2,
                "border-color": "#000",
                "text-margin-y": 3,
            }
        },
        {
            selector: "edge[ker_label]",
            style: {
                "curve-style": "unbundled-bezier",
                "width": `${40 * fontSizeMultiplier}px`,
                "line-color": "#93d5f6",
                "opacity": 0.8,
                "target-arrow-shape": "triangle",
                "target-arrow-color": "#93d5f6",
                "label": "data(ker_label)",
                "text-margin-y": 1,
                "text-rotation": "autorotate",
                "font-size": `${40 * fontSizeMultiplier}px`,
                "font-weight": "bold",
                "color": "#000"
            }
        },
        {
            selector: ".uniprot-node",
            style: {
                "shape": "rectangle",
                "opacity": 0.6,
                "label": "data(label)",
                "background-color": "#f2f2f2",
                "text-valign": "center",
                "text-halign": "center",
                "color": "#000000",
                "font-size": `${45 * fontSizeMultiplier}px`,
                "font-weight": "bold",
                "border-width": 0,
            }
        },
        {
            selector: ".ensembl-node",
            style: {
                "shape": "ellipse",
                "background-opacity": 0,
                "label": "data(label)",
                "text-valign": "center",
                "text-halign": "center",
                "color": "#000000",
                "font-size": `${45 * fontSizeMultiplier}px`,
                "font-weight": "bold",
                "border-width": 0,
                "border-color": "transparent"
            }
        },
        {
            selector: "edge[label]",
            style: {
                "label": "data(label)",
                "text-rotation": "autorotate",
                "text-margin-y": -15,
                "font-size": `${40 * fontSizeMultiplier}px`,
                "curve-style": "unbundled-bezier",

            }
        },
        {
            selector: "edge[type='interaction']",
            style: {
                "width": `${40 * fontSizeMultiplier}px`,
                "line-color": "#ceafc0",
                "opacity": 0.5,
                "target-arrow-shape": "triangle",
                "target-arrow-color": "#ceafc0",
                "text-margin-y": 1,
                "text-rotation": "autorotate",
                "font-size": `${40 * fontSizeMultiplier}px`,
                "font-weight": "bold",
                "color": "#000"
            }
        },
        {
            selector: "edge[label='part of']",
            style: {
                "width": `${40 * fontSizeMultiplier}px`,
                "line-color": "#ccffcc",
                "opacity": 0.5,
                "target-arrow-shape": "triangle",
                "target-arrow-color": "#ccffcc",
                "text-margin-y": 1,
                "text-rotation": "autorotate",
                "font-size": `${40 * fontSizeMultiplier}px`,
                "font-weight": "bold",
                "color": "#000"
            }
        },
        {
            // Bounding boxes (aop nodes) should auto-size based on their children.
            selector: ".bounding-box",
            style: {
                "shape": "roundrectangle",
                "background-opacity": 0.1,
                "border-width": 2,
                "border-color": "#000",
                "label": "data(label)",
                "text-valign": "top",
                "text-halign": "center",
                "font-size": `${50 * fontSizeMultiplier}px`,
                "text-wrap": "wrap",
                "font-weight": "bold",
                "text-max-width": `${1400 * fontSizeMultiplier}px`
            }
        }
    ]).update();
}

// Add event listener for font size slider with safety checks
document.addEventListener('DOMContentLoaded', function() {
    const fontSlider = document.getElementById('font-size-slider');
    if (fontSlider) {
        fontSlider.addEventListener('input', function() {
            const fontSizeMultiplier = parseFloat(this.value);
            console.log('Font size:', fontSizeMultiplier);
            if (window.cy) {
                positionNodes(window.cy, fontSizeMultiplier);
            }
        });
    }
});

// Add window resize handler with safety checks
window.addEventListener("resize", function() { 
    if (window.cy) {
        positionNodes(window.cy);
    }
});

// Make positionNodes available globally
window.positionNodes = positionNodes;