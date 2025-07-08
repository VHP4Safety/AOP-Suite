/**
 * Enhanced AOP Table functionality with filtering and network integration
 */

class AOPTableManager {
    constructor() {
        this.currentData = [];
        this.filteredData = [];
        this.filterText = '';
        this.selectedAop = null; // Track currently selected AOP
        this.init();
    }

    init() {
        this.setupFilterInput();
        this.setupTableStyles();
    }

    setupFilterInput() {
        // Add filter input if it doesn't exist
        const tableContainer = document.querySelector('#aop-table-container, .aop-table-container');
        if (tableContainer && !document.querySelector('#aop-table-filter')) {
            const filterContainer = document.createElement('div');
            filterContainer.className = 'aop-table-filter-container mb-3';
            filterContainer.innerHTML = `
                <div class="input-group">
                    <div class="input-group-prepend">
                        <span class="input-group-text"><i class="fas fa-search"></i></span>
                    </div>
                    <input type="text" id="aop-table-filter" class="form-control" 
                           placeholder="Filter AOP table and network (search nodes, relationships, AOPs...)">
                    <div class="input-group-append">
                        <button class="btn btn-outline-secondary" id="clear-aop-filter" type="button">
                            <i class="fas fa-times"></i>
                        </button>
                    </div>
                </div>
                <small class="form-text text-muted">
                    Filter affects both table display and network visibility. Use keywords like "MIE", "AO", specific node names, or AOP numbers.
                </small>
            `;
            
            tableContainer.insertBefore(filterContainer, tableContainer.firstChild);
            
            // Add event listeners
            document.getElementById('aop-table-filter').addEventListener('input', (e) => {
                this.handleFilter(e.target.value);
            });
            
            document.getElementById('clear-aop-filter').addEventListener('click', () => {
                document.getElementById('aop-table-filter').value = '';
                this.handleFilter('');
            });
        }
    }

    generateTableHTML() {
        const headers = [
            'Source Node',
            'Type',
            'KER Label',
            'Target Node', 
            'Type',
            'AOP IDs',
            'AOP Titles'
        ];

        let html = '<thead><tr>';
        headers.forEach(header => {
            html += `<th>${header}</th>`;
        });
        html += '</tr></thead><tbody>';

        this.filteredData.forEach((row, index) => {
            const rowClass = row.is_connected ? '' : 'disconnected-row';
            html += `<tr class="${rowClass}" data-row-index="${index}">`;
            
            // Source node
            html += `<td>
                <span class="node-type-badge node-type-${row.source_type}">${row.source_type.toUpperCase()}</span>
                <div class="${row.source_label.includes('(missing label)') ? 'missing-label' : ''}" 
                     data-node-id="${row.source_id}">${this.highlightMatch(row.source_label)}</div>
            </td>`;
            
            // Source type
            html += `<td>${row.source_type}</td>`;
            
            // KER Label
            html += `<td><span class="ker-label-cell">${this.highlightMatch(row.ker_label)}</span></td>`;
            
            // Target node
            html += `<td>
                ${row.target_label !== 'N/A' ? 
                    `<span class="node-type-badge node-type-${row.target_type}">${row.target_type.toUpperCase()}</span>
                     <div class="${row.target_label.includes('(missing label)') ? 'missing-label' : ''}" 
                          data-node-id="${row.target_id}">${this.highlightMatch(row.target_label)}</div>` 
                    : 'N/A'}
            </td>`;
            
            // Target type
            html += `<td>${row.target_type}</td>`;
            
            // AOP IDs - make clickable
            html += `<td>
                ${this.generateClickableAopIds(row.aop_list)}
            </td>`;
            
            // AOP Titles - make clickable
            html += `<td class="aop-titles-cell">
                ${this.generateClickableAopTitles(row.aop_titles, row.aop_list)}
            </td>`;
            
            html += '</tr>';
        });

        html += '</tbody>';
        
        // Add summary
        const totalRows = this.currentData.length;
        const filteredRows = this.filteredData.length;
        const connectedRows = this.filteredData.filter(r => r.is_connected).length;
        const disconnectedRows = filteredRows - connectedRows;
        
        html += `<tfoot><tr><td colspan="7" class="text-muted small">
            Showing ${filteredRows} of ${totalRows} entries 
            (${connectedRows} connected, ${disconnectedRows} disconnected nodes)
            ${this.filterText ? ` - Filtered by: "${this.filterText}"` : ''}
            ${this.selectedAop ? ` - Filtered by AOP: ${this.selectedAop}` : ''}
        </td></tr></tfoot>`;

        return html;
    }

