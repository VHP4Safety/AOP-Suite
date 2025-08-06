/**
 * Base Data Table Manager - provides common functionality for all table types
 */
class DataTableManager {
    constructor(tableId, containerSelector) {
        this.tableId = tableId;
        this.containerSelector = containerSelector;
        this.currentData = [];
        this.filteredData = [];
        this.filterText = '';
        this.isUpdating = false;
        this.updateTimeout = null;
        this.selectedRows = new Set();
        this.originalStyles = new Map(); // Store original network element styles
    }

    // Common initialization
    init() {
        this.setupFilterInput();
        this.setupTableStyles();
        this.setupBaseEventHandlers();
    }

    // Setup filter input - can be overridden by subclasses
    setupFilterInput() {
        const tableContainer = document.querySelector(this.containerSelector);
        if (tableContainer && !document.querySelector(`#${this.tableId}-filter`)) {
            const filterContainer = document.createElement('div');
            filterContainer.className = 'table-filter-container mb-3';
            filterContainer.innerHTML = `
                <div class="input-group">
                    <div class="input-group-prepend">
                        <span class="input-group-text"><i class="fas fa-search"></i></span>
                    </div>
                    <input type="text" id="${this.tableId}-filter" class="form-control" 
                           placeholder="Filter ${this.getTableDisplayName()} table...">
                    <div class="input-group-append">
                        <button class="btn btn-outline-secondary" id="clear-${this.tableId}-filter" type="button">
                            <i class="fas fa-times"></i>
                        </button>
                    </div>
                </div>
                <small class="form-text text-muted">
                    ${this.getFilterHelpText()}
                </small>
            `;
            
            tableContainer.insertBefore(filterContainer, tableContainer.firstChild);
            
            // Add event listeners
            document.getElementById(`${this.tableId}-filter`).addEventListener('input', (e) => {
                this.handleFilter(e.target.value);
            });
            
            document.getElementById(`clear-${this.tableId}-filter`).addEventListener('click', () => {
                document.getElementById(`${this.tableId}-filter`).value = '';
                this.handleFilter('');
            });
        }
    }

    // Abstract methods to be implemented by subclasses
    getTableDisplayName() {
        return 'data';
    }

    getFilterHelpText() {
        return 'Enter keywords to filter table rows.';
    }

    // Common filter handling
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

    // Default filter matching - can be overridden
    matchesFilter(row) {
        return JSON.stringify(row).toLowerCase().includes(this.filterText);
    }

    // Common network highlighting
    highlightNodeInNetwork(nodeId) {
        if (window.cy && nodeId) {
            // Clear previous highlights
            window.cy.elements().removeClass('highlighted');
            
            // Highlight the selected node
            const node = window.cy.getElementById(nodeId);
            if (node.length > 0) {
                node.addClass('highlighted');
                
                // Center on the node with animation
                window.cy.animate({
                    center: { eles: node },
                    zoom: Math.max(window.cy.zoom(), 1.5)
                }, {
                    duration: 500
                });
                
                // Remove highlight after a few seconds
                setTimeout(() => {
                    node.removeClass('highlighted');
                }, 3000);
            }
        }
    }

    // Common network filtering
    filterNetworkNodes() {
        if (!window.cy) return;

        this.saveOriginalStyles();

        const visibleNodeIds = this.getVisibleNodeIds();

        window.cy.batch(() => {
            window.cy.nodes().forEach(node => {
                if (visibleNodeIds.has(node.id())) {
                    node.removeClass('filtered-out').style('opacity', 1);
                } else {
                    node.addClass('filtered-out').style('opacity', 0.1);
                }
            });
            
            window.cy.edges().forEach(edge => {
                const sourceVisible = visibleNodeIds.has(edge.source().id());
                const targetVisible = visibleNodeIds.has(edge.target().id());
                
                if (sourceVisible && targetVisible) {
                    edge.removeClass('filtered-out').style('opacity', 1);
                } else {
                    edge.addClass('filtered-out').style('opacity', 0.1);
                }
            });
        });
    }

    // Get visible node IDs from filtered data - to be implemented by subclasses
    getVisibleNodeIds() {
        return new Set();
    }

    // Common method to show all network nodes
    showAllNetworkNodes() {
        if (!window.cy) return;

        window.cy.batch(() => {
            window.cy.nodes().forEach(node => {
                node.removeClass('filtered-out aop-filtered aop-grouped aop-faded aop-highlighted')
                    .style('opacity', node.data('original-opacity') || 1)
                    .style('border-width', node.data('original-border-width') || '2px')
                    .style('border-color', node.data('original-border-color') || '#000');
            });
            
            window.cy.edges().forEach(edge => {
                edge.removeClass('filtered-out aop-edge-highlighted aop-edge-faded')
                    .style('opacity', edge.data('original-opacity') || 1)
                    .style('line-color', edge.data('original-line-color') || '#93d5f6')
                    .style('target-arrow-color', edge.data('original-target-arrow-color') || '#93d5f6')
                    .style('width', edge.data('original-width') || '2px');
            });
        });
    }

    // Save original network element styles
    saveOriginalStyles() {
        if (!window.cy) return;
        
        window.cy.nodes().forEach(node => {
            const currentStyle = node.style();
            
            // Save all relevant style properties if not already saved
            if (!node.data('original-opacity')) {
                node.data('original-opacity', currentStyle['opacity'] || 1);
            }
            if (!node.data('original-border-width')) {
                node.data('original-border-width', currentStyle['border-width'] || '2px');
            }
            if (!node.data('original-border-color')) {
                node.data('original-border-color', currentStyle['border-color'] || '#000');
            }
        });
        
        window.cy.edges().forEach(edge => {
            const currentStyle = edge.style();
            
            // Save all relevant style properties if not already saved
            if (!edge.data('original-opacity')) {
                edge.data('original-opacity', currentStyle['opacity'] || 1);
            }
            if (!edge.data('original-line-color')) {
                edge.data('original-line-color', currentStyle['line-color'] || '#93d5f6');
            }
            if (!edge.data('original-target-arrow-color')) {
                edge.data('original-target-arrow-color', currentStyle['target-arrow-color'] || '#93d5f6');
            }
            if (!edge.data('original-width')) {
                edge.data('original-width', currentStyle['width'] || '2px');
            }
        });
    }

