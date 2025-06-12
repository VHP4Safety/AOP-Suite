// AOP Table functionality

document.addEventListener("DOMContentLoaded", function() {
    console.log("AOP table module loaded");
    
    // Always populate AOP table when DOM is ready - with delay to ensure cy is ready
    setTimeout(() => {
        if (window.cy && window.cy.elements().length > 0) {
            console.log("Initial AOP table population");
            populateAopTable();
        } else {
            console.log("No elements in network yet, showing empty state");
            showEmptyAopTable();
        }
    }, 2000);
});

function populateAopTable() {
    console.log("populateAopTable called");
    
    if (!window.cy) {
        console.error("Cytoscape instance not available");
        showEmptyAopTable();
        return;
    }
    
    const cyElements = window.cy.elements().jsons();
    console.log("Sending", cyElements.length, "elements to backend");
    
    // Show loading indicator
    const loadingElement = document.getElementById("loading_aop_table");
    if (loadingElement) {
        loadingElement.style.display = "block";
    }
    
    $.ajax({
        url: "/populate_qaop_table", // Keep backend endpoint name for now
        type: "POST",
        contentType: "application/json",
        data: JSON.stringify({ cy_elements: cyElements }),
        success: response => {
            console.log("AOP table response received:", response);
            
            // Make sure we target the correct table
            const table = $("#aop_table").last(); // Get the last one (always-visible table)
            const loadingElement = document.getElementById("loading_aop_table");
            if (loadingElement) {
                loadingElement.style.display = "none";
            }
            
            const tableBody = table.find("tbody").empty();
            console.log("Table body found:", tableBody.length, "elements");
            
            if (response.qaop_data && response.qaop_data.length > 0) {
                response.qaop_data.forEach((item, index) => {
                    const row = `
                        <tr>
                            <td><a href="${item.source_id}" target="_blank">${item.source_label}</a></td>
                            <td>${item.curie}</td>
                            <td><a href="${item.target_id}" target="_blank">${item.target_label}</a></td>
                        </tr>
                    `;
                    tableBody.append(row);
                    console.log(`Added row ${index + 1}:`, item);
                });
                console.log("AOP table populated with", response.qaop_data.length, "rows.");
            } else {
                showEmptyAopTable();
                console.log("No AOP data available");
            }
        },
        error: (xhr, status, error) => {
            console.error("Error populating AOP table:", error);
            const tableBody = $("#aop_table").last().find("tbody").empty();
            tableBody.append(`
                <tr>
                    <td colspan="3" style="text-align: center; color: #dc3545;">
                        Error loading AOP data
                    </td>
                </tr>
            `);
            const loadingElement = document.getElementById("loading_aop_table");
            if (loadingElement) {
                loadingElement.style.display = "none";
            }
        }
    });
}

function showEmptyAopTable() {
    const tableBody = $("#aop_table").last().find("tbody").empty();
    tableBody.append(`
        <tr>
            <td colspan="3" style="text-align: center; color: #6c757d; font-style: italic;">
                No relationships in current network
            </td>
        </tr>
    `);
    console.log("Showing empty AOP table state");
}

// Make function available globally and ensure it's immediately available
window.populateAopTable = populateAopTable;