    generateClickableAopIds(aopList) {
        if (!aopList || aopList === 'N/A') return aopList;
        
        const aopIds = aopList.split(',').map(id => id.trim());
        return aopIds.map(aopId => {
            const isSelected = this.selectedAop === aopId;
            const className = isSelected ? 'aop-link selected-aop' : 'aop-link';
            return `<span class="${className}" data-aop-id="${aopId}" title="Click to filter network by this AOP">${this.highlightMatch(aopId)}</span>`;
        }).join(', ');
    }

    generateClickableAopTitles(aopTitles, aopList) {
        if (!aopTitles || aopTitles === 'N/A') return aopTitles;
        
        // Split titles and corresponding IDs
        const titles = aopTitles.split(';').map(title => title.trim());
        const aopIds = aopList && aopList !== 'N/A' ? aopList.split(',').map(id => id.trim()) : [];
        
        return titles.map((title, index) => {
            const correspondingAopId = aopIds[index] || aopIds[0] || ''; // Fallback to first ID
            const isSelected = this.selectedAop === correspondingAopId;
            const className = isSelected ? 'aop-title-link selected-aop' : 'aop-title-link';
            return `<span class="${className}" data-aop-id="${correspondingAopId}" title="Click to filter network by this AOP: ${correspondingAopId}">${this.highlightMatch(title)}</span>`;
        }).join('; ');
    }

    highlightMatch(text) {
        if (!this.filterText || !text || text === 'N/A') return text;
        
        const regex = new RegExp(`(${this.filterText})`, 'gi');
        return text.replace(regex, '<span class="highlight-match">$1</span>');
    }

    addNodeClickHandlers(table) {
        // Add click handlers to highlight nodes in network
        table.querySelectorAll('[data-node-id]').forEach(element => {
            element.style.cursor = 'pointer';
            element.addEventListener('click', (e) => {
                const nodeId = e.target.getAttribute('data-node-id');
                this.highlightNodeInNetwork(nodeId);
            });
        });

        // Add click handlers for AOP filtering
        table.querySelectorAll('.aop-link, .aop-title-link').forEach(element => {
            element.style.cursor = 'pointer';
            element.addEventListener('click', (e) => {
                e.preventDefault();
                e.stopPropagation();
                const aopId = e.target.getAttribute('data-aop-id');
                this.toggleAopFilter(aopId);
            });
        });
    }

    toggleAopFilter(aopId) {
        console.log('Toggling AOP filter for:', aopId);
        
        // If clicking the same AOP, clear the filter
        if (this.selectedAop === aopId) {
            this.clearAopFilter();
            return;
        }
        
        // Set new AOP filter
        this.selectedAop = aopId;
        this.filterByAop(aopId);
        this.renderTable();
    }

    clearAopFilter() {
        console.log('Clearing AOP filter');
        this.selectedAop = null;
        this.showAllNetworkNodes();
        this.renderTable();
    }

    filterByAop(aopId) {
        if (!window.cy || !aopId) return;
        
        console.log('Filtering network by AOP:', aopId);
        
        // Find all nodes that belong to this AOP
        const aopNodes = new Set();
        
        // Check all nodes for the AOP data
        window.cy.nodes().forEach(node => {
            const nodeData = node.data();
            const nodeAops = nodeData.aop || [];
            
            // Handle both array and single value cases
            const aopsToCheck = Array.isArray(nodeAops) ? nodeAops : [nodeAops];
            
            // Check if any of the node's AOPs match our target AOP
            const hasMatchingAop = aopsToCheck.some(nodeAop => {
                if (!nodeAop) return false;
                
                // Extract AOP ID from various formats
                let nodeAopId = '';
                if (nodeAop.includes('aop/')) {
                    nodeAopId = `AOP:${nodeAop.split('aop/').pop()}`;
                } else if (nodeAop.startsWith('AOP:')) {
                    nodeAopId = nodeAop;
                } else if (nodeAop.match(/^\d+$/)) {
                    nodeAopId = `AOP:${nodeAop}`;
                }
                
                return nodeAopId === aopId;
            });
            
            if (hasMatchingAop) {
                aopNodes.add(node.id());
            }
        });
        
        console.log(`Found ${aopNodes.size} nodes for AOP ${aopId}:`, Array.from(aopNodes));
        
        if (aopNodes.size === 0) {
            console.warn(`No nodes found for AOP ${aopId}`);
            return;
        }
        
        // Apply visual filtering with animation
        window.cy.batch(() => {
            // Fade out non-matching nodes
            window.cy.nodes().forEach(node => {
                if (aopNodes.has(node.id())) {
                    node.removeClass('filtered-out aop-filtered')
                         .addClass('aop-highlighted')
                         .style('opacity', 1)
                         .style('border-width', '4px')
                         .style('border-color', '#ff6b35');
                } else {
                    node.addClass('filtered-out aop-filtered')
                         .removeClass('aop-highlighted')
                         .style('opacity', 0.2)
                         .style('border-width', '2px');
                }
            });
            
            // Handle edges - only show edges between highlighted nodes
            window.cy.edges().forEach(edge => {
                const sourceId = edge.source().id();
                const targetId = edge.target().id();
                
                if (aopNodes.has(sourceId) && aopNodes.has(targetId)) {
                    edge.removeClass('filtered-out')
                        .style('opacity', 1)
                        .style('line-color', '#ff6b35')
                        .style('target-arrow-color', '#ff6b35')
                        .style('width', '3px');
                } else {
                    edge.addClass('filtered-out')
                        .style('opacity', 0.1);
                }
            });
        });
        
        // Center and zoom to the filtered nodes
        if (aopNodes.size > 0) {
            const nodesToFit = window.cy.nodes().filter(node => aopNodes.has(node.id()));
            
            window.cy.animate({
                fit: { eles: nodesToFit, padding: 50 },
                duration: 1000,
                easing: 'ease-out'
            });
        }
        
        // Show status message
        this.showFilterStatus(`Network filtered to show ${aopNodes.size} nodes from ${aopId}`, 'info');
    }

