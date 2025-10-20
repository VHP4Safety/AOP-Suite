// Network persistence and state management

class NetworkState {
    constructor() {
        this.autoSaveInterval = null;
    //    this.setupAutoSave();
    }

    //// Auto-save network state every 30 minutes
    //setupAutoSave() {
    //    this.autoSaveInterval = setInterval(() => {
    //        this.saveNetworkState(true); // true = auto-save
    //    }, 30000);
    //}

    // Save current network state
    async saveNetworkState(isAutoSave = false) {
        if (!window.cy) {
            console.warn("Cannot save: Cytoscape instance not available");
            return;
        }

        try {
            // Extract positions safely to avoid cyclic references
            const positions = {};
            window.cy.nodes().forEach(node => {
                const pos = node.position();
                positions[node.id()] = {
                    x: pos.x,
                    y: pos.y
                };
            });

            const networkData = {
                elements: window.cy.elements().jsons(),
                style: this.extractStyleData(),
                layout: positions,
                metadata: {
                    timestamp: new Date().toISOString(),
                    version: "1.0",
                    isAutoSave: isAutoSave,
                    compoundsVisible: window.compoundsVisible || false,
                    genesVisible: window.genesVisible || false,
                    boundingBoxesVisible: window.boundingBoxesVisible || false
                }
            };

            const response = await fetch('/save_network_state', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(networkData)
            });

            if (response.ok) {
                const result = await response.json();
                if (!isAutoSave) {
                    this.showNotification("Network saved successfully", "success");
                }
                console.log("Network saved:", result);
            } else {
                throw new Error(`Save failed: ${response.status}`);
            }
        } catch (error) {
            console.error("Error saving network:", error);
            if (!isAutoSave) {
                this.showNotification("Failed to save network", "error");
            }
        }
    }

    // Extract style data safely without cyclic references
    extractStyleData() {
        try {
            // Return basic style information instead of full style object
            return {
                fontSizeMultiplier: parseFloat(document.getElementById('font-size-slider')?.value || 0.5),
                timestamp: new Date().toISOString()
            };
        } catch (error) {
            console.warn("Could not extract style data:", error);
            return {};
        }
    }

    // Load network state
    async loadNetworkState() {
        try {
            const response = await fetch('/load_network_state', {
                method: 'GET'
            });

            if (response.ok) {
                const networkData = await response.json();
                await this.restoreNetworkState(networkData);
                this.showNotification("Network loaded successfully", "success");
            } else {
                throw new Error(`Load failed: ${response.status}`);
            }
        } catch (error) {
            console.error("Error loading network:", error);
            this.showNotification("Failed to load network", "error");
        }
    }

    // Restore network from saved state
    async restoreNetworkState(networkData) {
        if (!window.cy) {
            console.error("Cannot restore: Cytoscape instance not available");
            return;
        }

        try {
            // Clear current network
            window.cy.elements().remove();

            // Add saved elements
            if (networkData.elements) {
                window.cy.add(networkData.elements);
            }

            // Restore positions if available
            if (networkData.layout) {
                Object.entries(networkData.layout).forEach(([nodeId, position]) => {
                    const node = window.cy.getElementById(nodeId);
                    if (node.length > 0 && position.x !== undefined && position.y !== undefined) {
                        node.position({
                            x: parseFloat(position.x),
                            y: parseFloat(position.y)
                        });
                    }
                });
            }

            // Restore style settings
            if (networkData.style && networkData.style.fontSizeMultiplier) {
                const fontSlider = document.getElementById('font-size-slider');
                if (fontSlider) {
                    fontSlider.value = networkData.style.fontSizeMultiplier;
                }
            }

            // Restore state variables
            if (networkData.metadata) {
                window.compoundsVisible = networkData.metadata.compoundsVisible || false;
                window.genesVisible = networkData.metadata.genesVisible || false;
                window.boundingBoxesVisible = networkData.metadata.boundingBoxesVisible || false;

                // Update button states
                this.updateButtonStates();
            }

            // Fit view and apply styling
            window.cy.fit();
            positionNodes(window.cy);

        } catch (error) {
            console.error("Error restoring network state:", error);
            throw error;
        }
    }

    // Update button states based on loaded state
    updateButtonStates() {
        $("#toggle_compounds").text(window.compoundsVisible ? "Hide Compounds" : "Show Compounds");
        $("#see_genes").text(window.genesVisible ? "Hide Genes" : "See Genes");
        $("#toggle_bounding_boxes").text(window.boundingBoxesVisible ? "Remove AOP Boxes" : "Group by AOP");
    }

    // Download network as JSON file
    downloadNetworkJSON() {
        if (!window.cy) {
            this.showNotification("No network to download", "error");
            return;
        }

        try {
            // Download Cytoscape elements and style
            const networkData = {
                elements: window.cy.elements().jsons(),
                style: window.cy.style().json()
            };

            const blob = new Blob([JSON.stringify(networkData, null, 2)], { 
                type: "application/json" 
            });
            const url = URL.createObjectURL(blob);
            const a = document.createElement("a");
            a.href = url;
            a.download = `aop_network_${new Date().toISOString().split('T')[0]}.json`;
            document.body.appendChild(a);
            a.click();
            document.body.removeChild(a);
            URL.revokeObjectURL(url);

            this.showNotification("Network downloaded", "success");
        } catch (error) {
            console.error("Error downloading network:", error);
            this.showNotification("Failed to download network", "error");
        }
    }

    // Alias for legacy callers - download full Cytoscape JSON
    downloadCytoscapeJSON() {
        return this.downloadNetworkJSON();
    }

    // Download Cytoscape style specification as JSON
    downloadCytoscapeStylesJSON() {
        if (!window.cy) {
            this.showNotification("No Cytoscape instance available", "error");
            return;
        }

        try {
            let styleJson = null;
            try {
                styleJson = window.cy.style().json();
            } catch (e) {
                // Fallback: use extracted minimal style
                styleJson = this.extractStyleData();
            }

            const blob = new Blob([JSON.stringify(styleJson, null, 2)], { type: 'application/json' });
            const url = URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = `aop_cytoscape_styles_${new Date().toISOString().split('T')[0]}.json`;
            document.body.appendChild(a);
            a.click();
            document.body.removeChild(a);
            URL.revokeObjectURL(url);

            this.showNotification('Cytoscape styles downloaded', 'success');
        } catch (err) {
            console.error('Error downloading styles:', err);
            this.showNotification('Failed to download styles', 'error');
        }
    }

    // Export network to NDEx via server route; server returns CX2 JSON which we save
    async downloadNdexNetwork() {
        if (!window.cy) {
            this.showNotification('No network to export', 'error');
            return;
        }

        try {
            // Get elements directly from Cytoscape - they already contain the full data
            // because they were created using to_cytoscape methods from the data model
            const elements = window.cy.elements().jsons();
            
            if (elements.length === 0) {
                this.showNotification('Network is empty, nothing to export', 'error');
                return;
            }

            // Show loading notification
            this.showNotification('Exporting network to NDEx format...', 'info');

            // Use network metadata or generate defaults
            const networkName = this.getNetworkName() || 'AOP Network';
            const networkDescription = this.getNetworkDescription() || 'Exported from AOP Network Builder';

            // Include comprehensive network metadata for better CX2 export
            const metadata = this.collectNetworkMetadata();

            const body = { 
                elements,
                name: networkName,
                description: networkDescription,
                metadata: metadata
            };

            const resp = await fetch('/ndex/to_ndex_network', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(body)
            });

            if (!resp.ok) {
                let errorMsg = `Server returned ${resp.status}`;
                try {
                    const errorData = await resp.json();
                    errorMsg = errorData.error || errorMsg;
                } catch (e) {
                    const txt = await resp.text();
                    errorMsg = txt || errorMsg;
                }
                throw new Error(errorMsg);
            }

            const cx2 = await resp.json();

            // Trigger download of CX2 JSON
            const blob = new Blob([JSON.stringify(cx2, null, 2)], { type: 'application/json' });
            const url = URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = `${this.sanitizeFilename(networkName)}_cx2_${new Date().toISOString().split('T')[0]}.json`;
            document.body.appendChild(a);
            a.click();
            document.body.removeChild(a);
            URL.revokeObjectURL(url);

            this.showNotification('NDEx CX2 exported successfully', 'success');
            return cx2;
        } catch (err) {
            console.error('Error exporting to NDEx:', err);
            this.showNotification('Failed to export NDEx network: ' + (err.message || err), 'error');
            throw err;
        }
    }

    // Collect comprehensive network metadata including node/edge type statistics
    collectNetworkMetadata() {
        if (!window.cy) return {};

        const metadata = {
            timestamp: new Date().toISOString(),
            version: '1.0',
            nodeTypes: {},
            edgeTypes: {},
            totalNodes: 0,
            totalEdges: 0
        };

        // Count node types
        window.cy.nodes().forEach(node => {
            const nodeType = node.data('type') || node.data('node_type') || 'unknown';
            metadata.nodeTypes[nodeType] = (metadata.nodeTypes[nodeType] || 0) + 1;
            metadata.totalNodes++;
        });

        // Count edge types
        window.cy.edges().forEach(edge => {
            const edgeType = edge.data('type') || edge.data('edge_type') || edge.data('interaction') || 'unknown';
            metadata.edgeTypes[edgeType] = (metadata.edgeTypes[edgeType] || 0) + 1;
            metadata.totalEdges++;
        });

        // Add state information
        metadata.compoundsVisible = window.compoundsVisible || false;
        metadata.genesVisible = window.genesVisible || false;
        metadata.boundingBoxesVisible = window.boundingBoxesVisible || false;

        return metadata;
    }

    // Helper: Get network name from metadata or title
    getNetworkName() {
        // Try to get from saved metadata first
        if (window.cy) {
            const scratch = window.cy.scratch('_metadata');
            if (scratch && scratch.name) return scratch.name;
        }
        
        // Fall back to page title or container data
        const container = document.querySelector('[data-title]');
        if (container) {
            const title = container.getAttribute('data-title');
            if (title && title !== 'AOP Network Builder') return title;
        }
        
        return document.title || 'AOP Network';
    }

    // Helper: Get network description
    getNetworkDescription() {
        if (window.cy) {
            const scratch = window.cy.scratch('_metadata');
            if (scratch && scratch.description) return scratch.description;
        }
        
        // Generate a basic description from network stats
        const stats = this.getNetworkStats();
        return `AOP Network with ${stats.nodes} nodes and ${stats.edges}. Exported from AOP Network Builder.`;
    }

    // Helper: Get network stats
    getNetworkStats() {
        if (!window.cy) return { nodes: 0, edges: 0 };
        return {
            nodes: window.cy.nodes().length,
            edges: window.cy.edges().length
        };
    }

    // Helper: Sanitize filename
    sanitizeFilename(name) {
        return name.replace(/[^a-z0-9_\-]/gi, '_').substring(0, 50);
    }

    // TODO
    downloadNetworkPNG() {
        this.showNotification('PNG export not implemented', 'error');
    }

    downloadNetworkSVG() {
        this.showNotification('SVG export not implemented', 'error');
    }

    // Show notification to user
    showNotification(message, type = "info") {
        // Create notification element
        const notification = document.createElement("div");
        notification.className = `notification notification-${type}`;
        notification.innerHTML = `
            <i class="fas fa-${type === 'success' ? 'check-circle' : type === 'error' ? 'exclamation-circle' : 'info-circle'}"></i>
            <span>${message}</span>
        `;

        // Add to DOM
        document.body.appendChild(notification);

        // Auto-remove after 3 seconds
        setTimeout(() => {
            if (notification.parentNode) {
                notification.parentNode.removeChild(notification);
            }
        }, 3000);
    }

    // Clean up
    destroy() {
        if (this.autoSaveInterval) {
            clearInterval(this.autoSaveInterval);
        }
    }
}

