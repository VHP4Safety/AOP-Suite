document.addEventListener("DOMContentLoaded", function () {
    // Global variables
    window.cy = null;
    window.boundingBoxesVisible = false;
    window.genesVisible = false;
    window.compoundsVisible = false;
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
                        <h4>QAOP Network Builder</h4>
                        <p>Start building your network by:</p>
                        <ul style="text-align: left; display: inline-block;">
                            <li>Adding AOP network data manually</li>
                            <li>Using manual controls to add nodes and edges</li>
                            <li>Uploading custom tables</li>
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

        // Log when nodes are added.
        window.cy.on("add", "node", function (evt) {
            console.debug(`Node added: ${evt.target.id()}`);
            positionNodes(window.cy);
        });

        // Button event handlers
        setupButtonHandlers();
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
    return fetch('/populate_gene_table', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ cy_elements: window.cy.elements().jsons() })
    })
    .then(response => response.json())
    .then(response => {
        const tableBody = $("#gene_table tbody").empty();
        response.gene_data.forEach(gene => {
            tableBody.append(`
                <tr data-gene="${gene.gene}">
                    <td>${gene.gene}</td>
                    <td class="gene-expression-cell">${gene.expression_cell}</td>
                </tr>
            `);
        });
        console.log("Gene table populated.");
    });
};

// Event listener for data-type-dropdown
$(document).ready(function() {
    $("#data-type-dropdown").on("change", function () {
        const selectedValue = $(this).val();
        if (selectedValue === "qaop_div") {
            populateQaopTable();
        }
    });
});

function populateQaopTable() {
    if (!window.cy) {
        console.error("Cytoscape instance not available");
        return Promise.resolve();
    }
    
    return fetch('/populate_qaop_table', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ cy_elements: window.cy.elements().jsons() })
    })
    .then(response => response.json())
    .then(response => {
        const table = $("#qaop_table");
        document.getElementById("loading_qaop_table").style.display = "none";
        const tableBody = table.find("tbody").empty();
        
        if (response.qaop_data && response.qaop_data.length > 0) {
            response.qaop_data.forEach(item => {
                tableBody.append(`
                    <tr>
                        <td><a href="${item.source_id}" target="_blank">${item.source_label}</a></td>
                        <td>${item.curie}</td>
                        <td><a href="${item.target_id}" target="_blank">${item.target_label}</a></td>
                    </tr>
                `);
            });
            console.log("QAOP table populated with", response.qaop_data.length, "rows.");
        } else {
            tableBody.append('<tr><td colspan="3">No QAOP relationships found</td></tr>');
        }
    })
    .catch(error => {
        console.error("Error populating QAOP table:", error);
    });
}

// Make function available globally
window.populateQaopTable = populateQaopTable;