    // Common row selection methods
    toggleRowSelection(row, rowData) {
        const rowIndex = parseInt(row.dataset.rowIndex);
        
        if (this.selectedRows.has(rowIndex)) {
            this.selectedRows.delete(rowIndex);
            row.classList.remove('table-selected');
        } else {
            this.selectedRows.add(rowIndex);
            row.classList.add('table-selected');
        }
    }

    clearTableSelection() {
        document.querySelectorAll('.table-selected').forEach(row => {
            row.classList.remove('table-selected');
        });
        this.selectedRows.clear();
    }

    // Base table styles
    setupTableStyles() {
        if (!document.querySelector('#base-table-styles')) {
            const styles = document.createElement('style');
            styles.id = 'base-table-styles';
            styles.textContent = `
                .table-filter-container {
                    margin-bottom: 1rem;
                }
                
                .table-selected {
                    background-color: #e3f2fd !important;
                    border-left: 4px solid #2196f3 !important;
                }
                
                .table-selected:hover {
                    background-color: #e1f5fe !important;
                }
                
                .filtered-out {
                    display: none !important;
                }
                
                .highlight-match {
                    background-color: #fff3cd;
                    font-weight: bold;
                }
                
                .highlighted-cell {
                    background-color: #fff3cd !important;
                    border: 2px solid #ffc107 !important;
                    font-weight: bold;
                    box-shadow: 0 0 8px rgba(255, 193, 7, 0.5);
                }
            `;
            document.head.appendChild(styles);
        }
    }

    // Base event handlers
    setupBaseEventHandlers() {
        // Common event handling can go here
    }

    // Highlight text matches in table content
    highlightMatch(text) {
        if (!this.filterText || !text || text === 'N/A') return text;
        
        const regex = new RegExp(`(${this.filterText})`, 'gi');
        return text.replace(regex, '<span class="highlight-match">$1</span>');
    }

    // Abstract methods to be implemented by subclasses
    renderTable() {
        throw new Error('renderTable must be implemented by subclass');
    }

    updateTable(data) {
        this.currentData = data;
        this.filteredData = [...data];
        this.renderTable();
    }

    async performTableUpdate() {
        throw new Error('performTableUpdate must be implemented by subclass');
    }
}

/**
 * AOP Table Manager - extends base functionality for AOP-specific features
 */
class AOPTableManager extends DataTableManager {
    constructor() {
        super('aop-table', '#aop-table-container, .aop-table-container');
        this.selectedAop = null;
        this.groupedAops = new Set();
        this.aopColorMap = new Map(); // Add color mapping storage
        this.init();
        this.setupNetworkListeners();
    }

    getTableDisplayName() {
        return 'AOP';
    }

    getFilterHelpText() {
        return 'Filter affects both table display and network visibility. Use keywords like "MIE", "AO", specific node names, or AOP numbers.';
    }

    getVisibleNodeIds() {
        const visibleNodeIds = new Set();
        this.filteredData.forEach(row => {
            if (row.source_id !== 'N/A') visibleNodeIds.add(row.source_id);
            if (row.target_id !== 'N/A') visibleNodeIds.add(row.target_id);
        });
        return visibleNodeIds;
    }

    matchesFilter(row) {
        const searchFields = [
            row.source_label,
            row.target_label,
            row.ker_label,
            row.aop_list,
            row.aop_titles,
            row.source_type,
            row.target_type
        ].join(' ').toLowerCase();
        
        return searchFields.includes(this.filterText);
    }

