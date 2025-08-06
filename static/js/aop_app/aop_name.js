// Global variables for both AOP and KE data
let aopNameData = [];
let keNameData = [];
let aopFuzzyInstance = null;
let keFuzzyInstance = null;

console.log('AOP Name Utils: Script loaded');

// Load external script helper
function loadScript(src) {
    return new Promise((resolve, reject) => {
        const script = document.createElement('script');
        script.src = src;
        script.onload = resolve;
        script.onerror = reject;
        document.head.appendChild(script);
    });
}

// Initialize Fuse.js for fuzzy matching (updated to handle both datasets)
async function initializeFuzzySearch() {
    console.log('AOP Name Utils: Initializing fuzzy search');
    
    // Load Fuse.js library if not already loaded
    if (typeof Fuse === 'undefined') {
        console.log('AOP Name Utils: Loading Fuse.js library');
        await loadScript('https://cdn.jsdelivr.net/npm/fuse.js@6.6.2');
    }
    
    const options = {
        keys: ['name', 'id'],
        threshold: 0.3,
        distance: 100,
        includeScore: true,
        includeMatches: true,
        minMatchCharLength: 2
    };
    
    if (aopNameData.length > 0) {
        aopFuzzyInstance = new Fuse(aopNameData, options);
        console.log('AOP Name Utils: AOP fuzzy instance created with', aopNameData.length, 'items');
    }
    
    if (keNameData.length > 0) {
        keFuzzyInstance = new Fuse(keNameData, options);
        console.log('AOP Name Utils: KE fuzzy instance created with', keNameData.length, 'items');
    }
}

// Load AOP name data from CSV
async function loadAopNameData() {
    console.log('AOP Name Utils: Loading AOP name data');
    try {
        const response = await fetch('/static/data/aopName.csv');
        console.log('AOP Name Utils: AOP CSV response status:', response.status);
        
        if (!response.ok) {
            throw new Error(`HTTP ${response.status}: ${response.statusText}`);
        }
        
        const csvText = await response.text();
        console.log('AOP Name Utils: AOP CSV text length:', csvText.length);

        Papa.parse(csvText, {
            header: true,
            skipEmptyLines: true,
            complete: function (results) {
                console.log('AOP Name Utils: AOP CSV parsed, rows:', results.data.length);
                console.log('AOP Name Utils: Sample AOP row:', results.data[0]);
                
                aopNameData = results.data.map(row => ({
                    id: extractAopId(row.aop),
                    fullUri: row.aop,
                    name: row.aopname,
                    aopname: row.aopname
                }));
                
                console.log('AOP Name Utils: AOP data processed, items:', aopNameData.length);
                console.log('AOP Name Utils: Sample processed AOP:', aopNameData[0]);
                
                initializeFuzzySearch();
            },
            error: function(error) {
                console.error('AOP Name Utils: Papa Parse error for AOP data:', error);
            }
        });
    } catch (error) {
        console.error('AOP Name Utils: Error loading AOP name data:', error);
    }
}

// Load KE name data from CSV
async function loadKeNameData() {
    console.log('AOP Name Utils: Loading KE name data');
    try {
        const response = await fetch('/static/data/keName.csv');
        console.log('AOP Name Utils: KE CSV response status:', response.status);
        
        if (!response.ok) {
            throw new Error(`HTTP ${response.status}: ${response.statusText}`);
        }
        
        const csvText = await response.text();
        console.log('AOP Name Utils: KE CSV text length:', csvText.length);
        
        Papa.parse(csvText, {
            header: true,
            skipEmptyLines: true,
            complete: function(results) {
                console.log('AOP Name Utils: KE CSV parsed, rows:', results.data.length);
                console.log('AOP Name Utils: Sample KE row:', results.data[0]);
                
                keNameData = results.data.map(row => ({
                    id: extractKeId(row.ke),
                    fullUri: row.ke,
                    name: row.kename,
                    kename: row.kename
                }));
                
                console.log('AOP Name Utils: KE data processed, items:', keNameData.length);
                console.log('AOP Name Utils: Sample processed KE:', keNameData[0]);
                
                initializeFuzzySearch();
            },
            error: function(error) {
                console.error('AOP Name Utils: Papa Parse error for KE data:', error);
            }
        });
    } catch (error) {
        console.error('AOP Name Utils: Error loading KE name data:', error);
    }
}

// Extract AOP ID from different formats
function extractAopId(identifier) {
    if (!identifier) return null;

    // Handle full URI: https://identifiers.org/aop/123
    if (identifier.includes('identifiers.org/aop/')) {
        return identifier.split('/').pop();
    }

    // Handle prefixed: aop:123
    if (identifier.includes(':')) {
        return identifier.split(':').pop();
    }

    // Handle plain number: 123
    return identifier.toString();
}