    showAllNetworkNodes() {
        if (!window.cy) return;

        console.log('Showing all network nodes');

        window.cy.batch(() => {
            // Reset all nodes
            window.cy.nodes().forEach(node => {
                node.removeClass('filtered-out aop-filtered aop-highlighted')
                    .style('opacity', 1)
                    .style('border-width', '2px')
                    .style('border-color', node.data('original-border-color') || '#666');
            });
            
            // Reset all edges
            window.cy.edges().forEach(edge => {
                edge.removeClass('filtered-out')
                    .style('opacity', 1)
                    .style('line-color', edge.data('original-line-color') || '#666')
                    .style('target-arrow-color', edge.data('original-arrow-color') || '#666')
                    .style('width', '2px');
            });
        });

        // Re-layout all nodes
        this.relayoutAllNodes();
        
        // Clear status message
        this.showFilterStatus('', 'info');
    }

    showFilterStatus(message, type = 'info') {
        // Create or update status element
        let statusElement = document.querySelector('#aop-filter-status');
        if (!statusElement) {
            statusElement = document.createElement('div');
            statusElement.id = 'aop-filter-status';
            statusElement.className = 'mt-2 small';
            
            const tableContainer = document.querySelector('#aop-table-container');
            if (tableContainer) {
                tableContainer.appendChild(statusElement);
            }
        }
        
        if (message) {
            const alertClass = {
                'info': 'alert-info',
                'success': 'alert-success',
                'warning': 'alert-warning',
                'error': 'alert-danger'
            }[type] || 'alert-info';
            
            statusElement.innerHTML = `
                <div class="alert ${alertClass} py-1 px-2 mb-1">
                    <small>${message}</small>
                    <button type="button" class="btn btn-sm btn-outline-secondary ml-2" onclick="window.aopTableManager.clearAopFilter()">
                        Clear Filter
                    </button>
                </div>
            `;
        } else {
            statusElement.innerHTML = '';
        }
    }

    setupTableStyles() {
        // Add custom CSS for better table display
        if (!document.querySelector('#aop-table-styles')) {
            const styles = document.createElement('style');
            styles.id = 'aop-table-styles';
            styles.textContent = `
                .aop-table-container {
                    max-height: 600px;
                    overflow-y: auto;
                }
                
                .aop-table {
                    font-size: 0.9em;
                }
                
                .aop-table td {
                    vertical-align: top;
                    padding: 12px 8px;
                    line-height: 1.4;
                    word-wrap: break-word;
                    max-width: 200px;
                }
                
                .aop-table th {
                    position: sticky;
                    top: 0;
                    background-color: #f8f9fa;
                    z-index: 10;
                    border-bottom: 2px solid #dee2e6;
                    font-weight: 600;
                }
                
                .node-type-badge {
                    display: inline-block;
                    padding: 2px 6px;
                    border-radius: 4px;
                    font-size: 0.8em;
                    font-weight: 500;
                    margin-right: 4px;
                }
                
                .node-type-mie { background-color: #e3f2fd; color: #1976d2; }
                .node-type-ao { background-color: #ffebee; color: #c62828; }
                .node-type-key_event { background-color: #f3e5f5; color: #7b1fa2; }
                .node-type-unknown { background-color: #f5f5f5; color: #666; }
                
                .disconnected-row {
                    background-color: #fff3cd;
                    border-left: 4px solid #ffc107;
                }
                
                .missing-label {
                    font-style: italic;
                    color: #6c757d;
                }
                
                .aop-titles-cell {
                    font-size: 0.85em;
                    color: #495057;
                }
                
                .ker-label-cell {
                    font-family: 'Monaco', 'Menlo', monospace;
                    font-size: 0.9em;
                    background-color: #f8f9fa;
                    padding: 4px 8px;
                    border-radius: 4px;
                }
                
                .filtered-out {
                    display: none !important;
                }
                
                .highlight-match {
                    background-color: #fff3cd;
                    font-weight: bold;
                }
                
                .aop-link, .aop-title-link {
                    cursor: pointer;
                    color: #007bff;
                    text-decoration: none;
                    padding: 2px 4px;
                    border-radius: 3px;
                    transition: all 0.2s ease;
                }
                
                .aop-link:hover, .aop-title-link:hover {
                    background-color: #e7f3ff;
                    text-decoration: underline;
                }
                
                .aop-link.selected-aop, .aop-title-link.selected-aop {
                    background-color: #ff6b35;
                    color: white;
                    font-weight: bold;
                }
                
                .aop-highlighted {
                    border-color: #ff6b35 !important;
                    border-width: 4px !important;
                    box-shadow: 0 0 10px rgba(255, 107, 53, 0.5);
                }
            `;
            document.head.appendChild(styles);
        }
    }

