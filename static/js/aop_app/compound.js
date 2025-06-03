$(document).ready(() => {
    const qid = $("#compound-container").data("qid");
    if (!qid) {
        console.error("No 'qid' found in #compound-container.");
        return;
    }

    // Load compound table using backend endpoint
    $.ajax({
        url: `/populate_compound_table/${qid}`,
        type: "GET",
        success: response => {
            const loadingElement = document.getElementById("loading_compound");
            if (loadingElement) {
                loadingElement.style.display = "none";
            }

            window.compoundMapping = response.compound_mapping;
            window.compoundTableData = response.table_data;
            
            const tableBody = $("#compound_table tbody").empty();
            response.table_data.forEach(compound => {
                tableBody.append(`
                    <tr>
                        <td>
                            <img src="${compound.img_url}" alt="${compound.smiles}" />
                            <p>${compound.compound_cell}</p> 
                            <p>PubChem ID: ${compound.pubchem_cell}</p>
                        </td>
                    </tr>
                `);
            });
        },
        error: () => {
            console.error("Failed to fetch compounds. Retrying...");
            setTimeout(() => {
                location.reload();
            }, 400);
        }
    });

    // Enable row selection to filter the Cytoscape network by compound.
    $("#compound_table").on("click", "tbody tr", function (e) {
        if ($(e.target).is("a") || $(e.target).is("button")) return;
        if (!fetched_preds) return;

        const compoundLink = $(this).find("td:first-child a");
        if (compoundLink.length) {
            compoundLink.toggleClass("selected");
            const compoundName = compoundLink.text().trim();
            if (compoundName) {
                const cyNode = cy.nodes(`[label="${compoundName}"]`);
                if (cyNode.length) {
                    cyNode.toggleClass("selected");
                }
            }
        }

        updateCytoscapeSubset();
        positionNodes(cy);
    });

    // Handle compound link
    $("#compound_table").on("click", ".compound-link", function (e) {
        const url = $(this).attr("href");
        $("#compound-frame").attr("src", url);
        positionNodes(cy);
    });
});

// function to collect all cids
function getAllCIDs() {
    return new Promise((resolve, reject) => {
        if (!window.compoundTableData) {
            reject("Compound table data not loaded");
            return;
        }

        $.ajax({
            url: "/get_all_cids",
            type: "POST",
            contentType: "application/json",
            data: JSON.stringify({ table_data: window.compoundTableData }),
            success: response => {
                console.log('retrieved cids', response.cids);
                resolve(response.cids);
            },
            error: () => {
                reject("Error fetching CIDs");
            }
        });
    });
}

function updateCytoscapeSubset() {
    const selectedCompounds = [];

    // Collect the names of compounds that are selected in the table.
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
        cy.elements().show();
        cy.fit(cy.elements(), 50);
        return;
    }

    const visited = new Set();
    let activated = cy.collection();

    // Breadth-first search function to traverse outgoing edges.
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

    // Start BFS from selected chemical nodes.
    selectedCompounds.forEach(compoundName => {
        const node = cy.nodes(`[label="${compoundName}"]`);
        if (!node.empty() && node.hasClass("chemical-node")) {
            bfs(node);
        }
    });

    // Keep only edges connecting activated nodes.
    const activatedEdges = cy.edges().filter(edge =>
        activated.contains(edge.source()) && activated.contains(edge.target())
    );

    cy.elements().hide();
    activated.show();
    activatedEdges.show();
    cy.fit(activated, 50);
    positionNodes(cy);
}
