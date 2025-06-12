document.addEventListener("DOMContentLoaded", function () {
    // Global variables
    window.cy = null;
    window.boundingBoxesVisible = false;
    window.genesVisible = false;
    window.compoundsVisible = false;
    window.goProcessesVisible = false;
    window.fetched_preds = false;
    window.compound_data = {};
    window.modelToProteinInfo = {};
    window.compoundMapping = {};

    // Check if we're in standalone mode or template mode
    const isStandaloneMode = !document.querySelector("#compound-container[data-mies]") || 
                            !document.querySelector("#compound-container").dataset.mies;

    console.log("App mode:", isStandaloneMode ? "Standalone" : "Template");

    // Fetch data for the AOP network.
    function fetchAOPData(mies) {
        console.debug(`Fetching AOP network data for: ${mies}`);
        return fetch(`/get_aop_network?mies=${encodeURIComponent(mies)}`)
            .then(response => {
                if (!response.ok) {
                    throw new Error(`HTTP ${response.status}: ${response.statusText}`);
                }
                return response.json();
            })
            .catch(error => {
                console.error("Error fetching AOP data:", error);
                return [];
            });
    }

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
            
            // Initialize positioning
            if (window.positionNodes) {
                window.positionNodes(window.cy);
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
                window.positionNodes(window.cy);
            }
            
            setupEventHandlers();
            initializeModules();
            
            // Show helpful message for standalone mode
            const loadingOverlay = document.querySelector(".loading-overlay");
            if (loadingOverlay) {
                loadingOverlay.innerHTML = `
                    <div class="text-center">
                        <i class="fas fa-project-diagram fa-3x mb-3" style="color: #6c757d;"></i>
                        <h4>AOP Network Builder</h4>
                        <p>Start building your network by:</p>
                        <ul style="text-align: left; display: inline-block;">
                            <li>Adding nodes and edges manually</li>
                            <li>Querying the AOP wiki for Key Events, AOPs, Compounds and Genes</li>
                            <li>Querying OpenTargets for Compound data</li>
                            <li>Querying Bgee for organ-specific gene expression data</li>
                            <li>Adding your own data tables as weights for the nodes.</li>
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
            // Initialize gene view (safe to call without data)
            initializeGeneView();
            
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
        }, 200);
    }

    function initializeGeneView() {
        if (!window.cy) {
            console.warn("Cytoscape not ready for gene initialization");
            return;
        }
        
        // Always populate the gene table, even if empty
        setTimeout(() => {
            if (window.populateGeneTable) {
                window.populateGeneTable();
            }
        }, 100);
        
        // Only try to load genes if we have MIE data
        const dashboardContainer = document.querySelector("#compound-container");
        const mies = dashboardContainer?.dataset?.mies;
        
        if (!mies || isStandaloneMode) {
            console.log("No MIE data available - skipping gene loading");
            return;
        }
        
        // Load gene elements but keep them hidden initially
        fetch('/toggle_genes', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ 
                action: 'show',
                cy_elements: window.cy.elements().jsons() 
            })
        })
        .then(response => {
            if (!response.ok) {
                console.warn(`Gene initialization failed: ${response.status}`);
                return { gene_elements: [] };
            }
            return response.json();
        })
        .then(data => {
            if (data.gene_elements && data.gene_elements.length > 0) {
                data.gene_elements.forEach(element => {
                    const elementId = element.data?.id;
                    if (elementId && !window.cy.getElementById(elementId).length) {
                        try {
                            window.cy.add(element);
                        } catch (error) {
                            console.warn("Skipping duplicate element:", elementId);
                        }
                    }
                });
                
                // Keep genes hidden by default
                window.cy.elements(".uniprot-node, .ensembl-node").hide();
                window.cy.edges().filter(edge => {
                    const source = edge.source();
                    const target = edge.target();
                    return source.hasClass("uniprot-node") || source.hasClass("ensembl-node") ||
                           target.hasClass("uniprot-node") || target.hasClass("ensembl-node");
                }).hide();
                
                $("#see_genes").text("See Genes");
                window.genesVisible = false;
                
                console.log("Gene elements loaded but hidden by default");
            }
        })
        .catch(error => {
            console.warn("Error initializing gene view:", error);
        });
    }

    function setupEventHandlers() {
        // Node click event.
        window.cy.on("tap", "node", function (evt) {
            const node = evt.target;
            const url = node.id();
            console.debug(`Node tapped: ${node.id()}, data:`, node.data());
            if (node.hasClass("uniprot-node")) {
                window.open(`https://www.uniprot.org/uniprotkb/${url.replace("uniprot_", "")}`, "_blank");
            } else if (node.hasClass("ensembl-node")) {
                window.open(`https://identifiers.org/ensembl/${url.replace("ensembl_", "")}`, "_blank");
            } else if (node.hasClass("go-process-node")) {
                const uri = node.data("uri");
                if (uri) {
                    window.open(uri, "_blank");
                }
            } else if (node.hasClass("bounding-box")) {
                window.open(node.data("aop"), "_blank");
            } else {
                window.open(`${url}`);
            }
        });
        
        window.cy.on("tap", "edge", function(evt) {
            const edge = evt.target;
            if (edge.data("ker_label")) {
                window.open(`https://identifiers.org/aop.relationships/${edge.data("ker_label")}`);
            }
        });

        // Network change listeners for automatic table updates
        window.cy.on("add", "node", function (evt) {
            const node = evt.target;
            console.debug(`Node added: ${node.id()}`);
            
            // Auto-update tables based on node type
            autoUpdateTables(node, 'added');
            
            positionNodes(window.cy);
        });

        window.cy.on("remove", "node", function (evt) {
            const node = evt.target;
            console.debug(`Node removed: ${node.id()}`);
            
            // Auto-update tables based on node type
            autoUpdateTables(node, 'removed');
        });

        window.cy.on("add", "edge", function (evt) {
            const edge = evt.target;
            console.debug(`Edge added: ${edge.id()}`);
            
            // Update AOP table when edges are added
            if (window.populateAopTable) {
                setTimeout(() => {
                    window.populateAopTable();
                }, 200);
            }
        });

        window.cy.on("remove", "edge", function (evt) {
            const edge = evt.target;
            console.debug(`Edge removed: ${edge.id()}`);
            
            // Update AOP table when edges are removed  
            if (window.populateAopTable) {
                setTimeout(() => {
                    window.populateAopTable();
                }, 200);
            }
        });

        window.cy.on("data", "node", function (evt) {
            const node = evt.target;
            console.debug(`Node data changed: ${node.id()}`);
            
            // Auto-update tables based on node type
            autoUpdateTables(node, 'updated');
        });

        // Button event handlers
        setupButtonHandlers();
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
            updateGeneTable();
        }
        
        // Check if it's a compound node (Chemical)
        if (nodeClasses.includes("chemical-node") || 
            nodeType === "chemical") {
            
            console.log(`Compound node ${action}: ${nodeData.label || nodeId}`);
            updateCompoundTableFromNetwork();
        }
        
        // Always update AOP table for any node/edge changes (since it shows relationships)
        console.log("Triggering AOP table update");
        if (window.populateAopTable) {
            setTimeout(() => {
                console.log("Executing delayed AOP table update");
                window.populateAopTable();
            }, 200); // Increased delay to ensure network is fully updated
        } else {
            console.error("populateAopTable function not available");
        }
    }

    function setupButtonHandlers() {
        // Toggle Bounding Boxes
        $("#toggle_bounding_boxes").on("click", function () {
            toggleBoundingBoxes();
        });

        // Toggle compounds
        $("#toggle_compounds").on("click", function() {
            if (window.toggleCompounds) {
                window.toggleCompounds();
            }
        });

        // Toggle genes
        $("#see_genes").on("click", function () {
            toggleGenes();
        });

        // Reset layout
        $("#reset_layout").on("click", function () {
            positionNodes(window.cy);
        });

        // Download network
        $("#download_network").on("click", function () {
            downloadNetwork();
        });

        // Toggle GO processes
        $("#toggle_go_processes").on("click", function() {
            toggleGOProcesses();
        });

        $("#show_go_hierarchy").on("click", function() {
            showGOProcessHierarchy();
        });

        // OpenTargets dropdown handlers
        $("#opentargets_query_compounds").on("click", function() {
            queryOpenTargetsCompounds();
        });

        $("#opentargets_query_targets").on("click", function() {
            queryOpenTargetsTargets();
        });

        $("#opentargets_query_diseases").on("click", function() {
            queryOpenTargetsDiseases();
        });

        // Bgee dropdown handlers
        $("#bgee_query_expression").on("click", function() {
            queryBgeeExpression();
        });

        $("#bgee_query_developmental").on("click", function() {
            queryBgeeDevelopmental();
        });

        $("#bgee_query_anatomical").on("click", function() {
            queryBgeeAnatomical();
        });
    }

    function toggleGenes() {
        const action = window.genesVisible ? 'hide' : 'show';
        
        fetch('/toggle_genes', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ 
                action: action,
                cy_elements: window.cy.elements().jsons() 
            })
        })
        .then(response => {
            if (!response.ok) {
                throw new Error(`HTTP ${response.status}: ${response.statusText}`);
            }
            return response.json();
        })
        .then(data => {
            if (data.error) {
                console.error("Gene toggle error:", data.error);
                return;
            }
            
            if (action === 'show' && data.gene_elements) {
                // Add only new elements
                data.gene_elements.forEach(element => {
                    const elementId = element.data?.id;
                    if (elementId && !window.cy.getElementById(elementId).length) {
                        try {
                            window.cy.add(element);
                        } catch (error) {
                            console.warn("Error adding element:", elementId, error.message);
                        }
                    }
                });
                
                // Show all gene nodes and their edges
                window.cy.elements(".uniprot-node, .ensembl-node").show();
                window.cy.edges().forEach(function(edge) {
                    const source = edge.source();
                    const target = edge.target();
                    
                    // Show edge if both source and target are visible
                    if (source.visible() && target.visible()) {
                        edge.show();
                    }
                });
                
                $("#see_genes").text("Hide Genes");
                window.genesVisible = true;
            
                // Populate gene table after showing genes
                setTimeout(() => {
                    if (window.populateGeneTable) {
                        window.populateGeneTable();
                    }
                }, 100);
            } else if (action === 'hide') {
                // Hide gene nodes
                window.cy.elements(".uniprot-node, .ensembl-node").hide();
                // Hide edges connected to gene nodes
                window.cy.edges().forEach(function(edge) {
                    const source = edge.source();
                    const target = edge.target();
                    
                    // Hide edge if either end is a gene node
                    if (source.hasClass("uniprot-node") || source.hasClass("ensembl-node") ||
                        target.hasClass("uniprot-node") || target.hasClass("ensembl-node")) {
                        edge.hide();
                    }
                });
                
                $("#see_genes").text("See Genes");
                window.genesVisible = false;
            }
            
            positionNodes(window.cy);
        })
        .catch(error => {
            console.error("Error toggling genes:", error);
        });
    }

    function toggleBoundingBoxes() {
        const action = window.boundingBoxesVisible ? 'remove' : 'add';
        
        fetch('/toggle_bounding_boxes', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ 
                action: action,
                cy_elements: window.cy.elements().jsons() 
            })
        })
        .then(response => {
            if (!response.ok) {
                throw new Error(`HTTP ${response.status}: ${response.statusText}`);
            }
            return response.json();
        })
        .then(updatedElements => {
            if (Array.isArray(updatedElements)) {
                window.cy.elements().remove();
                window.cy.add(updatedElements);
                window.boundingBoxesVisible = !window.boundingBoxesVisible;
                $("#toggle_bounding_boxes").text(window.boundingBoxesVisible ? "Remove AOP Boxes" : "Group by AOP");
            }
            positionNodes(window.cy);
        })
        .catch(error => {
            console.error("Error toggling bounding boxes:", error);
        });
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