    updateTable(aopData) {
        this.currentData = aopData;
        this.filteredData = [...aopData];
        this.renderTable();
    }

    handleFilter(filterText) {
        this.filterText = filterText.toLowerCase().trim();
        
        if (!this.filterText) {
            this.filteredData = [...this.currentData];
            this.showAllNetworkNodes();
        } else {
            this.filteredData = this.currentData.filter(row => this.matchesFilter(row));
            this.filterNetworkNodes();
        }
        
        this.renderTable();
    }

    matchesFilter(row) {
        const searchText = this.filterText;
        
        // Search in all relevant fields
        const searchFields = [
            row.source_label,
            row.target_label,
            row.ker_label,
            row.aop_list,
            row.aop_titles,
            row.source_type,
            row.target_type
        ].join(' ').toLowerCase();
        
        return searchFields.includes(searchText);
    }

    renderTable() {
        const tableContainer = document.querySelector('#aop-table-container, .aop-table-container');
        if (!tableContainer) return;

        let table = tableContainer.querySelector('.aop-table');
        if (!table) {
            table = document.createElement('table');
            table.className = 'table table-striped table-hover aop-table';
            tableContainer.appendChild(table);
        }

        const html = this.generateTableHTML();
        table.innerHTML = html;
        
        // Add click handlers for node highlighting
        this.addNodeClickHandlers(table);
    }

    relayoutVisibleNodes(visibleNodeIds) {
        if (!window.cy || visibleNodeIds.size === 0) return;

        const visibleNodes = window.cy.nodes().filter(node => visibleNodeIds.has(node.id()));
        
        if (visibleNodes.length > 0) {
            const layout = visibleNodes.layout({
                name: 'cose',
                animate: true,
                animationDuration: 800,
                animationEasing: 'ease-out',
                nodeRepulsion: 8000,
                nodeOverlap: 20,
                idealEdgeLength: 100
            });
            
            layout.run();
        }
    }

    relayoutAllNodes() {
        if (!window.cy) return;

        const layout = window.cy.layout({
            name: 'cose',
            animate: true,
            animationDuration: 800,
            animationEasing: 'ease-out',
            nodeRepulsion: 8000,
            nodeOverlap: 20,
            idealEdgeLength: 100
        });
        
        layout.run();
    }
}

// Initialize the AOP Table Manager
window.aopTableManager = new AOPTableManager();

// Enhanced populate AOP table function
window.populateAopTable = function() {
    if (!window.cy) {
        console.warn("Network not initialized");
        return;
    }

    const cyElements = window.cy.elements().jsons();
    
    fetch('/populate_aop_table', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ cy_elements: cyElements })
    })
    .then(response => response.json())
    .then(data => {
        if (data.error) {
            console.error("Error populating AOP table:", data.error);
            return;
        }
        
        window.aopTableManager.updateTable(data.aop_data);
        console.log(`AOP table populated with ${data.aop_data.length} entries`);
    })
    .catch(error => {
        console.error("Error populating AOP table:", error);
    });
};

// Add CSS for node highlighting
if (!document.querySelector('#network-highlight-styles')) {
    const highlightStyles = document.createElement('style');
    highlightStyles.id = 'network-highlight-styles';
    highlightStyles.textContent = `
        .highlighted {
            border-width: 4px !important;
            border-color: #ff6b35 !important;
            z-index: 999 !important;
        }
    `;
    document.head.appendChild(highlightStyles);
}
