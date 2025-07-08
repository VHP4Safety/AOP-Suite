$(document).ready(() => {
    // Initialize global variables if they don't exist
    if (!window.compoundMapping) window.compoundMapping = {};
    if (!window.compound_data) window.compound_data = {};
    
    // Use the compound-container ID to match the actual container
    const container = document.querySelector("#compound-container");
    console.log("Container found:", container);
    
    if (!container) {
        console.error("Compound container not found");
        return;
    }
    
    console.log("All data attributes:", container.dataset);
    const qid = container.dataset.qid;
    console.log("Raw qid data:", qid);
    
    // Check if we're in standalone mode
    const isStandaloneMode = !qid || qid.trim() === '';
    
    if (isStandaloneMode) {
        console.log("Running in standalone mode - no compound data to load");
        
        // Hide loading indicator
        const loadingElement = document.getElementById("loading_compound");
        if (loadingElement) {
            loadingElement.style.display = "none";
        }
        
        // Show empty state message
        const tableBody = $("#compound_table tbody").empty();
        tableBody.append(`
            <tr>
                <td style="text-align: center; padding: 2rem; color: #6c757d;">
                    <i class="fas fa-flask fa-2x mb-2"></i><br>
                    <em>No compound data loaded</em><br>
                    <small>Use manual controls or data sources to add compounds</small>
                </td>
            </tr>
        `);
        
        // Still set up controls for potential future use
        addCompoundControls();
        setupTableObserver();
        setupEventHandlers();
        return;
    }

    // Template mode - load compounds from QID
    console.log("Loading compounds for QID:", qid);
    
    // Load compound table using the working old approach
    $.getJSON(`/get_compounds/${qid}`, data => {
        console.log("Compound data received:", data);
        const loadingElement = document.getElementById("loading_compound");
        if (loadingElement) {
            loadingElement.style.display = "none";
        }

        const tableBody = $("#compound_table tbody").empty();
        
        data.forEach(option => {
            const encodedSMILES = encodeURIComponent(option.SMILES);
            
            // Store compound mapping
            window.compoundMapping[option.SMILES] = { 
                term: option.Term, 
                url: `/compound/${option.ID}`, 
                target: "_blank" 
            };
            
            // Handle CID properly - store actual CID value
            const cidValue = option.cid && option.cid !== "nan" ? option.cid : "";
            const cidUrl = cidValue ? `https://pubchem.ncbi.nlm.nih.gov/compound/${cidValue}` : "";
            
            // Update compound_data
            window.compound_data[option.SMILES] = {
                compoundCell: `<a href="/compound/${option.ID}" class="compound-link" target="_blank">${option.Term}</a>`,
                cidValue: cidValue,
                pubChemCell: cidValue ? 
                    `<a href="${cidUrl}" class="cid-link" data-cid="${cidValue}" target="_blank">${cidValue}</a>` :
                    `<span class="cid-link" data-cid="">No CID</span>`
            };

            tableBody.append(`
                <tr data-smiles="${option.SMILES}" data-cid="${cidValue}">
                    <td>
                        <img src="https://cdkdepict.cloud.vhp4safety.nl/depict/bot/svg?w=-1&h=-1&abbr=off&hdisp=bridgehead&showtitle=false&zoom=0.5&annotate=cip&r=0&smi=${encodedSMILES}" 
                             alt="${option.SMILES}" />
                        <p>${window.compound_data[option.SMILES].compoundCell}</p> 
                        <p>PubChem ID: ${window.compound_data[option.SMILES].pubChemCell}</p>
                    </td>
                </tr>
            `);
        });
        
        // Normalize table after initial load
        normalizeCompoundTable();
        
        // Add search and selection controls
        addCompoundControls();
        
        console.log("Compounds loaded. Testing CID extraction...");
        getAllCIDs().then(cids => {
            console.log("Test CID extraction result:", cids);
        });
        
    }).fail((xhr, status, error) => {
        console.error("Failed to fetch compounds:", error);
        
        // Show error state instead of reloading
        const loadingElement = document.getElementById("loading_compound");
        if (loadingElement) {
            loadingElement.style.display = "none";
        }
        
        const tableBody = $("#compound_table tbody").empty();
        tableBody.append(`
            <tr>
                <td style="text-align: center; padding: 2rem; color: #dc3545;">
                    <i class="fas fa-exclamation-triangle fa-2x mb-2"></i><br>
                    <em>Failed to load compound data</em><br>
                    <small>Error: ${error}</small>
                </td>
            </tr>
        `);
    });

    // Set up table observer and event handlers
    setupTableObserver();
    setupEventHandlers();
});