// Expose functions globally for other modules
window.populateGeneTable = function() {
    updateGeneTable();
};

function updateGeneTable() {
    if (!window.cy) {
        console.warn("Cytoscape not available for gene table update");
        return Promise.resolve();
    }
    
    return fetch('/populate_gene_table', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ cy_elements: window.cy.elements().jsons() })
    })
    .then(response => response.json())
    .then(response => {
        const tableBody = $("#gene_table tbody").empty();
        
        if (response.gene_data && response.gene_data.length > 0) {
            response.gene_data.forEach(gene => {
                tableBody.append(`
                    <tr data-gene="${gene.gene}">
                        <td>${gene.gene}</td>
                        <td class="gene-expression-cell">${gene.expression_cell}</td>
                    </tr>
                `);
            });
            console.log(`Gene table updated with ${response.gene_data.length} genes.`);
        } else {
            tableBody.append(`
                <tr>
                    <td colspan="2" style="text-align: center; color: #6c757d; font-style: italic;">
                        No genes in network
                    </td>
                </tr>
            `);
        }
    })
    .catch(error => {
        console.error("Error updating gene table:", error);
    });
}

// New function to update compound table from network
function updateCompoundTableFromNetwork() {
    if (!window.cy) {
        console.warn("Cytoscape not available for compound table update");
        return;
    }
    
    // Get all chemical nodes from the network
    const chemicalNodes = window.cy.nodes('.chemical-node');
    const tableBody = $("#compound_table tbody");
    
    // If no chemical nodes, show empty state (but don't clear existing compound data)
    if (chemicalNodes.length === 0) {
        console.log("No chemical nodes in network");
        return;
    }
    
    // Add network chemical nodes to table if they're not already there
    chemicalNodes.forEach(node => {
        const nodeData = node.data();
        const nodeLabel = nodeData.label;
        const nodeSmiles = nodeData.smiles || "";
        const nodeId = nodeData.id;
        
        // Check if this compound is already in the table
        const existingRow = tableBody.find(`tr[data-smiles="${nodeSmiles}"]`);
        if (existingRow.length === 0 && nodeLabel) {
            // Add new row for network compound
            const encodedSMILES = encodeURIComponent(nodeSmiles);
            const imgUrl = nodeSmiles ? 
                `https://cdkdepict.cloud.vhp4safety.nl/depict/bot/svg?w=-1&h=-1&abbr=off&hdisp=bridgehead&showtitle=false&zoom=0.5&annotate=cip&r=0&smi=${encodedSMILES}` :
                '';
            
            tableBody.append(`
                <tr data-smiles="${nodeSmiles}" data-compound-source="network" class="network-compound">
                    <td>
                        ${imgUrl ? `<img src="${imgUrl}" alt="${nodeSmiles}" style="max-width: 100px; height: auto;" />` : ''}
                        <p><span class="compound-link network-compound-link">${nodeLabel}</span></p>
                        <p><small style="color: #6c757d;">From network</small></p>
                    </td>
                </tr>
            `);
            
            console.log(`Added network compound to table: ${nodeLabel}`);
        }
    });
    
    // Remove compounds from table that are no longer in the network
    tableBody.find('tr.network-compound').each(function() {
        const row = $(this);
        const compoundLabel = row.find('.compound-link').text().trim();
        
        // Check if this compound still exists in the network
        const networkNode = window.cy.nodes().filter(node => {
            return node.hasClass('chemical-node') && node.data('label') === compoundLabel;
        });
        
        if (networkNode.length === 0) {
            row.remove();
            console.log(`Removed compound from table: ${compoundLabel}`);
        }
    });
}

// Event listener for data-type-dropdown
$(document).ready(function() {
    // Initial population of AOP table with longer delay
    setTimeout(() => {
        console.log("DOM ready - triggering initial AOP table population");
        if (window.populateAopTable) {
            window.populateAopTable();
        } else {
            console.error("populateAopTable not available in DOM ready");
        }
    }, 3000); // Increased delay to ensure everything is loaded
});

function populateQaopTable() {
    // Redirect to the new function name
    if (window.populateAopTable) {
        return window.populateAopTable();
    }
    
    console.warn("populateAopTable function not available");
    return Promise.resolve();
}

// GO Process functionality - add at end of file
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

// OpenTargets functionality
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
                updateCompoundTableFromNetwork();
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
                updateGeneTable();
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

    if (type === 'success' || type === 'info') {
        setTimeout(() => {
            if (statusDiv.innerHTML.includes(message)) {
                statusDiv.innerHTML = '';
            }
        }, 5000);
    }
}

// Bgee functionality
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
                updateGeneTable();
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

    if (type === 'success' || type === 'info') {
        setTimeout(() => {
            if (statusDiv.innerHTML.includes(message)) {
                statusDiv.innerHTML = '';
            }
        }, 5000);
    }
}