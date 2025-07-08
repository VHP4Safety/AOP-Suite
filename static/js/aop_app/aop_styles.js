function positionNodes(cy, fontSizeMultiplier = 0.5, animate = false) { // Changed default from 1 to 0.5
    if (!cy || !cy.elements) {
        console.warn("Invalid Cytoscape instance passed to positionNodes");
        return;
    }

    // Only run layout if animate is false (for reset layout, we handle animation separately)
    if (!animate) {
        cy.layout({
            name: 'breadthfirst',
            directed: true,
            padding: 30,
        }).run();
    }
    
    // Apply styles with optional animation
    const transitionDuration = animate ? "0.3s" : "0s";
    
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
                "border-color": "#000",
                "transition-property": "width, height, font-size, text-max-width",
                "transition-duration": transitionDuration,
                "transition-timing-function": "ease-out"
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
                "transition-property": "width, height, font-size, text-max-width",
                "transition-duration": transitionDuration,
                "transition-timing-function": "ease-out"
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
                "color": "#000",
                "transition-property": "width, font-size",
                "transition-duration": transitionDuration,
                "transition-timing-function": "ease-out"
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
                "transition-property": "font-size",
                "transition-duration": transitionDuration,
                "transition-timing-function": "ease-out"
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
                "border-color": "transparent",
                "transition-property": "font-size",
                "transition-duration": transitionDuration,
                "transition-timing-function": "ease-out"
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
                "transition-property": "font-size",
                "transition-duration": transitionDuration,
                "transition-timing-function": "ease-out"
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
                "color": "#000",
                "transition-property": "width, font-size",
                "transition-duration": transitionDuration,
                "transition-timing-function": "ease-out"
            }
        },
        {
            selector: ".qspr-prediction-edge",
            style: {
                "width": `${35 * fontSizeMultiplier}px`,
                "line-color": "#ff6b6b",
                "opacity": 0.7,
                "target-arrow-shape": "triangle",
                "target-arrow-color": "#ff6b6b",
                "text-margin-y": 1,
                "text-rotation": "autorotate",
                "font-size": `${35 * fontSizeMultiplier}px`,
                "font-weight": "bold",
                "color": "#000",
                "line-style": "dashed",
                "transition-property": "width, font-size",
                "transition-duration": transitionDuration,
                "transition-timing-function": "ease-out"
            }
        },
        {
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
                "text-max-width": `${1400 * fontSizeMultiplier}px`,
                "transition-property": "font-size, text-max-width",
                "transition-duration": transitionDuration,
                "transition-timing-function": "ease-out"
            }
        }
    ]).update();
}

// Enhanced font slider event listener with smooth transitions
document.addEventListener('DOMContentLoaded', function() {
    const fontSlider = document.getElementById('font-size-slider');
    if (fontSlider) {
        fontSlider.addEventListener('input', function() {
            const fontSizeMultiplier = parseFloat(this.value);
            console.log('Font size:', fontSizeMultiplier);
            if (window.cy) {
                // Use smooth transitions for font size changes
                positionNodes(window.cy, fontSizeMultiplier, true);
            }
        });
    }
});

// Add window resize handler with safety checks
window.addEventListener("resize", function() { 
    if (window.cy) {
        // Get the current font size from slider to maintain consistency
        const fontSlider = document.getElementById('font-size-slider');
        const fontSizeMultiplier = fontSlider ? parseFloat(fontSlider.value) : 0.5;
        positionNodes(window.cy, fontSizeMultiplier);
    }
});

// Make positionNodes available globally
window.positionNodes = positionNodes;