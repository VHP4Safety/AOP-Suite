// General AutoComplete System for multiple data sources
class AutoCompleteManager {
    constructor() {
        this.dataSources = new Map();
        this.fuzzyInstances = new Map();
        this.fuzzyLoaded = false;
    }

    // Load Fuse.js library if needed
    async loadFuzzyLibrary() {
        if (typeof Fuse === 'undefined') {
            await this.loadScript('https://cdn.jsdelivr.net/npm/fuse.js@6.6.2');
        }
        this.fuzzyLoaded = true;
    }

    // Helper to load external scripts
    loadScript(src) {
        return new Promise((resolve, reject) => {
            const script = document.createElement('script');
            script.src = src;
            script.onload = resolve;
            script.onerror = reject;
            document.head.appendChild(script);
        });
    }

    // Register a data source with its configuration
    registerDataSource(sourceId, config) {
        this.dataSources.set(sourceId, {
            data: [],
            config: {
                csvUrl: config.csvUrl,
                idColumn: config.idColumn || 'id',
                nameColumn: config.nameColumn || 'name',
                uriColumn: config.uriColumn || 'uri',
                extractIdFunc: config.extractIdFunc,
                normalizeIdFunc: config.normalizeIdFunc,
                isIdentifierFunc: config.isIdentifierFunc,
                searchKeys: config.searchKeys || ['name', 'id'],
                fuzzyOptions: config.fuzzyOptions || {
                    threshold: 0.3,
                    distance: 100,
                    includeScore: true,
                    includeMatches: true,
                    minMatchCharLength: 2
                }
            }
        });
    }

    // Load data for a specific source
    async loadDataSource(sourceId) {
        const source = this.dataSources.get(sourceId);
        if (!source) {
            console.error(`Data source ${sourceId} not registered`);
            return;
        }

        try {
            const response = await fetch(source.config.csvUrl);
            const csvText = await response.text();

            Papa.parse(csvText, {
                header: true,
                skipEmptyLines: true,
                complete: (results) => {
                    source.data = results.data.map(row => ({
                        id: source.config.extractIdFunc(row[source.config.uriColumn]),
                        fullUri: row[source.config.uriColumn],
                        name: row[source.config.nameColumn]
                    }));
                    this.initializeFuzzyForSource(sourceId);
                }
            });
        } catch (error) {
            console.error(`Error loading data for ${sourceId}:`, error);
        }
    }

    // Initialize fuzzy search for a specific source
    async initializeFuzzyForSource(sourceId) {
        if (!this.fuzzyLoaded) {
            await this.loadFuzzyLibrary();
        }

        const source = this.dataSources.get(sourceId);
        if (!source) return;

        const options = {
            keys: source.config.searchKeys,
            ...source.config.fuzzyOptions
        };

        this.fuzzyInstances.set(sourceId, new Fuse(source.data, options));
    }

    // Get data source for query type
    getDataSourceForQueryType(queryType) {
        if (queryType === 'aop') {
            return 'aop';
        } else {
            // For MIE, ke_upstream, ke_downstream - use KE data
            return 'ke';
        }
    }

    // Search by query type
    searchByQueryType(searchText, queryType) {
        if (!searchText || searchText.length < 1) {
            return [];
        }

        const sourceId = this.getDataSourceForQueryType(queryType);
        const source = this.dataSources.get(sourceId);
        const fuzzyInstance = this.fuzzyInstances.get(sourceId);

        if (!source) return [];

        // If it looks like an identifier, search by ID first
        if (source.config.isIdentifierFunc(searchText)) {
            const idResults = this.findById(searchText, sourceId);
            if (idResults.length > 0) {
                return idResults;
            }
        }

        // If not an identifier or no ID match found, do fuzzy text search
        if (searchText.length >= 2 && fuzzyInstance) {
            const results = fuzzyInstance.search(searchText);
            return results.slice(0, 10).map(result => ({
                id: result.item.id,
                fullUri: result.item.fullUri,
                name: result.item.name,
                score: result.score,
                matches: result.matches
            }));
        }

        return [];
    }