function setupEventHandlers() {
    // Click on compound table rows
    $(document).on("click", "#compound_table tbody tr", function (e) {
        if ($(e.target).is("a") || $(e.target).is("button")) return;
        
        console.log("Row clicked");
        
        const clickedRow = $(this);
        const compoundLink = clickedRow.find(".compound-link").first();
        
        // Check if this is an empty state row
        if (compoundLink.length === 0) {
            return;
        }
        
        const compoundName = compoundLink.text().trim();
        
        // Toggle selection instead of clearing all
        const isCurrentlySelected = clickedRow.hasClass("selected");
        
        if (!isCurrentlySelected) {
            // Select the row and link
            clickedRow.addClass("selected");
            compoundLink.addClass("selected");
            
            console.log("Selecting compound:", compoundName);
            
            if (compoundName && window.cy) {
                let cyNode = window.cy.nodes(`[label="${compoundName}"]`);
                
                if (cyNode.length === 0) {
                    const smiles = clickedRow.data("smiles");
                    createCompoundNode(compoundName, smiles);
                    // Node creation will trigger automatic table update via network listener
                }
                
                cyNode = window.cy.nodes(`[label="${compoundName}"]`);
                if (cyNode.length) {
                    cyNode.addClass("selected");
                }
            }
        } else {
            // Deselect the row and link
            clickedRow.removeClass("selected");
            compoundLink.removeClass("selected");
            
            console.log(`Deselecting compound "${compoundName}"`);
            
            if (compoundName && window.cy) {
                let cyNode = window.cy.nodes(`[label="${compoundName}"]`);
                if (cyNode.length) {
                    cyNode.removeClass("selected");
                    hideCompoundNode(compoundName);
                    // Node removal will trigger automatic table update via network listener
                }
            }
        }

        // Immediate network update after each selection change
        updateNetworkWithSelectedCompounds();
    });

    // Enhanced compound link click handler to work with network compounds
    $(document).on("click", "#compound_table .compound-link", function (e) {
        if (e.ctrlKey || e.metaKey) {
            e.preventDefault();
            $(this).toggleClass("selected");
            
            // Also toggle the row selection for consistency
            const row = $(this).closest("tr");
            const compoundName = $(this).text().trim();
            
            if ($(this).hasClass("selected")) {
                row.addClass("selected");
            } else {
                row.removeClass("selected");
            }
            
            console.log("Link clicked with modifier:", compoundName);
            
            if (compoundName && window.cy) {
                let cyNode = window.cy.nodes(`[label="${compoundName}"]`);
                
                if (cyNode.length === 0) {
                    const smiles = row.data("smiles");
                    createCompoundNode(compoundName, smiles);
                }
                
                cyNode = window.cy.nodes(`[label="${compoundName}"]`);
                if (cyNode.length) {
                    if ($(this).hasClass("selected")) {
                        cyNode.addClass("selected");
                    } else {
                        cyNode.removeClass("selected");
                        hideCompoundNode(compoundName);
                    }
                }
            }
            
            // Immediate network update after each selection change
            updateNetworkWithSelectedCompounds();
        } else {
            // Handle regular link clicks for non-network compounds
            if (!$(this).hasClass("network-compound-link")) {
                const url = $(this).attr("href");
                const frame = $("#compound-frame");
                if (frame.length) {
                    frame.attr("src", url);
                }
            }
        }
    });
}

