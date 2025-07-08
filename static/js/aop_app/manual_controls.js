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
        const nodeLabels = $("#node-label").val().trim();
        const nodeIds = $("#node-id").val().trim();

        if (!nodeLabels) {
            alert("Please enter node label(s)");
            return;
        }

        if (!window.cy) {
            alert("Network not initialized");
            return;
        }

        // Parse multiple labels (space or comma separated)
        const labels = this.parseMultipleValues(nodeLabels);
        const ids = nodeIds ? this.parseMultipleValues(nodeIds) : [];
        
        console.log(`Adding ${labels.length} nodes of type: ${nodeType}`);
        
        let addedCount = 0;
        let skippedCount = 0;
        const nodesToAdd = [];
        
        labels.forEach((label, index) => {
            if (!label) return;
            
            // Generate ID if not provided or use corresponding ID from list
            const finalId = ids[index] || `${nodeType}_${label.replace(/\s+/g, '_')}_${Date.now()}_${index}`;

            // Check if node already exists
            if (window.cy.getElementById(finalId).length > 0) {
                console.warn(`Node with ID "${finalId}" already exists - skipping`);
                skippedCount++;
                return;
            }

            try {
                // Create node data
                const nodeData = {
                    data: {
                        id: finalId,
                        label: label,
                        type: nodeType
                    },
                    classes: `${nodeType}-node`
                };

                nodesToAdd.push(nodeData);
                addedCount++;
                
                console.log(`Prepared node: ${finalId} (type: ${nodeType})`);

            } catch (error) {
                console.error(`Error preparing node ${label}:`, error);
                skippedCount++;
            }
        });

        // Add all nodes in a batch for smooth animation
        if (nodesToAdd.length > 0) {
            window.cy.batch(() => {
                window.cy.add(nodesToAdd);
            });
            
            // Hide loading overlay if this is the first element
            const loadingOverlay = document.querySelector(".loading-overlay");
            if (loadingOverlay && window.cy.elements().length > 0) {
                loadingOverlay.style.display = "none";
            }

            // Reposition nodes with smooth animation
            if (window.positionNodes) {
                const fontSlider = document.getElementById('font-size-slider');
                const fontSizeMultiplier = fontSlider ? parseFloat(fontSlider.value) : 0.5;
                
                setTimeout(() => {
                    window.positionNodes(window.cy, fontSizeMultiplier, true);
                }, 100);
            }
        }

        // Show summary
        let message = `Added ${addedCount} node(s)`;
        if (skippedCount > 0) {
            message += `, skipped ${skippedCount} duplicate(s)`;
        }

        // Clear form
        $("#node-label").val("");
        $("#node-id").val("");
        
        // Show status
        this.showStatus(message, addedCount > 0 ? 'success' : 'warning');
    }

    parseMultipleValues(input) {
        if (!input) return [];
        
        // Split by comma or space, then clean up
        return input.split(/[,\s]+/)
            .map(value => value.trim())
            .filter(value => value.length > 0);
    }

    showStatus(message, type = 'info') {
        // Create or update status message
        let statusEl = document.getElementById('manual-controls-status');
        if (!statusEl) {
            statusEl = document.createElement('div');
            statusEl.id = 'manual-controls-status';
            statusEl.style.cssText = `
                margin-top: 10px;
                padding: 8px 12px;
                border-radius: 4px;
                font-size: 0.8rem;
                transition: opacity 0.3s ease;
            `;
            
            // Insert after the add node button
            const addNodeBtn = document.getElementById('add-node');
            if (addNodeBtn && addNodeBtn.parentNode) {
                addNodeBtn.parentNode.appendChild(statusEl);
            }
        }
        
        // Set style based on type
        const styles = {
            success: 'background-color: #d4edda; color: #155724; border: 1px solid #c3e6cb;',
            warning: 'background-color: #fff3cd; color: #856404; border: 1px solid #ffeaa7;',
            error: 'background-color: #f8d7da; color: #721c24; border: 1px solid #f5c6cb;',
            info: 'background-color: #d1ecf1; color: #0c5460; border: 1px solid #bee5eb;'
        };
        
        statusEl.style.cssText += styles[type] || styles.info;
        statusEl.textContent = message;
        statusEl.style.opacity = '1';
        
        // Auto-hide after 3 seconds
        setTimeout(() => {
            statusEl.style.opacity = '0';
        }, 3000);
    }

    // Add a new connection between nodes
    addConnection() {
        const sourceId = $("#source-node").val();
        const targetId = $("#target-node").val();
        const edgeType = $("#edge-type").val();
        const edgeLabel = $("#edge-label").val().trim();

        if (!sourceId || !targetId) {
            alert("Please select both source and target nodes");
            return;
        }

        if (sourceId === targetId) {
            alert("Source and target cannot be the same node");
            return;
        }

        if (!window.cy) {
            alert("Network not initialized");
            return;
        }

        // Generate edge ID
        const edgeId = `${sourceId}_${targetId}_${Date.now()}`;

        // Check if edge already exists
        const existingEdge = window.cy.edges().filter(edge => {
            return edge.source().id() === sourceId && edge.target().id() === targetId;
        });

        if (existingEdge.length > 0) {
            if (!confirm("An edge already exists between these nodes. Add another?")) {
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

            // Add to network with smooth animation
            window.cy.add(edgeData);

            // Reposition nodes with smooth animation
            if (window.positionNodes) {
                const fontSlider = document.getElementById('font-size-slider');
                const fontSizeMultiplier = fontSlider ? parseFloat(fontSlider.value) : 0.5;
                
                setTimeout(() => {
                    window.positionNodes(window.cy, fontSizeMultiplier, true);
                }, 50);
            }

            // Clear form
            $("#source-node").val("");
            $("#target-node").val("");
            $("#edge-label").val("");
            
            // Clear search boxes
            $("#source-node-search").val("");
            $("#target-node-search").val("");

            // Manually trigger AOP table update
            if (window.populateAopTable) {
                console.log("Manual edge addition - triggering AOP table update");
                setTimeout(() => {
                    window.populateAopTable();
                }, 100);
                
                setTimeout(() => {
                    window.populateAopTable();
                }, 500);
            }

            console.log(`Added edge: ${edgeId}`);

        } catch (error) {
            console.error("Error adding edge:", error);
            alert("Error adding edge: " + error.message);
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
