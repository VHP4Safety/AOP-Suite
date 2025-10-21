// Global variables to store base styles from backend
let baseStyles = [];
let layoutConfig = {};

// Function to apply font size multiplier to styles (like the original implementation)
function applyFontSizeToStyles(styles, fontSizeMultiplier) {
    return styles.map(styleRule => {
        const newStyleRule = JSON.parse(JSON.stringify(styleRule)); // Deep copy
        
        if (newStyleRule.style && typeof newStyleRule.style === 'object') {
            // Apply font size multiplier to all size-related properties
            Object.keys(newStyleRule.style).forEach(property => {
                const value = newStyleRule.style[property];
                if (typeof value === 'string') {
                    // Handle pixel values
                    if (value.includes('px')) {
                        const numericValue = parseFloat(value);
                        if (!isNaN(numericValue)) {
                            newStyleRule.style[property] = `${numericValue * fontSizeMultiplier}px`;
                        }
                    }
                    // Handle numeric pixel values without 'px'
                    else if (/^\d+(\.\d+)?$/.test(value)) {
                        const numericValue = parseFloat(value);
                        newStyleRule.style[property] = `${numericValue * fontSizeMultiplier}px`;
                    }
                }
                // Handle numeric values
                else if (typeof value === 'number') {
                    newStyleRule.style[property] = value * fontSizeMultiplier;
                }
            });
        }
        
        return newStyleRule;
    });
}

// Function to initialize styles from backend
function initializeStylesFromBackend(networkData) {
    if (networkData && networkData.style) {
        baseStyles = networkData.style;
        layoutConfig = networkData.layout || {"name": "breadthfirst", "directed": true, "padding": 30};
        console.log('Base styles loaded from backend:', baseStyles.length, 'style rules');
    } else {
        console.warn('No styles received from backend');
    }
}

// Enhanced positionNodes function with font size multiplier (restoring original behavior)
function positionNodes(cy, fontSizeMultiplier = 0.5, animate = false) {
    if (!cy || !cy.elements) {
        console.warn("Invalid Cytoscape instance passed to positionNodes");
        return;
    }

    if (!baseStyles || baseStyles.length === 0) {
        console.warn("No base styles available. Make sure to initialize styles from backend first.");
        return;
    }

    // Apply font size multiplier to base styles
    const scaledStyles = applyFontSizeToStyles(baseStyles, fontSizeMultiplier);
    
    // Set transition duration based on animate parameter
    const transitionDuration = animate ? "0.3s" : "0s";
    scaledStyles.forEach(styleRule => {
        if (styleRule.style && typeof styleRule.style === 'object') {
            styleRule.style["transition-duration"] = transitionDuration;
        }
    });

    // Apply the scaled styles
    cy.style(scaledStyles).update();

    // Run layout only if not animating (for reset layout, we handle animation separately)
    if (!animate && layoutConfig) {
        cy.layout(layoutConfig).run();
    }
}

// Function to reset layout with animation
function resetLayout(cy, animate = true) {
    if (!cy || !layoutConfig) {
        console.warn("Cannot reset layout: missing Cytoscape instance or layout config");
        return;
    }
    
    if (animate) {
        // Get current font size for consistent styling during animation
        const fontSlider = document.getElementById('font-size-slider');
        const fontSizeMultiplier = fontSlider ? parseFloat(fontSlider.value) : 0.5;
        
        // Apply current styles with animation
        positionNodes(cy, fontSizeMultiplier, true);
        
        // Run layout after a brief delay to allow style transitions
        setTimeout(() => {
            cy.layout(layoutConfig).run();
        }, 50);
    } else {
        cy.layout(layoutConfig).run();
    }
}

// Enhanced font slider event listener with smooth transitions (original behavior)
document.addEventListener('DOMContentLoaded', function() {
    const fontSlider = document.getElementById('font-size-slider');
    if (fontSlider) {
        fontSlider.addEventListener('input', function() {
            const fontSizeMultiplier = parseFloat(this.value);
            console.log('Font size:', fontSizeMultiplier);
            if (window.cy && baseStyles.length > 0) {
                // Use smooth transitions for font size changes
                positionNodes(window.cy, fontSizeMultiplier, true);
            }
        });
    }
});

// Add window resize handler with safety checks
window.addEventListener("resize", function() { 
    if (window.cy && baseStyles.length > 0) {
        // Get the current font size from slider to maintain consistency
        const fontSlider = document.getElementById('font-size-slider');
        const fontSizeMultiplier = fontSlider ? parseFloat(fontSlider.value) : 0.5;
        positionNodes(window.cy, fontSizeMultiplier, false);
    }
});

// Function to initialize network with styles from backend (main entry point)
function initializeNetworkWithStyles(cy, networkData) {
    if (!cy || !networkData) {
        console.warn("Cannot initialize network: missing Cytoscape instance or network data");
        return;
    }
    
    // Initialize base styles from backend data
    initializeStylesFromBackend(networkData);
    
    // Apply initial styles with current font size
    if (baseStyles.length > 0) {
        const fontSlider = document.getElementById('font-size-slider');
        const fontSizeMultiplier = fontSlider ? parseFloat(fontSlider.value) : 0.5;
        positionNodes(cy, fontSizeMultiplier, false);
    }
}

// Make functions available globally
window.positionNodes = positionNodes;
window.resetLayout = resetLayout;
window.initializeNetworkWithStyles = initializeNetworkWithStyles;
window.initializeStylesFromBackend = initializeStylesFromBackend;