    generateTableHTML() {
        const headers = [
            'Source Node',
            'KER Label',
            'Target Node', 
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
        
        html += `<tfoot><tr><td colspan="5" class="text-muted small">
            Showing ${filteredRows} of ${totalRows} entries 
            (${connectedRows} connected, ${disconnectedRows} disconnected nodes)
            ${this.filterText ? ` - Filtered by: "${this.filterText}"` : ''}
            ${this.selectedAop ? ` - Filtered by AOP: ${this.selectedAop}` : ''}
            ${this.groupedAops.size > 0 ? ` - Grouped AOPs: ${this.groupedAops.size}` : ''}
        </td></tr></tfoot>`;

        return html;
    }

    generateClickableAopIds(aopList) {
        if (!aopList || aopList === 'N/A') return aopList;
        
        const aopIds = aopList.split(',').map(id => id.trim());
        return aopIds.map(aopId => {
            const isSelected = this.selectedAop === aopId;
            const isGrouped = this.groupedAops.has(aopId);
            let className = 'aop-link';
            let style = '';
            
            if (isSelected) {
                className += ' selected-aop';
            } else if (isGrouped) {
                className += ' grouped-aop';
                // Use the same color as in the network
                const color = this.aopColorMap.get(aopId);
                if (color) {
                    style = `background-color: ${color}; color: white; font-weight: bold;`;
                }
            }
            
            return `<span class="${className}" data-aop-id="${aopId}" title="Click to filter network by this AOP (Ctrl+Click to group)" ${style ? `style="${style}"` : ''}>${this.highlightMatch(aopId)}</span>`;
        }).join(', ');
    }

    generateClickableAopTitles(aopTitles, aopList) {
        if (!aopTitles || aopTitles === 'N/A') return aopTitles;
        
        const titles = aopTitles.split(';').map(title => title.trim());
        const aopIds = aopList && aopList !== 'N/A' ? aopList.split(',').map(id => id.trim()) : [];
        
        return titles.map((title, index) => {
            const correspondingAopId = aopIds[index] || aopIds[0] || '';
            const isSelected = this.selectedAop === correspondingAopId;
            const isGrouped = this.groupedAops.has(correspondingAopId);
            let className = 'aop-title-link';
            let style = '';
            
            if (isSelected) {
                className += ' selected-aop';
            } else if (isGrouped) {
                className += ' grouped-aop';
                // Use the same color as in the network
                const color = this.aopColorMap.get(correspondingAopId);
                if (color) {
                    style = `background-color: ${color}; color: white; font-weight: bold;`;
                }
            }
            
            return `<span class="${className}" data-aop-id="${correspondingAopId}" title="Click to filter network by this AOP (Ctrl+Click to group): ${correspondingAopId}" ${style ? `style="${style}"` : ''}>${this.highlightMatch(title)}</span>`;
        }).join('; ');
    }

    renderTable() {
        const tableContainer = document.querySelector(this.containerSelector);
        if (!tableContainer) return;

        let table = tableContainer.querySelector('.aop-table');
        if (!table) {
            table = document.createElement('table');
            table.className = 'table table-striped table-hover aop-table';
            tableContainer.appendChild(table);
        }

        const html = this.generateTableHTML();
        table.innerHTML = html;
        this.addNodeClickHandlers(table);
    }

    setupTableStyles() {
        super.setupTableStyles();
        
        if (!document.querySelector('#aop-table-styles')) {
            const styles = document.createElement('style');
            styles.id = 'aop-table-styles';
            styles.textContent = `
                .aop-table-container {
                    max-height: 600px;
                    overflow-y: auto;
                }
                
                .node-type-badge {
                    display: inline-block;
                    padding: 2px 6px;
                    border-radius: 4px;
                    font-size: 0.8em;
                    font-weight: 500;
                    margin-right: 4px;
                }
                
                .node-type-mie { background-color: #ccffcc; color:rgb(139, 192, 155); }
                .node-type-ao { background-color: #ffe6e6; color: #c62828; }
                .node-type-key_event { background-color: #ffff99; color:rgb(180, 180, 56); }
                .node-type-unknown { background-color: #f5f5f5; color: #666; }
                
                .aop-link, .aop-title-link {
                    cursor: pointer;
                    color: #007bff;
                    text-decoration: none;
                    padding: 2px 4px;
                    border-radius: 3px;
                    transition: all 0.2s ease;
                    display: inline-block;
                    margin: 1px;
                }
                
                .aop-link.selected-aop, .aop-title-link.selected-aop {
                    background-color: #ff6b35;
                    color: white;
                    font-weight: bold;
                }
                
                .aop-link.grouped-aop, .aop-title-link.grouped-aop {
                    background-color: #4CAF50;
                    color: white;
                    font-weight: bold;
                }
            `;
            document.head.appendChild(styles);
        }
    }

    addNodeClickHandlers(table) {
        table.querySelectorAll('[data-node-id]').forEach(element => {
            element.style.cursor = 'pointer';
            element.addEventListener('click', (e) => {
                const nodeId = e.target.getAttribute('data-node-id');
                this.highlightNodeInNetwork(nodeId);
            });
        });

        table.querySelectorAll('.aop-link, .aop-title-link').forEach(element => {
            element.style.cursor = 'pointer';
            element.addEventListener('click', (e) => {
                e.preventDefault();
                e.stopPropagation();
                const aopId = e.target.getAttribute('data-aop-id');
                
                if (e.ctrlKey || e.metaKey) {
                    this.toggleAopGroup(aopId);
                } else {
                    this.toggleAopFilter(aopId);
                }
            });
        });
        
        this.setupRowSelection(table);
    }

    toggleAopGroup(aopId) {
        console.log('Toggling AOP group for:', aopId);
        
        if (this.groupedAops.has(aopId)) {
            this.groupedAops.delete(aopId);
        } else {
            this.groupedAops.add(aopId);
        }
        
        if (this.selectedAop) {
            this.selectedAop = null;
        }
        
        // Check if all groups are now cleared
        if (this.groupedAops.size === 0) {
            this.aopColorMap.clear();
            this.showAllNetworkNodes();
        } else {
            this.applyGroupHighlighting();
        }
        
        this.renderTable();
    }

    toggleAopFilter(aopId) {
        console.log('Toggling AOP filter for:', aopId);
        
        this.groupedAops.clear();
        
        if (this.selectedAop === aopId) {
            this.clearAopFilter();
            return;
        }
        
        this.selectedAop = aopId;
        this.filterByAop(aopId);
        this.renderTable();
    }

    clearAopFilter() {
        console.log('Clearing AOP filter');
        this.selectedAop = null;
        this.aopColorMap.clear(); // Clear color mapping when clearing filter
        this.showAllNetworkNodes();
        this.renderTable();
    }

    applyGroupHighlighting() {
        if (!window.cy || this.groupedAops.size === 0) {
            this.showAllNetworkNodes();
            this.aopColorMap.clear(); // Clear color mapping when no groups
            return;
        }
        
        this.saveOriginalStyles();
        
        // Expanded color palette for better variety
        const colors = [
            '#ff6b35', '#4CAF50', '#2196F3', '#9C27B0', '#FF9800', 
            '#795548', '#607D8B', '#E91E63', '#00BCD4', '#8BC34A',
            '#F44336', '#673AB7', '#3F51B5', '#009688', '#CDDC39',
            '#FFC107', '#FF5722', '#9E9E9E', '#5D4037', '#37474F',
            '#1A237E', '#004D40', '#33691E', '#E65100', '#BF360C',
            '#212121', '#3E2723', '#1B5E20', '#0D47A1', '#006064',
            '#827717', '#F57F17', '#FF6F00', '#E65100', '#BF360C'
        ];
        
        // Clear and rebuild color mapping
        this.aopColorMap.clear();
        Array.from(this.groupedAops).forEach((aopId, index) => {
            this.aopColorMap.set(aopId, colors[index % colors.length]);
        });
        
        const nodeColorMap = new Map();
        
        window.cy.nodes().forEach(node => {
            const nodeData = node.data();
            const nodeAops = nodeData.aop || [];
            const aopsToCheck = Array.isArray(nodeAops) ? nodeAops : [nodeAops];
            
            for (const nodeAop of aopsToCheck) {
                if (!nodeAop) continue;
                
                let nodeAopId = '';
                if (nodeAop.includes('aop/')) {
                    nodeAopId = `AOP:${nodeAop.split('aop/').pop()}`;
                } else if (nodeAop.startsWith('AOP:')) {
                    nodeAopId = nodeAop;
                } else if (nodeAop.match(/^\d+$/)) {
                    nodeAopId = `AOP:${nodeAop}`;
                }
                
                if (this.groupedAops.has(nodeAopId)) {
                    nodeColorMap.set(node.id(), this.aopColorMap.get(nodeAopId));
                    break;
                }
            }
        });
        
        window.cy.batch(() => {
            window.cy.nodes().forEach(node => {
                const nodeColor = nodeColorMap.get(node.id());
                if (nodeColor) {
                    node.removeClass('filtered-out aop-filtered')
                         .addClass('aop-grouped')
                         .style('opacity', 1)
                         .style('border-width', '4px')
                         .style('border-color', nodeColor);
                } else {
                    node.removeClass('aop-grouped')
                         .addClass('aop-faded')
                         .style('opacity', 0.3)
                         .style('border-width', '2px')
                         .style('border-color', '#ccc');
                }
            });
            
            window.cy.edges().forEach(edge => {
                const sourceColor = nodeColorMap.get(edge.source().id());
                const targetColor = nodeColorMap.get(edge.target().id());
                
                if (sourceColor && targetColor) {
                    edge.removeClass('filtered-out')
                        .addClass('aop-edge-highlighted')
                        .style('opacity', 1)
                        .style('line-color', sourceColor)
                        .style('target-arrow-color', sourceColor)
                        .style('width', '3px');
                } else {
                    edge.removeClass('aop-edge-highlighted')
                        .addClass('aop-edge-faded')
                        .style('opacity', 0.2)
                        .style('line-color', '#ccc')
                        .style('target-arrow-color', '#ccc')
                        .style('width', '1px');
                }
            });
        });
    }

    filterByAop(aopId) {
        if (!window.cy || !aopId) return;
        
        console.log('Filtering network by AOP:', aopId);
        
        const aopNodes = new Set();
        this.saveOriginalStyles();
        
        window.cy.nodes().forEach(node => {
            const nodeData = node.data();
            const nodeAops = nodeData.aop || [];
            const aopsToCheck = Array.isArray(nodeAops) ? nodeAops : [nodeAops];
            
            const hasMatchingAop = aopsToCheck.some(nodeAop => {
                if (!nodeAop) return false;
                
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
        
        window.cy.batch(() => {
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
        
        if (aopNodes.size > 0) {
            const nodesToFit = window.cy.nodes().filter(node => aopNodes.has(node.id()));
            
            window.cy.animate({
                fit: { eles: nodesToFit, padding: 50 },
                duration: 1000,
                easing: 'ease-out'
            });
        }
    }

    setupRowSelection(table) {
        table.removeEventListener('click', this.handleRowClick);
        
        this.handleRowClick = (e) => {
            const row = e.target.closest('tr');
            if (!row || !row.dataset.rowIndex) return;
            
            if (e.target.closest('.aop-link, .aop-title-link, [data-node-id]')) return;
            
            const rowIndex = parseInt(row.dataset.rowIndex);
            const rowData = this.filteredData[rowIndex];
            if (!rowData) return;
            
            e.preventDefault();
            
            if (e.ctrlKey || e.metaKey) {
                this.toggleRowSelection(row, rowData);
            } else {
                this.clearTableSelection();
                this.selectedRows.add(rowIndex);
                row.classList.add('table-selected');
            }
        };
        
        table.addEventListener('click', this.handleRowClick);
    }

    setupNetworkListeners() {
        if (!window.cy) {
            console.log('Cytoscape not ready, will setup AOP table listeners later');
            return;
        }
        
        console.log('Setting up AOP table network listeners');
        
        window.cy.on('add remove', (event) => {
            console.log('Network changed, updating AOP table with smooth transition');
            clearTimeout(window.aopTableUpdateTimeout);
            window.aopTableUpdateTimeout = setTimeout(() => {
                const tableBody = $("#aop_table tbody");
                if (tableBody.length > 0) {
                    tableBody.addClass('updating');
                }
                
                setTimeout(() => {
                    this.performTableUpdate().then(() => {
                        if (tableBody.length > 0) {
                            tableBody.removeClass('updating');
                        }
                    });
                }, 100);
            }, 500);
        });
    }
    groupByAllAops() {
        console.log('Grouping by all AOPs');

        // Clear single selection
        this.selectedAop = null;

        // Get all unique AOP IDs from current data
        const allAopIds = new Set();
        this.currentData.forEach(row => {
            if (row.aop_list && row.aop_list !== 'N/A') {
                const aopIds = row.aop_list.split(',').map(id => id.trim());
                aopIds.forEach(id => allAopIds.add(id));
            }
        });

        // Toggle: if all are already grouped, clear them; otherwise group all
        const allAlreadyGrouped = Array.from(allAopIds).every(id => this.groupedAops.has(id));

        if (allAlreadyGrouped) {
            this.groupedAops.clear();
            this.aopColorMap.clear(); // Clear color mapping
            this.showAllNetworkNodes(); // Restore original styles
        } else {
            this.groupedAops = new Set(allAopIds);
            this.applyGroupHighlighting();
        }

        this.renderTable();

        // Update button text
        const button = document.getElementById('toggle_bounding_boxes');
        if (button) {
            button.textContent = this.groupedAops.size > 0 ? 'Clear AOP Groups' : 'Group by AOP';
        }
    }
    debouncedUpdateTable(delay = 500) {
        // Clear any existing timeout
        if (this.updateTimeout) {
            clearTimeout(this.updateTimeout);
        }

        // Set new timeout
        this.updateTimeout = setTimeout(() => {
            if (!this.isUpdating) {
                this.performTableUpdate();
            }
        }, delay);
    }

    async performTableUpdate() {
        if (this.isUpdating) {
            console.log('Table update already in progress, skipping');
            return;
        }

        if (!window.cy) {
            console.warn("Network not initialized for table update");
            return;
        }

        this.isUpdating = true;
        console.log('Starting AOP table update...');

        try {
            const cyElements = window.cy.elements().jsons();
            
            const response = await fetch('/populate_aop_table', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ cy_elements: cyElements })
            });

            if (!response.ok) {
                throw new Error(`HTTP ${response.status}: ${response.statusText}`);
            }

            const data = await response.json();
            
            if (data.error) {
                console.error("Error populating AOP table:", data.error);
                this.currentData = [];
                this.filteredData = [];
                this.renderTable();
                return;
            }
            
            if (data.aop_data && data.aop_data.length > 0) {
                this.updateTable(data.aop_data);
                console.log(`AOP table updated with ${data.aop_data.length} entries`);
            } else {
                this.currentData = [];
                this.filteredData = [];
                this.renderTable();
            }
            
        } catch (error) {
            console.error("Error updating AOP table:", error);
            this.currentData = [];
            this.filteredData = [];
            this.renderTable();
        } finally {
            this.isUpdating = false;
        }
    }
}

/**
 * Gene Table Manager - extends base functionality for gene-specific features
 */
class GeneTableManager extends DataTableManager {
    constructor() {
        super('gene-table', '#gene-table-container');
        this.init();
        this.setupNetworkListeners();
    }

    getTableDisplayName() {
        return 'Gene';
    }

    getFilterHelpText() {
        return 'Filter by gene symbols, protein names, UniProt IDs, or Ensembl IDs.';
    }

    getVisibleNodeIds() {
        const visibleNodeIds = new Set();
        this.filteredData.forEach(row => {
            if (row.ensembl_id && row.ensembl_id !== 'N/A') visibleNodeIds.add(row.ensembl_id);
            if (row.uniprot_node_id && row.uniprot_node_id !== 'N/A') visibleNodeIds.add(row.uniprot_node_id);
        });
        return visibleNodeIds;
    }

    matchesFilter(row) {
        const searchFields = [
            row.gene,
            row.protein,
            row.uniprot_id,
            row.ensembl_id,
            row.uniprot_node_id
        ].join(' ').toLowerCase();
        
        return searchFields.includes(this.filterText);
    }

    setupFilterInput() {
        // Find the correct container for the gene table
        const geneTableWrapper = document.querySelector('#gene_table')?.closest('.table-wrapper') || 
                                 document.querySelector('.gene-table-panel .table-wrapper');
        
        if (geneTableWrapper && !document.querySelector(`#${this.tableId}-filter`)) {
            const filterContainer = document.createElement('div');
            filterContainer.className = 'table-filter-container mb-3';
            filterContainer.innerHTML = `
                <div class="input-group">
                    <div class="input-group-prepend">
                        <span class="input-group-text"><i class="fas fa-search"></i></span>
                    </div>
                    <input type="text" id="${this.tableId}-filter" class="form-control" 
                           placeholder="Filter ${this.getTableDisplayName()} table...">
                    <div class="input-group-append">
                        <button class="btn btn-outline-secondary" id="clear-${this.tableId}-filter" type="button">
                            <i class="fas fa-times"></i>
                        </button>
                    </div>
                </div>
                <small class="form-text text-muted">
                    ${this.getFilterHelpText()}
                </small>
            `;
            
            geneTableWrapper.insertBefore(filterContainer, geneTableWrapper.firstChild);
            
            // Add event listeners
            document.getElementById(`${this.tableId}-filter`).addEventListener('input', (e) => {
                this.handleFilter(e.target.value);
            });
            
            document.getElementById(`clear-${this.tableId}-filter`).addEventListener('click', () => {
                document.getElementById(`${this.tableId}-filter`).value = '';
                this.handleFilter('');
            });
        }
    }

    setupNetworkListeners() {
        if (!window.cy) {
            console.log('Cytoscape not ready, will setup gene table listeners later');
            return;
        }
        
        console.log('Setting up gene table network listeners');
        
        window.cy.on('add remove', (event) => {
            console.log('Network changed, updating gene table');
            this.debouncedUpdateTable();
        });
    }

    debouncedUpdateTable(delay = 500) {
        if (this.updateTimeout) {
            clearTimeout(this.updateTimeout);
        }

        this.updateTimeout = setTimeout(() => {
            if (!this.isUpdating) {
                this.performTableUpdate();
            }
        }, delay);
    }

    generateTableHTML() {
        const headers = ['Gene Symbol', 'Protein Name'];

        let html = '<thead><tr>';
        headers.forEach(header => {
            html += `<th>${header}</th>`;
        });
        html += '</tr></thead><tbody>';

        this.filteredData.forEach((gene, index) => {
            const proteinDisplay = gene.protein !== "N/A" ?
                `<a href="https://www.uniprot.org/uniprotkb/${gene.uniprot_id}" target="_blank">${this.highlightMatch(gene.protein)}</a>` :
                "N/A";

            const geneDisplay = gene.gene !== "N/A" ?
                `<a href="https://identifiers.org/ensembl:${gene.gene}" target="_blank">${this.highlightMatch(gene.gene)}</a>` :
                "N/A";

            html += `
                <tr data-gene="${gene.gene}" 
                    data-uniprot-id="${gene.uniprot_id}" 
                    data-ensembl-id="${gene.ensembl_id}"
                    data-uniprot-node-id="${gene.uniprot_node_id}"
                    data-row-index="${index}"
                    style="cursor: pointer;">
                    <td class="gene-cell clickable-cell" data-node-id="${gene.ensembl_id}" style="cursor: pointer;">
                        ${geneDisplay}
                    </td>
                    <td class="protein-cell clickable-cell" data-node-id="${gene.uniprot_node_id}" style="cursor: pointer;">
                        ${proteinDisplay}
                    </td>
                </tr>
            `;
        });

        html += '</tbody>';

        // Add summary
        const totalRows = this.currentData.length;
        const filteredRows = this.filteredData.length;
        
        html += `<tfoot><tr><td colspan="2" class="text-muted small">
            Showing ${filteredRows} of ${totalRows} genes
            ${this.filterText ? ` - Filtered by: "${this.filterText}"` : ''}
        </td></tr></tfoot>`;

        return html;
    }

    renderTable() {
        const tableContainer = document.querySelector('#gene_table')?.closest('.table-responsive') || 
                              document.querySelector('#gene_table')?.parentElement ||
                              document.querySelector(this.containerSelector);
        
        if (!tableContainer) {
            console.warn("Gene table container not found");
            return;
        }

        let table = document.querySelector('#gene_table');
        if (!table) {
            console.warn("Gene table not found");
            return;
        }

        if (this.filteredData.length === 0) {
            this.showEmptyTable();
            return;
        }

        const html = this.generateTableHTML();
        table.innerHTML = html;
        this.setupGeneTableEventHandlers();
    }

    setupTableStyles() {
        super.setupTableStyles();
        
        if (!document.querySelector('#gene-table-styles')) {
            const styles = document.createElement('style');
            styles.id = 'gene-table-styles';
            styles.textContent = `
                #gene_table tbody tr {
                    cursor: pointer;
                    transition: background-color 0.2s ease;
                }

                #gene_table tbody tr:hover {
                    background-color: #f8f9fa !important;
                    cursor: pointer;
                }

                .gene-cell, .protein-cell {
                    transition: all 0.2s ease;
                    padding: 8px 12px;
                    border-radius: 4px;
                }

                .gene-cell:hover, .protein-cell:hover {
                    background-color: #e7f3ff !important;
                    transform: translateY(-1px);
                    box-shadow: 0 2px 4px rgba(0, 123, 255, 0.2);
                }

                .gene-table-panel .table-filter-container {
                    background: #f8f9fa;
                    padding: 10px;
                    border-radius: 5px;
                    margin-bottom: 10px;
                }

                .gene-table-panel .input-group-text {
                    background: #e9ecef;
                    border-color: #ced4da;
                }
            `;
            document.head.appendChild(styles);
        }
    }

    setupGeneTableEventHandlers() {
        const table = document.querySelector('#gene_table');
        if (!table) return;

        // Remove existing listeners
        const tbody = table.querySelector('tbody');
        const newTbody = tbody.cloneNode(true);
        tbody.parentNode.replaceChild(newTbody, tbody);

        // Gene/protein cell click handlers
        newTbody.querySelectorAll('.gene-cell, .protein-cell').forEach(cell => {
            cell.addEventListener('click', (e) => {
                if (e.target.closest('a')) return;
                
                e.preventDefault();
                e.stopPropagation();

                const nodeId = cell.getAttribute('data-node-id');
                if (!nodeId || nodeId === 'N/A') return;

                this.highlightNodeInNetwork(nodeId);

                // Visual feedback
                document.querySelectorAll('.gene-cell, .protein-cell').forEach(c => 
                    c.classList.remove('highlighted-cell'));
                cell.classList.add('highlighted-cell');

                setTimeout(() => {
                    cell.classList.remove('highlighted-cell');
                }, 3000);
            });
        });

        // Row click handlers
        newTbody.querySelectorAll('tr').forEach(row => {
            row.addEventListener('click', (e) => {
                if (e.target.closest('a') || e.target.closest('.gene-cell, .protein-cell')) return;

                const geneSymbol = row.dataset.gene;
                const uniprotId = row.dataset.uniprotId;
                const ensemblId = row.dataset.ensemblId;
                
                if (!geneSymbol) return;
                
                // Selection handling
                if (e.ctrlKey || e.metaKey) {
                    this.toggleRowSelection(row, { gene: geneSymbol });
                } else {
                    this.clearTableSelection();
                    row.classList.add('table-selected');
                    this.selectedRows.add(parseInt(row.dataset.rowIndex));
                }
                
                // Network highlighting
                if (window.cy) {
                    window.cy.elements().removeClass('highlighted');
                    
                    const ensemblNode = window.cy.getElementById(ensemblId);
                    const uniprotNode = window.cy.$(`[uniprot_id="${uniprotId}"]`);
                    
                    if (ensemblNode.length > 0) {
                        ensemblNode.addClass('highlighted');
                        window.cy.center(ensemblNode);
                    }
                    
                    if (uniprotNode.length > 0) {
                        uniprotNode.addClass('highlighted');
                    }
                }
            });
        });
    }

    async performTableUpdate() {
        if (this.isUpdating) {
            console.log('Gene table update already in progress, skipping');
            return;
        }

        if (!window.cy) {
            console.warn("Cytoscape not available for gene table update");
            return;
        }

        this.isUpdating = true;

        try {
            const response = await fetch('/populate_gene_table', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ cy_elements: window.cy.elements().jsons() })
            });

            const data = await response.json();

            if (data.gene_data && data.gene_data.length > 0) {
                this.updateTable(data.gene_data);
                console.log(`Gene table updated with ${data.gene_data.length} genes.`);
            } else {
                this.currentData = [];
                this.filteredData = [];
                this.showEmptyTable();
            }
        } catch (error) {
            console.error("Error updating gene table:", error);
            this.showEmptyTable();
        } finally {
            this.isUpdating = false;
        }
    }

    showEmptyTable() {
        const tableBody = document.querySelector("#gene_table tbody");
        if (!tableBody) return;

        tableBody.innerHTML = `
            <tr id="default-gene-row">
                <td colspan="2" style="text-align: center; padding: 20px;">
                    <div style="color: #6c757d; font-style: italic; margin-bottom: 15px;">
                        No genes in network. You can query the AOP-Wiki RDF for gene sets associated with Key Events or draw your own Ensembl identifiers.
                    </div>
                    <button id="get-genes-table-btn" class="btn btn-primary btn-sm">
                        <i class="fas fa-dna"></i> Get gene sets
                    </button>
                </td>
            </tr>
        `;
        
        document.getElementById("get-genes-table-btn")?.addEventListener("click", function(e) {
            e.preventDefault();
            e.stopPropagation();
            if (window.toggleGenes) {
                window.toggleGenes();
            }
        });
    }
}

/**
 * Compound Table Manager - extends base functionality for compound-specific features
 */
class CompoundTableManager extends DataTableManager {
    constructor() {
        super('compound-table', '#compound-table-container');
        this.init();
        this.setupNetworkListeners();
    }

