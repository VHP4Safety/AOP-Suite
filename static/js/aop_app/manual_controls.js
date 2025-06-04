// Manual node and connection creation controls

class ManualControls {
    constructor() {
        this.setupEventHandlers();
        this.nodeCounter = 0;
        this.edgeCounter = 0;
    }

    setupEventHandlers() {
        // Add node button
        $("#add-node").on("click", () => {
            this.addNode();
        });

        // Add connection button
        $("#add-connection").on("click", () => {
            this.addConnection();
        });

        // Update dropdowns when network changes
        if (window.cy) {
            window.cy.on('add remove', () => {
                this.updateNodeDropdowns();
            });
        }

        // Node type change handler
        $("#node-type").on("change", () => {
            this.updateNodeForm();
        });
    }

    // Add a new node to the network
    addNode() {
        const nodeType = $("#node-type").val();
        const nodeLabel = $("#node-label").val().trim();
        const nodeId = $("#node-id").val().trim() || this.generateNodeId(nodeType);

        if (!nodeLabel) {
            this.showError("Please enter a node label");
            return;
        }

        if (!window.cy) {
            this.showError("Network not initialized");
            return;
        }

        // Check if node already exists
        if (window.cy.getElementById(nodeId).length > 0) {
            this.showError("Node with this ID already exists");
            return;
        }

        try {
            const nodeData = this.createNodeData(nodeType, nodeId, nodeLabel);
            window.cy.add(nodeData);

            // Clear form
            $("#node-label").val("");
            $("#node-id").val("");

            // Update dropdowns
            this.updateNodeDropdowns();

            // Reposition nodes
            positionNodes(window.cy);

            this.showSuccess(`${nodeType} node added successfully`);

        } catch (error) {
            console.error("Error adding node:", error);
            this.showError("Failed to add node");
        }
    }

    // Create node data based on type
    createNodeData(nodeType, nodeId, nodeLabel) {
        const baseData = {
            data: {
                id: nodeId,
                label: nodeLabel,
                type: nodeType,
                manually_added: true
            }
        };

        switch (nodeType) {
            case "ke":
                return {
                    ...baseData,
                    classes: "ke-node",
                    data: {
                        ...baseData.data,
                        is_mie: false,
                        is_ao: false
                    }
                };
            case "chemical":
                return {
                    ...baseData,
                    classes: "chemical-node",
                    data: {
                        ...baseData.data,
                        smiles: ""
                    }
                };
            case "uniprot":
                return {
                    ...baseData,
                    classes: "uniprot-node"
                };
            case "ensembl":
                return {
                    ...baseData,
                    classes: "ensembl-node"
                };
            default:
                return baseData;
        }
    }

    // Add a new connection between nodes
    addConnection() {
        const sourceId = $("#source-node").val();
        const targetId = $("#target-node").val();
        const edgeType = $("#edge-type").val();
        const edgeLabel = $("#edge-label").val().trim();

        if (!sourceId || !targetId) {
            this.showError("Please select both source and target nodes");
            return;
        }

        if (sourceId === targetId) {
            this.showError("Source and target cannot be the same node");
            return;
        }

        if (!window.cy) {
            this.showError("Network not initialized");
            return;
        }

        try {
            const edgeId = this.generateEdgeId(sourceId, targetId);
            
            // Check if edge already exists
            if (window.cy.getElementById(edgeId).length > 0) {
                this.showError("Connection already exists between these nodes");
                return;
            }

            const edgeData = this.createEdgeData(edgeId, sourceId, targetId, edgeType, edgeLabel);
            window.cy.add(edgeData);

            // Clear form
            $("#edge-label").val("");
            $("#source-node").val("");
            $("#target-node").val("");

            // Reposition nodes
            positionNodes(window.cy);

            this.showSuccess(`${edgeType} connection added successfully`);

        } catch (error) {
            console.error("Error adding connection:", error);
            this.showError("Failed to add connection");
        }
    }