// Extract KE ID from different formats
function extractKeId(identifier) {
    if (!identifier) return null;
    
    // Handle full URI: https://identifiers.org/aop.events/123
    if (identifier.includes('identifiers.org/aop.events/')) {
        return identifier.split('/').pop();
    }
    
    // Handle prefixed: aop.events:123
    if (identifier.includes('aop.events:')) {
        return identifier.split(':').pop();
    }
    
    // Handle plain number: 123
    return identifier.toString();
}

// Normalize identifier to standard format
function normalizeAopId(identifier) {
    const id = extractAopId(identifier);
    return `https://identifiers.org/aop/${id}`;
}

// Normalize KE identifier to standard format
function normalizeKeId(identifier) {
    const id = extractKeId(identifier);
    return `https://identifiers.org/aop.events/${id}`;
}

// Check if input looks like an identifier
function isIdentifierFormat(text) {
    if (!text) return false;
    
    // Check for full URI
    if (text.includes('identifiers.org/aop/')) return true;
    
    // Check for prefixed format (aop:123)
    if (/^aop:\d+$/i.test(text)) return true;
    
    // Check for plain number
    if (/^\d+$/.test(text)) return true;
    
    return false;
}

// Check if input looks like a KE identifier
function isKeIdentifierFormat(text) {
    if (!text) return false;
    
    // Check for full URI
    if (text.includes('identifiers.org/aop.events/')) return true;
    
    // Check for prefixed format (aop.events:123)
    if (/^aop\.events:\d+$/i.test(text)) return true;
    
    // Check for plain number (could be either AOP or KE, context matters)
    if (/^\d+$/.test(text)) return true;
    
    return false;
}

// Determine query type from context
function getQueryTypeFromContext() {
    const queryTypeSelect = document.getElementById('query-type');
    const queryType = queryTypeSelect ? queryTypeSelect.value : 'aop';
    console.log('AOP Name Utils: Query type from context:', queryType);
    return queryType;
}

// Enhanced search function that handles both AOP and KE based on query type
function searchByQueryType(searchText, queryType) {
    console.log('AOP Name Utils: searchByQueryType called with:', { searchText, queryType });
    
    if (!searchText || searchText.length < 1) {
        console.log('AOP Name Utils: Search text too short or empty');
        return [];
    }
    
    // Determine which dataset to use based on query type
    let dataset, fuzzyInstance, normalizeFunc, isIdentifierFunc;
    
    if (queryType === 'aop') {
        dataset = aopNameData;
        fuzzyInstance = aopFuzzyInstance;
        normalizeFunc = normalizeAopId;
        isIdentifierFunc = isIdentifierFormat;
        console.log('AOP Name Utils: Using AOP dataset with', dataset.length, 'items');
    } else {
        // For MIE, ke_upstream, ke_downstream - use KE data
        dataset = keNameData;
        fuzzyInstance = keFuzzyInstance;
        normalizeFunc = normalizeKeId;
        isIdentifierFunc = isKeIdentifierFormat;
        console.log('AOP Name Utils: Using KE dataset with', dataset.length, 'items');
    }
    
    // If it looks like an identifier, search by ID first
    if (isIdentifierFunc(searchText)) {
        console.log('AOP Name Utils: Text looks like identifier, searching by ID');
        const idResults = findById(searchText, dataset, normalizeFunc);
        if (idResults.length > 0) {
            console.log('AOP Name Utils: Found ID results:', idResults);
            return idResults;
        }
    }
    
    // If not an identifier or no ID match found, do fuzzy text search
    if (searchText.length >= 2 && fuzzyInstance) {
        console.log('AOP Name Utils: Performing fuzzy search');
        const results = fuzzyInstance.search(searchText);
        const mappedResults = results.slice(0, 10).map(result => ({
            id: result.item.id,
            fullUri: result.item.fullUri,
            name: result.item.name,
            score: result.score,
            matches: result.matches
        }));
        console.log('AOP Name Utils: Fuzzy search results:', mappedResults);
        return mappedResults;
    }
    
    console.log('AOP Name Utils: No fuzzy instance available or search text too short');
    return [];
}