// Table normalization function - simplified since initial table already has compound-link class
function normalizeCompoundTable() {
    $("#compound_table tbody tr").each(function() {
        const row = $(this);
        
        // Find any compound link in the row that doesn't already have compound-link class
        let compoundLinks = row.find("a[href*='/compound/']");
        
        compoundLinks.each(function() {
            const link = $(this);
            if (!link.hasClass("compound-link")) {
                link.addClass("compound-link");
                console.log("Added compound-link class to:", link.text().trim());
            }
        });
        
        // Ensure the row has SMILES data
        if (!row.data("smiles")) {
            // Try to extract from image alt attribute if available
            const img = row.find("img").first();
            if (img.length && img.attr("alt")) {
                row.attr("data-smiles", img.attr("alt"));
            }
        }
    });
}

// Set up mutation observer to watch for table changes
function setupTableObserver() {
    const tableBody = document.querySelector("#compound_table tbody");
    if (!tableBody) return;
    
    const observer = new MutationObserver((mutations) => {
        let shouldNormalize = false;
        
        mutations.forEach((mutation) => {
            if (mutation.type === 'childList' && mutation.addedNodes.length > 0) {
                // Check if new rows were added
                mutation.addedNodes.forEach(node => {
                    if (node.nodeType === 1 && node.tagName === 'TR') {
                        shouldNormalize = true;
                    }
                });
            }
        });
        
        if (shouldNormalize) {
            console.log("Table structure changed, normalizing...");
            setTimeout(() => normalizeCompoundTable(), 100); // Small delay to ensure DOM is updated
        }
    });
    
    observer.observe(tableBody, {
        childList: true,
        subtree: true
    });
    
    console.log("Table observer set up");
}

// Function to create compound nodes in the network
function createCompoundNode(compoundName, smiles) {
    if (!window.cy) {
        console.error("Cytoscape instance not available");
        return;
    }
    
    // Check if node already exists
    const existingNode = window.cy.getElementById(compoundName);
    if (existingNode.length > 0) {
        console.log(`Compound node already exists: ${compoundName}`);
        return existingNode;
    }
    
    try {
        const nodeData = {
            data: { 
                id: compoundName, 
                label: compoundName, 
                type: "chemical", 
                smiles: smiles || ""
            }, 
            classes: "chemical-node" 
        };
        
        const newNode = window.cy.add(nodeData);
        console.log(`Created compound node: ${compoundName}`);
        
        // Reposition nodes with smooth animation
        if (window.positionNodes) {
            const fontSlider = document.getElementById('font-size-slider');
            const fontSizeMultiplier = fontSlider ? parseFloat(fontSlider.value) : 0.5;
            
            setTimeout(() => {
                window.positionNodes(window.cy, fontSizeMultiplier, true);
            }, 50);
        }
        
        return newNode;
    } catch (error) {
        console.error("Error creating compound node:", error);
        return null;
    }
}

// Enhanced function to create multiple compound nodes
function createMultipleCompoundNodes(compoundData) {
    if (!window.cy) {
        console.error("Cytoscape instance not available");
        return { added: 0, skipped: 0 };
    }
    
    let added = 0;
    let skipped = 0;
    
    // Handle different input formats
    let compounds = [];
    
    if (typeof compoundData === 'string') {
        // Parse space/comma separated compound names
        const names = compoundData.split(/[,\s]+/).map(name => name.trim()).filter(name => name);
        compounds = names.map(name => ({ name, smiles: "" }));
    } else if (Array.isArray(compoundData)) {
        compounds = compoundData;
    } else if (compoundData.name) {
        compounds = [compoundData];
    }
    
    // Use batch operation for multiple nodes
    const nodesToAdd = [];
    
    compounds.forEach(compound => {
        const compoundName = compound.name || compound.label || compound;
        const smiles = compound.smiles || "";
        
        if (!compoundName) return;
        
        // Check if node already exists
        if (window.cy.getElementById(compoundName).length > 0) {
            console.log(`Compound node already exists: ${compoundName}`);
            skipped++;
            return;
        }
        
        try {
            const nodeData = {
                data: { 
                    id: compoundName, 
                    label: compoundName, 
                    type: "chemical", 
                    smiles: smiles
                }, 
                classes: "chemical-node" 
            };
            
            nodesToAdd.push(nodeData);
            console.log(`Prepared compound node: ${compoundName}`);
            added++;
            
        } catch (error) {
            console.error(`Error preparing compound node ${compoundName}:`, error);
            skipped++;
        }
    });
    
    // Add all nodes in a batch for smooth animation
    if (nodesToAdd.length > 0) {
        window.cy.batch(() => {
            window.cy.add(nodesToAdd);
        });
        
        // Reposition nodes with smooth animation
        if (window.positionNodes) {
            const fontSlider = document.getElementById('font-size-slider');
            const fontSizeMultiplier = fontSlider ? parseFloat(fontSlider.value) : 0.5;
            
            setTimeout(() => {
                window.positionNodes(window.cy, fontSizeMultiplier, true);
            }, 100);
        }
    }
    
    return { added, skipped };
}

