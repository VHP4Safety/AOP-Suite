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

        // Handle edge type changes to update label options
        const edgeTypeSelect = document.getElementById('edge-type');
        if (edgeTypeSelect) {
            edgeTypeSelect.addEventListener('change', () => {
                const sourceId = document.getElementById('source-node').value;
                const targetId = document.getElementById('target-node').value;
                
                const sourceType = this.getNodeTypeFromDropdown(sourceId);
                const targetType = this.getNodeTypeFromDropdown(targetId);
                
                this.updateEdgeLabelOptions(edgeTypeSelect.value, sourceType, targetType);
            });
        }

        // Handle node selection changes to update edge label options
        const sourceNodeSelect = document.getElementById('source-node');
        const targetNodeSelect = document.getElementById('target-node');
        
        if (sourceNodeSelect) {
            sourceNodeSelect.addEventListener('change', () => {
                const edgeType = document.getElementById('edge-type').value;
                const sourceType = this.getNodeTypeFromDropdown(sourceNodeSelect.value);
                const targetType = this.getNodeTypeFromDropdown(targetNodeSelect.value);
                
                this.updateEdgeLabelOptions(edgeType, sourceType, targetType);
            });
        }
        
        if (targetNodeSelect) {
            targetNodeSelect.addEventListener('change', () => {
                const edgeType = document.getElementById('edge-type').value;
                const sourceType = this.getNodeTypeFromDropdown(sourceNodeSelect.value);
                const targetType = this.getNodeTypeFromDropdown(targetNodeSelect.value);
                
                this.updateEdgeLabelOptions(edgeType, sourceType, targetType);
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

    // Enhanced addNode to handle component node types
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
            const finalId = ids[index] || this.generateNodeId(nodeType, label);

            // Check if node already exists
            if (window.cy.getElementById(finalId).length > 0) {
                console.warn(`Node with ID "${finalId}" already exists - skipping`);
                skippedCount++;
                return;
            }

            try {
                // Create node data with type-specific properties and correct classes
                const nodeData = {
                    data: {
                        id: finalId,
                        label: label,
                        type: nodeType
                    },
                    classes: this.getNodeClasses(nodeType)  // Use proper class assignment
                };

                // Add type-specific properties
                if (nodeType === 'component_process') {
                    nodeData.data.process_name = label;
                    nodeData.data.process_id = finalId.replace('component_process_', '');
                    nodeData.data.process_iri = `http://purl.obolibrary.org/obo/${finalId.replace('component_process_', '')}`;
                } else if (nodeType === 'component_object') {
                    nodeData.data.object_name = label;
                    nodeData.data.object_id = finalId.replace('component_object_', '');
                    nodeData.data.object_iri = `http://purl.obolibrary.org/obo/${finalId.replace('component_object_', '')}`;
                } else if (nodeType === 'ke') {
                    // Add KE-specific properties
                    nodeData.data.is_mie = false;
                    nodeData.data.is_ao = false;
                } else if (nodeType === 'chemical') {
                    nodeData.data.compound_name = label;
                    nodeData.data.chemical_label = label;
                } else if (nodeType === 'uniprot') {
                    nodeData.data.uniprot_id = finalId.replace('uniprot_', '');
                } else if (nodeType === 'ensembl') {
                    nodeData.data.ensembl_id = finalId.replace('ensembl_', '');
                } else if (nodeType === 'organ') {
                    nodeData.data.organ_name = label;
                }

                nodesToAdd.push(nodeData);
                addedCount++;
                
                console.log(`Prepared node: ${finalId} (type: ${nodeType}, classes: ${nodeData.classes})`);

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

    // Get the correct CSS classes for each node type
    getNodeClasses(nodeType) {
        const classMap = {
            'ke': 'ke-node',
            'mie': 'mie-node',
            'ao': 'ao-node',
            'chemical': 'chemical-node',
            'uniprot': 'uniprot-node',
            'ensembl': 'ensembl-node',
            'component_process': 'process-node',
            'component_object': 'object-node',
            'organ': 'organ-node',
            'custom': 'custom-node'
        };
        return classMap[nodeType] || `${nodeType}-node`;
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
        let edgeLabel = $("#edge-label").val().trim();

        // Check for edge label select (for component actions)
        const edgeLabelSelect = document.getElementById('edge-label-select');
        if (edgeLabelSelect && edgeLabelSelect.value) {
            edgeLabel = edgeLabelSelect.value;
        }

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
            // Create edge data with type-specific properties
            const edgeData = {
                data: {
                    id: edgeId,
                    source: sourceId,
                    target: targetId,
                    type: edgeType,
                    label: edgeLabel || this.getDefaultEdgeLabel(edgeType)
                }
            };

            // Handle component action edge types specially
            if (this.isComponentActionEdgeType(edgeType)) {
                // For component actions, use the action label directly
                if (edgeType === 'has_process') {
                    edgeData.data.type = 'has process';
                } else if (edgeType === 'has_object') {
                    edgeData.data.type = 'has object';
                } else {
                    // For direct component actions, use the full label
                    edgeData.data.type = 'has process';  // Underlying type is has_process
                    edgeData.data.label = this.getDefaultEdgeLabel(edgeType);  // Action label
                }
            } else if (edgeType === 'is_stressor_of') {
                edgeData.data.type = 'is stressor of';
            }

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
            
            // Clear edge label select if it exists
            if (edgeLabelSelect) {
                edgeLabelSelect.value = '';
            }
            
            // Clear search boxes
            $("#source-node-search").val("");
            $("#target-node-search").val("");

            // Update relevant tables based on the edge type
            if (this.isComponentActionEdgeType(edgeType)) {
                // Component edge - update component table
                console.log("Manual component edge addition - triggering component table update");
                if (window.componentTableManager && window.componentTableManager.performTableUpdate) {
                    setTimeout(() => {
                        window.componentTableManager.performTableUpdate();
                    }, 100);
                }
            } else {
                // Regular edge - update AOP table
                console.log("Manual edge addition - triggering AOP table update");
                if (window.populateAopTable) {
                    setTimeout(() => {
                        window.populateAopTable();
                    }, 100);
                }
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
            'translates_to': 'Translates to',
            'has_process': 'Has process',
            'has_object': 'Has object',
            'is_stressor_of': 'Is stressor of',
            'expression_in': 'Expression in',
            'increased_process_quality': 'increased process quality',
            'decreased_process_quality': 'decreased process quality',
            'delayed': 'delayed',
            'occurrence': 'occurrence',
            'abnormal': 'abnormal',
            'premature': 'premature',
            'disrupted': 'disrupted',
            'functional_change': 'functional change',
            'morphological_change': 'morphological change',
            'pathological': 'pathological',
            'arrested': 'arrested',
            'custom': 'Connection'
        };
        return labels[edgeType] || 'Connection';
    }

    // Get appropriate placeholder for edge label based on type
    getEdgeLabelPlaceholder(edgeType) {
        const placeholders = {
            'ker': 'e.g., directly leads to, indirectly leads to',
            'interaction': 'e.g., binds to, inhibits, activates',
            'part_of': 'e.g., component of, member of',
            'translates_to': 'e.g., codes for, produces',
            'has_process': 'e.g., increased, decreased, abnormal',
            'has_object': 'e.g., affects, targets',
            'is_stressor_of': 'e.g., triggers, initiates',
            'expression_in': 'e.g., expressed in, localized to',
            'increased_process_quality': 'Increased process quality',
            'decreased_process_quality': 'Decreased process quality',
            'delayed': 'Delayed process',
            'occurrence': 'Process occurrence',
            'abnormal': 'Abnormal process',
            'premature': 'Premature process',
            'disrupted': 'Disrupted process',
            'functional_change': 'Functional change in process',
            'morphological_change': 'Morphological change in process',
            'pathological': 'Pathological process',
            'arrested': 'Arrested process',
            'custom': 'Enter custom relationship'
        };
        return placeholders[edgeType] || 'Enter connection label';
    }

    // Check if edge type is a component action
    isComponentActionEdgeType(edgeType) {
        const componentActionTypes = [
            'has_process', 'has_object', 'increased_process_quality', 'decreased_process_quality',
            'delayed', 'occurrence', 'abnormal', 'premature', 'disrupted', 
            'functional_change', 'morphological_change', 'pathological', 'arrested'
        ];
        return componentActionTypes.includes(edgeType);
    }

    // Get component action options for process edges
    getComponentActionOptions() {
        return [
            { value: 'increased process quality', label: 'Increased process quality' },
            { value: 'decreased process quality', label: 'Decreased process quality' },
            { value: 'delayed', label: 'Delayed' },
            { value: 'occurrence', label: 'Occurrence' },
            { value: 'abnormal', label: 'Abnormal' },
            { value: 'premature', label: 'Premature' },
            { value: 'disrupted', label: 'Disrupted' },
            { value: 'functional change', label: 'Functional change' },
            { value: 'morphological change', label: 'Morphological change' },
            { value: 'pathological', label: 'Pathological' },
            { value: 'arrested', label: 'Arrested' }
        ];
    }

    // Update edge label options based on edge type and nodes
    updateEdgeLabelOptions(edgeType, sourceNodeType, targetNodeType) {
        const edgeLabelInput = document.getElementById('edge-label');
        const edgeLabelSelect = document.getElementById('edge-label-select');
        
        // Remove existing select if present
        if (edgeLabelSelect) {
            edgeLabelSelect.remove();
        }

        // For KE -> process edges, show component action dropdown
        if (edgeType === 'has_process' && 
            (sourceNodeType === 'ke' || sourceNodeType === 'mie' || sourceNodeType === 'ao') &&
            targetNodeType === 'component_process') {
            
            // Create dropdown for component actions
            const select = document.createElement('select');
            select.id = 'edge-label-select';
            select.className = 'form-control';
            
            // Add default option
            const defaultOption = document.createElement('option');
            defaultOption.value = '';
            defaultOption.textContent = 'Select action...';
            select.appendChild(defaultOption);
            
            // Add component action options
            this.getComponentActionOptions().forEach(action => {
                const option = document.createElement('option');
                option.value = action.value;  // Use the actual edge label value
                option.textContent = action.label;
                select.appendChild(option);
            });
            
            // Replace input with select
            edgeLabelInput.style.display = 'none';
            edgeLabelInput.parentNode.appendChild(select);
            
            // Update input value when select changes
            select.addEventListener('change', () => {
                edgeLabelInput.value = select.value;
            });
        } else {
            // Show regular input
            edgeLabelInput.style.display = 'block';
            edgeLabelInput.placeholder = this.getEdgeLabelPlaceholder(edgeType);
        }
    }

    // Get node type from dropdown selection
    getNodeTypeFromDropdown(nodeId) {
        if (!window.cy || !nodeId) return 'unknown';
        
        const node = window.cy.getElementById(nodeId);
        if (node.length > 0) {
            return node.data('type') || 'unknown';
        }
        return 'unknown';
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