// Generic find by ID function
function findById(identifier, dataset, normalizeFunc) {
    console.log('AOP Name Utils: findById called with:', { identifier, datasetLength: dataset.length });
    
    const normalizedId = extractAopId(identifier) || extractKeId(identifier);
    console.log('AOP Name Utils: Normalized ID:', normalizedId);
    
    const item = dataset.find(item => item.id === normalizedId);
    console.log('AOP Name Utils: Found item:', item);
    
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

// Updated search function that uses query type context
function searchAop(searchText) {
    const queryType = getQueryTypeFromContext();
    return searchByQueryType(searchText, queryType);
}

// Create autocomplete dropdown
function createAutocompleteDropdown(inputElement) {
    console.log('AOP Name Utils: Creating autocomplete dropdown');
    const dropdown = document.createElement('div');
    dropdown.className = 'aop-autocomplete-dropdown';
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
    console.log('AOP Name Utils: Dropdown created and added to body');
    return dropdown;
}

// Create dropdown item that works for both AOP and KE
function createDropdownItemForQueryType(item, index, isSelected = false, queryType = 'aop') {
    const dropdownItem = document.createElement('div');
    dropdownItem.className = `aop-dropdown-item ${isSelected ? 'selected' : ''}`;
    dropdownItem.style.cssText = `
        padding: 8px 12px;
        cursor: pointer;
        border-bottom: 1px solid #eee;
        background: ${isSelected ? '#007bff' : 'white'};
        color: ${isSelected ? 'white' : '#333'};
    `;
    
    const prefix = queryType === 'aop' ? 'AOP' : 'KE';
    const itemName = item.name || item.aopname || item.kename || 'Unknown';
    
    dropdownItem.innerHTML = `
        <div style="font-weight: bold; font-size: 12px; color: ${isSelected ? '#cce6ff' : '#666'};">
            ${prefix} ${item.id}
        </div>
        <div style="margin-top: 2px; line-height: 1.3;">
            ${highlightMatches(itemName, item.matches)}
        </div>
    `;
    
    dropdownItem.dataset.itemId = item.id;
    dropdownItem.dataset.itemUri = item.fullUri;
    dropdownItem.dataset.index = index;
    
    return dropdownItem;
}

// Highlight search matches
function highlightMatches(text, matches) {
    if (!matches || matches.length === 0) return text;
    
    let highlightedText = text;
    const highlights = [];
    
    matches.forEach(match => {
        // Handle both 'aopname', 'kename', and 'name' keys
        if (match.key === 'aopname' || match.key === 'kename' || match.key === 'name') {
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

// Setup autocomplete for a textarea element (line-based)
function setupAopAutocompleteTextarea(textareaElement) {
    console.log('AOP Name Utils: Setting up textarea autocomplete');
    let dropdown = null;
    let selectedIndex = -1;
    let currentResults = [];
    let debounceTimer = null;
    let currentLine = '';
    let currentLineStart = 0;
    let currentLineEnd = 0;
    
    // Create dropdown on first use
    function ensureDropdown() {
        if (!dropdown) {
            dropdown = createAutocompleteDropdown(textareaElement);
        }
        return dropdown;
    }
    
    // Get current line information
    function getCurrentLineInfo() {
        const text = textareaElement.value;
        const cursorPos = textareaElement.selectionStart;
        
        // Find line boundaries
        let lineStart = text.lastIndexOf('\n', cursorPos - 1) + 1;
        let lineEnd = text.indexOf('\n', cursorPos);
        if (lineEnd === -1) lineEnd = text.length;
        
        const lineText = text.substring(lineStart, lineEnd).trim();
        
        return {
            text: lineText,
            start: lineStart,
            end: lineEnd,
            cursorInLine: cursorPos - lineStart
        };
    }
    
    // Update dropdown position based on cursor line
    function updateDropdownPosition() {
        if (dropdown) {
            const rect = textareaElement.getBoundingClientRect();
            
            dropdown.style.left = rect.left + 'px';
            dropdown.style.top = (rect.top - Math.min(210, dropdown.scrollHeight + 10)) + 'px';
            dropdown.style.width = Math.max(rect.width, 300) + 'px';
        }
    }
    
    // Show dropdown with results
    function showDropdown(results, lineText) {
        console.log('AOP Name Utils: showDropdown called with', results.length, 'results');
        const dd = ensureDropdown();
        currentResults = results;
        selectedIndex = -1;
        
        if (results.length === 0 || lineText.length < 1) {
            console.log('AOP Name Utils: Hiding dropdown - no results or short text');
            dd.style.display = 'none';
            return;
        }
        
        const queryType = getQueryTypeFromContext();
        dd.innerHTML = '';
        results.forEach((item, index) => {
            const dropdownItem = createDropdownItemForQueryType(item, index, false, queryType);
            dd.appendChild(dropdownItem);
            
            dropdownItem.addEventListener('click', () => {
                console.log('AOP Name Utils: Dropdown item clicked:', item);
                selectItem(item, lineText);
            });
            
            dropdownItem.addEventListener('mouseenter', () => {
                setSelectedIndex(index);
            });
        });
        
        updateDropdownPosition();
        dd.style.display = 'block';
        console.log('AOP Name Utils: Dropdown displayed with', results.length, 'items');
    }
    
    // Hide dropdown
    function hideDropdown() {
        if (dropdown) {
            dropdown.style.display = 'none';
        }
        selectedIndex = -1;
        currentResults = [];
    }
    
    // Set selected index and update visual selection
    function setSelectedIndex(index) {
        selectedIndex = index;
        if (dropdown) {
            const items = dropdown.querySelectorAll('.aop-dropdown-item');
            items.forEach((item, i) => {
                const isSelected = i === index;
                item.className = `aop-dropdown-item ${isSelected ? 'selected' : ''}`;
                item.style.background = isSelected ? '#007bff' : 'white';
                item.style.color = isSelected ? 'white' : '#333';
                
                // Update prefix color
                const prefixDiv = item.querySelector('div');
                if (prefixDiv) {
                    prefixDiv.style.color = isSelected ? '#cce6ff' : '#666';
                }
                
                // Scroll into view if needed
                if (isSelected) {
                    item.scrollIntoView({ block: 'nearest' });
                }
            });
        }
    }
    
    // Select an item and update the current line
    function selectItem(item, searchText) {
        console.log('AOP Name Utils: selectItem called with:', item);
        const lineInfo = getCurrentLineInfo();
        const text = textareaElement.value;
        
        // Replace current line with the selected item URI
        const newText = text.substring(0, lineInfo.start) + 
                       item.fullUri + 
                       text.substring(lineInfo.end);
        
        textareaElement.value = newText;
        
        // Position cursor at end of replaced text
        const newCursorPos = lineInfo.start + item.fullUri.length;
        textareaElement.setSelectionRange(newCursorPos, newCursorPos);
        
        hideDropdown();
        
        // Trigger change event
        const event = new Event('change', { bubbles: true });
        textareaElement.dispatchEvent(event);
        
        // Focus back to textarea
        textareaElement.focus();
    }
    
    // Handle input changes with query type awareness
    textareaElement.addEventListener('input', function(e) {
        console.log('AOP Name Utils: Textarea input event');
        const lineInfo = getCurrentLineInfo();
        currentLine = lineInfo.text;
        currentLineStart = lineInfo.start;
        currentLineEnd = lineInfo.end;
        
        console.log('AOP Name Utils: Current line text:', currentLine);
        
        clearTimeout(debounceTimer);
        debounceTimer = setTimeout(() => {
            if (currentLine.length >= 1) {
                console.log('AOP Name Utils: Triggering search for:', currentLine);
                const queryType = getQueryTypeFromContext();
                const results = searchByQueryType(currentLine, queryType);
                showDropdown(results, currentLine);
            } else {
                hideDropdown();
            }
        }, 150);
    });
    
    // Handle cursor movement and selection changes
    textareaElement.addEventListener('click', function(e) {
        // Update current line info when clicking
        setTimeout(() => {
            const lineInfo = getCurrentLineInfo();
            if (lineInfo.text !== currentLine) {
                hideDropdown();
            }
        }, 10);
    });
    
    // Handle keyboard navigation
    textareaElement.addEventListener('keydown', function(e) {
        if (!dropdown || dropdown.style.display === 'none') return;
        
        switch (e.key) {
            case 'ArrowDown':
                if (currentResults.length > 0) {
                    e.preventDefault();
                    setSelectedIndex(Math.min(selectedIndex + 1, currentResults.length - 1));
                }
                break;
                
            case 'ArrowUp':
                if (currentResults.length > 0) {
                    e.preventDefault();
                    setSelectedIndex(Math.max(selectedIndex - 1, -1));
                }
                break;
                
            case 'Enter':
                if (selectedIndex >= 0 && currentResults[selectedIndex]) {
                    e.preventDefault();
                    selectItem(currentResults[selectedIndex], currentLine);
                }
                break;
                
            case 'Escape':
                e.preventDefault();
                hideDropdown();
                break;
                
            case 'Tab':
                if (selectedIndex >= 0 && currentResults[selectedIndex]) {
                    e.preventDefault();
                    selectItem(currentResults[selectedIndex], currentLine);
                }
                break;
        }
    });
    
    // Handle focus out
    textareaElement.addEventListener('blur', function(e) {
        // Delay hiding to allow clicks on dropdown items
        setTimeout(() => {
            if (!textareaElement.matches(':focus')) {
                hideDropdown();
            }
        }, 150);
    });
    
    // Handle window resize and scroll
    window.addEventListener('resize', updateDropdownPosition);
    window.addEventListener('scroll', updateDropdownPosition);
}

// Update the existing setupAopAutocomplete to handle both input and textarea
function setupAopAutocomplete(element) {
    console.log('AOP Name Utils: setupAopAutocomplete called for element:', element.tagName);
    if (element.tagName.toLowerCase() === 'textarea') {
        setupAopAutocompleteTextarea(element);
    } else {
        // setupAopAutocompleteInput(element); // We can implement this later if needed
        console.log('AOP Name Utils: Input autocomplete not implemented yet');
    }
}

// Update placeholder text based on query type
function updatePlaceholderText() {
    console.log('AOP Name Utils: updatePlaceholderText called');
    const queryType = getQueryTypeFromContext();
    const queryValuesElement = document.getElementById('query-values');
    
    if (queryValuesElement) {
        const placeholders = {
            'aop': 'Search by AOP name or enter identifiers (one per line)\nExamples:\nliver fibrosis\n1\naop:2\nhttps://identifiers.org/aop/3',
            'mie': 'Search by KE name or enter identifiers (one per line)\nExamples:\nAryl hydrocarbon receptor activation\n18\naop.events:18\nhttps://identifiers.org/aop.events/18',
            'ke_upstream': 'Search by KE name or enter identifiers (one per line)\nExamples:\nMitochondrial dysfunction\n177\naop.events:177\nhttps://identifiers.org/aop.events/177',
            'ke_downstream': 'Search by KE name or enter identifiers (one per line)\nExamples:\nLiver cancer\n1395\naop.events:1395\nhttps://identifiers.org/aop.events/1395'
        };
        
        queryValuesElement.placeholder = placeholders[queryType] || placeholders['aop'];
        console.log('AOP Name Utils: Placeholder updated for query type:', queryType);
    }
}

// Initialize AOP name functionality
document.addEventListener('DOMContentLoaded', function () {
    console.log('AOP Name Utils: DOM Content Loaded');
    
    loadAopNameData();
    loadKeNameData();
    
    // Setup autocomplete for query values element
    const queryValuesElement = document.getElementById('query-values');
    if (queryValuesElement) {
        console.log('AOP Name Utils: Found query-values element, setting up autocomplete');
        setupAopAutocomplete(queryValuesElement);
    } else {
        console.error('AOP Name Utils: query-values element not found!');
    }
    
    // Listen for query type changes to update placeholder text
    const queryTypeSelect = document.getElementById('query-type');
    if (queryTypeSelect) {
        console.log('AOP Name Utils: Found query-type select, adding change listener');
        queryTypeSelect.addEventListener('change', function() {
            console.log('AOP Name Utils: Query type changed to:', this.value);
            updatePlaceholderText();
        });
    } else {
        console.error('AOP Name Utils: query-type select not found!');
    }
    
    // Update placeholder initially
    updatePlaceholderText();
});

// Export functions for use in other modules
window.aopNameUtils = {
    findAopByText: (text) => {
        if (!aopFuzzyInstance || !text || text.length < 2) return [];
        const results = aopFuzzyInstance.search(text);
        return results.slice(0, 10).map(result => ({
            id: result.item.id,
            fullUri: result.item.fullUri,
            name: result.item.name,
            score: result.score,
            matches: result.matches
        }));
    },
    findKeByText: (text) => {
        if (!keFuzzyInstance || !text || text.length < 2) return [];
        const results = keFuzzyInstance.search(text);
        return results.slice(0, 10).map(result => ({
            id: result.item.id,
            fullUri: result.item.fullUri,
            name: result.item.name,
            score: result.score,
            matches: result.matches
        }));
    },
    findAopNameById: (identifier) => {
        const normalizedId = extractAopId(identifier);
        const aop = aopNameData.find(item => item.id === normalizedId);
        return aop ? aop.name : null;
    },
    findKeNameById: (identifier) => {
        const normalizedId = extractKeId(identifier);
        const ke = keNameData.find(item => item.id === normalizedId);
        return ke ? ke.name : null;
    },
    findAopById: (identifier) => findById(identifier, aopNameData, normalizeAopId),
    findKeById: (identifier) => findById(identifier, keNameData, normalizeKeId),
    searchAop,
    searchByQueryType,
    setupAopAutocomplete,
    normalizeAopId,
    normalizeKeId,
    extractAopId,
    extractKeId,
    isIdentifierFormat,
    isKeIdentifierFormat,
    updatePlaceholderText
};

console.log('AOP Name Utils: Script setup complete, exported functions available');
