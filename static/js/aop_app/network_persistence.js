// Network persistence and state management

class NetworkState {
    constructor() {
        this.autoSaveInterval = null;
        this.setupAutoSave();
    }

    // Auto-save network state every 30 seconds
    setupAutoSave() {
        this.autoSaveInterval = setInterval(() => {
            this.saveNetworkState(true); // true = auto-save
        }, 30000);
    }

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
            // Extract positions safely
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
                    exported: true
                }
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

    // Override the existing download function
    $("#download_network").off("click").on("click", () => {
        networkState.downloadNetworkJSON();
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
