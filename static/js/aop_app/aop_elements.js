document.addEventListener("DOMContentLoaded", function () {
    // Global variables
    window.cy = null;
    window.genesVisible = false;
    window.compoundsVisible = false;
    window.componentsVisible = false;
    window.goProcessesVisible = false;
    window.fetched_preds = false;
    window.compound_data = {};
    window.modelToProteinInfo = {};
    window.compoundMapping = {};

    // Check if we're in standalone mode or template mode
    const isStandaloneMode = !document.querySelector("#compound-container[data-mies]") ||
        !document.querySelector("#compound-container").dataset.mies;

    console.log("App mode:", isStandaloneMode ? "Standalone" : "Template");

    // ===== UTILITY FUNCTIONS =====
    
    // Helper function to show status messages
    function showStatus(message, type = 'info') {
        // You can implement a status display system here if needed
        console.log(`[${type.toUpperCase()}] ${message}`);
    }

    // ===== NETWORK DATA EXTRACTION FUNCTIONS =====

    // Helper function to get Key Events from network (either selected or all)
    function getKeyEventsFromNetwork(useSelection = false) {
        if (!window.cy) {
            return [];
        }

        let nodes;
        if (useSelection) {
            const selected = window.cy.$(':selected');
            // Only consider selected nodes, filter out edges
            nodes = selected.nodes();
            console.log(`Using ${nodes.length} selected nodes for Key Event extraction`);
        } else {
            nodes = window.cy.nodes();
            console.log(`Using all ${nodes.length} nodes for Key Event extraction`);
        }

        const keyEventUris = [];

        nodes.forEach(node => {
            const nodeData = node.data();
            const nodeId = nodeData.id;
            const nodeType = nodeData.type;
            const isMie = nodeData.is_mie;
            const isAo = nodeData.is_ao;

            // Collect all Key Events (MIEs, intermediate KEs, and AOs)
            if (nodeId && (nodeId.includes('aop.events') || isMie || isAo || nodeType === 'mie' || nodeType === 'key_event' || nodeType === 'ao')) {
                // Ensure proper URI format for the SPARQL query
                if (nodeId.startsWith('http')) {
                    keyEventUris.push(`<${nodeId}>`);
                } else if (nodeId.includes('aop.events')) {
                    keyEventUris.push(`<${nodeId}>`);
                }
            }
        });

        return keyEventUris;
    }

    // Helper function to get AOP URIs from network (either selected or all)
    function getAOPsFromNetwork(useSelection = false) {
        if (!window.cy) {
            return [];
        }

        let nodes;
        if (useSelection) {
            const selected = window.cy.$(':selected');
            // Only consider selected nodes, filter out edges
            nodes = selected.nodes();
            console.log(`Using ${nodes.length} selected nodes for AOP extraction`);
        } else {
            nodes = window.cy.nodes();
            console.log(`Using all ${nodes.length} nodes for AOP extraction`);
        }

        const aopUris = new Set();

        nodes.forEach(node => {
            const nodeData = node.data();
            
            // Primary method: Check the 'aop' array property (main source based on your data)
            if (nodeData.aop && Array.isArray(nodeData.aop)) {
                nodeData.aop.forEach(aopUri => {
                    if (aopUri && typeof aopUri === 'string') {
                        aopUris.add(aopUri);
                    }
                });
            }
            
            // Secondary method: Check if it's an AOP node or has AOP associations
            if (nodeData.aop_uris) {
                nodeData.aop_uris.forEach(uri => aopUris.add(uri));
            }
            
            // Tertiary method: Extract from associated AOPs if available
            if (nodeData.associated_aops) {
                nodeData.associated_aops.forEach(aop => {
                    if (aop.aop_uri) aopUris.add(aop.aop_uri);
                    if (aop.aop_id) {
                        // Construct URI from AOP ID
                        const aopUri = `https://identifiers.org/aop/${aop.aop_id}`;
                        aopUris.add(aopUri);
                    }
                });
            }

            // Quaternary method: Extract from node ID if it looks like an AOP URI
            if (nodeData.id && nodeData.id.includes('aop/')) {
                aopUris.add(nodeData.id);
            }

            // Quintary method: Check for AOP info in other data fields
            if (nodeData.aop_id) {
                // Construct URI from AOP ID
                const aopUri = `https://identifiers.org/aop/${nodeData.aop_id}`;
                aopUris.add(aopUri);
            }

            // Debug logging for the first few nodes
            if (aopUris.size === 0 && nodes.length <= 5) {
                console.log(`Node ${nodeData.id} data:`, nodeData);
                console.log(`AOP array:`, nodeData.aop);
            }
        });

        const aopUriArray = Array.from(aopUris);
        console.log(`Extracted ${aopUriArray.length} AOP URIs:`, aopUriArray);
        
        return aopUriArray;
    }

    // ===== TOGGLE FUNCTIONS =====

    function toggleGenes() {
        const action = window.genesVisible ? 'hide' : 'show';
        if (action === 'show') {
            // Check if there are selected elements
            const hasSelection = window.cy && window.cy.$(':selected').length > 0;
            // Extract Key Event URIs from either selected nodes or all nodes
            const keyEventUris = getKeyEventsFromNetwork(hasSelection);
            if (keyEventUris.length === 0) {
                const scopeMessage = hasSelection ? "selected elements" : "network";
                console.log(`No Key Events found in ${scopeMessage} for gene loading`);
                $("#see_genes").html('<i class="fas fa-dna"></i> Remove gene sets');
                window.genesVisible = true;
                return;
            }
            const scopeMessage = hasSelection ? `${window.cy.$(':selected').nodes().length} selected nodes` : "all network nodes";
            console.log(`Found ${keyEventUris.length} Key Events from ${scopeMessage} for gene loading:`, keyEventUris);
            // Call the load_and_show_genes endpoint with the extracted KEs
            fetch(`/load_and_show_genes?kes=${encodeURIComponent(keyEventUris.join(' '))}`, {
                method: 'GET'
            })
                .then(response => {
                    if (!response.ok) {
                        throw new Error(`HTTP ${response.status}: ${response.statusText}`);
                    }
                    return response.json();
                })
                .then(data => {
                    if (data.error) {
                        console.error("Gene loading error:", data.error);
                        showStatus(`Error loading genes: ${data.error}`, 'error');
                        return;
                    }

                    const fontSlider = document.getElementById('font-size-slider');
                    const fontSizeMultiplier = fontSlider ? parseFloat(fontSlider.value) : 0.5;
                    
                    // Add query to history table
                    if (data.sparql_query && window.historyTableManager) {
                        window.historyTableManager.addHistoryEntry('gene', 'AOP-Wiki RDF', data.sparql_query, null, data.gene_elements);
                    }

                    // Add only new gene elements
                    data.gene_elements.forEach(element => {
                        console.log(element.data);
                        const elementId = element.data?.id;
                        if (elementId && !window.cy.getElementById(elementId).length) {
                            try {
                                window.cy.add(element);
                            } catch (error) {
                                console.warn("Error adding gene element:", elementId, error.message);
                            }
                        }
                    });

                    // Show genes based on selection
                    if (hasSelection) {
                        // Only show genes connected to selected nodes
                        const selectedNodes = window.cy.$(':selected').nodes();
                        const geneNodesToShow = window.cy.collection();
                        selectedNodes.forEach(node => {
                            const connectedGenes = node.connectedEdges().connectedNodes('.uniprot-node, .ensembl-node');
                            geneNodesToShow.merge(connectedGenes);
                        });
                        geneNodesToShow.show();
                        geneNodesToShow.connectedEdges().show();
                        console.log(`Showed ${geneNodesToShow.length} genes connected to selected nodes`);
                    } else {
                        // Show all genes
                        window.cy.elements(".uniprot-node, .ensembl-node").show();
                        window.cy.edges().forEach(function (edge) {
                            const source = edge.source();
                            const target = edge.target();
                            const sourceIsGene = source.hasClass("uniprot-node") || source.hasClass("ensembl-node");
                            const targetIsGene = target.hasClass("uniprot-node") || target.hasClass("ensembl-node");
                            if (source.visible() && target.visible() && (sourceIsGene || targetIsGene)) {
                                edge.show();
                            }
                        });
                        console.log(`Showed all gene nodes`);
                    }

                    // Update button and state - set to hide mode when showing genes
                    $("#see_genes").text("Remove gene sets");
                    window.genesVisible = true;

                    // Update gene table
                    setTimeout(() => {
                        if (window.populateGeneTable) {
                            window.populateGeneTable();
                        }
                    }, 100);

                    // Layout update
                    setTimeout(() => {
                        positionNodes(window.cy, fontSizeMultiplier, true);
                    }, 150);
                    window.resetNetworkLayout();
                })
                .catch(error => {
                    console.error("Error loading genes:", error);
                    showStatus(`Error loading genes: ${error.message}`, 'error');
                });
        } else {
            // Remove gene sets
            const hasSelection = window.cy && window.cy.$(':selected').length > 0;
            if (hasSelection) {
                // Hide only genes connected to selected nodes
                const selectedNodes = window.cy.$(':selected').nodes();
                const genesToHide = window.cy.collection();
                const proteinsToHide = window.cy.collection();
                selectedNodes.forEach(node => {
                    const connectedProts = node.connectedEdges().connectedNodes('.uniprot-node');
                    const connectedGenes = connectedProts.connectedEdges().connectedNodes('.ensembl-node');
                    genesToHide.merge(connectedGenes);
                    proteinsToHide.merge(connectedProts);
                });

                genesToHide.remove();
                genesToHide.connectedEdges().remove();
                proteinsToHide.remove();
                proteinsToHide.connectedEdges().remove();
                console.log(`Removed ${genesToHide.length} genes and ${proteinsToHide.length} proteins connected to selected nodes`);
            } else {
                // Hide all genes
                const allGenes = window.cy.elements(".uniprot-node, .ensembl-node");
                allGenes.remove();
                allGenes.connectedEdges().remove();

                console.log(`Removed all gene nodes`);
            }

            // Reset layout and update table
            window.resetNetworkLayout();
            window.genesVisible = false;
            $("#see_genes").html('<i class="fas fa-dna"></i> Get gene sets');
            setTimeout(() => {
                if (window.populateGeneTable) {
                    window.populateGeneTable();
                }
            }, 100);
        }
    }

    function toggleCompounds() {
        const action = window.compoundsVisible ? 'hide' : 'show';
        if (action === 'show') {
            // Check if there are selected elements
            const hasSelection = window.cy && window.cy.$(':selected').length > 0;
            // Extract AOP URIs from either selected nodes or all nodes
            const aopUris = getAOPsFromNetwork(hasSelection);
            if (aopUris.length === 0) {
                const scopeMessage = hasSelection ? "selected elements" : "network";
                console.log(`No AOPs found in ${scopeMessage} for compound loading`);
                $("#toggle_compounds").html('<i class="fas fa-flask"></i>  Remove chemical stressors');
                window.compoundsVisible = true;
                return;
            }
            const scopeMessage = hasSelection ? `${window.cy.$(':selected').nodes().length} selected nodes` : "all network nodes";
            console.log(`Found ${aopUris.length} AOPs from ${scopeMessage} for compound loading:`, aopUris);
            // Call the load_and_show_compounds endpoint with the extracted AOPs
            fetch(`/load_and_show_compounds?aops=${encodeURIComponent(aopUris.join(' '))}`, {
                method: 'GET'
            })
                .then(response => {
                    if (!response.ok) {
                        throw new Error(`HTTP ${response.status}: ${response.statusText}`);
                    }
                    return response.json();
                })
                .then(data => {
                    if (data.error) {
                        console.error("Compound loading error:", data.error);
                        showStatus(`Error loading compounds: ${data.error}`, 'error');
                        return;
                    }

                    const fontSlider = document.getElementById('font-size-slider');
                    const fontSizeMultiplier = fontSlider ? parseFloat(fontSlider.value) : 0.5;

                    // Add query to history table
                    if (data.sparql_query && window.historyTableManager) {
                        window.historyTableManager.addHistoryEntry('compound', 'AOP-Wiki RDF', data.sparql_query, null, data.compound_elements);
                    }

                    // Add only new compound elements
                    data.compound_elements.forEach(element => {
                        console.log(element.data);
                        const elementId = element.data?.id;
                        if (elementId && !window.cy.getElementById(elementId).length) {
                            try {
                                window.cy.add(element);
                            } catch (error) {
                                console.warn("Error adding compound element:", elementId, error.message);
                            }
                        }
                    });

                    // Show compounds based on selection
                    if (hasSelection) {
                        // Only show compounds connected to selected nodes
                        const selectedNodes = window.cy.$(':selected').nodes();
                        const compoundNodesToShow = window.cy.collection();
                        selectedNodes.forEach(node => {
                            const connectedCompounds = node.connectedEdges().connectedNodes('.chemical-node');
                            compoundNodesToShow.merge(connectedCompounds);
                        });
                        compoundNodesToShow.show();
                        compoundNodesToShow.connectedEdges().show();
                        console.log(`Showed ${compoundNodesToShow.length} compounds connected to selected nodes`);
                    } else {
                        // Show all compounds
                        window.cy.elements(".chemical-node").show();
                        window.cy.edges().forEach(function (edge) {
                            const source = edge.source();
                            const target = edge.target();
                            const sourceIsCompound = source.hasClass("chemical-node");
                            const targetIsCompound = target.hasClass("chemical-node");
                            if (source.visible() && target.visible() && (sourceIsCompound || targetIsCompound)) {
                                edge.show();
                            }
                        });
                        console.log(`Showed all compound nodes`);
                    }
                    window.resetNetworkLayout();

                    // Update both buttons when showing compounds
                    $("#toggle_compounds").text(" Remove chemical stressors");
                    $("#sidebar_toggle_compounds").text(" Remove chemical stressors");
                    window.compoundsVisible = true;

                    // Update compound table
                    setTimeout(() => {
                        populateCompoundTable();
                    }, 100);

                    // Layout update
                    setTimeout(() => {
                        positionNodes(window.cy, fontSizeMultiplier, true);
                    }, 150);
                })
                .catch(error => {
                    console.error("Error loading compounds:", error);
                    showStatus(`Error loading compounds: ${error.message}`, 'error');
                });
        } else {
            // Remove compound sets
            const hasSelection = window.cy && window.cy.$(':selected').length > 0;
            if (hasSelection) {
                // Hide only compounds connected to selected nodes
                const selectedNodes = window.cy.$(':selected').nodes();
                const compoundsToHide = window.cy.collection();
                selectedNodes.forEach(node => {
                    const connectedCompounds = node.connectedEdges().connectedNodes('.chemical-node');
                    compoundsToHide.merge(connectedCompounds);
                });
                compoundsToHide.remove();
                compoundsToHide.connectedEdges().remove();
                console.log(`Removed ${compoundsToHide.length} compounds connected to selected nodes`);
            } else {
                // Hide all compounds
                const allCompounds = window.cy.elements(".chemical-node");
                allCompounds.remove();
                allCompounds.connectedEdges().remove();

                console.log(`Removed all compound nodes`);
            }

            // Reset layout and update table
            window.resetNetworkLayout();
            window.compoundsVisible = false;
            $("#toggle_compounds").html('<i class="fas fa-flask"></i> Get chemical stressors for the network');
            $("#sidebar_toggle_compounds").html('<i class="fas fa-flask"></i> Get chemical stressors for the network');
            setTimeout(() => {
                populateCompoundTable();
            }, 100);
        }
    }

    function toggleComponents() {
        const action = window.componentsVisible ? 'hide' : 'show';
        if (action === 'show') {
            // Check if there are selected elements
            const hasSelection = window.cy && window.cy.$(':selected').length > 0;
            // Extract Key Event URIs from either selected nodes or all nodes
            const keyEventUris = getKeyEventsFromNetwork(hasSelection);
            if (keyEventUris.length === 0) {
                const scopeMessage = hasSelection ? "selected elements" : "network";
                console.log(`No Key Events found in ${scopeMessage} for component loading`);
                $("#get-components-table-btn").text("Remove components");
                window.componentsVisible = true;
                return;
            }
            const scopeMessage = hasSelection ? `${window.cy.$(':selected').nodes().length} selected nodes` : "all network nodes";
            console.log(`Found ${keyEventUris.length} Key Events from ${scopeMessage} for component loading:`, keyEventUris);
            
            // Call the load_and_show_components endpoint with the extracted KEs
            fetch(`/load_and_show_components?kes=${encodeURIComponent(keyEventUris.join(' '))}`, {
                method: 'GET'
            })
                .then(response => {
                    if (!response.ok) {
                        throw new Error(`HTTP ${response.status}: ${response.statusText}`);
                    }
                    return response.json();
                })
                .then(data => {
                    if (data.error) {
                        console.error("Component loading error:", data.error);
                        showStatus(`Error loading components: ${data.error}`, 'error');
                        return;
                    }

                    const fontSlider = document.getElementById('font-size-slider');
                    const fontSizeMultiplier = fontSlider ? parseFloat(fontSlider.value) : 0.5;

                    // Add query to history table
                    if (data.sparql_query && window.historyTableManager) {
                        window.historyTableManager.addHistoryEntry(
                            'Components Query',
                            'AOP-Wiki SPARQL',
                            data.sparql_query,
                            null,
                            data.component_elements
                        );
                    }

                    // Add component elements to the network
                    if (data.component_elements && data.component_elements.length > 0) {
                        window.cy.batch(() => {
                            data.component_elements.forEach(element => {
                                // Check if element already exists
                                if (!window.cy.getElementById(element.data.id).length) {
                                    window.cy.add(element);
                                }
                            });
                        });

                        console.log(`Added ${data.component_elements.length} component elements to network`);
                        showStatus(`Added ${data.component_elements.length} component elements from ${scopeMessage}`, 'success');
                    }

                    // Show components based on selection
                    if (hasSelection) {
                        // Show only components connected to selected nodes
                        const selectedNodes = window.cy.$(':selected').nodes();
                        const componentNodesToShow = window.cy.collection();
                        selectedNodes.forEach(node => {
                            const connectedComponents = node.connectedEdges().connectedNodes('.process-node, [type="component_process"]');
                            componentNodesToShow.merge(connectedComponents);
                        });
                        componentNodesToShow.show();
                        componentNodesToShow.connectedEdges().show();
                        console.log(`Showed ${componentNodesToShow.length} components connected to selected nodes`);
                    } else {
                        // Show all components
                        window.cy.elements(".process-node, [type='component_process']").show();
                        window.cy.edges().forEach(function (edge) {
                            const source = edge.source();
                            const target = edge.target();
                            const sourceIsComponent = source.hasClass("process-node") || source.data("type") === "component_process";
                            const targetIsComponent = target.hasClass("process-node") || target.data("type") === "component_process";
                            if (source.visible() && target.visible() && (sourceIsComponent || targetIsComponent)) {
                                edge.show();
                            }
                        });
                        console.log(`Showed all component nodes`);
                    }
                    
                    window.resetNetworkLayout();

                    // Update button state
                    $("#get-components-table-btn").text("Remove components");
                    window.componentsVisible = true;

                    // Update component table
                    setTimeout(() => {
                        if (window.componentTableManager && window.componentTableManager.performTableUpdate) {
                            window.componentTableManager.performTableUpdate();
                        }
                    }, 100);

                    // Layout update
                    setTimeout(() => {
                        positionNodes(window.cy, fontSizeMultiplier, true);
                    }, 150);
                })
                .catch(error => {
                    console.error("Error loading components:", error);
                    showStatus(`Error loading components: ${error.message}`, 'error');
                });
        } else {
            // Remove component sets
            const hasSelection = window.cy && window.cy.$(':selected').length > 0;
            if (hasSelection) {
                // Hide only components connected to selected nodes
                const selectedNodes = window.cy.$(':selected').nodes();
                const componentsToHide = window.cy.collection();
                selectedNodes.forEach(node => {
                    const connectedComponents = node.connectedEdges().connectedNodes('.process-node, [type="component_process"]');
                    componentsToHide.merge(connectedComponents);
                });
                componentsToHide.remove();
                componentsToHide.connectedEdges().remove();
                console.log(`Removed ${componentsToHide.length} components connected to selected nodes`);
            } else {
                // Hide all components
                const allComponents = window.cy.elements(".process-node, [type='component_process']");
                allComponents.remove();
                allComponents.connectedEdges().remove();

                console.log(`Removed all component nodes`);
            }

            // Reset layout and update table
            window.resetNetworkLayout();
            window.componentsVisible = false;
            $("#get-components-table-btn").text("Get components");
            setTimeout(() => {
                if (window.componentTableManager && window.componentTableManager.performTableUpdate) {
                    window.componentTableManager.performTableUpdate();
                }
            }, 100);
        }
    }

    // ===== CORE NETWORK FUNCTIONS =====
    function renderAOPNetwork(elements) {
        console.debug("Rendering AOP network with elements:", elements);
        const loadingOverlay = document.querySelector(".loading-overlay");
        if (loadingOverlay) {
            loadingOverlay.style.display = "none";
        }

        // Ensure we have elements to render
        if (!Array.isArray(elements) || elements.length === 0) {
            console.warn("No elements to render in network");
            // Initialize empty network for standalone mode
            initializeEmptyNetwork();
            return;
        }

        // Create Cytoscape instance.
        try {
            window.cy = cytoscape({
                container: document.getElementById("cy"),
                elements: elements.map(ele => ({
                    data: {
                        id: ele.id,
                        ...ele.data
                    }
                })),
                style: [
                    {
                        selector: 'node',
                        style: {
                            'label': 'data(label)',
                            'text-valign': 'center',
                            'text-halign': 'center',
                            'color': 'white',
                            'font-size': '10px',
                            'font-weight': 'bold',
                            'width': 40,
                            'height': 40,
                            'shape': 'circle',
                            'text-wrap': 'wrap',
                            'text-max-width': '30px'
                        }
                    },
                    {
                        selector: '.uniprot-node',
                        style: {
                            'background-color': '#3498DB',
                            'border-color': '#2980B9',
                            'border-width': 2
                        }
                    },
                    {
                        selector: '.ensembl-node',
                        style: {
                            'background-color': '#2ECC71',
                            'border-color': '#27AE60',
                            'border-width': 2
                        }
                    },
                    {
                        selector: '.chemical-node',
                        style: {
                            'background-color': '#E67E22',
                            'border-color': '#D35400',
                            'border-width': 2
                        }
                    },
                    {
                        selector: '.go-process-node',
                        style: {
                            'background-color': '#8E44AD',
                            'border-color': '#6C3483',
                            'border-width': 2,
                            'label': 'data(label)',
                            'text-valign': 'center',
                            'text-halign': 'center',
                            'color': 'white',
                            'font-size': '10px',
                            'font-weight': 'bold',
                            'width': 60,
                            'height': 60,
                            'shape': 'hexagon',
                            'text-wrap': 'wrap',
                            'text-max-width': '50px'
                        }
                    },
                    {
                        selector: 'edge',
                        style: {
                            'width': 2,
                            'opacity': 0.7
                        }
                    },
                    {
                        selector: 'edge[type="aop_relationship"]',
                        style: {
                            'line-color': '#3498DB',
                            'target-arrow-color': '#3498DB',
                            'target-arrow-shape': 'triangle',
                            'curve-style': 'bezier',
                            'arrow-scale': 1.2
                        }
                    },
                    {
                        selector: 'edge[type="go_hierarchy"]',
                        style: {
                            'line-color': '#8E44AD',
                            'target-arrow-color': '#8E44AD',
                            'target-arrow-shape': 'triangle',
                            'curve-style': 'bezier',
                            'arrow-scale': 1.2,
                            'width': 2,
                            'opacity': 0.7
                        }
                    }
                ]
            });
            console.debug("Cytoscape instance created with elements:", window.cy.elements());

            // Initialize positioning with correct font size from slider
            if (window.positionNodes) {
                const fontSlider = document.getElementById('font-size-slider');
                const fontSizeMultiplier = fontSlider ? parseFloat(fontSlider.value) : 0.5; // Use 0.5 as default to match HTML
                window.positionNodes(window.cy, fontSizeMultiplier);
            }

            setupEventHandlers();
            initializeModules();
        } catch (error) {
            console.error("Error creating Cytoscape instance:", error);
            initializeEmptyNetwork();
        }
    }

    function initializeEmptyNetwork() {
        console.log("Initializing empty network for standalone mode");
        try {
            window.cy = cytoscape({
                container: document.getElementById("cy"),
                elements: [],
            });

            if (window.positionNodes) {
                const fontSlider = document.getElementById('font-size-slider');
                const fontSizeMultiplier = fontSlider ? parseFloat(fontSlider.value) : 0.5; // Use 0.5 as default to match HTML
                window.positionNodes(window.cy, fontSizeMultiplier);
            }

            setupEventHandlers();
            initializeModules();
            // Show helpful message for standalone mode
            const loadingOverlay = document.querySelector(".loading-overlay");
            if (loadingOverlay) {
                loadingOverlay.innerHTML = `
                    <div class="text-center">
                        <img width="100px" alt="icon" src="/static/images/aopapp_favicon.ico"/>
                        <h4>AOP Network Builder</h4>
                        <p>Start building your network by:</p>
                        <ul style="text-align: left; display: inline-block;">
                            <li>Adding nodes and edges manually</li>
                            <li>Querying the AOP wiki for Key Events, AOPs, Compounds and Genes</li>
                        </ul>
                        <p>Enhance your network by:</p>
                        <ul style="text-align: left; display: inline-block;">
                            <li>Querying OpenTargets for Compound data</li>
                            <li>Querying Bgee for organ-specific gene expression data</li>
                            <li>Adding your own data tables as weights for the nodes (Work in progress).</li>
                        </ul>
                    </div>
                `;
                loadingOverlay.style.display = "flex";
                loadingOverlay.style.flexDirection = "column";
                loadingOverlay.style.justifyContent = "center";
            }
        } catch (error) {
            console.error("Error creating empty Cytoscape instance:", error);
        }
    }

    function initializeModules() {
        setTimeout(() => {
            // Initialize manual controls
            if (window.initializeManualControls) {
                window.initializeManualControls();
            }

            // Initialize AOP network data manager
            if (window.initializeAOPNetworkData) {
                window.initializeAOPNetworkData();
            }

            // Setup network change tracking
            if (window.setupNetworkChangeTracking) {
                window.setupNetworkChangeTracking();
            }

            // Setup default gene table button handler
            $("#get-genes-table-btn").on("click", function(e) {
                e.preventDefault();
                e.stopPropagation();
                if (window.toggleGenes) {
                    window.toggleGenes();
                }
            });

            // Trigger immediate AOP table population after modules are initialized
            setTimeout(() => {
                console.log("Modules initialized - triggering AOP table population");
                if (window.populateAopTable) {
                    window.populateAopTable(true); // true = immediate
                }
            }, 500);
        }, 200);
    }

    function setupEventHandlers() {
        // Initialize selection functionality
        initializeNetworkSelection();

        // Ensure selection controls are created
        setTimeout(() => {
            updateSelectionControls();
        }, 100);

        // Network change listeners for automatic table updates with smooth animations
        window.cy.on("add", "node", function (evt) {
            const node = evt.target;
            console.debug(`Node added: ${node.id()}`);
            // Auto-update tables based on node type
            autoUpdateTables(node, 'added');
            // Always use smooth animation when nodes are added
            const fontSlider = document.getElementById('font-size-slider');
            const fontSizeMultiplier = fontSlider ? parseFloat(fontSlider.value) : 0.5;

            // Small delay to allow the addition to complete, then animate
            setTimeout(() => {
                positionNodes(window.cy, fontSizeMultiplier, true);
            }, 50);
        });

        window.cy.on("remove", "node", function (evt) {
            const node = evt.target;
            console.debug(`Node removed: ${node.id()}`);

            // Auto-update tables based on node type
            autoUpdateTables(node, 'removed');
            // Always use smooth animation when nodes are removed
            const fontSlider = document.getElementById('font-size-slider');
            const fontSizeMultiplier = fontSlider ? parseFloat(fontSlider.value) : 0.5;
            // Small delay to allow the removal to complete, then animate
            setTimeout(() => {
                positionNodes(window.cy, fontSizeMultiplier, true);
            }, 50);
        });

        window.cy.on("add", "edge", function (evt) {
            const edge = evt.target;
            console.debug(`Edge added: ${edge.id()}`);
            // Use debounced update for edge additions
            if (window.populateAopTable) {
                window.populateAopTable(false); // false = debounced
            }

            // Smooth animation for edge additions
            const fontSlider = document.getElementById('font-size-slider');
            const fontSizeMultiplier = fontSlider ? parseFloat(fontSlider.value) : 0.5;
            setTimeout(() => {
                positionNodes(window.cy, fontSizeMultiplier, true);
            }, 50);
        });

        window.cy.on("remove", "edge", function (evt) {
            const edge = evt.target;
            console.debug(`Edge removed: ${edge.id()}`);

            // Use debounced update for edge removals
            if (window.populateAopTable) {
                window.populateAopTable(false); // false = debounced
            }
            // Smooth animation for edge removals
            const fontSlider = document.getElementById('font-size-slider');
            const fontSizeMultiplier = fontSlider ? parseFloat(fontSlider.value) : 0.5;
            setTimeout(() => {
                positionNodes(window.cy, fontSizeMultiplier, true);
            }, 50);
        });

        window.cy.on("data", "node", function (evt) {
            const node = evt.target;
            console.debug(`Node data changed: ${node.id()}`);
            // Auto-update tables based on node type
            autoUpdateTables(node, 'updated');
            // Smooth animation for data changes that might affect layout
            const fontSlider = document.getElementById('font-size-slider');
            const fontSizeMultiplier = fontSlider ? parseFloat(fontSlider.value) : 0.5;
            setTimeout(() => {
                positionNodes(window.cy, fontSizeMultiplier, true);
            }, 50);
        });

        // Add batch operation handler for multiple simultaneous changes
        window.cy.on("batch", function (evt) {
            console.debug("Batch operation completed");
            if (window.populateAopTable) {
                window.populateAopTable(false); // false = debounced
            }
            // Smooth animation after batch operations
            const fontSlider = document.getElementById('font-size-slider');
            const fontSizeMultiplier = fontSlider ? parseFloat(fontSlider.value) : 0.5;
            setTimeout(() => {
                positionNodes(window.cy, fontSizeMultiplier, true);
            }, 100);
        });

        // Button event handlers
        setupButtonHandlers();
    }

    // Initialize network selection functionality
    function initializeNetworkSelection() {
        if (!window.cy) return;

        // Add styles for selected elements
        addSelectionStyles();

        // Enable box selection for multi-select
        window.cy.boxSelectionEnabled(true);

        // Remove any existing tap handlers to prevent URL navigation
        window.cy.removeListener('tap');

        // Handle single click selection
        window.cy.on('tap', function (evt) {
            const target = evt.target;
            // If clicking on background, clear selection unless shift is held
            if (target === window.cy) {
                if (!evt.originalEvent.shiftKey) {
                    window.cy.$(':selected').unselect();
                }
                return;
            }

            // Handle node/edge selection
            if (target.isNode() || target.isEdge()) {
                evt.stopPropagation();
                evt.preventDefault(); // Prevent any default URL navigation
                if (evt.originalEvent.shiftKey) {
                    // Shift+click: toggle selection
                    if (target.selected()) {
                        target.unselect();
                    } else {
                        target.select();
                    }
                } else {
                    // Regular click: select only this element
                    window.cy.$(':selected').unselect();
                    target.select();
                }
            }
        });

        // Update selection controls when selection changes
        window.cy.on('select unselect', function () {
            updateSelectionControls();
        });

        // Prevent default href behavior on nodes/edges
        window.cy.on('tap', 'node, edge', function (evt) {
            evt.preventDefault();
            evt.stopPropagation();
        });
    }

    function addSelectionStyles() {
        // Add CSS styles for element selection highlighting
        if (!document.querySelector('#element-selection-styles')) {
            const styles = document.createElement('style');
            styles.id = 'element-selection-styles';
            styles.textContent = `
                /* Cytoscape selection styles are handled via the Cytoscape style sheet */
            `;
            document.head.appendChild(styles);
        }

        // Add Cytoscape-specific selection styles
        if (window.cy) {
            window.cy.style()
                .selector('.element-selected')
                .style({
                    'border-width': '4px',
                    'border-color': '#ff6b35',
                    'border-opacity': 1,
                    'overlay-color': '#ff6b35',
                    'overlay-opacity': 0.3,
                    'overlay-padding': '4px'
                })
                .selector('edge.element-selected')
                .style({
                    'line-color': '#ff6b35',
                    'target-arrow-color': '#ff6b35',
                    'source-arrow-color': '#ff6b35',
                    'width': '4px',
                    'opacity': 1
                })
                .update();
        }
    }

    // Selection management functions
    function updateSelectionControls() {
        const selectionControls = document.getElementById('selection-controls');
        const selectionInfo = document.getElementById('selection-info');
        if (!selectionControls || !selectionInfo) {
            // Create selection controls if they don't exist
            createSelectionControls();
            return;
        }

        if (window.cy) {
            const selected = window.cy.$(':selected');
            const tableSelected = window.aopTableManager ? window.aopTableManager.selectedRows.size : 0;
            if (selected.length > 0 || tableSelected > 0) {
                selectionControls.style.display = 'flex';
                selectionControls.style.visibility = 'visible';
                if (tableSelected > 0) {
                    selectionInfo.textContent = `${selected.length} network, ${tableSelected} table rows selected`;
                } else {
                    selectionInfo.textContent = `${selected.length} selected`;
                }
                // Add visual highlighting to selected network elements
                highlightSelectedElements(selected);
            } else {
                selectionControls.style.display = 'none';
                // Remove highlighting when nothing is selected
                clearElementHighlighting();
            }
        }
    }

    function createSelectionControls() {
        // Check if selection controls already exist
        if (document.getElementById('selection-controls')) return;

        // Find a suitable container or create one
        let container = document.querySelector('.main-content') || document.querySelector('#cy').parentElement;
        const selectionControlsHtml = `
            <div id="selection-controls" style="
                position: fixed;
                top: 10px;
                right: 10px;
                background: rgba(255, 255, 255, 0.95);
                border: 1px solid #ddd;
                border-radius: 8px;
                padding: 10px;
                box-shadow: 0 2px 10px rgba(0,0,0,0.1);
                z-index: 1000;
                display: none;
                align-items: center;
                gap: 10px;
                font-size: 14px;
            ">
                <span id="selection-info" style="margin-right: 10px; font-weight: 500; color: #333;"></span>
                <button id="delete_selected" class="btn btn-sm btn-danger" style="
                    background-color: #dc3545;
                    border-color: #dc3545;
                    color: white;
                    padding: 4px 8px;
                    border-radius: 4px;
                    border: none;
                    cursor: pointer;
                ">
                    <i class="fas fa-trash"></i> Delete
                </button>
                <button id="clear_selection" class="btn btn-sm btn-secondary" style="
                    background-color: #6c757d;
                    border-color: #6c757d;
                    color: white;
                    padding: 4px 8px;
                    border-radius: 4px;
                    border: none;
                    cursor: pointer;
                ">
                    <i class="fas fa-times"></i> Clear
                </button>
            </div>
        `;
        container.insertAdjacentHTML('beforeend', selectionControlsHtml);
        console.log('Selection controls created');
    }

    function highlightSelectedElements(selected) {
        if (!window.cy) return;

        // Remove previous highlights
        window.cy.elements().removeClass('element-selected');

        // Add highlight class to selected elements
        selected.addClass('element-selected');

        console.log(`Highlighted ${selected.length} selected elements`);
    }

    function clearElementHighlighting() {
        if (!window.cy) return;

        window.cy.elements().removeClass('element-selected');
    }

    function deleteSelectedElements() {
        if (!window.cy) return;

        const selected = window.cy.$(':selected');
        const tableSelected = window.aopTableManager ? window.aopTableManager.selectedRows.size : 0;

        if (selected.length === 0 && tableSelected === 0) {
            console.log("No elements selected for deletion");
            return;
        }

        // Store element data for table updates
        const deletedNodes = selected.nodes().map(node => ({
            id: node.id(),
            data: node.data(),
            classes: node.classes()
        }));
        const deletedEdges = selected.edges().map(edge => ({
            id: edge.id(),
            data: edge.data()
        }));

        // Remove elements from the network
        window.cy.batch(() => {
            selected.remove();
        });

        // Clear table selection after deletion
        if (window.aopTableManager) {
            window.aopTableManager.clearTableSelection();
        }

        // Update tables based on deleted elements
        updateTablesAfterDeletion(deletedNodes, deletedEdges);

        // Update selection controls
        updateSelectionControls();

        // Trigger layout update with smooth animation
        setTimeout(() => {
            const fontSlider = document.getElementById('font-size-slider');
            const fontSizeMultiplier = fontSlider ? parseFloat(fontSlider.value) : 0.5;
            if (window.positionNodes) {
                window.positionNodes(window.cy, fontSizeMultiplier, true);
            }
        }, 50);

        console.log(`Deleted ${selected.length} elements from network`);
    }

    function clearSelection() {
        if (window.cy) {
            window.cy.$(':selected').unselect();
            // Also clear table selection
            if (window.aopTableManager) {
                window.aopTableManager.clearTableSelection();
            }
            updateSelectionControls();
        }
    }

    function updateTablesAfterDeletion(deletedNodes, deletedEdges) {
        // Update compound table if compounds were deleted
        const deletedCompounds = deletedNodes.filter(node =>
            node.classes.includes("chemical-node") ||
            node.data.type === "chemical"
        );
        if (deletedCompounds.length > 0) {
            console.log(`Updating compound table after deleting ${deletedCompounds.length} compounds`);
            // Remove from compound_data if it exists
            deletedCompounds.forEach(compound => {
                if (window.compound_data && window.compound_data[compound.id]) {
                    delete window.compound_data[compound.id];
                }
            });
            // Update compound table
            setTimeout(() => {
                populateCompoundTable();
            }, 100);
        }

        // Update gene table if genes were deleted
        const deletedGenes = deletedNodes.filter(node =>
            node.classes.includes("uniprot-node") ||
            node.classes.includes("ensembl-node") ||
            node.data.type === "uniprot" ||
            node.data.type === "ensembl"
        );
        if (deletedGenes.length > 0) {
            console.log(`Updating gene table after deleting ${deletedGenes.length} genes`);
            setTimeout(() => {
                window.populateGeneTable();
            }, 100);
        }

        // Update AOP table for any network changes
        console.log("Updating AOP table after element deletion");
        setTimeout(() => {
            if (window.populateAopTable) {
                window.populateAopTable(false); // debounced update
            }
        }, 100);
    }

    // New function to automatically update tables based on network changes
    function autoUpdateTables(node, action) {
        const nodeData = node.data();
        const nodeClasses = node.classes();
        const nodeType = nodeData.type;
        const nodeId = nodeData.id;

        console.log(`Network change detected: ${action} - ${nodeId}`);
        // Check if it's a gene node (Ensembl)
        if (nodeClasses.includes("ensembl-node") ||
            nodeType === "ensembl" ||
            nodeId.startsWith("ensembl_")) {
            console.log(`Gene node ${action}: ${nodeData.label || nodeId}`);
            populateGeneTable();
        }

        // Check if it's a compound node (Chemical)
        if (nodeClasses.includes("chemical-node") ||
            nodeType === "chemical") {
            console.log(`Compound node ${action}: ${nodeData.label || nodeId}`);
            populateCompoundTable();
        }

        // Use debounced AOP table update for network changes
        console.log("Triggering debounced AOP table update");
        if (window.populateAopTable) {
            window.populateAopTable(false); // false = use debounced version
        } else {
            console.error("populateAopTable function not available");
        }
    }

    function setupButtonHandlers() {
        // Remove any existing event handlers first to prevent multiple bindings
        $("#toggle_bounding_boxes").off("click");
        $("#toggle_compounds").off("click");
        $("#sidebar_toggle_compounds").off("click");
        $("#see_genes").off("click");
        $("#reset_layout").off("click");
        $("#download_network").off("click");
        $("#toggle_go_processes").off("click");
        $("#show_go_hierarchy").off("click");

        // Selection control handlers
        $(document).on('click', '#delete_selected', function (e) {
            e.preventDefault();
            e.stopPropagation();
            deleteSelectedElements();
        });

        $(document).on('click', '#clear_selection', function (e) {
            e.preventDefault();
            e.stopPropagation();
            clearSelection();
        });

        // Keyboard shortcuts
        $(document).on('keydown', function (e) {
            // Only process shortcuts if we're not in an input field
            if (e.target.tagName === 'INPUT' || e.target.tagName === 'TEXTAREA') {
                return;
            }

            // Delete key to remove selected elements
            if (e.key === 'Delete' || e.key === 'Backspace') {
                e.preventDefault();
                deleteSelectedElements();
            }

            // Escape key to clear selection
            if (e.key === 'Escape') {
                e.preventDefault();
                clearSelection();
            }

            // Ctrl+A to select all
            if (e.ctrlKey && e.key === 'a') {
                e.preventDefault();
                if (window.cy) {
                    window.cy.elements().select();
                }
            }
        });

        // Group by AOP
        $("#toggle_bounding_boxes").on("click", function (e) {
            e.preventDefault();
            e.stopPropagation();
            console.log('Group by AOP button clicked');
            if (window.aopTableManager) {
                window.aopTableManager.groupByAllAops();
                // Ensure network layout is updated after grouping
                setTimeout(() => {
                    const fontSlider = document.getElementById('font-size-slider');
                    const fontSizeMultiplier = fontSlider ? parseFloat(fontSlider.value) : 0.5;
                    if (window.positionNodes) {
                        window.positionNodes(window.cy, fontSizeMultiplier, true);
                    }
                }, 100);
            } else {
                console.error('AOP Table Manager not available');
            }
        });

        // Toggle compounds
        $("#toggle_compounds").on("click", function (e) {
            e.preventDefault();
            e.stopPropagation();
            if (window.toggleCompounds) {
                window.toggleCompounds();
            }
        });

        // Toggle compounds (sidebar button)
        $("#sidebar_toggle_compounds").on("click", function (e) {
            e.preventDefault();
            e.stopPropagation();
            if (window.toggleCompounds) {
                window.toggleCompounds();
            }
        });
                
        // Setup compound table button handler
        $("#get-compounds-table-btn").on("click", function (e) {
            e.preventDefault();
            e.stopPropagation();
            if (window.toggleCompounds) {
                window.toggleCompounds();
            }
        });

        // Toggle genes
        $("#see_genes").on("click", function (e) {
            e.preventDefault();
            e.stopPropagation();
            toggleGenes();
        });
        $('#get-genes-table-btn').on('click', function (e) {
            e.preventDefault();
            e.stopPropagation();
            toggleGenes();
        });

        // Reset layout with smooth animation
        $("#reset_layout").on("click", function (e) {
            e.preventDefault();
            e.stopPropagation();
            resetNetworkLayout();
        });

        // Download network
        $("#download_network").on("click", function (e) {
            e.preventDefault();
            e.stopPropagation();
            downloadNetwork();
        });

        // Toggle GO processes
        $("#toggle_go_processes").on("click", function (e) {
            e.preventDefault();
            e.stopPropagation();
            toggleGOProcesses();
        });
        $("#show_go_hierarchy").on("click", function (e) {
            e.preventDefault();
            e.stopPropagation();
            showGOProcessHierarchy();
        });

        // OpenTargets dropdown handlers
        $("#opentargets_query_compounds").on("click", function (e) {
            e.preventDefault();
            e.stopPropagation();
            queryOpenTargetsCompounds();
        });
        $("#opentargets_query_targets").on("click", function (e) {
            e.preventDefault();
            e.stopPropagation();
            queryOpenTargetsTargets();
        });
        $("#opentargets_query_diseases").on("click", function (e) {
            e.preventDefault();
            e.stopPropagation();
            queryOpenTargetsDiseases();
        });

        // Bgee dropdown handlers
        $("#bgee_query_expression").on("click", function (e) {
            e.preventDefault();
            e.stopPropagation();
            queryBgeeExpression();
        });

        $("#bgee_query_developmental").on("click", function (e) {
            e.preventDefault();
            e.stopPropagation();
            queryBgeeDevelopmental();
        });

        $("#bgee_query_anatomical").on("click", function (e) {
            e.preventDefault();
            e.stopPropagation();
            queryBgeeAnatomical();
        });

        // Setup component table button handler
        $("#get-components-table-btn").on("click", function (e) {
            e.preventDefault();
            e.stopPropagation();
            if (window.toggleComponents) {
                window.toggleComponents();
            }
        });
    }

    // Enhanced function to handle sidebar toggles with smooth transitions
    function toggleSidebar(sidebarId) {
        const sidebar = document.getElementById(sidebarId);
        if (!sidebar) return;

        sidebar.classList.toggle('collapsed');

        // Trigger resize event for Cytoscape to adjust with smooth animation
        setTimeout(() => {
            if (window.cy) {
                // Resize first
                window.cy.resize();
                // Then apply layout with animation
                setTimeout(() => {
                    const fontSlider = document.getElementById('font-size-slider');
                    const fontSizeMultiplier = fontSlider ? parseFloat(fontSlider.value) : 0.5; // Use 0.5 as default
                    // Use animated positioning
                    if (window.positionNodes) {
                        window.positionNodes(window.cy, fontSizeMultiplier, true);
                    }
                }, 50);
            }
        }, 300); // Match the CSS transition duration
    }

    // ===== LAYOUT AND DOWNLOAD FUNCTIONS =====
    function toggleBoundingBoxes() {
        // Legacy function - now redirects to table manager
        if (window.aopTableManager) {
            window.aopTableManager.groupByAllAops();
        } else {
            console.error('AOP Table Manager not available for bounding boxes');
        }
    }

    function downloadNetwork() {
        const cyJson = window.cy.json();
        const blob = new Blob([JSON.stringify(cyJson)], { type: "application/json" });
        const url = URL.createObjectURL(blob);
        const a = document.createElement("a");
        a.href = url;
        a.download = "cytoscape_network.json";
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        URL.revokeObjectURL(url);
    }

    // New function to reset network layout with smooth animation
    function resetNetworkLayout() {
        if (!window.cy) {
            console.warn("Cytoscape not available for layout reset");
            return;
        }

        // Get current font size multiplier with correct default
        const fontSlider = document.getElementById('font-size-slider');
        const fontSizeMultiplier = fontSlider ? parseFloat(fontSlider.value) : 0.5; // Use 0.5 as default

        // Trigger resize first (like sidebar animations do)
        window.cy.resize();

        // Add a slight delay to allow resize to complete, then animate layout
        setTimeout(() => {
            // Use the animated layout approach
            const layout = window.cy.layout({
                name: 'breadthfirst',
                directed: true,
                padding: 30,
                animate: true,
                animationDuration: 500,
                animationEasing: 'ease-out',
                fit: true
            });

            // Run the layout
            layout.run();

            // After layout animation completes, apply styles smoothly
            layout.one('layoutstop', function () {
                // Apply styles with updated font size and smooth transitions
                if (window.positionNodes) {
                    window.positionNodes(window.cy, fontSizeMultiplier, true);
                }
            });
        }, 100);
    }

    // ===== GLOBAL FUNCTION EXPORTS =====

    // Make functions available globally
    window.toggleSidebar = toggleSidebar;
    window.toggleCompounds = toggleCompounds;
    window.toggleGenes = toggleGenes;
    window.toggleComponents = toggleComponents;
    window.downloadNetwork = downloadNetwork;
    window.resetNetworkLayout = resetNetworkLayout;
    window.populateaopTable = populateaopTable;

    // ===== GO PROCESS FUNCTIONS =====

    function toggleGOProcesses() {
        if (!window.cy) {
            console.warn("Cytoscape not available");
            showGOProcessStatus("Network not initialized", "error");
            return;
        }

        const currentElements = window.cy.elements().jsons();
        const params = new URLSearchParams({
            cy_elements: JSON.stringify(currentElements),
            include_hierarchy: 'false'
        });

        showGOProcessStatus("Fetching GO processes...", "loading");

        fetch(`/get_go_processes?${params}`)
            .then(response => response.json())
            .then(data => {
                if (data.error) {
                    showGOProcessStatus(`Error: ${data.error}`, "error");
                    return;
                }

                if (!data.processes || data.processes.length === 0) {
                    showGOProcessStatus(data.message || "No GO processes found for current Key Events", "warning");
                    return;
                }

                data.processes.forEach(process => {
                    if (!window.cy.getElementById(process.id).length) {
                        window.cy.add({
                            data: {
                                id: process.id,
                                label: process.label,
                                uri: process.uri,
                                type: 'go_process'
                            },
                            classes: 'go-process-node'
                        });
                    }
                });

                window.cy.elements(".go-process-node").show();
                window.goProcessesVisible = true;
                $("#toggle_go_processes").text("Hide GO Processes");

                showGOProcessStatus(`Added ${data.processes.length} GO processes to network`, "success");
                if (window.positionNodes) {
                    window.positionNodes(window.cy);
                }
            })
            .catch(error => {
                console.error("Error:", error);
                showGOProcessStatus("Error fetching GO processes", "error");
            });
    }

    function showGOProcessHierarchy() {
        if (!window.cy) {
            console.warn("Cytoscape not available");
            showGOProcessStatus("Network not initialized", "error");
            return;
        }

        const currentElements = window.cy.elements().jsons();
        const params = new URLSearchParams({
            cy_elements: JSON.stringify(currentElements),
            include_hierarchy: 'true'
        });

        showGOProcessStatus("Fetching GO process hierarchy...", "loading");

        fetch(`/get_go_processes?${params}`)
            .then(response => response.json())
            .then(data => {
                if (data.error) {
                    showGOProcessStatus(`Error: ${data.error}`, "error");
                    return;
                }
                const nodes = data.processes.nodes || data.processes;
                const edges = data.processes.edges || [];
                if (!nodes || nodes.length === 0) {
                    showGOProcessStatus("No GO process hierarchy found for current Key Events", "warning");
                    return;
                }

                nodes.forEach(process => {
                    if (!window.cy.getElementById(process.id).length) {
                        window.cy.add({
                            data: {
                                id: process.id,
                                label: process.label,
                                uri: process.uri,
                                type: 'go_process'
                            },
                            classes: 'go-process-node'
                        });
                    }
                });

                edges.forEach(edge => {
                    if (!window.cy.getElementById(edge.id).length) {
                        window.cy.add({
                            data: {
                                id: edge.id,
                                source: edge.source,
                                target: edge.target,
                                type: edge.type,
                                label: edge.label
                            }
                        });
                    }
                });

                window.cy.elements(".go-process-node").show();
                window.cy.edges('[type="go_hierarchy"]').show();
                window.goProcessesVisible = true;
                $("#toggle_go_processes").text("Hide GO Processes");

                showGOProcessStatus(`Added ${nodes.length} GO processes and ${edges.length} hierarchy relationships`, "success");
                if (window.positionNodes) {
                    window.positionNodes(window.cy);
                }
            })
            .catch(error => {
                console.error("Error:", error);
                showGOProcessStatus("Error fetching GO process hierarchy", "error");
            });
    }

    function showGOProcessStatus(message, type = 'info') {
        const statusDiv = document.getElementById('go-processes-status');
        if (!statusDiv) return;

        const icons = {
            'loading': 'fas fa-spinner fa-spin',
            'success': 'fas fa-check',
            'error': 'fas fa-exclamation-triangle',
            'warning': 'fas fa-exclamation-circle',
            'info': 'fas fa-info-circle'
        };

        const colors = {
            'loading': '#6c757d',
            'success': '#28a745',
            'error': '#dc3545',
            'warning': '#ffc107',
            'info': '#17a2b8'
        };

        statusDiv.innerHTML = `
            <div style="color: ${colors[type]}; font-size: 0.8rem; margin-top: 0.5rem;">
                <i class="${icons[type]}"></i> ${message}
            </div>
        `;

        // Auto-clear success/info messages after 5 seconds
        if (type === 'success' || type === 'info') {
            setTimeout(() => {
                if (statusDiv.innerHTML.includes(message)) {
                    statusDiv.innerHTML = '';
                }
            }, 5000);
        }
    }

    // ===== OPENTARGETS FUNCTIONS =====

    function queryOpenTargetsCompounds() {
        if (!window.cy) {
            showOpenTargetsStatus("Network not initialized", "error");
            return;
        }

        const currentElements = window.cy.elements().jsons();
        showOpenTargetsStatus("Querying OpenTargets for compound data...", "loading");

        fetch('/query_opentargets_compounds', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ cy_elements: currentElements })
        })
            .then(response => response.json())
            .then(data => {
                if (data.error) {
                    showOpenTargetsStatus(`Error: ${data.error}`, "error");
                    return;
                }

                if (data.compounds && data.compounds.length > 0) {
                    // Add compound nodes to network
                    data.compounds.forEach(compound => {
                        if (!window.cy.getElementById(compound.id).length) {
                            window.cy.add({
                                data: {
                                    id: compound.id,
                                    label: compound.label,
                                    type: 'chemical',
                                    smiles: compound.smiles,
                                    chembl_id: compound.chembl_id,
                                    targets: compound.targets
                                },
                                classes: 'chemical-node opentargets-compound'
                            });
                        }
                    });

                    // Add target relationships if available
                    if (data.relationships) {
                        data.relationships.forEach(rel => {
                            if (!window.cy.getElementById(rel.id).length) {
                                window.cy.add({
                                    data: {
                                        id: rel.id,
                                        source: rel.source,
                                        target: rel.target,
                                        type: 'compound_target',
                                        confidence: rel.confidence
                                    }
                                });
                            }
                        });
                    }

                    showOpenTargetsStatus(`Added ${data.compounds.length} compounds from OpenTargets`, "success");
                    if (window.positionNodes) {
                        window.positionNodes(window.cy);
                    }

                    // Update compound table
                    setTimeout(() => {
                        populateCompoundTable();
                    }, 200);
                } else {
                    showOpenTargetsStatus("No compound data found in OpenTargets", "warning");
                }
            })
            .catch(error => {
                console.error("Error querying OpenTargets compounds:", error);
                showOpenTargetsStatus("Error querying OpenTargets compounds", "error");
            });
    }

    function queryOpenTargetsTargets() {
        if (!window.cy) {
            showOpenTargetsStatus("Network not initialized", "error");
            return;
        }

        const currentElements = window.cy.elements().jsons();
        showOpenTargetsStatus("Querying OpenTargets for target data...", "loading");

        fetch('/query_opentargets_targets', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ cy_elements: currentElements })
        })
            .then(response => response.json())
            .then(data => {
                if (data.error) {
                    showOpenTargetsStatus(`Error: ${data.error}`, "error");
                    return;
                }

                if (data.targets && data.targets.length > 0) {
                    data.targets.forEach(target => {
                        if (!window.cy.getElementById(target.id).length) {
                            window.cy.add({
                                data: {
                                    id: target.id,
                                    label: target.label,
                                    type: 'protein',
                                    uniprot_id: target.uniprot_id,
                                    ensembl_id: target.ensembl_id,
                                    target_class: target.target_class
                                },
                                classes: 'uniprot-node opentargets-target'
                            });
                        }
                    });

                    showOpenTargetsStatus(`Added ${data.targets.length} targets from OpenTargets`, "success");
                    if (window.positionNodes) {
                        window.positionNodes(window.cy);
                    }

                    // Update gene table
                    setTimeout(() => {
                        populateGeneTable();
                    }, 200);
                } else {
                    showOpenTargetsStatus("No target data found in OpenTargets", "warning");
                }
            })
            .catch(error => {
                console.error("Error querying OpenTargets targets:", error);
                showOpenTargetsStatus("Error querying OpenTargets targets", "error");
            });
    }

    function queryOpenTargetsDiseases() {
        if (!window.cy) {
            showOpenTargetsStatus("Network not initialized", "error");
            return;
        }

        const currentElements = window.cy.elements().jsons();
        showOpenTargetsStatus("Querying OpenTargets for disease associations...", "loading");

        fetch('/query_opentargets_diseases', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ cy_elements: currentElements })
        })
            .then(response => response.json())
            .then(data => {
                if (data.error) {
                    showOpenTargetsStatus(`Error: ${data.error}`, "error");
                    return;
                }

                if (data.associations && data.associations.length > 0) {
                    // Add disease associations as edges or annotations
                    data.associations.forEach(assoc => {
                        // Update existing nodes with disease information
                        const targetNode = window.cy.getElementById(assoc.target_id);
                        if (targetNode.length > 0) {
                            const currentDiseases = targetNode.data('diseases') || [];
                            currentDiseases.push({
                                disease_id: assoc.disease_id,
                                disease_name: assoc.disease_name,
                                score: assoc.score
                            });
                            targetNode.data('diseases', currentDiseases);
                        }
                    });

                    showOpenTargetsStatus(`Added disease associations for ${data.associations.length} targets`, "success");
                } else {
                    showOpenTargetsStatus("No disease associations found in OpenTargets", "warning");
                }
            })
            .catch(error => {
                console.error("Error querying OpenTargets diseases:", error);
                showOpenTargetsStatus("Error querying OpenTargets diseases", "error");
            });
    }

    function showOpenTargetsStatus(message, type = 'info') {
        const statusDiv = document.getElementById('opentargets-status');
        if (!statusDiv) return;

        const icons = {
            'loading': 'fas fa-spinner fa-spin',
            'success': 'fas fa-check',
            'error': 'fas fa-exclamation-triangle',
            'warning': 'fas fa-exclamation-circle',
            'info': 'fas fa-info-circle'
        };

        const colors = {
            'loading': '#6c757d',
            'success': '#28a745',
            'error': '#dc3545',
            'warning': '#ffc107',
            'info': '#17a2b8'
        };

        statusDiv.innerHTML = `
            <div style="color: ${colors[type]}; font-size: 0.8rem; margin-top: 0.5rem;">
                <i class="${icons[type]}"></i> ${message}
            </div>
        `;

        // Auto-clear success/info messages after 5 seconds
        if (type === 'success' || type === 'info') {
            setTimeout(() => {
                if (statusDiv.innerHTML.includes(message)) {
                    statusDiv.innerHTML = '';
                }
            }, 5000);
        }
    }

    // ===== BGEE FUNCTIONS =====

    function queryBgeeExpression() {
        if (!window.cy) {
            showBgeeStatus("Network not initialized", "error");
            return;
        }

        const currentElements = window.cy.elements().jsons();
        showBgeeStatus("Querying Bgee for gene expression data...", "loading");

        fetch('/query_bgee_expression', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ cy_elements: currentElements })
        })
            .then(response => response.json())
            .then(data => {
                if (data.error) {
                    showBgeeStatus(`Error: ${data.error}`, "error");
                    return;
                }

                if (data.expression_data && data.expression_data.length > 0) {
                    // Update existing gene nodes with expression data
                    data.expression_data.forEach(expr => {
                        const geneNode = window.cy.getElementById(expr.gene_id);
                        if (geneNode.length > 0) {
                            geneNode.data('expression_level', expr.expression_level);
                            geneNode.data('anatomical_entity', expr.anatomical_entity);
                            geneNode.data('developmental_stage', expr.developmental_stage);
                            geneNode.data('expression_score', expr.expression_score);
                        }
                    });

                    showBgeeStatus(`Updated ${data.expression_data.length} genes with Bgee expression data`, "success");

                    // Update gene table to show new expression data
                    setTimeout(() => {
                        populateGeneTable();
                    }, 200);
                } else {
                    showBgeeStatus("No expression data found in Bgee", "warning");
                }
            })
            .catch(error => {
                console.error("Error querying Bgee expression:", error);
                showBgeeStatus("Error querying Bgee expression data", "error");
            });
    }

    function queryBgeeDevelopmental() {
        if (!window.cy) {
            showBgeeStatus("Network not initialized", "error");
            return;
        }

        const currentElements = window.cy.elements().jsons();
        showBgeeStatus("Querying Bgee for developmental stage data...", "loading");

        fetch('/query_bgee_developmental', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ cy_elements: currentElements })
        })
            .then(response => response.json())
            .then(data => {
                if (data.error) {
                    showBgeeStatus(`Error: ${data.error}`, "error");
                    return;
                }

                if (data.developmental_data && data.developmental_data.length > 0) {
                    // Update existing gene nodes with developmental data
                    data.developmental_data.forEach(dev => {
                        const geneNode = window.cy.getElementById(dev.gene_id);
                        if (geneNode.length > 0) {
                            const currentStages = geneNode.data('developmental_stages') || [];
                            currentStages.push({
                                stage: dev.stage,
                                stage_name: dev.stage_name,
                                expression_score: dev.expression_score
                            });
                            geneNode.data('developmental_stages', currentStages);
                        }
                    });

                    showBgeeStatus(`Updated genes with developmental stage data from Bgee`, "success");
                } else {
                    showBgeeStatus("No developmental data found in Bgee", "warning");
                }
            })
            .catch(error => {
                console.error("Error querying Bgee developmental:", error);
                showBgeeStatus("Error querying Bgee developmental data", "error");
            });
    }

    function queryBgeeAnatomical() {
        if (!window.cy) {
            showBgeeStatus("Network not initialized", "error");
            return;
        }

        const currentElements = window.cy.elements().jsons();
        showBgeeStatus("Querying Bgee for organ-specific expression...", "loading");

        fetch('/query_bgee_anatomical', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ cy_elements: currentElements })
        })
            .then(response => response.json())
            .then(data => {
                if (data.error) {
                    showBgeeStatus(`Error: ${data.error}`, "error");
                    return;
                }

                if (data.anatomical_data && data.anatomical_data.length > 0) {
                    // Update existing gene nodes with organ-specific expression
                    data.anatomical_data.forEach(anat => {
                        const geneNode = window.cy.getElementById(anat.gene_id);
                        if (geneNode.length > 0) {
                            const currentOrgans = geneNode.data('organ_expression') || [];
                            currentOrgans.push({
                                organ: anat.organ,
                                organ_name: anat.organ_name,
                                expression_level: anat.expression_level,
                                confidence: anat.confidence
                            });
                            geneNode.data('organ_expression', currentOrgans);
                        }
                    });

                    showBgeeStatus(`Updated genes with organ-specific expression from Bgee`, "success");
                } else {
                    showBgeeStatus("No organ-specific expression data found in Bgee", "warning");
                }
            })
            .catch(error => {
                console.error("Error querying Bgee anatomical:", error);
                showBgeeStatus("Error querying Bgee anatomical data", "error");
            });
    }

    function showBgeeStatus(message, type = 'info') {
        const statusDiv = document.getElementById('bgee-status');
        if (!statusDiv) return;

        const icons = {
            'loading': 'fas fa-spinner fa-spin',
            'success': 'fas fa-check',
            'error': 'fas fa-exclamation-triangle',
            'warning': 'fas fa-exclamation-circle',
            'info': 'fas fa-info-circle'
        };

        const colors = {
            'loading': '#6c757d',
            'success': '#28a745',
            'error': '#dc3545',
            'warning': '#ffc107',
            'info': '#17a2b8'
        };

        statusDiv.innerHTML = `
            <div style="color: ${colors[type]}; font-size: 0.8rem; margin-top: 0.5rem;">
                <i class="${icons[type]}"></i> ${message}
            </div>
        `;

        // Auto-clear success/info messages after 5 seconds
        if (type === 'success' || type === 'info') {
            setTimeout(() => {
                if (statusDiv.innerHTML.includes(message)) {
                    statusDiv.innerHTML = '';
                }
            }, 5000);
        }
    }

    // ===== INITIALIZATION =====

    // Initialize the application
    const dashboardContainer = document.querySelector("#compound-container");
    console.log("Dashboard container found:", dashboardContainer);

    if (!dashboardContainer) {
        console.error("Dashboard container not found");
        return;
    }

    if (isStandaloneMode) {
        console.log("Running in standalone mode - initializing empty network");
        initializeEmptyNetwork();
        return;
    }

    // Template mode - try to load data from template
    console.log("All data attributes:", dashboardContainer.dataset);
    const mies = dashboardContainer.dataset.mies;
    console.log("Raw mies data:", mies);

    if (mies && mies.trim() !== '') {
        console.log("Found MIEs:", mies);
        fetchAOPData(mies).then(data => {
            console.debug("Fetched AOP data:", data);
            if (data && data.length > 0) {
                renderAOPNetwork(data);
            } else {
                console.warn("No AOP data received");
                initializeEmptyNetwork();
            }
        });
    } else {
        console.log("No MIEs data found - running in standalone mode");
        initializeEmptyNetwork();
    }
});

// ===== DOCUMENT READY HANDLERS =====

// Event listener for data-type-dropdown
$(document).ready(function () {
    // Initial population of AOP table with immediate update after longer delay
    setTimeout(() => {
        console.log("DOM ready - triggering initial AOP table population");
        if (window.aopTableManager && window.aopTableManager.performTableUpdate) {
            // Use the enhanced table manager if available
            window.aopTableManager.performTableUpdate();
        } else if (window.populateAopTable) {
            window.populateAopTable(true); // true = immediate, not debounced
        } else {
            console.error("No AOP table manager available in DOM ready");
        }
    }, 3000); // Keep the delay to ensure everything is loaded
});

function populateaopTable() {
    console.log('populateaopTable called - using enhanced table manager');
    // Redirect to the enhanced table manager
    if (window.aopTableManager && window.aopTableManager.performTableUpdate) {
        return window.aopTableManager.performTableUpdate();
    } else if (window.populateAopTable) {
        return window.populateAopTable();
    }

    console.warn("No AOP table manager available");
    return Promise.resolve();
}
