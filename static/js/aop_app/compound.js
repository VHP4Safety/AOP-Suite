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
                    cyNode = window.cy.nodes(`[label="${compoundName}"]`);
                }
                
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
                }
            }
        }

        // Immediate network update after each selection change
        updateNetworkWithSelectedCompounds();
    });

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
                    cyNode = window.cy.nodes(`[label="${compoundName}"]`);
                }
                
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
            const url = $(this).attr("href");
            const frame = $("#compound-frame");
            if (frame.length) {
                frame.attr("src", url);
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
    if (window.cy.getElementById(compoundName).length > 0) {
        return;
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
        
        window.cy.add(nodeData);
        console.log(`Created compound node: ${compoundName}`);
        
        // Reposition nodes
        if (window.positionNodes) {
            window.positionNodes(window.cy);
        }
    } catch (error) {
        console.error("Error creating compound node:", error);
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
            cyNode.remove();
            console.log(`Removed compound node: ${compoundName}`);
            
            // Reposition remaining nodes
            if (window.positionNodes) {
                window.positionNodes(window.cy);
            }
        }
    } catch (error) {
        console.error("Error removing compound node:", error);
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
        // No compounds selected - show everything
        window.cy.elements().show();
        window.cy.fit(window.cy.elements(), 50);
        return;
    }

    // Ensure compound nodes exist in the network
    selectedCompounds.forEach(compoundName => {
        let cyNode = window.cy.nodes(`[label="${compoundName}"]`);
        if (cyNode.length === 0) {
            // Find the SMILES for this compound - use compound-link selector
            $("#compound_table tbody tr").each(function() {
                const link = $(this).find(".compound-link").first();
                if (link.text().trim() === compoundName) {
                    const smiles = $(this).data("smiles");
                    createCompoundNode(compoundName, smiles);
                    return false; // Break out of each loop
                }
            });
        }
    });

    const visited = new Set();
    let activated = window.cy.collection();

    // Start with all existing AOP network nodes (non-compound nodes)
    window.cy.nodes().forEach(node => {
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
        const compoundNode = window.cy.nodes(`[label="${compoundName}"]`);
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
        const compoundNode = window.cy.nodes(`[label="${compoundName}"]`);
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

    // Show the activated subset (this preserves the AOP network)
    window.cy.elements().show(); // Show everything first
    activated.show();
    activatedEdges.show();
    
    // Fit view to the subset
    if (activated.length > 0) {
        window.cy.fit(activated.union(activatedEdges), 50);
    } else {
        // Fallback: show everything if no paths found
        window.cy.elements().show();
        window.cy.fit(window.cy.elements(), 50);
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
