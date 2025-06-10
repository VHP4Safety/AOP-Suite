// Manual node and edge controls

class ManualControls {
    constructor() {
        this.setupEventHandlers();
        this.setupCollapsibleSections();
        this.setupSearchableDropdowns();
    }

    setupCollapsibleSections() {
        // Initialize collapsible sections
        document.querySelectorAll('.collapsible-header').forEach(header => {
            header.addEventListener('click', (e) => {
                this.toggleSection(header);
            });
        });

        // Start with all sections collapsed
        document.querySelectorAll('.collapsible-content').forEach(content => {
            content.classList.add('collapsed');
            content.style.maxHeight = '0px';
        });
        
        document.querySelectorAll('.collapsible-header').forEach(header => {
            header.classList.add('collapsed');
        });
    }

    toggleSection(header) {
        const targetId = header.getAttribute('data-target');
        const content = document.getElementById(targetId);
        const icon = header.querySelector('.collapse-icon');

        if (content.classList.contains('collapsed')) {
            // Expand section
            content.classList.remove('collapsed');
            header.classList.remove('collapsed');
            content.style.maxHeight = content.scrollHeight + 'px';
            
            // Reset max-height after animation completes
            setTimeout(() => {
                if (!content.classList.contains('collapsed')) {
                    content.style.maxHeight = 'none';
                }
            }, 300);
        } else {
            // Collapse section
            content.style.maxHeight = content.scrollHeight + 'px';
            // Force reflow
            content.offsetHeight;
            content.classList.add('collapsed');
            header.classList.add('collapsed');
            content.style.maxHeight = '0px';
        }
    }

    setupEventHandlers() {
        // Add node button
        const addNodeBtn = document.getElementById('add-node');
        if (addNodeBtn) {
            addNodeBtn.addEventListener('click', () => {
                this.addNode();
            });
        }

        // Add connection button
        const addConnectionBtn = document.getElementById('add-connection');
        if (addConnectionBtn) {
            addConnectionBtn.addEventListener('click', () => {
                this.addConnection();
            });
        }

        // Update node dropdowns when network changes
        if (window.cy) {
            window.cy.on('add remove', 'node', () => {
                this.updateNodeDropdowns();
            });
        }
    }

    setupSearchableDropdowns() {
        // Source node search
        $("#source-node-search").on("input", (e) => {
            this.filterDropdown("source-node", e.target.value);
        });

        // Target node search
        $("#target-node-search").on("input", (e) => {
            this.filterDropdown("target-node", e.target.value);
        });

        // Clear search when dropdown gets focus
        $("#source-node, #target-node").on("focus", function() {
            const searchInput = $(this).siblings(".dropdown-search");
            if (searchInput.length) {
                searchInput.val("");
                $(this).find("option").removeClass("hidden").show();
            }
        });
    }

    filterDropdown(selectId, searchTerm) {
        const select = $(`#${selectId}`);
        const options = select.find("option");
        
        searchTerm = searchTerm.toLowerCase();
        
        options.each(function() {
            const option = $(this);
            const text = option.text().toLowerCase();
            const value = option.val().toLowerCase();
            
            if (searchTerm === "" || text.includes(searchTerm) || value.includes(searchTerm)) {
                option.removeClass("hidden").show();
            } else {
                option.addClass("hidden").hide();
            }
        });
        
        // Reset selection if current selection is hidden
        const currentOption = select.find("option:selected");
        if (currentOption.hasClass("hidden")) {
            select.val("");
        }
    }

    populateNodeDropdowns() {
        if (!window.cy) {
            console.log("Cytoscape not available - clearing dropdowns");
            const sourceSelect = $("#source-node");
            const targetSelect = $("#target-node");
            
            sourceSelect.find("option:not(:first)").remove();
            targetSelect.find("option:not(:first)").remove();
            return;
        }

        const sourceSelect = $("#source-node");
        const targetSelect = $("#target-node");
        
        // Clear existing options except the first one
        sourceSelect.find("option:not(:first)").remove();
        targetSelect.find("option:not(:first)").remove();
        
        // Get all nodes from the network
        const nodes = window.cy.nodes().map(node => ({
            id: node.id(),
            label: node.data("label") || node.id(),
            type: node.data("type") || "unknown"
        }));
        
        if (nodes.length === 0) {
            console.log("No nodes in network - dropdowns will remain empty");
            return;
        }
        
        // Sort nodes by label for better UX
        nodes.sort((a, b) => a.label.localeCompare(b.label));
        
        // Add nodes to dropdowns
        nodes.forEach(node => {
            const optionText = `${node.label} (${node.type})`;
            const option = `<option value="${node.id}">${optionText}</option>`;
            sourceSelect.append(option);
            targetSelect.append(option);
        });
        
        console.log(`Updated node dropdowns with ${nodes.length} nodes`);
    }

