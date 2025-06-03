// async function to collect all genes
async function getAllGenes() {
    var cy = window.cy;

    if (!genesVisible) {
        console.log("Showing genes");
        await toggleGeneView(cy);
        await positionNodes(cy);
    }

    return new Promise((resolve, reject) => {
        const cyElements = cy.elements().jsons();
        
        $.ajax({
            url: "/get_all_genes",
            type: "POST",
            contentType: "application/json",
            data: JSON.stringify({ cy_elements: cyElements }),
            success: response => {
                console.log('retrieved genes', response.genes);
                resolve(response.genes);
            },
            error: () => {
                reject("Error fetching genes");
            }
        });
    });
}

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

                // Populate the gene table via backend
                populateGeneTable();
            } catch (error) {
                console.warn("Error processing elements:", error);
            }
        })
        .catch(error => {
            console.warn("Error fetching genes data:", error);
        });
}

// Function to populate the gene table with Ensembl nodes - now calls backend
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
            console.log("Gene table populated with Ensembl nodes.");
        },
        error: () => {
            console.error("Error populating gene table");
        }
    });
}