    getTableDisplayName() {
        return 'Compound';
    }

    getFilterHelpText() {
        return 'Filter by compound names, CAS IDs, PubChem IDs, or chemical labels.';
    }

    getVisibleNodeIds() {
        const visibleNodeIds = new Set();
        this.filteredData.forEach(row => {
            if (row.node_id && row.node_id !== 'N/A') visibleNodeIds.add(row.node_id);
        });
        return visibleNodeIds;
    }

    matchesFilter(row) {
        const searchFields = [
            row.compound_name,
            row.cas_id,
            row.chemical_label,
            row.pubchem_id,
            row.smiles
        ].join(' ').toLowerCase();
        
        return searchFields.includes(this.filterText);
    }

    setupFilterInput() {
        // Find the correct container for the compound table
        const compoundTableWrapper = document.querySelector('#compound_table')?.closest('.table-wrapper') || 
                                    document.querySelector('.compound-table-panel .table-wrapper');
        
        if (compoundTableWrapper && !document.querySelector(`#${this.tableId}-filter`)) {
            const filterContainer = document.createElement('div');
            filterContainer.className = 'table-filter-container mb-3';
            filterContainer.innerHTML = `
                <div class="input-group">
                    <div class="input-group-prepend">
                        <span class="input-group-text"><i class="fas fa-search"></i></span>
                    </div>
                    <input type="text" id="${this.tableId}-filter" class="form-control" 
                           placeholder="Filter ${this.getTableDisplayName()} table...">
                    <div class="input-group-append">
                        <button class="btn btn-outline-secondary" id="clear-${this.tableId}-filter" type="button">
                            <i class="fas fa-times"></i>
                        </button>
                    </div>
                </div>
                <small class="form-text text-muted">
                    ${this.getFilterHelpText()}
                </small>
            `;
            
            compoundTableWrapper.insertBefore(filterContainer, compoundTableWrapper.firstChild);
            
            // Add event listeners
            document.getElementById(`${this.tableId}-filter`).addEventListener('input', (e) => {
                this.handleFilter(e.target.value);
            });
            
            document.getElementById(`clear-${this.tableId}-filter`).addEventListener('click', () => {
                document.getElementById(`${this.tableId}-filter`).value = '';
                this.handleFilter('');
            });
        }
    }

