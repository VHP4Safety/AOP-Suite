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
            'mie': 'Enter one per line:<br>• Search by name: "liver fibrosis", "reproductive dysfunction"<br>• Or enter IDs: 1, aop.events:1, https://identifiers.org/aop.events/1<br>• Mix both approaches as needed',
            'aop': 'Enter one AOP per line:<br>• Search by name: "liver fibrosis", "reproductive dysfunction"<br>• Or enter IDs: 1, aop:1, https://identifiers.org/aop/1<br>• Mix both approaches as needed',
            'ke_upstream': 'Enter one per line:<br>• Search by name: "liver fibrosis", "reproductive dysfunction"<br>• Or enter IDs: 3, aop.events:3, https://identifiers.org/aop.events/3<br>• Mix both approaches as needed',
            'ke_downstream': 'Enter one per line:<br>• Search by name: "liver fibrosis", "reproductive dysfunction"<br>• Or enter IDs: 5, aop.events:5, https://identifiers.org/aop.events/5<br>• Mix both approaches as needed'
        };

        helpText.innerHTML = examples[queryType] || 'Enter values...';
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

        // Parse multiple values from the textarea
        const normalizedValues = this.parseQueryValues(values);
        
        if (normalizedValues.length === 0) {
            this.showStatus('No valid values found', 'error');
            return;
        }

        // Filter out null values
        const validValues = normalizedValues.filter(v => v !== null);
        
        if (validValues.length === 0) {
            this.showStatus('No valid identifiers found.', 'error');
            return;
        }
        
        if (validValues.length < normalizedValues.length) {
            this.showStatus(`Processing ${validValues.length} valid value(s) out of ${normalizedValues.length} entered...`, 'warning');
        } else {
            this.showStatus(`Processing ${validValues.length} value(s)...`, 'info');
        }

        const requestData = {
            query_type: queryType,
            values: validValues.join(' ') // Join with spaces for backend
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

                let statusMessage = `Successfully added ${result.elements_count} elements from ${validValues.length} ${queryType} value(s)`;
                
                // Show warning popup if backup query was used
                if (result.warning && result.warning.type === 'incomplete_aop_structure') {
                    this.showIncompleteAopWarning(result.warning);
                    statusMessage += ' (with limitations)';
                }

                this.showStatus(statusMessage, 'success');

                // Clear the input
                document.getElementById('query-values').value = '';
            } else {
                console.warn('No elements returned or success=false');
                this.showStatus(`No new data found for the ${validValues.length} specified ${queryType} value(s)`, 'warning');
            }

        } catch (error) {
            console.error('Error in addAopNetworkData:', error);
            this.showStatus(`Error: ${error.message}`, 'error');
        }
    }

    // Parse query values from textarea (one per line) or input (space/comma separated)
    parseQueryValues(queryString) {
        if (!queryString || !queryString.trim()) {
            return [];
        }
        
        const values = [];
        
        // Check if it contains newlines (textarea input)
        if (queryString.includes('\n')) {
            // Split by lines and process each
            const lines = queryString.split('\n');
            lines.forEach(line => {
                const trimmedLine = line.trim();
                if (trimmedLine) {
                    values.push(this.normalizeIdentifier(trimmedLine));
                }
            });
        } else {
            // Original logic for space/comma separated values
            const rawValues = queryString.includes(',') 
                ? queryString.split(',') 
                : queryString.split(/\s+/);
            
            rawValues.forEach(value => {
                const trimmedValue = value.trim();
                if (trimmedValue) {
                    values.push(this.normalizeIdentifier(trimmedValue));
                }
            });
        }
        
        return values;
    }

    // Enhanced normalize identifier function
    normalizeIdentifier(identifier) {
        if (!identifier || !identifier.trim()) {
            return null;
        }
        
        const trimmed = identifier.trim();
        const queryType = document.getElementById('query-type').value;
        
        // If it's already a full URI, return as-is
        if (trimmed.includes('identifiers.org/')) {
            return trimmed;
        }
        
        // Handle based on query type
        if (window.aopNameUtils) {
            if (queryType === 'aop') {
                // Handle AOP identifiers
                if (window.aopNameUtils.isIdentifierFormat(trimmed)) {
                    return window.aopNameUtils.normalizeAopId(trimmed);
                }
                
                // For text searches, try to find matching AOP
                const results = window.aopNameUtils.findAopByText(trimmed);
                if (results.length > 0) {
                    return results[0].fullUri;
                }
                
                // If no match found, try to treat as ID anyway
                if (/^\d+$/.test(trimmed)) {
                    return `https://identifiers.org/aop/${trimmed}`;
                }
            } else {
                // Handle KE identifiers (for MIE, ke_upstream, ke_downstream)
                if (window.aopNameUtils.isKeIdentifierFormat(trimmed)) {
                    return window.aopNameUtils.normalizeKeId(trimmed);
                }
                
                // For text searches, try to find matching KE
                const results = window.aopNameUtils.findKeByText(trimmed);
                if (results.length > 0) {
                    return results[0].fullUri;
                }
                
                // If no match found, try to treat as ID anyway
                if (/^\d+$/.test(trimmed)) {
                    return `https://identifiers.org/aop.events/${trimmed}`;
                }
            }
        }
        
        // Last resort: return original
        return trimmed;
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
        const validNodes = new Set();
        const skippedEdges = [];

        // First pass: collect all valid nodes and track node IDs
        elements.forEach((element, index) => {
            const elementId = element.data?.id;
            
            if (!elementId) {
                console.warn(`Element ${index} has no ID, skipping:`, element);
                return;
            }
            
            if (existingIds.has(elementId)) {
                if (index < 5) {
                    console.log(`Skipping duplicate element ${index}:`, elementId);
                }
                return;
            }

            // If it's a node (no source/target) or has group 'nodes'
            if (!element.data?.source && !element.data?.target || element.group === 'nodes') {
                newElements.push(element);
                validNodes.add(elementId);
                if (index < 5) {
                    console.log(`New node element ${index}:`, element);
                }
            }
        });

        // Add existing nodes to valid nodes set
        window.cy.nodes().forEach(node => {
            validNodes.add(node.id());
        });

        // Second pass: handle edges - be more permissive for incomplete AOP structures
        elements.forEach((element, index) => {
            const elementId = element.data?.id;
            
            if (!elementId || existingIds.has(elementId)) {
                return; // Skip duplicates and invalid elements
            }

            // If it's an edge (has source and target) or has group 'edges'
            if ((element.data?.source && element.data?.target) || element.group === 'edges') {
                const source = element.data?.source;
                const target = element.data?.target;
                
                // Basic validation - ensure we have source and target
                if (!source || !target) {
                    console.warn(`Edge ${elementId} has missing source or target:`, { source, target });
                    skippedEdges.push({ id: elementId, reason: 'Missing source or target' });
                    return;
                }
                
                // For incomplete AOP structures, we'll be more lenient
                // Check if both source and target nodes exist, but don't skip if they don't
                const sourceExists = validNodes.has(source);
                const targetExists = validNodes.has(target);
                
                if (!sourceExists || !targetExists) {
                    console.warn(`Edge ${elementId} references potentially missing nodes: source=${source} (exists: ${sourceExists}), target=${target} (exists: ${targetExists})`);
                    // Still add the edge - Cytoscape will handle missing nodes gracefully
                    // This allows us to preserve the graph structure even with incomplete data
                }
                
                // Add the edge regardless - let Cytoscape handle it
                newElements.push(element);
                if (index < 5) {
                    console.log(`New edge element ${index}:`, element);
                }
            }
        });

        console.log('New elements to add:', newElements.length);
        if (skippedEdges.length > 0) {
            console.warn('Skipped edges due to missing source/target:', skippedEdges);
        }

        if (newElements.length > 0) {
            // Add new elements to the network with batch operation for smooth animation
            try {
                console.log('Adding elements to Cytoscape...');
                
                window.cy.batch(() => {
                    // Add elements one by one with error handling for individual elements
                    const successfullyAdded = [];
                    newElements.forEach((element, index) => {
                        try {
                            window.cy.add(element);
                            successfullyAdded.push(element);
                        } catch (elementError) {
                            console.warn(`Failed to add element ${index} (${element.data?.id}):`, elementError.message);
                            // Continue with other elements
                        }
                    });

                    console.log(`Successfully added ${successfullyAdded.length} out of ${newElements.length} elements`);

                    setTimeout(() => {
                        // Use the animated layout approach
                        const layout = window.cy.layout({
                            name: 'breadthfirst',
                            directed: true,
                            padding: 30,
                            animate: true,
                            animationDuration: 500,
                            animationEasing: 'ease-out',
                            fit: true
                        });

                        // Run the layout
                        layout.run();

                        // After layout animation completes, apply styles smoothly
                        layout.one('layoutstop', function () {
                            // Apply styles with updated font size and smooth transitions
                            if (window.positionNodes) {
                                window.positionNodes(window.cy);
                            }
                        });
                    }, 100);

                });
                
                console.log('Elements added successfully');

                // Reposition nodes with smooth animation
                if (window.positionNodes) {
                    console.log('Repositioning nodes with smooth animation...');
                    const fontSlider = document.getElementById('font-size-slider');
                    const fontSizeMultiplier = fontSlider ? parseFloat(fontSlider.value) : 0.5;
                    
                    setTimeout(() => {
                        window.positionNodes(window.cy, fontSizeMultiplier, true);
                    }, 100);
                }

                // Manually trigger AOP table update after adding network data
                if (window.populateAopTable) {
                    console.log('Triggering AOP table update after network data addition');
                    setTimeout(() => {
                        window.populateAopTable();
                    }, 300);
                }

                console.log(`Successfully processed ${newElements.length} new elements to the network`);
            } catch (cyError) {
                console.error('Error adding elements to Cytoscape:', cyError);
                this.showStatus(`Error adding elements to network: ${cyError.message}`, 'error');
            }
        } else {
            console.log('All elements already exist in the network or were invalid');
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

    showIncompleteAopWarning(warning) {
        // Create modal HTML
        const modalHtml = `
            <div class="modal fade" id="aopWarningModal" tabindex="-1" role="dialog" aria-labelledby="aopWarningModalLabel" aria-hidden="true">
                <div class="modal-dialog" role="document">
                    <div class="modal-content">
                        <div class="modal-header bg-warning">
                            <h5 class="modal-title" id="aopWarningModalLabel">
                                <i class="fas fa-exclamation-triangle"></i> AOP Structure Warning
                            </h5>
                            <button type="button" class="close" data-dismiss="modal" aria-label="Close">
                                <span aria-hidden="true">&times;</span>
                            </button>
                        </div>
                        <div class="modal-body">
                            <p><strong>Limited AOP data retrieved:</strong></p>
                            <p>${warning.message}</p>
                            <div class="alert alert-info">
                                <strong>What this means:</strong><br>
                                ${warning.details}
                            </div>
                            <p><strong>Impact on your network:</strong></p>
                            <ul>
                                <li>You'll see the main AOP components (MIE and Adverse Outcome)</li>
                                <li>Key Event Relationships (KERs) between intermediate steps may be missing</li>
                                <li>The network may appear less connected than expected</li>
                            </ul>
                        </div>
                        <div class="modal-footer">
                            <button type="button" class="btn btn-secondary" data-dismiss="modal">Understood</button>
                            <button type="button" class="btn btn-primary" onclick="window.open('https://aopwiki.org/', '_blank')">
                                Visit AOP-Wiki
                            </button>
                        </div>
                    </div>
                </div>
            </div>
        `;

        // Remove existing modal if present
        const existingModal = document.getElementById('aopWarningModal');
        if (existingModal) {
            existingModal.remove();
        }

        // Add modal to page
        document.body.insertAdjacentHTML('beforeend', modalHtml);

        // Show modal using Bootstrap
        if (typeof $ !== 'undefined' && $.fn.modal) {
            $('#aopWarningModal').modal('show');
            
            // Auto-remove modal when hidden
            $('#aopWarningModal').on('hidden.bs.modal', function () {
                $(this).remove();
            });
        } else {
            // Fallback for non-Bootstrap environments
            const modal = document.getElementById('aopWarningModal');
            modal.style.display = 'block';
            modal.classList.add('show');
            
            // Add click handlers for close buttons
            modal.querySelectorAll('[data-dismiss="modal"], .close').forEach(btn => {
                btn.addEventListener('click', () => {
                    modal.style.display = 'none';
                    modal.remove();
                });
            });
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

    // Setup autocomplete for AOP query textarea
    const queryValuesElement = document.getElementById('query-values');
    if (queryValuesElement && window.aopNameUtils) {
        window.aopNameUtils.setupAopAutocomplete(queryValuesElement);
        
        // Update placeholder when query type changes
        const queryTypeSelect = document.getElementById('query-type');
        if (queryTypeSelect) {
            queryTypeSelect.addEventListener('change', () => {
                // Trigger placeholder update after a short delay to ensure aopNameUtils is ready
                setTimeout(() => {
                    if (window.aopNameUtils.updatePlaceholderText) {
                        window.aopNameUtils.updatePlaceholderText();
                    }
                }, 100);
            });
        }
    }
});