// Function to show compound nodes (instead of recreating them)
function showCompoundNode(compoundName, smiles) {
    if (!window.cy) {
        console.error("Cytoscape instance not available");
        return;
    }
    
    try {
        const cyNode = window.cy.nodes(`[label="${compoundName}"]`);
        if (cyNode.length) {
            // Node exists, just show it with smooth transition
            window.cy.batch(() => {
                cyNode.show();
                
                // Show edges connected to this compound where both ends are visible
                cyNode.connectedEdges().forEach(edge => {
                    const source = edge.source();
                    const target = edge.target();
                    if (source.visible() && target.visible()) {
                        edge.show();
                    }
                });
            });
            
            console.log(`Shown existing compound node: ${compoundName}`);
        } else {
            // Node doesn't exist, create it
            createCompoundNode(compoundName, smiles);
            return; // createCompoundNode handles its own animation
        }
        
        // Smooth animation for showing nodes
        if (window.positionNodes) {
            const fontSlider = document.getElementById('font-size-slider');
            const fontSizeMultiplier = fontSlider ? parseFloat(fontSlider.value) : 0.5;
            
            setTimeout(() => {
                window.positionNodes(window.cy, fontSizeMultiplier, true);
            }, 50);
        }
    } catch (error) {
        console.error("Error showing compound node:", error);
    }
}

// Function to hide compound nodes from the network
function hideCompoundNode(compoundName) {
    if (!window.cy) {
        console.error("Cytoscape instance not available");
        return;
    }
    
    try {
        const cyNode = window.cy.nodes(`[label="${compoundName}"]`);
        if (cyNode.length) {
            // Hide the node and its edges with smooth transition
            window.cy.batch(() => {
                cyNode.hide();
                cyNode.connectedEdges().hide();
            });
            
            console.log(`Hidden compound node: ${compoundName}`);
            
            // Reposition remaining visible nodes with smooth animation
            if (window.positionNodes) {
                const fontSlider = document.getElementById('font-size-slider');
                const fontSizeMultiplier = fontSlider ? parseFloat(fontSlider.value) : 0.5;
                
                setTimeout(() => {
                    window.positionNodes(window.cy, fontSizeMultiplier, true);
                }, 50);
            }
        }
    } catch (error) {
        console.error("Error hiding compound node:", error);
    }
}

// Function to collect all CIDs - handle standalone mode
function getAllCIDs() {
    return new Promise((resolve, reject) => {
        const container = document.querySelector("#compound-container");
        const qid = container?.dataset?.qid;
        
        if (!qid || qid.trim() === '') {
            console.log("No QID available - returning empty CID list for standalone mode");
            resolve([]);
            return;
        }

        // Get CIDs directly from backend
        $.getJSON(`/get_compounds/${qid}`)
            .done(data => {
                const cids = data
                    .map(compound => compound.cid)
                    .filter(cid => cid && cid !== "nan" && cid !== "NA" && cid.trim() !== "")
                    .map(cid => String(cid).trim());
                
                console.log('Retrieved CIDs from backend:', cids);
                resolve([...new Set(cids)]); // Remove duplicates
            })
            .fail((xhr, status, error) => {
                console.error("Failed to fetch CIDs from backend:", error);
                resolve([]);
            });
    });
}