    // Find by ID in specific data source
    findById(identifier, sourceId) {
        const source = this.dataSources.get(sourceId);
        if (!source) return [];

        const normalizedId = source.config.extractIdFunc(identifier);
        const item = source.data.find(item => item.id === normalizedId);

        if (item) {
            return [{
                id: item.id,
                fullUri: item.fullUri,
                name: item.name,
                score: 0,
                matches: []
            }];
        }

        return [];
    }

    // Find by text in specific data source
    findByText(searchText, sourceId) {
        const fuzzyInstance = this.fuzzyInstances.get(sourceId);
        if (!fuzzyInstance || !searchText || searchText.length < 2) {
            return [];
        }

        const results = fuzzyInstance.search(searchText);
        return results.slice(0, 10).map(result => ({
            id: result.item.id,
            fullUri: result.item.fullUri,
            name: result.item.name,
            score: result.score,
            matches: result.matches
        }));
    }

    // Find name by ID in specific data source
    findNameById(identifier, sourceId) {
        const source = this.dataSources.get(sourceId);
        if (!source) return null;

        const normalizedId = source.config.extractIdFunc(identifier);
        const item = source.data.find(item => item.id === normalizedId);
        return item ? item.name : null;
    }

    // Create autocomplete dropdown
    createDropdown(inputElement) {
        const dropdown = document.createElement('div');
        dropdown.className = 'autocomplete-dropdown';
        dropdown.style.cssText = `
            position: absolute;
            background: white;
            border: 1px solid #ddd;
            border-radius: 4px;
            box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
            max-height: 200px;
            overflow-y: auto;
            z-index: 1000;
            display: none;
            min-width: 300px;
            font-size: 14px;
        `;

        document.body.appendChild(dropdown);
        return dropdown;
    }

    // Create dropdown item
    createDropdownItem(item, index, isSelected = false, queryType = 'aop') {
        const dropdownItem = document.createElement('div');
        dropdownItem.className = `autocomplete-dropdown-item ${isSelected ? 'selected' : ''}`;
        dropdownItem.style.cssText = `
            padding: 8px 12px;
            cursor: pointer;
            border-bottom: 1px solid #eee;
            background: ${isSelected ? '#007bff' : 'white'};
            color: ${isSelected ? 'white' : '#333'};
        `;

        const prefix = queryType === 'aop' ? 'AOP' : 'KE';
        dropdownItem.innerHTML = `
            <div style="font-weight: bold; font-size: 12px; color: ${isSelected ? '#cce6ff' : '#666'};">
                ${prefix} ${item.id}
            </div>
            <div style="margin-top: 2px; line-height: 1.3;">
                ${this.highlightMatches(item.name, item.matches)}
            </div>
        `;

        dropdownItem.dataset.itemId = item.id;
        dropdownItem.dataset.itemUri = item.fullUri;
        dropdownItem.dataset.index = index;

        return dropdownItem;
    }

    // Highlight search matches
    highlightMatches(text, matches) {
        if (!matches || matches.length === 0) return text;

        let highlightedText = text;
        const highlights = [];

        matches.forEach(match => {
            if (match.key === 'name') {
                match.indices.forEach(([start, end]) => {
                    highlights.push({ start, end });
                });
            }
        });

        // Sort highlights by start position (descending to avoid index shifts)
        highlights.sort((a, b) => b.start - a.start);

        highlights.forEach(({ start, end }) => {
            const before = highlightedText.substring(0, start);
            const match = highlightedText.substring(start, end + 1);
            const after = highlightedText.substring(end + 1);
            highlightedText = before + `<mark style="background: yellow; color: black;">${match}</mark>` + after;
        });

        return highlightedText;
    }

    // Setup autocomplete for an element
    setupAutocomplete(element, options = {}) {
        if (element.tagName.toLowerCase() === 'textarea') {
            this.setupTextareaAutocomplete(element, options);
        } else {
            this.setupInputAutocomplete(element, options);
        }
    }

