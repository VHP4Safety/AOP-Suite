// Gene-related functionality - simplified to use backend endpoints

async function getAllGenes() {
    if (!window.cy) {
        throw new Error("Cytoscape instance not available");
    }

    // If genes aren't visible, show them first to get gene data
    if (!window.genesVisible) {
        console.log("Showing genes first to get gene data");
        await toggleGenes();
    }

    return new Promise((resolve, reject) => {
        const cyElements = window.cy.elements().jsons();
        
        $.ajax({
            url: "/get_all_genes",
            type: "POST",
            contentType: "application/json",
            data: JSON.stringify({ cy_elements: cyElements }),
            success: response => {
                console.log('Retrieved genes:', response.genes);
                resolve(response.genes || []);
            },
            error: (xhr, status, error) => {
                console.error("Error fetching genes:", error);
                reject(`Error fetching genes: ${error}`);
            }
        });
    });
}

// Simplified toggle function that uses the backend endpoint
async function toggleGenes() {
    if (!window.cy) {
        console.error("Cytoscape instance not available");
        return;
    }
    
    const action = window.genesVisible ? 'hide' : 'show';
    
    try {
        const response = await fetch('/toggle_genes', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ 
                action: action,
                cy_elements: window.cy.elements().jsons() 
            })
        });
        
        if (!response.ok) {
            throw new Error(`HTTP ${response.status}: ${response.statusText}`);
        }
        
        const data = await response.json();
        
        if (data.error) {
            console.error("Gene toggle error:", data.error);
            return;
        }
        
        if (action === 'show' && data.gene_elements) {
            data.gene_elements.forEach(element => {
                try {
                    window.cy.add(element);
                } catch (error) {
                    console.warn("Skipping duplicate element:", element.data?.id);
                }
            });
            
            // Show all gene nodes
            window.cy.elements(".uniprot-node, .ensembl-node").show();
            
            // Show all edges connected to visible gene nodes
            window.cy.edges().forEach(function(edge) {
                const source = edge.source();
                const target = edge.target();
                
                // Show edge if both source and target are visible
                if (source.visible() && target.visible()) {
                    edge.show();
                }
            });
            
            $("#see_genes").html('<i class="fas fa-dna"></i> Hide Genes');
            window.genesVisible = true;
            
            // Populate the gene table after showing genes
            if (window.populateGeneTable) {
                await window.populateGeneTable();
            }
        } else if (action === 'hide') {
            // Hide gene nodes
            window.cy.elements(".uniprot-node, .ensembl-node").hide();
            
            // Hide edges connected to gene nodes (but don't remove them)
            window.cy.edges().forEach(function(edge) {
                const source = edge.source();
                const target = edge.target();
                
                // Hide edge if either end is a gene node
                if (source.hasClass("uniprot-node") || source.hasClass("ensembl-node") ||
                    target.hasClass("uniprot-node") || target.hasClass("ensembl-node")) {
                    edge.hide();
                }
            });
            
            $("#see_genes").html('<i class="fas fa-dna"></i> See Genes');
            window.genesVisible = false;
        }
        
        positionNodes(window.cy);
    } catch (error) {
        console.error("Error toggling genes:", error);
        console.error("Check that the /toggle_genes endpoint exists and returns valid JSON");
    }
}

// Make sure gene table is always populated when the page loads
$(document).ready(function() {
    // Wait for Cytoscape to be initialized before populating gene table
    setTimeout(() => {
        if (window.cy && window.populateGeneTable) {
            window.populateGeneTable();
        }
    }, 1000);
});

// Make functions available globally
window.getAllGenes = getAllGenes;
window.toggleGenes = toggleGenes;