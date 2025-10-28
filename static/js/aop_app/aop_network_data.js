// AOP Network Data Addition functionality

// Update API base URL to work from root
const API_BASE_URL = '';

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
            values: validValues.join(' '), // Join with spaces for backend
            cy_elements: window.cy ? { elements: window.cy.elements().jsons() } : { elements: [] } // Wrap in object with elements key
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
            
            // Perform AOP table update immediately after successful response with API data
            if (result.aop_table && window.aopTableManager) {
                window.aopTableManager.updateTable(result.aop_table);
                console.log('Updated AOP table with API data');
            }
            
            // Add query to history table - fix elements structure
            if (result.success && result.sparql_query && window.historyTableManager && result.elements) {
                // Extract elements array from the elements object
                const elementsArray = result.elements || result.elements;
                window.historyTableManager.addHistoryEntry('aop_network', 'AOP-Wiki RDF', result.sparql_query, null, elementsArray);
            }            
            // Handle the backend response to get data
            if (result.success && result.elements) {
                // Extract the nested elements structure
                const networkData = result.elements;

                // Check structure
                if (networkData.elements && Array.isArray(networkData.elements)) {
                    console.log(`Received ${networkData.elements.length} network elements`);

                    // Hide example text when network appears
                    this.hideExampleText();

                    // Initialize styles from backend if available
                    if (window.initializeStylesFromBackend && networkData.style && networkData.layout) {
                        window.initializeStylesFromBackend(networkData);
                        console.log('Initialized styles from backend');
                    }

                    // Create or update the network
                    if (window.cy) {
                        // Add new elements to existing network instead of clearing
                        console.log('Adding elements to existing network');
                        this.addElementsToNetwork(networkData.elements);

                        // Apply styles and layout from backend
                        if (window.positionNodes) {
                            // Get current font size multiplier
                            const fontSlider = document.getElementById('font-size-slider');
                            const fontSizeMultiplier = fontSlider ? parseFloat(fontSlider.value) : 0.5;

                            // Apply styles with proper font size
                            window.positionNodes(window.cy, fontSizeMultiplier, false);
                            console.log('Applied styles with font multiplier:', fontSizeMultiplier);
                        }
                    } else {
                        // Create new network
                        console.log('Creating new network');
                        this.createCytoscapeNetwork(networkData.elements);

                        // Initialize with backend styles after network creation
                        if (window.cy && window.positionNodes) {
                            const fontSlider = document.getElementById('font-size-slider');
                            const fontSizeMultiplier = fontSlider ? parseFloat(fontSlider.value) : 0.5;
                            window.positionNodes(window.cy, fontSizeMultiplier, false);
                        }
                    }

                    // Update tables and other UI elements
                    this.updateNetworkInfo(result);

                } else {
                    console.warn('No elements array found in response:', networkData);
                    displayErrorMessage('No network elements received from server');
                }
            } else {
                console.log('No elements returned or success=false');
                displayErrorMessage(result.error || 'Failed to fetch network data');
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
            } else if (queryType === 'mie') {
                // Handle MIE identifiers - use MIE-specific functions
                if (window.aopNameUtils.isMieIdentifierFormat(trimmed)) {
                    return window.aopNameUtils.normalizeMieId(trimmed);
                }

                // For text searches, try to find matching MIE
                const results = window.aopNameUtils.findMieByText(trimmed);
                if (results.length > 0) {
                    return results[0].fullUri;
                }

                // If no match found, try to treat as ID anyway
                if (/^\d+$/.test(trimmed)) {
                    return `https://identifiers.org/aop.events/${trimmed}`;
                }
            } else {
                // Handle KE identifiers (for ke_upstream, ke_downstream)
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
        if (!elements || elements.length === 0) {
            console.log('No elements to add to network');
            return;
        }

        // Track existing element IDs to avoid duplicates
        const existingIds = new Set();
        window.cy.elements().forEach(element => {
            existingIds.add(element.id());
        });

        console.log('Existing element IDs:', existingIds.size);

        const newElements = [];
        const seenIds = new Set(); // Track IDs within this batch
        const validNodes = new Set();
        const skippedEdges = [];

        // First pass: collect all valid nodes and track node IDs
        elements.forEach((element, index) => {
            const elementId = element.data?.id;

            if (!elementId) {
                console.warn(`Element ${index} has no ID, skipping:`, element);
                return;
            }

            // Check both existing network and current batch for duplicates
            if (existingIds.has(elementId) || seenIds.has(elementId)) {
                if (index < 5) {
                    console.log(`Skipping duplicate element ${index}:`, elementId);
                }
                return;
            }

            // If it's a node (no source/target) or has group 'nodes'
            if (!element.data?.source && !element.data?.target || element.group === 'nodes') {
                newElements.push(element);
                seenIds.add(elementId);
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

        // Second pass: handle edges
        elements.forEach((element, index) => {
            const elementId = element.data?.id;

            if (!elementId || existingIds.has(elementId) || seenIds.has(elementId)) {
                return;
            }

            if ((element.data?.source && element.data?.target) || element.group === 'edges') {
                const source = element.data?.source;
                const target = element.data?.target;

                if (!source || !target) {
                    console.warn(`Edge ${elementId} has missing source or target:`, { source, target });
                    skippedEdges.push({ id: elementId, reason: 'Missing source or target' });
                    return;
                }

                const sourceExists = validNodes.has(source);
                const targetExists = validNodes.has(target);

                if (!sourceExists || !targetExists) {
                    console.warn(`Edge ${elementId} references potentially missing nodes: source=${source} (exists: ${sourceExists}), target=${target} (exists: ${targetExists})`);
                }

                newElements.push(element);
                seenIds.add(elementId);
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
            try {
                window.cy.batch(() => {
                    newElements.forEach((element, index) => {
                        try {
                            window.cy.add(element);
                        } catch (addError) {
                            console.error(`Error adding individual element ${index} (${element.data?.id}):`, addError);
                            // Continue with other elements
                        }
                    });
                });

                console.log(`Added ${newElements.length} new elements to network`);

                // Preserve any existing AOP grouping after adding new elements
                if (window.aopTableManager && window.aopTableManager.groupedAops.size > 0) {
                    console.log('Preserving AOP grouping after adding new elements');
                    setTimeout(() => {
                        window.aopTableManager.applyGroupHighlighting();
                    }, 100);
                }

                // Update layout after adding elements
                if (window.resetNetworkLayout) {
                    setTimeout(() => {
                        window.resetNetworkLayout();
                    }, 200);
                }

                // Hide organs by default after adding AOP network elements
                setTimeout(() => {
                    if (window.cy) {
                        window.cy.nodes('[type="organ"]').style('display', 'none');
                        window.cy.edges('[type="associated_with"], [type="expression_in"]').style('display', 'none');
                        window.organsVisible = false;

                        // Update button state
                        const button = document.getElementById('toggle-organs-btn');
                        if (button) {
                            button.textContent = 'Query Organs';
                            button.classList.remove('active');
                        }
                    }
                }, 100);

                // Hide loading overlay if network has elements
                const loadingOverlay = document.querySelector(".loading-overlay");
                if (loadingOverlay && window.cy.elements().length > 0) {
                    loadingOverlay.style.display = "none";
                }

                // No longer call populateAopTable - table is updated above with API data
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

    hideExampleText() {
        // Hide the example text when network appears
        const exampleContainer = document.querySelector('.loading-overlay, .network-example, .example-text, #example-container');
        if (exampleContainer) {
            exampleContainer.style.display = 'none';
            console.log('Hidden example text container');
        }

        // Also try to hide any elements with example-related classes
        const exampleElements = document.querySelectorAll('.example, [class*="example"]');
        exampleElements.forEach(element => {
            if (element.textContent && element.textContent.includes('example')) {
                element.style.display = 'none';
            }
        });
    }

    createCytoscapeNetwork(elements) {
        // Call the global createCytoscapeNetwork function
        if (window.createCytoscapeNetwork) {
            window.createCytoscapeNetwork(elements);
        } else {
            console.error('Global createCytoscapeNetwork function not available');
        }
    }

    updateNetworkInfo(result) {
        // Update network information and tables
        if (result.report) {
            console.log('Network report:', result.report);
        }

        // No longer call deprecated populate functions
        // Tables are updated directly from API response data
        
        this.showStatus(`Successfully loaded ${result.elements_count || 'network'} elements`, 'success');
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
