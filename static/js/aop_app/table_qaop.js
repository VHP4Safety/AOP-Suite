// QAOP Table functionality

document.addEventListener("DOMContentLoaded", function() {
    // Function will be called by select_data.js when option is selected
    console.log("QAOP table module loaded");
});

function populateQaopTable() {
    if (!window.cy) {
        console.error("Cytoscape instance not available");
        return;
    }
    
    const cyElements = window.cy.elements().jsons();
    
    // Show loading indicator
    const loadingElement = document.getElementById("loading_qaop_table");
    if (loadingElement) {
        loadingElement.style.display = "block";
    }
    
    $.ajax({
        url: "/populate_qaop_table",
        type: "POST",
        contentType: "application/json",
        data: JSON.stringify({ cy_elements: cyElements }),
        success: response => {
            const table = $("#qaop_table");
            const loadingElement = document.getElementById("loading_qaop_table");
            if (loadingElement) {
                loadingElement.style.display = "none";
            }
            
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
                console.log("No QAOP data available");
            }
        },
        error: (xhr, status, error) => {
            console.error("Error populating QAOP table:", error);
            const tableBody = $("#qaop_table tbody").empty();
            tableBody.append('<tr><td colspan="3">Error loading QAOP data</td></tr>');
            const loadingElement = document.getElementById("loading_qaop_table");
            if (loadingElement) {
                loadingElement.style.display = "none";
            }
        }
    });
}

// Make function available globally
window.populateQaopTable = populateQaopTable;