// BFS
function updateCytoscapeSubset() {
    const selectedCompounds = [];

    $("#compound_table tbody tr").each(function () {
        const row = $(this);
        const isRowSelected = row.hasClass("selected");
        const compoundLink = row.find(".compound-link").first();
        const isLinkSelected = compoundLink.hasClass("selected");

        if (isRowSelected || isLinkSelected) {
            const compoundName = compoundLink.text().trim();
            if (compoundName) {
                selectedCompounds.push(compoundName);
            }
        }
    });

    console.log("Selected compounds:", selectedCompounds);

    if (!selectedCompounds.length) {
        // No compounds selected - show everything but hide unselected compounds
        window.cy.elements().show();
        
        // Hide compound nodes that aren't selected
        window.cy.nodes('.chemical-node').forEach(node => {
            const nodeLabel = node.data('label');
            if (!selectedCompounds.includes(nodeLabel)) {
                node.hide();
                node.connectedEdges().hide();
            }
        });
        
        window.cy.fit(window.cy.elements(':visible'), 50);
        return;
    }

    // Ensure compound nodes exist and are visible for selected compounds
    selectedCompounds.forEach(compoundName => {
        const row = $("#compound_table tbody tr").filter(function() {
            return $(this).find(".compound-link").text().trim() === compoundName;
        }).first();
        
        const smiles = row.data("smiles") || "";
        showCompoundNode(compoundName, smiles);
    });

    // Hide non-selected compound nodes
    window.cy.nodes('.chemical-node').forEach(node => {
        const nodeLabel = node.data('label');
        if (!selectedCompounds.includes(nodeLabel)) {
            node.hide();
            node.connectedEdges().hide();
        }
    });

    const visited = new Set();
    let activated = window.cy.collection();

    // Start with all existing visible AOP network nodes (non-compound nodes)
    window.cy.nodes(':visible').forEach(node => {
        if (!node.hasClass("chemical-node")) {
            visited.add(node.id());
            activated = activated.union(node);
        }
    });

    // Enhanced pathfinding function to traverse all paths leading to compound
    function findAllPathsToCompound(compoundNode) {
        const pathNodes = new Set();
        const queue = [{node: compoundNode, path: [compoundNode]}];
        
        // Find all incoming paths to the compound (reverse BFS)
        while (queue.length > 0) {
            const {node, path} = queue.shift();
            
            if (pathNodes.has(node.id())) continue;
            pathNodes.add(node.id());
            
            // Add all nodes in current path
            path.forEach(pathNode => {
                if (!visited.has(pathNode.id())) {
                    visited.add(pathNode.id());
                    activated = activated.union(pathNode);
                }
            });
            
            // Traverse incoming edges (predecessors)
            node.incomers('edge').forEach(edge => {
                const source = edge.source();
                if (!pathNodes.has(source.id())) {
                    const newPath = [source, ...path];
                    queue.push({node: source, path: newPath});
                }
            });
        }
        
        // Also traverse outgoing paths from compound (forward BFS)
        const forwardQueue = [{node: compoundNode, path: [compoundNode]}];
        const forwardVisited = new Set();
        
        while (forwardQueue.length > 0) {
            const {node, path} = forwardQueue.shift();
            
            if (forwardVisited.has(node.id())) continue;
            forwardVisited.add(node.id());
            
            // Add all nodes in current path
            path.forEach(pathNode => {
                if (!visited.has(pathNode.id())) {
                    visited.add(pathNode.id());
                    activated = activated.union(pathNode);
                }
            });
            
            // Traverse outgoing edges (successors)
            node.outgoers('edge').forEach(edge => {
                const target = edge.target();
                if (!forwardVisited.has(target.id())) {
                    const newPath = [...path, target];
                    forwardQueue.push({node: target, path: newPath});
                }
            });
        }
    }

    // Find paths for each selected compound
    selectedCompounds.forEach(compoundName => {
        const compoundNode = window.cy.nodes(`[label="${compoundName}"]:visible`);
        if (!compoundNode.empty()) {
            // Always include the compound node itself
            if (!visited.has(compoundNode.id())) {
                visited.add(compoundNode.id());
                activated = activated.union(compoundNode);
            }
            
            // If it has connections, do pathfinding
            if (compoundNode.hasClass("chemical-node") && compoundNode.degree() > 0) {
                findAllPathsToCompound(compoundNode);
            }
        }
    });

    // Also include any direct protein targets of the compounds
    selectedCompounds.forEach(compoundName => {
        const compoundNode = window.cy.nodes(`[label="${compoundName}"]:visible`);
        if (!compoundNode.empty()) {
            // Include direct neighbors (proteins the compound interacts with)
            compoundNode.neighborhood().forEach(neighbor => {
                if (!visited.has(neighbor.id())) {
                    visited.add(neighbor.id());
                    activated = activated.union(neighbor);
                }
            });
        }
    });

    // Include all edges that connect activated nodes
    const activatedEdges = window.cy.edges().filter(edge => {
        const source = edge.source();
        const target = edge.target();
        return activated.contains(source) && activated.contains(target);
    });

    // Show the activated subset
    activated.show();
    activatedEdges.show();
    
    // Fit view to the subset
    if (activated.length > 0) {
        window.cy.fit(activated.union(activatedEdges), 50);
    } else {
        // Fallback: show everything if no paths found
        window.cy.elements(':visible').show();
        window.cy.fit(window.cy.elements(':visible'), 50);
    }
    
    // Update layout for better visualization
    if (window.positionNodes) {
        window.positionNodes(window.cy);
    }
    
    console.log(`Showing ${activated.length} nodes and ${activatedEdges.length} edges including AOP network and selected compounds`);
}

