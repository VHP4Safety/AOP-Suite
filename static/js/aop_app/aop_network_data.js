// AOP Network Data Addition functionality

class AOPNetworkDataManager {
    constructor() {
        console.log('=== AOPNetworkDataManager Constructor ===');
        this.setupEventHandlers();
    }

    setupEventHandlers() {
        console.log('=== Setting up AOP Network Data Event Handlers ===');
        
        // Add AOP data button
        const addAopDataBtn = document.getElementById('add-aop-data');
        console.log('Add AOP data button found:', !!addAopDataBtn);
        
        if (addAopDataBtn) {
            addAopDataBtn.addEventListener('click', () => {
                console.log('Add AOP data button clicked');
                this.addAopNetworkData();
            });
        }

        // Query type change handler
        const queryTypeSelect = document.getElementById('query-type');
        console.log('Query type select found:', !!queryTypeSelect);
        
        if (queryTypeSelect) {
            queryTypeSelect.addEventListener('change', () => {
                console.log('Query type changed to:', queryTypeSelect.value);
                this.updateExampleText();
            });
        }
    }

    updateExampleText() {
        const queryType = document.getElementById('query-type').value;
        const helpText = document.querySelector('#query-values + .form-text');
        
        console.log('Updating example text for query type:', queryType);
        console.log('Help text element found:', !!helpText);

        if (!helpText) return;

        const examples = {
            'mie': 'Examples:<br>• Full URIs: https://identifiers.org/aop.events/1 https://identifiers.org/aop.events/2<br>• Short form: 1 2 3<br>• Prefixed: aop.events:1 aop.events:2<br><br><strong>Popular MIEs to try:</strong><br>• 17 (Aromatase inhibition)<br>• 25 (Thyroperoxidase inhibition)<br>• 109 (Histone deacetylase inhibition)',
            'aop': 'Examples:<br>• Full URIs: https://identifiers.org/aop/1 https://identifiers.org/aop/2<br>• Short form: 1 2 3<br>• Prefixed: aop:1 aop:2<br><br><strong>Popular AOPs to try:</strong><br>• 13 (Chronic binding of antagonist to N-methyl-D-aspartate receptors)<br>• 42 (Inhibition of thyroperoxidase activity)<br>• 54 (Inhibition of Na+/I- symporter)',
            'ke_upstream': 'Examples:<br>• Full URIs: https://identifiers.org/aop.events/3 https://identifiers.org/aop.events/4<br>• Short form: 3 4 5<br>• Prefixed: aop.events:3 aop.events:4<br><br><strong>Popular KEs to try:</strong><br>• 188 (Decreased, Triiodothyronine in serum)<br>• 280 (Decreased, Neuronal network function)',
            'ke_downstream': 'Examples:<br>• Full URIs: https://identifiers.org/aop.events/5 https://identifiers.org/aop.events/6<br>• Short form: 5 6 7<br>• Prefixed: aop.events:5 aop.events:6<br><br><strong>Popular KEs to try:</strong><br>• 188 (Decreased, Triiodothyronine in serum)<br>• 280 (Decreased, Neuronal network function)'
        };

        helpText.innerHTML = examples[queryType] || 'Enter space-separated URIs or identifiers...';
    }