    // Add a new node to the network
    addNode() {
        const nodeType = $("#node-type").val();
        const nodeLabel = $("#node-label").val().trim();
        const nodeId = $("#node-id").val().trim();

        if (!nodeLabel) {
            alert("Please enter a node label");
            return;
        }

        if (!window.cy) {
            alert("Network not initialized");
            return;
        }

        // Generate ID if not provided
        const finalId = nodeId || `${nodeType}_${Date.now()}`;

        // Check if node already exists
        if (window.cy.getElementById(finalId).length > 0) {
            alert(`Node with ID "${finalId}" already exists`);
            return;
        }

        try {
            // Create node data
            const nodeData = {
                data: {
                    id: finalId,
                    label: nodeLabel,
                    type: nodeType
                },
                classes: `${nodeType}-node`
            };

            // Add to network
            window.cy.add(nodeData);

            // Hide loading overlay if this is the first element
            const loadingOverlay = document.querySelector(".loading-overlay");
            if (loadingOverlay && window.cy.elements().length > 0) {
                loadingOverlay.style.display = "none";
            }

            // Reposition nodes
            if (window.positionNodes) {
                window.positionNodes(window.cy);
            }

            // Clear form
            $("#node-label").val("");
            $("#node-id").val("");

            console.log(`Added node: ${finalId}`);

        } catch (error) {
            console.error("Error adding node:", error);
            alert("Error adding node: " + error.message);
        }
    }

    // Add a new connection between nodes
    addConnection() {
        const sourceId = document.getElementById('source-node').value;
        const targetId = document.getElementById('target-node').value;
        const edgeType = document.getElementById('edge-type').value;
        const edgeLabel = document.getElementById('edge-label').value.trim();

        if (!sourceId || !targetId) {
            alert('Please select both source and target nodes');
            return;
        }

        if (sourceId === targetId) {
            alert('Source and target cannot be the same node');
            return;
        }

        if (!window.cy) {
            alert('Network not initialized');
            return;
        }

        // Generate edge ID
        const edgeId = `${sourceId}_${targetId}_${Date.now()}`;

        // Check if edge already exists
        const existingEdge = window.cy.edges().filter(edge => {
            return edge.source().id() === sourceId && edge.target().id() === targetId;
        });

        if (existingEdge.length > 0) {
            if (!confirm('An edge already exists between these nodes. Add another?')) {
                return;
            }
        }

        try {
            // Create edge data
            const edgeData = {
                data: {
                    id: edgeId,
                    source: sourceId,
                    target: targetId,
                    type: edgeType,
                    label: edgeLabel || edgeType
                }
            };

            // Add to network
            window.cy.add(edgeData);

            // Reposition nodes
            if (window.positionNodes) {
                window.positionNodes(window.cy);
            }

            // Clear form
            document.getElementById('source-node').value = '';
            document.getElementById('target-node').value = '';
            document.getElementById('edge-label').value = '';
            
            // Clear search boxes
            $("#source-node-search").val("");
            $("#target-node-search").val("");

            console.log(`Added edge: ${edgeId}`);

        } catch (error) {
            console.error('Error adding edge:', error);
            alert('Error adding edge: ' + error.message);
        }
    }

    // Update node dropdowns with current nodes
    updateNodeDropdowns() {
        if (!window.cy) return;

        const sourceSelect = $("#source-node");
        const targetSelect = $("#target-node");
        
        // Clear existing options except the first one
        sourceSelect.find("option:not(:first)").remove();
        targetSelect.find("option:not(:first)").remove();
        
        // Get all nodes from the network
        const nodes = window.cy.nodes().map(node => ({
            id: node.id(),
            label: node.data("label") || node.id(),
            type: node.data("type") || "unknown"
        }));
        
        // Sort nodes by label for better UX
        nodes.sort((a, b) => a.label.localeCompare(b.label));
        
        // Add nodes to dropdowns
        nodes.forEach(node => {
            const optionText = `${node.label} (${node.type})`;
            const option = `<option value="${node.id}">${optionText}</option>`;
            sourceSelect.append(option);
            targetSelect.append(option);
        });
        
        console.log(`Updated node dropdowns with ${nodes.length} nodes`);
    }

    // Generate unique node ID
    generateNodeId(nodeType, nodeLabel) {
        const timestamp = Date.now();
        const cleanLabel = nodeLabel.replace(/[^a-zA-Z0-9]/g, '_').toLowerCase();
        return `${nodeType}_${cleanLabel}_${timestamp}`;
    }

    // Get default edge label based on type
    getDefaultEdgeLabel(edgeType) {
        const labels = {
            'ker': 'Key Event Relationship',
            'interaction': 'Interacts with',
            'part_of': 'Part of',
            'translates_to': 'Translates to'
        };
        return labels[edgeType] || 'Connection';
    }
}

// Initialize manual controls
let manualControls;

function initializeManualControls() {
    if (!manualControls) {
        manualControls = new ManualControls();
        
        // Initial population of dropdowns
        setTimeout(() => {
            if (manualControls) {
                manualControls.updateNodeDropdowns();
            }
        }, 1000);
    }
    
    // Also initialize AOP network data manager
    if (window.initializeAOPNetworkData) {
        window.initializeAOPNetworkData();
    }
}

// Make available globally
window.initializeManualControls = initializeManualControls;
window.manualControls = manualControls;

// Initialize when DOM is ready
document.addEventListener('DOMContentLoaded', () => {
    // Don't initialize immediately - let aop_elements.js handle it
    console.log('Manual controls module loaded');
});