// Add show/hide compounds functionality - Update to use compound-link selectors
function showAllCompounds() {
    if (!window.cy) {
        console.error("Cytoscape instance not available");
        return;
    }
    
    // Select all compound links in the table
    $("#compound_table tbody tr .compound-link").addClass("selected");
    // Also add row selection for consistency
    $("#compound_table tbody tr").addClass("selected");
    
    // Ensure all compound nodes exist in the network
    $("#compound_table tbody tr").each(function() {
        const compoundLink = $(this).find(".compound-link").first();
        const compoundName = compoundLink.text().trim();
        const smiles = $(this).data("smiles");
        
        if (compoundName) {
            // Create compound node if it doesn't exist
            let cyNode = window.cy.nodes(`[label="${compoundName}"]`);
            if (cyNode.length === 0) {
                createCompoundNode(compoundName, smiles);
                cyNode = window.cy.nodes(`[label="${compoundName}"]`);
            }
            
            // Mark as selected
            if (cyNode.length) {
                cyNode.addClass("selected");
            }
        }
    });
    
    updateNetworkWithSelectedCompounds();
}

function hideAllCompounds() {
    // Remove selection from both compound links and rows
    $("#compound_table tbody tr .compound-link").removeClass("selected");
    $("#compound_table tbody tr").removeClass("selected");
    
    // Remove selected class from compound nodes
    if (window.cy) {
        window.cy.nodes(".chemical-node").removeClass("selected");
    }
    
    updateNetworkWithSelectedCompounds();
}

// Add compound search and selection controls
function addCompoundControls() {
    const tableContainer = $("#compound_table").parent();
    
    // Check if controls already exist
    if ($("#compound-controls").length > 0) {
        return;
    }
    
    const controlsHtml = `
        <div id="compound-controls" style="margin-bottom: 10px; padding: 10px; background: #f5f5f5; border-radius: 5px;">
            <div style="display: flex; gap: 10px; align-items: center; flex-wrap: wrap;">
                <input type="text" id="compound-search" placeholder="Search compounds by name or PubChem ID..." 
                       style="flex: 1; min-width: 200px; padding: 5px; border: 1px solid #ddd; border-radius: 3px;">
                <button id="select-all-compounds" class="btn btn-sm btn-primary">Select All</button>
                <button id="deselect-all-compounds" class="btn btn-sm btn-secondary">Deselect All</button>
                <button id="clear-search" class="btn btn-sm btn-outline-secondary">Clear Search</button>
            </div>
        </div>
    `;
    
    tableContainer.prepend(controlsHtml);
    
    // Set up event handlers
    setupCompoundControlHandlers();
}

