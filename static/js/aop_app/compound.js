$(document).ready(() => {
    // Use the compound-container ID to match the actual container
    const container = document.querySelector("#compound-container");
    console.log("Container found:", container);
    
    if (container) {
        console.log("All data attributes:", container.dataset);
        const qid = container.dataset.qid;
        console.log("Raw qid data:", qid);
        
        if (!qid) {
            console.error("No 'qid' found in compound-container.");
            return;
        }

        // Load compound table using the working old approach
        $.getJSON(`/get_compounds/${qid}`, data => {
            console.log(data);
            const loadingElement = document.getElementById("loading_compound");
            if (loadingElement) {
                loadingElement.style.display = "none";
            }

            const tableBody = $("#compound_table tbody").empty();
            data.forEach(option => {
                const encodedSMILES = encodeURIComponent(option.SMILES);
                window.compoundMapping[option.SMILES] = { term: option.Term, url: `/compound/${option.ID}`, target: "_blank" };
                if (option.cid && option.cid !== "nan") {
                    window.compoundMapping[option.cid] = {
                        cid: option.cid,
                        url: `https://pubchem.ncbi.nlm.nih.gov/compound/${option.cid}`,
                        target: "_blank"
                    };
                } else {
                    window.compoundMapping[option.cid] = {
                        cid: option.cid,
                        url: "",
                    };
                }

                // Update compound_data and populate the table
                window.compound_data[option.SMILES] = {
                    compoundCell: `<a href="${window.compoundMapping[option.SMILES].url}" class="compound-link" target="_blank">${option.Term}</a>`,
                    pubChemCell: `<a href="${window.compoundMapping[option.cid].url}" class="cid-link" target="_blank">${window.compoundMapping[option.cid].cid}</a>`
                };

                tableBody.append(`
                    <tr>
                        <td>
                            <img src="https://cdkdepict.cloud.vhp4safety.nl/depict/bot/svg?w=-1&h=-1&abbr=off&hdisp=bridgehead&showtitle=false&zoom=0.5&annotate=cip&r=0&smi=${encodedSMILES}" 
                                 alt="${option.SMILES}" />
                            <p>${window.compound_data[option.SMILES].compoundCell}</p> 
                            <p>PubChem ID: ${window.compound_data[option.SMILES].pubChemCell}</p>
                        </td>
                    </tr>
                `);
            });
            
            // Initialize global variables for QSPRPred
            window.compoundMapping = window.compoundMapping;
            window.compound_data = window.compound_data;
        }).fail(() => {
            console.error("Failed to fetch compounds. Retrying...");
            setTimeout(() => {
                location.reload();
            }, 400);
        });

        // Enable row selection to filter the Cytoscape network by compound
        $("#compound_table").on("click", "tbody tr", function (e) {
            if ($(e.target).is("a") || $(e.target).is("button")) return;
            if (!window.fetched_preds) return;

            const compoundLink = $(this).find("td:first-child a");
            if (compoundLink.length) {
                compoundLink.toggleClass("selected");

                const compoundName = compoundLink.text().trim();
                if (compoundName) {
                    const cyNode = window.cy.nodes(`[label="${compoundName}"]`);
                    if (cyNode.length) {
                        cyNode.toggleClass("selected");
                    }
                }
            }

            updateCytoscapeSubset();
            positionNodes(window.cy);
        });

        // Handle compound link clicks
        $("#compound_table").on("click", ".compound-link", function (e) {
            const url = $(this).attr("href");
            $("#compound-frame").attr("src", url);
            positionNodes(window.cy);
        });
    } else {
        console.error("Compound container not found");
        return;
    }
});

// Function to collect all CIDs
function getAllCIDs() {
    return new Promise((resolve, reject) => {
        const cids = [];
        $("#compound_table tbody tr").each((_, tr) => {
            const cidLink = $(tr).find(".cid-link");
            if (cidLink.length) {
                const cid = cidLink.text().trim();
                if (cid && cid !== "nan") {
                    cids.push(cid);
                }
            }
        });
        console.log('Retrieved CIDs:', cids);
        resolve(cids);
    });
}

function updateCytoscapeSubset() {
    const selectedCompounds = [];

    // Collect the names of compounds that are selected in the table
    $("#compound_table tbody tr").each(function () {
        const compoundLink = $(this).find("td:first-child a");
        if (compoundLink.hasClass("selected")) {
            const compoundName = compoundLink.text().trim();
            if (compoundName) {
                selectedCompounds.push(compoundName);
            }
        }
    });

    console.log("Selected compounds:", selectedCompounds);

    if (!selectedCompounds.length) {
        window.cy.elements().show();
        window.cy.fit(window.cy.elements(), 50);
        return;
    }

    const visited = new Set();
    let activated = window.cy.collection();

    // Breadth-first search function to traverse outgoing edges
    function bfs(startNode) {
        const queue = [startNode];
        while (queue.length > 0) {
            const node = queue.shift();
            if (visited.has(node.id())) continue;
            visited.add(node.id());
            activated = activated.union(node);

            node.outgoers('edge').forEach(edge => {
                const target = edge.target();
                if (!visited.has(target.id())) {
                    queue.push(target);
                }
            });
        }
    }

    // Start BFS from selected chemical nodes
    selectedCompounds.forEach(compoundName => {
        const node = window.cy.nodes(`[label="${compoundName}"]`);
        if (!node.empty() && node.hasClass("chemical-node")) {
            bfs(node);
        }
    });

    // Keep only edges connecting activated nodes
    const activatedEdges = window.cy.edges().filter(edge =>
        activated.contains(edge.source()) && activated.contains(edge.target())
    );

    window.cy.elements().hide();
    activated.show();
    activatedEdges.show();
    window.cy.fit(activated, 50);
    positionNodes(window.cy);
}

// Legacy functions for backward compatibility
function showAllCompounds() {
    console.log("showAllCompounds called - use compound table selection");
}

function hideAllCompounds() {
    console.log("hideAllCompounds called - use compound table selection");
}

function toggleCompounds() {
    console.log("toggleCompounds called - use compound table selection");
}

// Make functions available globally
window.getAllCIDs = getAllCIDs;
window.updateCytoscapeSubset = updateCytoscapeSubset;
window.showAllCompounds = showAllCompounds;
window.hideAllCompounds = hideAllCompounds;
window.toggleCompounds = toggleCompounds;
