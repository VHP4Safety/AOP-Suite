document.addEventListener("DOMContentLoaded", function () {
    // Fetch data for the AOP network.
    function fetchAOPData(mies) {
        console.debug(`Fetching AOP network data for: ${mies}`);
        return fetch(`/get_aop_network?mies=${encodeURIComponent(mies)}`)
            .then(response => response.json())
            .catch(error => {
                console.error("Error fetching AOP data:", error);
                return [];
            });
    }

    function renderAOPNetwork(elements) {
        console.debug("Rendering AOP network with elements:", elements);
        document.getElementById("loading_aop").style.display = "none";

        // Create Cytoscape instance.
        cy = cytoscape({
            container: document.getElementById("cy"),
            elements: elements.map(ele => ({
                data: {
                    id: ele.id,
                    ...ele.data
                }
            })),
        });

        console.debug("Cytoscape instance created with elements:", cy.elements());
        positionNodes(cy);
        console.log('Update gene table');
        toggleGeneView(cy);
        positionNodes(cy);
        populateGeneTable();

        // Node click event.
        cy.on("tap", "node", function (evt) {
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
        
        cy.on("tap", "edge", function(evt) {
            const edge = evt.target;
            if (edge.data("ker_label")) {
                window.open(`https://identifiers.org/aop.relationships/${edge.data("ker_label")}`);
            }
        });

        // Log when nodes are added.
        cy.on("add", "node", function (evt) {
            console.debug(`Node added: ${evt.target.id()}`);
            positionNodes(cy);
        });

        // Toggle Bounding Boxes (AOP boxes) button functionality.
        $("#toggle_bounding_boxes").on("click", function () {
            if (boundingBoxesVisible) {
                console.debug("Removing bounding boxes");
                cy.nodes().forEach(node => {
                    if (node.isChild()) {
                        node.move({ parent: null });
                    }
                });
                cy.elements(".bounding-box").remove();
                boundingBoxesVisible = false;
            } else {
                console.debug("Adding bounding boxes");
                const cyElements = cy.elements().jsons();

                $.ajax({
                    url: `/add_aop_bounding_box?aop=true`,
                    type: "POST",
                    contentType: "application/json",
                    data: JSON.stringify({ cy_elements: cyElements }),
                    success: updatedCyElements => {
                        cy.elements().remove();
                        cy.add(updatedCyElements);
                        console.log("debug");
                        boundingBoxesVisible = true;
                        positionNodes(cy);
                    },
                    error: (jqXHR, textStatus, errorThrown) => {
                        console.error("Error adding bounding boxes:", textStatus, errorThrown);
                        alert(`Error adding bounding boxes: ${textStatus} - ${errorThrown}`);
                    }
                });
            }
        });

        positionNodes(cy);
    }

    // Retrieve the "mies" data.
    const compoundContainer = document.getElementById("compound-container");
    const mies = compoundContainer ? compoundContainer.dataset.mies : null;
    if (mies) {
        fetchAOPData(mies).then(data => {
            console.debug("Fetched AOP data:", data);
            renderAOPNetwork(data);
        });
    } else {
        console.error("No 'mies' data found in compound-container");
    }

    // Reset layout button functionality.
    $("#reset_layout").on("click", function () {
        positionNodes(cy);
    });

    // Add "Download Cytoscape Network" button functionality.
    $("#download_network").on("click", function () {
        const cyJson = cy.json();
        console.log(cyJson);
        const blob = new Blob([JSON.stringify(cyJson)], { type: "application/json" });
        const url = URL.createObjectURL(blob);
        const a = document.createElement("a");
        a.href = url;
        a.download = "cytoscape_network.json";
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        URL.revokeObjectURL(url);
    });
});

function updateCytoscapeSubset() {
    const selectedCompounds = [];
    $("#compound_table tbody tr").each(function () {
        const compoundLink = $(this).find("td:first-child a");
        if (compoundLink.hasClass("selected")) {
            const compoundName = compoundLink.text().trim();
            if (compoundName) {
                selectedCompounds.push(compoundName);
            }
        }
    });

    const cyElements = cy.elements().jsons();
    
    $.ajax({
        url: "/update_cytoscape_subset",
        type: "POST",
        contentType: "application/json",
        data: JSON.stringify({
            selected_compounds: selectedCompounds,
            cy_elements: cyElements
        }),
        success: response => {
            if (response.show_all) {
                cy.elements().show();
                cy.fit(cy.elements(), 50);
            } else {
                cy.elements().hide();
                const visibleElements = cy.collection();
                response.visible_elements.forEach(element => {
                    const cyElement = cy.getElementById(element.data.id);
                    if (!cyElement.empty()) {
                        visibleElements.union(cyElement);
                    }
                });
                visibleElements.show();
                cy.fit(visibleElements, 50);
            }
            positionNodes(cy);
        },
        error: () => {
            console.error("Error updating cytoscape subset");
        }
    });
}

function populateGeneTable() {
    const cyElements = cy.elements().jsons();
    
    $.ajax({
        url: "/populate_gene_table",
        type: "POST",
        contentType: "application/json",
        data: JSON.stringify({ cy_elements: cyElements }),
        success: response => {
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
        },
        error: () => {
            console.error("Error populating gene table");
        }
    });
}

// Event listener for data-type-dropdown option value "qaop_table".
$("#data-type-dropdown").on("change", function () {
    const selectedValue = $(this).val();
    if (selectedValue === "qaop_div") {
        populateQaopTable();
    }
});

function populateQaopTable() {
    const cyElements = cy.elements().jsons();
    
    $.ajax({
        url: "/populate_qaop_table",
        type: "POST",
        contentType: "application/json",
        data: JSON.stringify({ cy_elements: cyElements }),
        success: response => {
            const table = $("#qaop_table");
            document.getElementById("loading_qaop_table").style.display = "none";
            const tableBody = table.find("tbody").empty();
            
            response.qaop_data.forEach(item => {
                tableBody.append(`
                    <tr>
                        <td><a href="${item.source_id}" target="_blank">${item.source_label}</a></td>
                        <td>${item.curie}</td>
                        <td><a href="${item.target_id}" target="_blank">${item.target_label}</a></td>
                    </tr>
                `);
            });
        },
        error: () => {
            console.error("Error populating QAOP table");
        }
    });
}

$("#see_genes").on("click", function () {
    if (genesVisible) {
        console.log("Hiding ", cy.elements(".ensembl-node"));
        cy.elements(".ensembl-node").hide();
        $(this).text("See Genes");
        genesVisible = false; 
    } else {
        console.log("Showing genes");
        toggleGeneView(cy);
        positionNodes(cy);
    }
});

function toggleGeneView(cy) {
    const mieNodeIds = cy.nodes().filter(node => node.data("is_mie")).map(node => node.id()).join(",");
    fetch(`/load_and_show_genes?mies=${encodeURIComponent(mieNodeIds)}`)
        .then(response => response.json())
        .then(data => {
            try {
                data.forEach(element => {
                    try {
                        cy.add(element);
                    } catch (error) {
                        console.warn("Skipping element");
                    }
                });
                console.log(cy.elements(".uniprot-node, .ensembl-node"));
                cy.elements(".uniprot-node, .ensembl-node").show();
                $("#see_genes").text("Hide Genes");
                genesVisible = true;
                populateGeneTable();
            } catch (error) {
                console.warn("Error processing elements:", error);
            }
        })
        .catch(error => {
            console.warn("Error fetching genes data:", error);
        });
}