// Set up event handlers for compound controls
function setupCompoundControlHandlers() {
    // Search functionality
    $("#compound-search").on("input", function() {
        const searchTerm = $(this).val().toLowerCase().trim();
        filterCompounds(searchTerm);
    });
    
    // Clear search
    $("#clear-search").on("click", function() {
        $("#compound-search").val("");
        filterCompounds("");
    });
    
    // Select all visible compounds
    $("#select-all-compounds").on("click", function() {
        $("#compound_table tbody tr:visible").each(function() {
            const row = $(this);
            const compoundLink = row.find(".compound-link").first();
            const compoundName = compoundLink.text().trim();
            
            if (!row.hasClass("selected")) {
                row.addClass("selected");
                compoundLink.addClass("selected");
                
                // Create compound node if needed
                if (compoundName && window.cy) {
                    let cyNode = window.cy.nodes(`[label="${compoundName}"]`);
                    if (cyNode.length === 0) {
                        const smiles = row.data("smiles");
                        createCompoundNode(compoundName, smiles);
                        cyNode = window.cy.nodes(`[label="${compoundName}"]`);
                    }
                    if (cyNode.length) {
                        cyNode.addClass("selected");
                    }
                }
            }
        });
        updateNetworkWithSelectedCompounds();
    });
    
    // Deselect all compounds
    $("#deselect-all-compounds").on("click", function() {
        // Get all compound names before deselecting
        const compoundNames = [];
        $("#compound_table tbody tr .compound-link").each(function() {
            const compoundName = $(this).text().trim();
            if (compoundName) {
                compoundNames.push(compoundName);
            }
        });
        
        // Remove selection from table
        $("#compound_table tbody tr").removeClass("selected");
        $("#compound_table tbody tr .compound-link").removeClass("selected");
        
        // Remove compound nodes from network
        if (window.cy) {
            compoundNames.forEach(compoundName => {
                hideCompoundNode(compoundName);
            });
            window.cy.nodes(".chemical-node").removeClass("selected");
        }
        
        updateNetworkWithSelectedCompounds();
    });
}

// Filter compounds based on search term
function filterCompounds(searchTerm) {
    if (!searchTerm) {
        // Show all rows
        $("#compound_table tbody tr").show();
        return;
    }
    
    $("#compound_table tbody tr").each(function() {
        const row = $(this);
        const compoundLink = row.find(".compound-link").first();
        const compoundName = compoundLink.text().toLowerCase();
        const cidText = row.find(".cid-link").text().toLowerCase();
        const smiles = row.data("smiles") || "";
        
        // Search in compound name, CID, and SMILES
        const isMatch = compoundName.includes(searchTerm) || 
                       cidText.includes(searchTerm) || 
                       smiles.toLowerCase().includes(searchTerm);
        
        if (isMatch) {
            row.show();
        } else {
            row.hide();
        }
    });
}

// Immediate network update function - called on every selection change
function updateNetworkWithSelectedCompounds() {
    console.log("Updating network with selected compounds...");
    updateCytoscapeSubset();
}

// Make functions available globally
window.getAllCIDs = getAllCIDs;
window.updateCytoscapeSubset = updateCytoscapeSubset;
window.updateNetworkWithSelectedCompounds = updateNetworkWithSelectedCompounds;
window.showAllCompounds = showAllCompounds;
window.hideAllCompounds = hideAllCompounds;
window.createCompoundNode = createCompoundNode;
window.hideCompoundNode = hideCompoundNode;

// Make enhanced functions available globally
window.createMultipleCompoundNodes = createMultipleCompoundNodes;
window.hideMultipleCompoundNodes = hideMultipleCompoundNodes;

// Make the network update function available globally
window.updateCompoundTableFromNetwork = updateCompoundTableFromNetwork;