    setupNetworkListeners() {
        if (!window.cy) {
            console.log('Cytoscape not ready, will setup compound table listeners later');
            return;
        }
        
        console.log('Setting up compound table network listeners');
        
        window.cy.on('add remove', (event) => {
            console.log('Network changed, updating compound table');
            this.debouncedUpdateTable();
        });
    }

    debouncedUpdateTable(delay = 500) {
        if (this.updateTimeout) {
            clearTimeout(this.updateTimeout);
        }

        this.updateTimeout = setTimeout(() => {
            if (!this.isUpdating) {
                this.performTableUpdate();
            }
        }, delay);
    }

    generateCompoundRowHTML(row, index) {
        const cas_id = row.cas_id || "";
        const chemical_label = row.chemical_label || "";
        const chemical_uri = row.chemical_uri || "";
        const compound_name = row.compound_name || "Unknown Compound";
        const node_id = row.node_id || "";
        const pubchem_compound = row.pubchem_compound || "";
        const pubchem_id = row.pubchem_id || "";
        const smiles = row.smiles || "";
        
        // Generate SMILES image URL if SMILES data is available
        const encodedSMILES = smiles ? encodeURIComponent(smiles) : "";
        const imgUrl = smiles ? 
            `https://cdkdepict.cloud.vhp4safety.nl/depict/bot/svg?w=-1&h=-1&abbr=off&hdisp=bridgehead&showtitle=false&zoom=0.5&annotate=cip&r=0&smi=${encodedSMILES}` 
            : '';

        // Create compound link with external URL if PubChem ID available
        const compoundLink = pubchem_id && pubchem_id !== "" ?
            `<a href="${pubchem_compound || `https://pubchem.ncbi.nlm.nih.gov/compound/${pubchem_id}`}" target="_blank" class="compound-link">${this.highlightMatch(compound_name)}</a>` :
            `<span class="compound-link">${this.highlightMatch(compound_name)}</span>`;

        return `
            <tr data-compound-id="${node_id}" 
                data-node-id="${node_id}"
                data-row-index="${index}"
                data-smiles="${smiles}" 
                data-chemical_label="${chemical_label}" 
                data-chemical_uri="${chemical_uri}" 
                data-compound_name="${compound_name}" 
                data-pubchem_compound="${pubchem_compound}" 
                data-compound-source="AOP-Wiki RDF" 
                class="network-compound"
                style="cursor: pointer;">
                <td>
                    ${imgUrl ? `<img src="${imgUrl}" alt="${smiles}" style="max-width: 100px; height: auto;" />` : ''}
                    <p>${compoundLink}</p>
                    ${cas_id && cas_id !== "" ? `<p><small>CAS: ${this.highlightMatch(cas_id)}</small></p>` : ''}
                </td>
            </tr>
        `;
    }

