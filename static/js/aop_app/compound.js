$(document).ready(() => {
    // Use the dashboard container with the correct data attributes
    const container = document.querySelector(".dashboard-container");
    console.log("Container found:", container);
    
    if (container) {
        console.log("All data attributes:", container.dataset);
        const qid = container.dataset.qid;
        console.log("Raw qid data:", qid);
        
        if (!qid) {
            console.error("No 'qid' found in dashboard-container.");
            return;
        }

        // Load compound table and store data (but don't render compounds in network)
        $.ajax({
            url: `/populate_compound_table/${qid}`,
            type: "GET",
            success: response => {
                const loadingElement = document.getElementById("loading_compound");
                if (loadingElement) {
                    loadingElement.style.display = "none";
                }

                // Store compound data globally
                window.compoundMapping = response.compound_mapping;
                window.compoundTableData = response.table_data;
                window.allCompoundElements = response.table_data.map(compound => ({
                    data: {
                        id: compound.term,
                        label: compound.term,
                        type: "chemical",
                        smiles: compound.smiles,
                    },
                    classes: "chemical-node",
                }));
                
                const tableBody = $("#compound_table tbody").empty();
                response.table_data.forEach(compound => {
                    tableBody.append(`
                        <tr data-compound-name="${compound.term}" data-smiles="${compound.smiles}">
                            <td>
                                <img src="${compound.img_url}" alt="${compound.smiles}" />
                                <p>${compound.compound_cell}</p> 
                                <p>PubChem ID: ${compound.pubchem_cell}</p>
                            </td>
                        </tr>
                    `);
                });

                console.log(`Loaded ${response.table_data.length} compounds (not rendered in network)`);
            },
            error: () => {
                console.error("Failed to fetch compounds. Retrying...");
                setTimeout(() => {
                    location.reload();
                }, 400);
            }
        });

        // Handle row selection - toggle individual compounds
        $("#compound_table").on("click", "tbody tr", function (e) {
            if ($(e.target).is("a") || $(e.target).is("button")) return;

            // Toggle selection on this row
            $(this).toggleClass("selected");
            
            const compoundName = $(this).data("compound-name");
            if (compoundName) {
                if ($(this).hasClass("selected")) {
                    addSelectedCompound(compoundName);
                } else {
                    removeSelectedCompound(compoundName);
                }
            }
        });

        // Handle compound link clicks
        $("#compound_table").on("click", ".compound-link", function (e) {
            const url = $(this).attr("href");
            $("#compound-frame").attr("src", url);
            positionNodes(window.cy);
        });
    } else {
        console.error("Dashboard container not found");
        return;
    }
});

function addSelectedCompound(compoundName) {
    if (!window.cy) {
        console.error("Cytoscape instance not available");
        return;
    }

    // Find the compound element
    const compoundElement = window.allCompoundElements.find(el => 
        el.data.label === compoundName
    );

    if (!compoundElement) {
        console.error("Compound not found:", compoundName);
        return;
    }

    // Add the compound if it doesn't exist
    try {
        window.cy.add(compoundElement);
        console.log(`Added compound: ${compoundName}`);
    } catch (error) {
        console.warn("Compound already exists:", compoundName);
    }

    // Show the compound
    window.cy.elements(`[label="${compoundName}"]`).show();
    window.cy.fit(window.cy.elements(), 50);
    positionNodes(window.cy);
    
    // Update button state if any compounds are visible
    const visibleCompounds = window.cy.elements(".chemical-node:visible");
    if (visibleCompounds.length > 0) {
        window.compoundsVisible = true;
        $("#toggle_compounds").text("Hide Compounds");
    }
}

function removeSelectedCompound(compoundName) {
    if (!window.cy) {
        console.error("Cytoscape instance not available");
        return;
    }

    // Remove the specific compound
    window.cy.elements(`[label="${compoundName}"]`).remove();
    console.log(`Removed compound: ${compoundName}`);

    // Update button state based on remaining visible compounds
    const visibleCompounds = window.cy.elements(".chemical-node:visible");
    if (visibleCompounds.length === 0) {
        window.compoundsVisible = false;
        $("#toggle_compounds").text("Show Compounds");
    }

    window.cy.fit(window.cy.elements(), 50);
    positionNodes(window.cy);
}

function showAllCompounds() {
    if (!window.cy || !window.allCompoundElements) {
        console.error("Cytoscape instance or compound data not available");
        return;
    }

    // Remove existing chemical nodes
    window.cy.elements(".chemical-node").remove();

    // Add all compound elements
    window.allCompoundElements.forEach(element => {
        try {
            window.cy.add(element);
        } catch (error) {
            console.warn("Skipping duplicate compound:", element.data.id);
        }
    });

    window.cy.elements(".chemical-node").show();
    
    // Select all rows in the table
    $("#compound_table tbody tr").addClass("selected");
    
    window.cy.fit(window.cy.elements(), 50);
    positionNodes(window.cy);
    
    window.compoundsVisible = true;
    $("#toggle_compounds").text("Hide Compounds");
    console.log(`Showed all ${window.allCompoundElements.length} compounds`);
}

function hideAllCompounds() {
    if (!window.cy) {
        console.error("Cytoscape instance not available");
        return;
    }

    // Remove all chemical nodes and their edges
    window.cy.elements(".chemical-node").remove();
    window.cy.edges("[type='interaction']").remove();
    
    // Clear table selections
    $("#compound_table tbody tr").removeClass("selected");
    
    window.compoundsVisible = false;
    $("#toggle_compounds").text("Show Compounds");
    
    window.cy.fit(window.cy.elements(), 50);
    positionNodes(window.cy);
    console.log("Hidden all compounds");
}

// Simplified toggle function
async function toggleCompounds() {
    if (!window.cy) {
        console.error("Cytoscape instance not available");
        return;
    }
    
    if (window.compoundsVisible) {
        hideAllCompounds();
    } else {
        showAllCompounds();
    }
}

function getAllCIDs() {
    return new Promise((resolve, reject) => {
        if (!window.compoundTableData) {
            reject("Compound table data not loaded");
            return;
        }

        const cids = window.compoundTableData
            .map(compound => compound.cid)
            .filter(cid => cid && cid !== "nan");
        
        console.log('Retrieved CIDs:', cids);
        resolve(cids);
    });
}

// Make functions available globally
window.toggleCompounds = toggleCompounds;
window.showSelectedCompound = addSelectedCompound; // Keep backward compatibility
window.showAllCompounds = showAllCompounds;
window.hideAllCompounds = hideAllCompounds;
window.addSelectedCompound = addSelectedCompound;
window.removeSelectedCompound = removeSelectedCompound;