// Initialize persistence manager
let networkState;

document.addEventListener("DOMContentLoaded", function() {
    networkState = new NetworkState();

    // Button event handlers
    $("#save_network").on("click", () => {
        networkState.saveNetworkState(false);
    });

    $("#load_network").on("click", () => {
        networkState.loadNetworkState();
    });

    // Simple button handlers - no dropdown complexity
    $("#download_network").on("click", () => {
        networkState.downloadNetworkJSON();
    });

    $("#download_ndex").on("click", async () => {
        try {
            await networkState.downloadNdexNetwork();
        } catch (err) {
            console.error("NDEx export failed:", err);
        }
    });

    $("#download_png").on("click", () => {
        networkState.downloadNetworkPNG();
    });

    $("#download_svg").on("click", () => {
        networkState.downloadNetworkSVG();
    });
});

// Auto-save when network changes
function setupNetworkChangeTracking() {
    if (!window.cy) return;

    let changeTimeout;
    const trackChange = () => {
        // Debounce changes to avoid excessive saving
        clearTimeout(changeTimeout);
        changeTimeout = setTimeout(() => {
            if (networkState) {
                networkState.saveNetworkState(true);
            }
        }, 5000); // Save 5 seconds after last change
    };

    // Track various network changes
    window.cy.on('add remove position', trackChange);
}

// Make functions available globally
window.networkState = networkState;
window.setupNetworkChangeTracking = setupNetworkChangeTracking;