    // Setup autocomplete for input element
    setupInputAutocomplete(inputElement, options = {}) {
        let dropdown = null;
        let selectedIndex = -1;
        let currentResults = [];
        let debounceTimer = null;

        const showDropdown = (results) => {
            if (!dropdown) {
                dropdown = this.createDropdown(inputElement);
            }

            currentResults = results;
            selectedIndex = -1;

            if (results.length === 0) {
                dropdown.style.display = 'none';
                return;
            }

            const queryType = this.getQueryTypeFromContext();
            dropdown.innerHTML = '';
            results.forEach((item, index) => {
                const dropdownItem = this.createDropdownItem(item, index, false, queryType);
                dropdown.appendChild(dropdownItem);

                dropdownItem.addEventListener('click', () => {
                    this.selectItem(inputElement, item, dropdown);
                });
            });

            this.updateDropdownPosition(dropdown, inputElement);
            dropdown.style.display = 'block';
        };

        inputElement.addEventListener('input', (e) => {
            const value = e.target.value.trim();
            clearTimeout(debounceTimer);
            debounceTimer = setTimeout(() => {
                if (value.length >= 1) {
                    const queryType = this.getQueryTypeFromContext();
                    const results = this.searchByQueryType(value, queryType);
                    showDropdown(results);
                } else {
                    if (dropdown) dropdown.style.display = 'none';
                }
            }, 150);
        });

        // Add keyboard navigation and other event handlers...
        this.addKeyboardNavigation(inputElement, dropdown, currentResults, selectedIndex);
    }

    // Setup autocomplete for textarea element
    setupTextareaAutocomplete(textareaElement, options = {}) {
        // Similar implementation for textarea with line-based autocomplete
        // Implementation details similar to the original but generalized
    }

    // Helper methods
    updateDropdownPosition(dropdown, inputElement) {
        if (dropdown) {
            const rect = inputElement.getBoundingClientRect();
            dropdown.style.left = rect.left + 'px';
            dropdown.style.top = (rect.top - Math.min(210, dropdown.scrollHeight + 10)) + 'px';
            dropdown.style.width = Math.max(rect.width, 300) + 'px';
        }
    }

    selectItem(inputElement, item, dropdown) {
        inputElement.value = item.fullUri;
        inputElement.dataset.itemId = item.id;
        inputElement.dataset.itemName = item.name;
        if (dropdown) dropdown.style.display = 'none';

        const event = new Event('change', { bubbles: true });
        inputElement.dispatchEvent(event);
    }

    getQueryTypeFromContext() {
        const queryTypeSelect = document.getElementById('query-type');
        return queryTypeSelect ? queryTypeSelect.value : 'aop';
    }

    addKeyboardNavigation(inputElement, dropdown, currentResults, selectedIndex) {
        // Implement keyboard navigation logic
    }

    // Update placeholder text based on query type
    updatePlaceholderText() {
        const queryType = this.getQueryTypeFromContext();
        const queryValuesElement = document.getElementById('query-values');
        
        if (queryValuesElement) {
            const placeholders = {
                'aop': 'Search by AOP name or enter identifiers (one per line)\nExamples:\nliver fibrosis\n1\naop:2\nhttps://identifiers.org/aop/3',
                'mie': 'Search by KE name or enter identifiers (one per line)\nExamples:\nAryl hydrocarbon receptor activation\n18\naop.events:18\nhttps://identifiers.org/aop.events/18',
                'ke_upstream': 'Search by KE name or enter identifiers (one per line)\nExamples:\nMitochondrial dysfunction\n177\naop.events:177\nhttps://identifiers.org/aop.events/177',
                'ke_downstream': 'Search by KE name or enter identifiers (one per line)\nExamples:\nLiver cancer\n1395\naop.events:1395\nhttps://identifiers.org/aop.events/1395'
            };
            
            queryValuesElement.placeholder = placeholders[queryType] || placeholders['aop'];
        }
    }
}

// Create global instance
const autoCompleteManager = new AutoCompleteManager();

