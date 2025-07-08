// AOP Table functionality

// Function to populate the AOP relationships table
function populateAopTable() {
    console.log('Populating AOP table from network data');
    
    if (!window.cy) {
        console.warn('Cytoscape instance not available for AOP table population');
        return;
    }
    
    const tableBody = $("#aop_table tbody");
    const loadingDiv = $("#loading_aop_table");
    
    // Show loading indicator
    loadingDiv.show();
    
    try {
        // Get current network elements
        const cyElements = window.cy.elements().jsons();
        
        // Call backend to process the elements into AOP table data
        $.ajax({
            url: "/populate_aop_table",
            type: "POST",
            contentType: "application/json",
            data: JSON.stringify({ cy_elements: cyElements }),
            success: function(response) {
                loadingDiv.hide();
                
                if (response.error) {
                    console.error('Error from backend:', response.error);
                    showEmptyAopTable();
                    return;
                }
                
                const aopData = response.aop_data || [];
                console.log('Received AOP table data:', aopData);
                
                if (aopData.length === 0) {
                    showEmptyAopTable();
                    return;
                }
                
                // Clear existing table content with smooth transition
                tableBody.fadeOut(200, function() {
                    tableBody.empty();
                    
                    // Populate table with new data
                    aopData.forEach(row => {
                        const tr = $("<tr></tr>");
                        
                        // Source column
                        tr.append(`<td title="${row.source_id}">${row.source_label}</td>`);
                        
                        // Relationship column with CURIE link
                        const relationshipCell = $("<td></td>");
                        if (row.curie) {
                            const curieLink = `<a href="#" class="curie-link" data-curie="${row.curie}" title="${row.curie}">${row.curie.split(':')[1] || row.curie}</a>`;
                            relationshipCell.html(curieLink);
                        } else {
                            relationshipCell.text('N/A');
                        }
                        tr.append(relationshipCell);
                        
                        // Target column
                        tr.append(`<td title="${row.target_id}">${row.target_label}</td>`);
                        
                        tableBody.append(tr);
                    });
                    
                    // Fade in the updated table content
                    tableBody.fadeIn(300);
                    console.log(`Populated AOP table with ${aopData.length} relationships`);
                });
            },
            error: function(xhr, status, error) {
                loadingDiv.hide();
                console.error('Error fetching AOP table data:', error);
                showEmptyAopTable();
            }
        });
        
    } catch (error) {
        loadingDiv.hide();
        console.error('Error in populateAopTable:', error);
        showEmptyAopTable();
    }
}

// Function to show empty table state with smooth transition
function showEmptyAopTable() {
    const tableBody = $("#aop_table tbody");
    tableBody.fadeOut(200, function() {
        tableBody.empty();
        tableBody.append(`
            <tr>
                <td colspan="3" style="text-align: center; color: #6c757d; font-style: italic;">
                    No relationships in current network
                </td>
            </tr>
        `);
        tableBody.fadeIn(300);
    });
}

// Function to handle CURIE link clicks
$(document).on('click', '.curie-link', function(e) {
    e.preventDefault();
    const curie = $(this).data('curie');
    console.log('CURIE clicked:', curie);
    
    // You can implement navigation to AOP Wiki or other actions here
    if (curie && curie.includes('aop.relationships:')) {
        const kerId = curie.split(':')[1];
        const aopWikiUrl = `https://aopwiki.org/relationships/${kerId}`;
        window.open(aopWikiUrl, '_blank');
    }
});

// Auto-populate table when network changes with debounced smooth updates
function setupAopTableListeners() {
    if (!window.cy) {
        console.log('Cytoscape not ready, will setup AOP table listeners later');
        return;
    }
    
    console.log('Setting up AOP table network listeners');
    
    // Listen for network changes with smooth transitions
    window.cy.on('add remove', function(event) {
        console.log('Network changed, updating AOP table with smooth transition');
        // Debounce rapid changes and add smooth transition
        clearTimeout(window.aopTableUpdateTimeout);
        window.aopTableUpdateTimeout = setTimeout(() => {
            // Add a subtle loading indicator during updates
            const tableBody = $("#aop_table tbody");
            tableBody.addClass('updating');
            
            setTimeout(() => {
                populateAopTable();
                tableBody.removeClass('updating');
            }, 100);
        }, 500);
    });
}

// Initialize AOP table functionality
function initializeAopTable() {
    console.log('Initializing AOP table functionality');
    
    // Set up listeners if Cytoscape is ready
    if (window.cy) {
        setupAopTableListeners();
        populateAopTable(); // Initial population
    } else {
        // Wait for Cytoscape to be ready
        const checkCytoscape = setInterval(() => {
            if (window.cy) {
                clearInterval(checkCytoscape);
                setupAopTableListeners();
                populateAopTable();
            }
        }, 500);
        
        // Clear interval after 10 seconds to avoid infinite checking
        setTimeout(() => {
            clearInterval(checkCytoscape);
        }, 10000);
    }
}

// Make functions available globally
window.populateAopTable = populateAopTable;
window.initializeAopTable = initializeAopTable;
window.setupAopTableListeners = setupAopTableListeners;

// Initialize when DOM is ready
$(document).ready(function() {
    initializeAopTable();
});
