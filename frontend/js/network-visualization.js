// Cytoscape styles
const cytoscapeStyles = [
    // ...existing styles...
    
    // Organ nodes
    {
        selector: '.organ-node',
        style: {
            'background-color': '#8FBC8F',
            'border-color': '#556B2F',
            'border-width': 2,
            'label': 'data(label)',
            'text-valign': 'center',
            'text-halign': 'center',
            'font-size': '10px',
            'font-weight': 'bold',
            'color': '#2F4F2F',
            'text-wrap': 'wrap',
            'text-max-width': '80px',
            'width': '40px',
            'height': '40px',
            'shape': 'hexagon',
            'display': 'none' // Hidden by default
        }
    },

    // Organ edges
    {
        selector: 'edge[type="associated_with"], edge[edge_type="ke_organ_association"]',
        style: {
            'line-color': '#8FBC8F',
            'target-arrow-color': '#8FBC8F',
            'target-arrow-shape': 'triangle',
            'curve-style': 'bezier',
            'width': 2,
            'opacity': 0.7,
            'display': 'none' // Hidden by default
        }
    },

    // Expression edges
    {
        selector: 'edge[type="expression_in"]',
        style: {
            'line-color': '#DDA0DD',
            'target-arrow-color': '#DDA0DD',
            'target-arrow-shape': 'triangle',
            'curve-style': 'bezier',
            'width': 2,
            'line-style': 'dashed',
            'opacity': 0.6,
            'display': 'none' // Hidden by default
        }
    },

    // ...existing styles...
];

// Add organ toggle controls after existing toggle controls
function addOrganToggleControls() {
    const controlsContainer = document.querySelector('.network-controls') || document.body;
    
    const organToggleContainer = document.createElement('div');
    organToggleContainer.className = 'toggle-container';
    organToggleContainer.innerHTML = `
        <label class="toggle-label">
            <input type="checkbox" id="organ-toggle" class="toggle-checkbox">
            <span class="toggle-text">Show Organs</span>
            <span class="toggle-count" id="organ-count">(0)</span>
        </label>
    `;
    
    controlsContainer.appendChild(organToggleContainer);
    
    // Add event listener
    document.getElementById('organ-toggle').addEventListener('change', toggleOrganVisibility);
}

function toggleOrganVisibility() {
    const checkbox = document.getElementById('organ-toggle');
    const isVisible = checkbox.checked;
    
    if (!window.cy) return;
    
    // Toggle organ nodes
    const organNodes = window.cy.nodes('.organ-node');
    const organEdges = window.cy.edges('[type="associated_with"], [edge_type="ke_organ_association"], [type="expression_in"]');
    
    if (isVisible) {
        organNodes.style('display', 'element');
        organEdges.style('display', 'element');
    } else {
        organNodes.style('display', 'none');
        organEdges.style('display', 'none');
    }
    
    // Re-run layout if needed
    if (isVisible && organNodes.length > 0) {
        runLayout();
    }
}

function updateOrganCount() {
    const organCountElement = document.getElementById('organ-count');
    if (organCountElement && window.cy) {
        const organCount = window.cy.nodes('.organ-node').length;
        organCountElement.textContent = `(${organCount})`;
    }
}

// Update the main initialization function
function initializeNetworkVisualization(elements, summary) {
    // ...existing initialization code...
    
    // Add organ toggle controls
    addOrganToggleControls();
    
    // Update counts including organs
    updateOrganCount();
    
    // ...rest of existing code...
}