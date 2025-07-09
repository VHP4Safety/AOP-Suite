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
            
            // Trigger immediate AOP table population after modules are initialized
            setTimeout(() => {
                console.log("Modules initialized - triggering AOP table population");
                if (window.populateAopTable) {
                    window.populateAopTable(true); // true = immediate
                }
            }, 500);
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
        // Initialize selection functionality
        initializeNetworkSelection();
        
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
        window.cy.on("batch", function(evt) {
            console.debug("Batch operation completed");
            
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

        // Enable box selection for multi-select
        window.cy.boxSelectionEnabled(true);
        
        // Remove any existing tap handlers to prevent URL navigation
        window.cy.removeListener('tap');
        
        // Handle single click selection
        window.cy.on('tap', function(evt) {
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
        window.cy.on('select unselect', function() {
            updateSelectionControls();
        });

        // Prevent default href behavior on nodes/edges
        window.cy.on('tap', 'node, edge', function(evt) {
            evt.preventDefault();
            evt.stopPropagation();
        });
    }

    // Selection management functions
    function updateSelectionControls() {
        const selectionControls = document.getElementById('selection-controls');
        const selectionInfo = document.getElementById('selection-info');
        
        if (!selectionControls || !selectionInfo) return;
        
        if (window.cy) {
            const selected = window.cy.$(':selected');
            
            if (selected.length > 0) {
                selectionControls.style.display = 'flex';
                selectionInfo.textContent = `${selected.length} selected`;
            } else {
                selectionControls.style.display = 'none';
            }
        }
    }

    function deleteSelectedElements() {
        if (!window.cy) return;

        const selected = window.cy.$(':selected');
        
        if (selected.length === 0) {
            console.log("No elements selected for deletion");
            return;
        }

        // Confirm deletion
        if (confirm(`Are you sure you want to delete ${selected.length} selected element(s)?`)) {
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
    }

    function clearSelection() {
        if (window.cy) {
            window.cy.$(':selected').unselect();
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
                updateCompoundTableFromNetwork();
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
                updateGeneTable();
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
            updateGeneTable();
        }
        
        // Check if it's a compound node (Chemical)
        if (nodeClasses.includes("chemical-node") || 
            nodeType === "chemical") {
            
            console.log(`Compound node ${action}: ${nodeData.label || nodeId}`);
            updateCompoundTableFromNetwork();
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
        $("#see_genes").off("click");
        $("#reset_layout").off("click");
        $("#download_network").off("click");
        $("#toggle_go_processes").off("click");
        $("#show_go_hierarchy").off("click");
        
        // Selection control handlers
        $(document).on('click', '#delete_selected', function(e) {
            e.preventDefault();
            e.stopPropagation();
            deleteSelectedElements();
        });
        
        $(document).on('click', '#clear_selection', function(e) {
            e.preventDefault();
            e.stopPropagation();
            clearSelection();
        });
        
        // Keyboard shortcuts
        $(document).on('keydown', function(e) {
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
        
        // Group by AOP - now uses table functionality
        $("#toggle_bounding_boxes").on("click", function (e) {
            e.preventDefault();
            e.stopPropagation();
            console.log('Group by AOP button clicked');
            
            if (window.aopTableManager) {
                window.aopTableManager.groupByAllAops();
            } else {
                console.error('AOP Table Manager not available');
            }
        });

        // Toggle compounds
        $("#toggle_compounds").on("click", function(e) {
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

        // Reset layout with smooth animation
        $("#reset_layout").on("click", function (e) {
            e.preventDefault();
            e.stopPropagation();
            if (window.cy) {
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
                    layout.one('layoutstop', function() {
                        // Apply styles with updated font size and smooth transitions
                        if (window.positionNodes) {
                            window.positionNodes(window.cy, fontSizeMultiplier, true);
                        }
                    });
                }, 100);
            }
        });

        // Download network
        $("#download_network").on("click", function (e) {
            e.preventDefault();
            e.stopPropagation();
            downloadNetwork();
        });

        // Toggle GO processes
        $("#toggle_go_processes").on("click", function(e) {
            e.preventDefault();
            e.stopPropagation();
            toggleGOProcesses();
        });

        $("#show_go_hierarchy").on("click", function(e) {
            e.preventDefault();
            e.stopPropagation();
            showGOProcessHierarchy();
        });

        // OpenTargets dropdown handlers
        $("#opentargets_query_compounds").on("click", function(e) {
            e.preventDefault();
            e.stopPropagation();
            queryOpenTargetsCompounds();
        });

        $("#opentargets_query_targets").on("click", function(e) {
            e.preventDefault();
            e.stopPropagation();
            queryOpenTargetsTargets();
        });

        $("#opentargets_query_diseases").on("click", function(e) {
            e.preventDefault();
            e.stopPropagation();
            queryOpenTargetsDiseases();
        });

        // Bgee dropdown handlers
        $("#bgee_query_expression").on("click", function(e) {
            e.preventDefault();
            e.stopPropagation();
            queryBgeeExpression();
        });

        $("#bgee_query_developmental").on("click", function(e) {
            e.preventDefault();
            e.stopPropagation();
            queryBgeeDevelopmental();
        });

        $("#bgee_query_anatomical").on("click", function(e) {
            e.preventDefault();
            e.stopPropagation();
            queryBgeeAnatomical();
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

    // Make toggleSidebar available globally for HTML onclick handlers
    window.toggleSidebar = toggleSidebar;

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
            
            const fontSlider = document.getElementById('font-size-slider');
            const fontSizeMultiplier = fontSlider ? parseFloat(fontSlider.value) : 0.5;
            
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
                
                // Show all gene nodes and their edges with smooth animation
                window.cy.batch(() => {
                    window.cy.elements(".uniprot-node, .ensembl-node").show();
                    window.cy.edges().forEach(function(edge) {
                        const source = edge.source();
                        const target = edge.target();
                        
                        if (source.visible() && target.visible()) {
                            edge.show();
                        }
                    });
                });
                
                $("#see_genes").text("Hide Genes");
                window.genesVisible = true;
            
                // Populate gene table after showing genes
                setTimeout(() => {
                    if (window.populateGeneTable) {
                        window.populateGeneTable();
                    }
                }, 100);
                
                // Smooth animation after showing genes
                setTimeout(() => {
                    positionNodes(window.cy, fontSizeMultiplier, true);
                }, 150);
                
            } else if (action === 'hide') {
                // Hide gene nodes and edges with smooth animation
                window.cy.batch(() => {
                    window.cy.elements(".uniprot-node, .ensembl-node").hide();
                    window.cy.edges().forEach(function(edge) {
                        const source = edge.source();
                        const target = edge.target();
                        
                        if (source.hasClass("uniprot-node") || source.hasClass("ensembl-node") ||
                            target.hasClass("uniprot-node") || target.hasClass("ensembl-node")) {
                            edge.hide();
                        }
                    });
                });
                
                $("#see_genes").text("See Genes");
                window.genesVisible = false;
                
                // Smooth animation after hiding genes
                setTimeout(() => {
                    positionNodes(window.cy, fontSizeMultiplier, true);
                }, 150);
            }
        })
        .catch(error => {
            console.error("Error toggling genes:", error);
        });
    }

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
    // Initial population of AOP table with immediate update after longer delay
    setTimeout(() => {
        console.log("DOM ready - triggering initial AOP table population");
        if (window.populateAopTable) {
            window.populateAopTable(true); // true = immediate, not debounced
        } else {
            console.error("populateAopTable not available in DOM ready");
        }
    }, 3000); // Keep the delay to ensure everything is loaded
});

function populateaopTable() {
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