// AOP-specific helper functions (for backward compatibility)
function extractAopId(identifier) {
    if (!identifier) return null;
    if (identifier.includes('identifiers.org/aop/')) {
        return identifier.split('/').pop();
    }
    if (identifier.includes(':')) {
        return identifier.split(':').pop();
    }
    return identifier.toString();
}

function extractKeId(identifier) {
    if (!identifier) return null;
    if (identifier.includes('identifiers.org/aop.events/')) {
        return identifier.split('/').pop();
    }
    if (identifier.includes('aop.events:')) {
        return identifier.split(':').pop();
    }
    return identifier.toString();
}

function normalizeAopId(identifier) {
    const id = extractAopId(identifier);
    return `https://identifiers.org/aop/${id}`;
}

function normalizeKeId(identifier) {
    const id = extractKeId(identifier);
    return `https://identifiers.org/aop.events/${id}`;
}

function isIdentifierFormat(text) {
    if (!text) return false;
    if (text.includes('identifiers.org/aop/')) return true;
    if (/^aop:\d+$/i.test(text)) return true;
    if (/^\d+$/.test(text)) return true;
    return false;
}

function isKeIdentifierFormat(text) {
    if (!text) return false;
    if (text.includes('identifiers.org/aop.events/')) return true;
    if (/^aop\.events:\d+$/i.test(text)) return true;
    if (/^\d+$/.test(text)) return true;
    return false;
}

// Initialize data sources
document.addEventListener('DOMContentLoaded', function() {
    // Register AOP data source
    autoCompleteManager.registerDataSource('aop', {
        csvUrl: '/static/data/aopName.csv',
        idColumn: 'aop',
        nameColumn: 'aopname',
        uriColumn: 'aop',
        extractIdFunc: extractAopId,
        normalizeIdFunc: normalizeAopId,
        isIdentifierFunc: isIdentifierFormat,
        searchKeys: ['name', 'id']
    });

    // Register KE data source
    autoCompleteManager.registerDataSource('ke', {
        csvUrl: '/static/data/keName.csv',
        idColumn: 'ke',
        nameColumn: 'kename',
        uriColumn: 'ke',
        extractIdFunc: extractKeId,
        normalizeIdFunc: normalizeKeId,
        isIdentifierFunc: isKeIdentifierFormat,
        searchKeys: ['name', 'id']
    });

    // Load data sources
    autoCompleteManager.loadDataSource('aop');
    autoCompleteManager.loadDataSource('ke');

    // Setup autocomplete for query values element
    const queryValuesElement = document.getElementById('query-values');
    if (queryValuesElement) {
        autoCompleteManager.setupAutocomplete(queryValuesElement);
    }

    // Listen for query type changes
    const queryTypeSelect = document.getElementById('query-type');
    if (queryTypeSelect) {
        queryTypeSelect.addEventListener('change', function() {
            autoCompleteManager.updatePlaceholderText();
        });
    }
});

// Export for backward compatibility
window.aopNameUtils = {
    findAopByText: (text) => autoCompleteManager.findByText(text, 'aop'),
    findKeByText: (text) => autoCompleteManager.findByText(text, 'ke'),
    findAopNameById: (id) => autoCompleteManager.findNameById(id, 'aop'),
    findKeNameById: (id) => autoCompleteManager.findNameById(id, 'ke'),
    findAopById: (id) => autoCompleteManager.findById(id, 'aop'),
    findKeById: (id) => autoCompleteManager.findById(id, 'ke'),
    searchAop: (text) => {
        const queryType = autoCompleteManager.getQueryTypeFromContext();
        return autoCompleteManager.searchByQueryType(text, queryType);
    },
    searchByQueryType: (text, type) => autoCompleteManager.searchByQueryType(text, type),
    setupAopAutocomplete: (element) => autoCompleteManager.setupAutocomplete(element),
    normalizeAopId,
    normalizeKeId,
    extractAopId,
    extractKeId,
    isIdentifierFormat,
    isKeIdentifierFormat,
    updatePlaceholderText: () => autoCompleteManager.updatePlaceholderText()
};

// Export the manager for future extensibility
window.autoCompleteManager = autoCompleteManager;