    renderTable() {
        const tableBody = $("#compound_table tbody");
        const table = document.querySelector('#compound_table');
        
        if (!tableBody.length || !table) {
            console.warn("Compound table not found");
            return;
        }

        if (this.filteredData.length === 0) {
            this.showEmptyTable();
            return;
        }

        // Clear the entire table body first
        tableBody.empty();

        this.filteredData.forEach((row, index) => {
            const rowHTML = this.generateCompoundRowHTML(row, index);
            tableBody.append(rowHTML);
        });

        // Add summary to tfoot
        const tfoot = table.querySelector('tfoot') || table.createTFoot();
        const totalRows = this.currentData.length;
        const filteredRows = this.filteredData.length;
        
        tfoot.innerHTML = `
            <tr>
                <td class="text-muted small">
                    Showing ${filteredRows} of ${totalRows} compounds
                    ${this.filterText ? ` - Filtered by: "${this.filterText}"` : ''}
                </td>
            </tr>
        `;

        this.setupCompoundTableEventHandlers();
        console.log(`Compound table updated with ${this.filteredData.length} compounds from network.`);
    }

    setupTableStyles() {
        super.setupTableStyles();
        
        if (!document.querySelector('#compound-table-styles')) {
            const styles = document.createElement('style');
            styles.id = 'compound-table-styles';
            styles.textContent = `
                .network-compound {
                    border-left: 3px solid #28a745 !important;
                    background-color: #f8fff9 !important;
                }

                .compound-link {
                    color: #155724 !important;
                    font-weight: bold;
                    position: relative;
                    z-index: 10;
                    pointer-events: auto;
                }

                #compound_table tbody tr {
                    cursor: pointer;
                    transition: background-color 0.2s ease;
                }

                #compound_table tbody tr:hover {
                    background-color: #f8f9fa !important;
                }

                #compound_table img {
                    max-width: 100px;
                    height: auto;
                    border-radius: 4px;
                    border: 1px solid #ddd;
                }

                .compound-table-panel .table-filter-container {
                    background: #f8f9fa;
                    padding: 10px;
                    border-radius: 5px;
                    margin-bottom: 10px;
                }

                .compound-table-panel .input-group-text {
                    background: #e9ecef;
                    border-color: #ced4da;
                }

                .compound-table-panel .compound-selection-hint {
                    background: #e7f3ff;
                    padding: 8px 12px;
                    border-radius: 4px;
                    margin-bottom: 10px;
                    font-size: 0.9em;
                    color: #0056b3;
                }
            `;
            document.head.appendChild(styles);
        }
    }

