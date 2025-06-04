// QAOP Table functionality

document.addEventListener("DOMContentLoaded", function() {
    // Event listener for data-type-dropdown option value "qaop_table"
    $("#data-type-dropdown").on("change", function () {
        const selectedValue = $(this).val();
        if (selectedValue === "qaop_div") {
            populateQaopTable();
        }
    });
});

function populateQaopTable() {
    if (!window.cy) {
        console.error("Cytoscape instance not available");
        return;
    }
    
    const cyElements = window.cy.elements().jsons();
    
    $.ajax({
        url: "/populate_qaop_table",
        type: "POST",
        contentType: "application/json",
        data: JSON.stringify({ cy_elements: cyElements }),
        success: response => {
            const table = $("#qaop_table");
            document.getElementById("loading_qaop_table").style.display = "none";
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
            document.getElementById("loading_qaop_table").style.display = "none";
        }
    });
}

// Make function available globally
window.populateQaopTable = populateQaopTable;