// Enhanced function specifically for updating compound table from network
function updateCompoundTableFromNetwork() {
    if (!window.cy) {
        console.warn("Cytoscape not available for compound table update");
        return;
    }
    
    // Get all chemical nodes from the network
    const chemicalNodes = window.cy.nodes('.chemical-node');
    const tableBody = $("#compound_table tbody");
    
    // Add network chemical nodes to table if they're not already there
    chemicalNodes.forEach(node => {
        const nodeData = node.data();
        const nodeLabel = nodeData.label;
        const nodeSmiles = nodeData.smiles || "";
        const nodeId = nodeData.id;
        
        // Check if this compound is already in the table (either from backend or network)
        const existingRow = tableBody.find(`tr`).filter(function() {
            const rowLink = $(this).find('.compound-link');
            return rowLink.text().trim() === nodeLabel;
        });
        
        if (existingRow.length === 0 && nodeLabel) {
            // Add new row for network compound
            const encodedSMILES = encodeURIComponent(nodeSmiles);
            const imgUrl = nodeSmiles ? 
                `https://cdkdepict.cloud.vhp4safety.nl/depict/bot/svg?w=-1&h=-1&abbr=off&hdisp=bridgehead&showtitle=false&zoom=0.5&annotate=cip&r=0&smi=${encodedSMILES}` :
                '';
            
            tableBody.append(`
                <tr data-smiles="${nodeSmiles}" data-compound-source="network" class="network-compound">
                    <td>
                        ${imgUrl ? `<img src="${imgUrl}" alt="${nodeSmiles}" style="max-width: 150px; height: auto; margin-bottom: 5px;" />` : ''}
                        <p><span class="compound-link network-compound-link" style="font-weight: bold;">${nodeLabel}</span></p>
                        <p><small style="color: #6c757d; font-style: italic;">Added from network</small></p>
                    </td>
                </tr>
            `);
            
            console.log(`Added network compound to table: ${nodeLabel}`);
        } else if (existingRow.length > 0) {
            // Mark existing row as having a network counterpart
            existingRow.addClass('has-network-node');
        }
    });
    
    // Clean up compounds that were added from network but no longer exist
    tableBody.find('tr.network-compound').each(function() {
        const row = $(this);
        const compoundLabel = row.find('.compound-link').text().trim();
        
        // Check if this compound still exists in the network
        const networkNode = window.cy.nodes().filter(node => {
            return node.hasClass('chemical-node') && node.data('label') === compoundLabel;
        });
        
        if (networkNode.length === 0) {
            row.remove();
            console.log(`Removed network compound from table: ${compoundLabel}`);
        }
    });
    
    // Remove network marking from compounds that no longer have network nodes
    tableBody.find('tr.has-network-node').each(function() {
        const row = $(this);
        const compoundLabel = row.find('.compound-link').text().trim();
        
        const networkNode = window.cy.nodes().filter(node => {
            return node.hasClass('chemical-node') && node.data('label') === compoundLabel;
        });
        
        if (networkNode.length === 0) {
            row.removeClass('has-network-node');
        }
    });
}

// Function to hide multiple compound nodes
function hideMultipleCompoundNodes() {
    if (!window.cy) {
        console.warn("Cytoscape not available for hiding compound nodes");
        return;
    }
    
    // Hide all chemical/compound nodes in the network
    const compoundNodes = window.cy.nodes('.chemical-node, [type="chemical"]');
    
    if (compoundNodes.length > 0) {
        window.cy.batch(() => {
            compoundNodes.hide();
            
            // Also hide edges connected to compound nodes
            compoundNodes.forEach(node => {
                node.connectedEdges().hide();
            });
        });
        
        console.log(`Hidden ${compoundNodes.length} compound nodes from network`);
        
        // Update the network layout after hiding nodes
        if (window.positionNodes) {
            const fontSlider = document.getElementById('font-size-slider');
            const fontSizeMultiplier = fontSlider ? parseFloat(fontSlider.value) : 0.5;
            
            setTimeout(() => {
                window.positionNodes(window.cy, fontSizeMultiplier, true);
            }, 100);
        }
        
        return true;
    }
    
    console.log("No compound nodes found to hide");
    return false;
}