    setupCompoundTableEventHandlers() {
        const tableBody = $("#compound_table tbody");
        if (!tableBody.length) return;

        // Remove existing event handlers to prevent duplicates
        tableBody.off("click", "tr");

        // Add click handler for compound rows
        tableBody.on("click", "tr", (e) => {
            // Don't trigger if clicking on a link
            if ($(e.target).is('a') || $(e.target).closest('a').length) {
                return;
            }

            e.preventDefault();
            e.stopPropagation();

            const row = $(e.currentTarget);
            const compoundId = row.data("compound-id");
            const nodeId = row.data("node-id");
            const rowIndex = row.data("row-index");

            // Selection handling
            if (e.ctrlKey || e.metaKey) {
                this.toggleRowSelection(row[0], { compound: compoundId });
            } else {
                this.clearTableSelection();
                row.addClass('table-selected');
                this.selectedRows.add(parseInt(rowIndex));
            }

            // Network highlighting
            if (nodeId && window.cy) {
                this.highlightNodeInNetwork(nodeId);
            }

            console.log(`Compound clicked: ${compoundId}`);
        });
    }

    async performTableUpdate() {
        if (this.isUpdating) {
            console.log('Compound table update already in progress, skipping');
            return;
        }

        if (!window.cy) {
            console.warn("Cytoscape not available for compound table update");
            return;
        }

        this.isUpdating = true;

        try {
            const response = await fetch('/populate_compound_table', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ cy_elements: window.cy.elements().jsons() })
            });