    async addAopNetworkData() {
        console.log('=== Adding AOP Network Data ===');
        
        if (!window.cy) {
            console.error('Cytoscape instance not available');
            this.showStatus('Network not initialized', 'error');
            return;
        }

        const queryType = document.getElementById('query-type').value;
        const values = document.getElementById('query-values').value.trim();

        console.log('Query type:', queryType);
        console.log('Values:', values);

        if (!values) {
            console.warn('No values provided');
            this.showStatus('Please enter values to query', 'error');
            return;
        }

        // Show helpful message for first-time users
        if (window.cy.elements().length === 0) {
            this.showStatus('Building your first network...', 'loading');
        } else {
            this.showStatus('Adding data to existing network...', 'loading');
        }

        const requestData = {
            query_type: queryType,
            values: values
        };
        
        console.log('Request data:', requestData);

        try {
            console.log('Making fetch request to /add_aop_network_data');
            
            const response = await fetch('/add_aop_network_data', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify(requestData)
            });

            console.log('Response status:', response.status);
            console.log('Response ok:', response.ok);

            if (!response.ok) {
                console.error('Response not ok, status:', response.status);
                const errorText = await response.text();
                console.error('Error response text:', errorText);
                throw new Error(`HTTP ${response.status}: ${errorText}`);
            }

            console.log('Parsing JSON response...');
            const result = await response.json();
            console.log('Parsed result:', result);

            if (result.error) {
                console.error('Server returned error:', result.error);
                throw new Error(result.error);
            }

            if (result.success && result.elements && result.elements.length > 0) {
                console.log(`Successfully received ${result.elements_count} elements`);
                
                this.addElementsToNetwork(result.elements);
                
                // Hide the loading overlay if this is the first network data
                const loadingOverlay = document.querySelector(".loading-overlay");
                if (loadingOverlay && window.cy.elements().length > 0) {
                    loadingOverlay.style.display = "none";
                }
                
                this.showStatus(
                    `Successfully added ${result.elements_count} elements to the network`, 
                    'success'
                );
                
                // Clear the input
                document.getElementById('query-values').value = '';
            } else {
                console.warn('No elements returned or success=false');
                this.showStatus('No new data found for the specified values', 'warning');
            }

        } catch (error) {
            console.error('Error in addAopNetworkData:', error);
            this.showStatus(`Error: ${error.message}`, 'error');
        }
    }

    addElementsToNetwork(elements) {
        console.log('=== Adding Elements to Network ===');
        console.log('Elements to add:', elements.length);
        
        if (!window.cy || !elements || elements.length === 0) {
            console.warn('Cannot add elements - cy or elements invalid');
            return;
        }

        // Track existing element IDs to avoid duplicates
        const existingIds = new Set();
        window.cy.elements().forEach(element => {
            existingIds.add(element.id());
        });
        
        console.log('Existing element IDs:', existingIds.size);

        const newElements = [];
        
        // Filter out existing elements
        elements.forEach((element, index) => {
            const elementId = element.data?.id;
            if (elementId && !existingIds.has(elementId)) {
                newElements.push(element);
                if (index < 5) {  // Log first few elements
                    console.log(`New element ${index}:`, element);
                }
            } else {
                if (index < 5) {
                    console.log(`Skipping duplicate element ${index}:`, elementId);
                }
            }
        });

        console.log('New elements to add:', newElements.length);

        if (newElements.length > 0) {
            // Add new elements to the network
            try {
                console.log('Adding elements to Cytoscape...');
                window.cy.add(newElements);
                console.log('Elements added successfully');
                
                // Reposition nodes
                if (window.positionNodes) {
                    console.log('Repositioning nodes...');
                    window.positionNodes(window.cy);
                }
                
                console.log(`Successfully added ${newElements.length} new elements to the network`);
            } catch (cyError) {
                console.error('Error adding elements to Cytoscape:', cyError);
                this.showStatus(`Error adding elements to network: ${cyError.message}`, 'error');
            }
        } else {
            console.log('All elements already exist in the network');
        }
    }

    showStatus(message, type = 'info') {
        console.log(`Status [${type}]:`, message);
        
        const statusDiv = document.getElementById('aop-data-status');
        if (!statusDiv) {
            console.warn('Status div not found');
            return;
        }

        // Clear existing content
        statusDiv.innerHTML = '';

        const icons = {
            'loading': 'fas fa-spinner fa-spin',
            'success': 'fas fa-check',
            'error': 'fas fa-exclamation-triangle',
            'warning': 'fas fa-exclamation-circle',
            'info': 'fas fa-info-circle'
        };

        const colors = {
            'loading': '#6c757d',
            'success': '#28a745',
            'error': '#dc3545',
            'warning': '#ffc107',
            'info': '#17a2b8'
        };

        statusDiv.innerHTML = `
            <div style="color: ${colors[type]}; font-size: 0.8rem; margin-top: 0.5rem;">
                <i class="${icons[type]}"></i> ${message}
            </div>
        `;

        // Auto-clear success messages after 5 seconds
        if (type === 'success') {
            setTimeout(() => {
                if (statusDiv.innerHTML.includes(message)) {
                    statusDiv.innerHTML = '';
                }
            }, 5000);
        }
    }
}

// Initialize AOP network data manager
let aopNetworkDataManager;

function initializeAOPNetworkData() {
    console.log('=== Initializing AOP Network Data Manager ===');
    
    if (!aopNetworkDataManager) {
        aopNetworkDataManager = new AOPNetworkDataManager();
        console.log('AOP Network Data Manager initialized successfully');
    } else {
        console.log('AOP Network Data Manager already initialized');
    }
}

// Make available globally
window.initializeAOPNetworkData = initializeAOPNetworkData;
window.aopNetworkDataManager = aopNetworkDataManager;

// Initialize when DOM is ready
document.addEventListener('DOMContentLoaded', () => {
    console.log('DOM loaded, initializing AOP Network Data Manager');
    initializeAOPNetworkData();
});