    // Create edge data based on type
    createEdgeData(edgeId, sourceId, targetId, edgeType, edgeLabel) {
        const baseData = {
            data: {
                id: edgeId,
                source: sourceId,
                target: targetId,
                type: edgeType,
                manually_added: true
            }
        };

        if (edgeLabel) {
            baseData.data.label = edgeLabel;
        }

        switch (edgeType) {
            case "ker":
                return {
                    ...baseData,
                    data: {
                        ...baseData.data,
                        ker_label: edgeLabel || `KER_${this.edgeCounter++}`,
                        curie: `aop.relationships:manual_${this.edgeCounter}`
                    }
                };
            case "interaction":
                return {
                    ...baseData,
                    data: {
                        ...baseData.data,
                        label: edgeLabel || "interaction"
                    }
                };
            case "part_of":
                return {
                    ...baseData,
                    data: {
                        ...baseData.data,
                        label: "part of"
                    }
                };
            case "translates_to":
                return {
                    ...baseData,
                    data: {
                        ...baseData.data,
                        label: "translates to"
                    }
                };
            default:
                return baseData;
        }
    }

    // Update node dropdowns with current nodes
    updateNodeDropdowns() {
        if (!window.cy) return;

        const sourceSelect = $("#source-node");
        const targetSelect = $("#target-node");
        
        // Store current values
        const currentSource = sourceSelect.val();
        const currentTarget = targetSelect.val();

        // Clear and rebuild options
        sourceSelect.empty().append('<option value="">Select source...</option>');
        targetSelect.empty().append('<option value="">Select target...</option>');

        window.cy.nodes().forEach(node => {
            const nodeId = node.id();
            const nodeLabel = node.data('label') || nodeId;
            const nodeType = node.data('type') || 'unknown';
            const optionText = `${nodeLabel} (${nodeType})`;
            
            sourceSelect.append(`<option value="${nodeId}">${optionText}</option>`);
            targetSelect.append(`<option value="${nodeId}">${optionText}</option>`);
        });

        // Restore previous values if they still exist
        if (currentSource && sourceSelect.find(`option[value="${currentSource}"]`).length) {
            sourceSelect.val(currentSource);
        }
        if (currentTarget && targetSelect.find(`option[value="${currentTarget}"]`).length) {
            targetSelect.val(currentTarget);
        }
    }

    // Update node form based on selected type
    updateNodeForm() {
        const nodeType = $("#node-type").val();
        const nodeIdField = $("#node-id");
        
        // Update placeholder text based on node type
        switch (nodeType) {
            case "ke":
                nodeIdField.attr("placeholder", "e.g., https://identifiers.org/aop.events/123");
                break;
            case "chemical":
                nodeIdField.attr("placeholder", "e.g., compound_name or SMILES");
                break;
            case "uniprot":
                nodeIdField.attr("placeholder", "e.g., uniprot_P12345");
                break;
            case "ensembl":
                nodeIdField.attr("placeholder", "e.g., ensembl_ENSG00000123456");
                break;
            default:
                nodeIdField.attr("placeholder", "Auto-generated if empty");
        }
    }

    // Generate unique node ID
    generateNodeId(nodeType) {
        const timestamp = Date.now();
        const random = Math.floor(Math.random() * 1000);
        
        switch (nodeType) {
            case "uniprot":
                return `uniprot_manual_${timestamp}_${random}`;
            case "ensembl":
                return `ensembl_manual_${timestamp}_${random}`;
            case "chemical":
                return `chemical_manual_${timestamp}_${random}`;
            default:
                return `${nodeType}_manual_${timestamp}_${random}`;
        }
    }

    // Generate unique edge ID
    generateEdgeId(sourceId, targetId) {
        return `edge_${sourceId}_${targetId}_${Date.now()}`;
    }

    // Show success message
    showSuccess(message) {
        if (window.networkState) {
            window.networkState.showNotification(message, "success");
        } else {
            console.log("Success:", message);
        }
    }

    // Show error message
    showError(message) {
        if (window.networkState) {
            window.networkState.showNotification(message, "error");
        } else {
            console.error("Error:", message);
            alert(message); // Fallback
        }
    }
}

// Initialize manual controls
let manualControls;

document.addEventListener("DOMContentLoaded", function() {
    manualControls = new ManualControls();
});

// Update dropdowns when Cytoscape is ready
function initializeManualControls() {
    if (manualControls && window.cy) {
        manualControls.updateNodeDropdowns();
        // Setup change tracking for the manual controls
        window.cy.on('add remove', () => {
            manualControls.updateNodeDropdowns();
        });
    }
}

// Make available globally
window.manualControls = manualControls;
window.initializeManualControls = initializeManualControls;