            const responseData = await response.json();
            
            // Handle the case where response is an array [data, status_code]
            const data = Array.isArray(responseData) ? responseData[0] : responseData;
            console.log("Received compound table data:", data);

            if (data.compound_data && data.compound_data.length > 0) {
                this.updateTable(data.compound_data);
                console.log(`Compound table updated with ${data.compound_data.length} compounds from network.`);
            } else {
                this.currentData = [];
                this.filteredData = [];
                this.showEmptyTable();
            }
        } catch (error) {
            console.error("Error updating compound table:", error);
            this.showErrorTable();
        } finally {
            this.isUpdating = false;
        }
    }

    showEmptyTable() {
        const tableBody = $("#compound_table tbody");
        const table = document.querySelector('#compound_table');
        
        if (!tableBody.length) return;

        tableBody.empty();
        tableBody.append(`
            <tr id="default-compound-row">
                <td style="text-align: center; padding: 20px;">
                    <div style="color: #6c757d; font-style: italic; margin-bottom: 15px;">
                        No compounds in network. You can query the AOP-Wiki RDF for compounds associated with Key Events or draw your own PubChem nodes.
                    </div>
                    <button id="get-compounds-table-btn" class="btn btn-primary btn-sm">
                        <i class="fas fa-flask"></i> Get compounds
                    </button>
                </td>
            </tr>
        `);

        // Clear tfoot when showing empty table
        const tfoot = table?.querySelector('tfoot');
        if (tfoot) tfoot.remove();

        // Clear filter when showing empty table
        const filterInput = document.getElementById(`${this.tableId}-filter`);
        if (filterInput) {
            filterInput.value = '';
            this.filterText = '';
        }

        // Add click handler for the table button
        $("#get-compounds-table-btn").off("click").on("click", function (e) {
            e.preventDefault();
            e.stopPropagation();
            if (window.toggleCompounds) {
                window.toggleCompounds();
            }
        });
    }

    showErrorTable() {
        const tableBody = $("#compound_table tbody");
        if (!tableBody.length) return;

        tableBody.empty();
        tableBody.append(`
            <tr>
                <td style="text-align: center; padding: 20px; color: #dc3545;">
                    <i class="fas fa-exclamation-triangle"></i> Error loading compound data
                </td>
            </tr>
        `);
    }
}

// Initialize the managers with proper delay to ensure DOM is ready
console.log('Initializing Data Table Managers...');
window.aopTableManager = new AOPTableManager();

// Initialize Gene Table Manager with delay to ensure DOM is ready
setTimeout(() => {
    if (!window.geneTableManager) {
        window.geneTableManager = new GeneTableManager();
        console.log('Gene Table Manager initialized with filtering');
    }
}, 100);

// Initialize Compound Table Manager with delay to ensure DOM is ready
setTimeout(() => {
    if (!window.compoundTableManager) {
        window.compoundTableManager = new CompoundTableManager();
        console.log('Compound Table Manager initialized with filtering');
    }
}, 100);

// Global functions
window.initializeAopTable = function () {
    console.log('Initializing AOP table functionality');

    if (window.cy) {
        window.aopTableManager.setupNetworkListeners();
        window.aopTableManager.performTableUpdate();
    } else {
        const checkCytoscape = setInterval(() => {
            if (window.cy) {
                clearInterval(checkCytoscape);
                window.aopTableManager.setupNetworkListeners();
                window.aopTableManager.performTableUpdate();
            }
        }, 500);

        setTimeout(() => {
            clearInterval(checkCytoscape);
        }, 10000);
    }
};

window.populateAopTable = function(immediate = false) {
    if (!window.aopTableManager) {
        console.warn("AOP Table Manager not initialized");
        return Promise.resolve();
    }

    if (immediate) {
        return window.aopTableManager.performTableUpdate();
    } else {
        // Ensure debouncedUpdateTable exists before calling
        if (typeof window.aopTableManager.debouncedUpdateTable === 'function') {
            window.aopTableManager.debouncedUpdateTable();
        } else {
            console.warn("debouncedUpdateTable method not found, falling back to immediate update");
            return window.aopTableManager.performTableUpdate();
        }
        return Promise.resolve();
    }
};

window.populateGeneTable = function () {
    if (window.geneTableManager) {
        return window.geneTableManager.performTableUpdate();
    }
    return Promise.resolve();
};

window.populateCompoundTable = function () {
    if (window.compoundTableManager) {
        return window.compoundTableManager.performTableUpdate();
    }
    return Promise.resolve();
};

// Legacy compatibility functions
window.updateGeneTable = window.populateGeneTable;
window.updateCompoundTableFromNetwork = window.populateCompoundTable;

$(document).ready(function() {
    if (!window.aopTableManager) {
        window.aopTableManager = new AOPTableManager();
    }
    
    window.initializeAopTable();

    // Initialize other table managers after a short delay to ensure DOM is ready
    setTimeout(() => {
        if (!window.geneTableManager) {
            window.geneTableManager = new GeneTableManager();
        }
        if (!window.compoundTableManager) {
            window.compoundTableManager = new CompoundTableManager();
        }
    }, 200);
});
