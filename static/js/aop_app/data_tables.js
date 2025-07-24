/**
 * Enhanced AOP Table functionality with filtering and network integration
 * Merged functionality from table_aop.js and aop_table_enhancements.js
 */

class AOPTableManager {
    constructor() {
        this.currentData = [];
        this.filteredData = [];
        this.filterText = '';
        this.selectedAop = null; // Track currently selected AOP (single selection with layout)
        this.groupedAops = new Set(); // Track grouped AOPs (multiple selection without layout change)
        this.isUpdating = false; // Prevent concurrent updates
        this.updateTimeout = null; // For debouncing
        this.selectedRows = new Set(); // Track selected table rows
        this.init();
    }

    init() {
        this.setupFilterInput();
        this.setupTableStyles();
        this.setupNetworkListeners();
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
            if (isSelected) className += ' selected-aop';
            if (isGrouped) className += ' grouped-aop';
            
            return `<span class="${className}" data-aop-id="${aopId}" title="Click to filter network by this AOP (Ctrl+Click to group)">${this.highlightMatch(aopId)}</span>`;
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
            const isGrouped = this.groupedAops.has(correspondingAopId);
            let className = 'aop-title-link';
            if (isSelected) className += ' selected-aop';
            if (isGrouped) className += ' grouped-aop';
            
            return `<span class="${className}" data-aop-id="${correspondingAopId}" title="Click to filter network by this AOP (Ctrl+Click to group): ${correspondingAopId}">${this.highlightMatch(title)}</span>`;
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
                
                if (e.ctrlKey || e.metaKey) {
                    // Ctrl+Click for grouping (multiple selection without layout change)
                    this.toggleAopGroup(aopId);
                } else {
                    // Normal click for filtering (single selection with layout change)
                    this.toggleAopFilter(aopId);
                }
            });
        });
        
        // Add row selection handlers
        this.setupRowSelection(table);
    }

    setupRowSelection(table) {
        // Remove existing row selection handlers
        table.removeEventListener('click', this.handleRowClick);
        
        // Add row click handler for selection
        this.handleRowClick = (e) => {
            const row = e.target.closest('tr');
            if (!row || !row.dataset.rowIndex) return;
            
            // Don't trigger selection if clicking on links or specific elements
            if (e.target.closest('.aop-link, .aop-title-link, [data-node-id]')) return;
            
            const rowIndex = parseInt(row.dataset.rowIndex);
            const rowData = this.filteredData[rowIndex];
            if (!rowData) return;
            
            e.preventDefault();
            
            if (e.ctrlKey || e.metaKey) {
                // Ctrl+Click: toggle row selection
                this.toggleRowSelection(row, rowData);
            } else if (e.shiftKey && this.selectedRows.size > 0) {
                // Shift+Click: select range
                this.selectRowRange(row, rowData);
            } else {
                // Regular click: select only this row
                this.selectSingleRow(row, rowData);
            }
            
            // Synchronize with network selection
            this.syncTableToNetwork();
        };
        
        table.addEventListener('click', this.handleRowClick);
        
        // Listen for network selection changes to sync back to table
        if (window.cy) {
            window.cy.removeListener('select unselect', this.handleNetworkSelection);
            this.handleNetworkSelection = () => {
                // Small delay to avoid conflicts with table selection
                setTimeout(() => {
                    this.syncNetworkToTable();
                }, 50);
            };
            window.cy.on('select unselect', this.handleNetworkSelection);
        }
    }

    toggleAopGroup(aopId) {
        console.log('Toggling AOP group for:', aopId);
        
        if (this.groupedAops.has(aopId)) {
            this.groupedAops.delete(aopId);
        } else {
            this.groupedAops.add(aopId);
        }
        
        // Clear single selection when grouping
        if (this.selectedAop) {
            this.selectedAop = null;
        }
        
        this.applyGroupHighlighting();
        this.renderTable();
    }

    toggleAopFilter(aopId) {
        console.log('Toggling AOP filter for:', aopId);
        
        // Clear grouped selections when doing single filter
        this.groupedAops.clear();
        
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

    clearAllAopSelections() {
        console.log('Clearing all AOP selections');
        this.selectedAop = null;
        this.groupedAops.clear();
        this.showAllNetworkNodes();
        this.renderTable();
    }

    // New method for "Group by AOP" button - highlights all AOPs without layout change
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
            this.showAllNetworkNodes();
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

    relayoutVisibleNodes(visibleNodeIds) {
        if (!window.cy || visibleNodeIds.size === 0) return;

        // Use the global resetNetworkLayout function for consistency
        if (window.resetNetworkLayout) {
            setTimeout(() => {
                window.resetNetworkLayout();
            }, 100);
        }
    }

    relayoutAllNodes() {
        if (!window.cy) return;
        
        // Use the global resetNetworkLayout function
        if (window.resetNetworkLayout) {
            setTimeout(() => {
                window.resetNetworkLayout();
            }, 100);
        }
    }

    applyGroupHighlighting() {
        if (!window.cy || this.groupedAops.size === 0) {
            this.showAllNetworkNodes();
            return;
        }
        
        console.log('Applying group highlighting for AOPs:', Array.from(this.groupedAops));
        
        // Save original styles before modifying them
        this.saveOriginalStyles();
        
        // Create color palette for different AOPs
        const colors = [
            '#ff6b35', '#4CAF50', '#2196F3', '#9C27B0', '#FF9800', 
            '#795548', '#607D8B', '#E91E63', '#00BCD4', '#8BC34A'
        ];
        
        const aopColorMap = new Map();
        Array.from(this.groupedAops).forEach((aopId, index) => {
            aopColorMap.set(aopId, colors[index % colors.length]);
        });
        
        // Find all nodes belonging to grouped AOPs
        const nodeColorMap = new Map();
        
        window.cy.nodes().forEach(node => {
            const nodeData = node.data();
            const nodeAops = nodeData.aop || [];
            const aopsToCheck = Array.isArray(nodeAops) ? nodeAops : [nodeAop]; // Fixed variable name
            
            // Check if node belongs to any grouped AOP
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
                    nodeColorMap.set(node.id(), aopColorMap.get(nodeAopId));
                    break; // Use first matching AOP color
                }
            }
        });
        
        console.log(`Found ${nodeColorMap.size} nodes for grouped AOPs`);
        
        // Apply visual highlighting without layout change
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
                         .style('opacity', 0.3)
                         .style('border-width', '2px')
                         .style('border-color', '#ccc');
                }
            });
            
            // Handle edges - highlight edges between grouped nodes
            window.cy.edges().forEach(edge => {
                const sourceColor = nodeColorMap.get(edge.source().id());
                const targetColor = nodeColorMap.get(edge.target().id());
                
                if (sourceColor && targetColor) {
                    // Use source node color for edge
                    edge.style('opacity', 1)
                        .style('line-color', sourceColor)
                        .style('target-arrow-color', sourceColor)
                        .style('width', '3px');
                } else {
                    edge.style('opacity', 0.2)
                        .style('line-color', '#ccc')
                        .style('target-arrow-color', '#ccc')
                        .style('width', '1px');
                }
            });
        });
        
        // Show status message
        this.showFilterStatus(`Grouped ${this.groupedAops.size} AOPs with ${nodeColorMap.size} nodes`, 'info');
    }

    filterByAop(aopId) {
        if (!window.cy || !aopId) return;
        
        console.log('Filtering network by AOP:', aopId);
        
        // Find all nodes that belong to this AOP
        const aopNodes = new Set();
        
        // Save original styles before modifying them
        this.saveOriginalStyles();
        
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

    // Update legacy table format with smooth transitions (from table_aop.js)
    updateLegacyTable(aopData, tableBody) {
        if (!tableBody || tableBody.length === 0) return;
        
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
            console.log(`Populated legacy AOP table with ${aopData.length} relationships`);
        });
    }

    // Show empty table state with smooth transition (from table_aop.js)
    showEmptyAopTable() {
        const tableBody = $("#aop_table tbody");
        if (tableBody.length > 0) {
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
        
        // Also clear enhanced table
        this.currentData = [];
        this.filteredData = [];
        this.renderTable();
    }

    // Setup network listeners with debounced smooth updates (from table_aop.js)
    setupNetworkListeners() {
        if (!window.cy) {
            console.log('Cytoscape not ready, will setup AOP table listeners later');
            return;
        }
        
        console.log('Setting up AOP table network listeners');
        
        // Listen for network changes with smooth transitions
        window.cy.on('add remove', (event) => {
            console.log('Network changed, updating AOP table with smooth transition');
            // Debounce rapid changes and add smooth transition
            clearTimeout(window.aopTableUpdateTimeout);
            window.aopTableUpdateTimeout = setTimeout(() => {
                // Add a subtle loading indicator during updates
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

    // Enhanced debouncedUpdateTable with legacy support
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

        const tableBody = $("#aop_table tbody");
        const loadingDiv = $("#loading_aop_table");
        
        // Show loading indicator if elements exist
        if (loadingDiv.length > 0) {
            loadingDiv.show();
        }

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
            
            // Hide loading indicator
            if (loadingDiv.length > 0) {
                loadingDiv.hide();
            }
            
            if (data.error) {
                console.error("Error populating AOP table:", data.error);
                this.showEmptyAopTable();
                return;
            }
            
            console.log('Enhanced AOP table manager - Received AOP table data:', data.aop_data);
            
            if (data.aop_data && data.aop_data.length > 0) {
                // Update enhanced table
                this.updateTable(data.aop_data);
                
                // Also update legacy table if it exists
                this.updateLegacyTable(data.aop_data, tableBody);
                
                console.log(`Enhanced AOP table updated with ${data.aop_data.length} entries`);
            } else {
                this.showEmptyAopTable();
            }
            
        } catch (error) {
            console.error("Error updating AOP table:", error);
            if (loadingDiv.length > 0) {
                loadingDiv.hide();
            }
            this.showEmptyAopTable();
        } finally {
            this.isUpdating = false;
        }
    }

    // New method to save original element styles before applying filters
    saveOriginalStyles() {
        if (!window.cy) return;
        
        // Save original node styles
        window.cy.nodes().forEach(node => {
            const currentStyle = node.style();
            if (!node.data('original-border-color')) {
                node.data('original-border-color', currentStyle['border-color'] || '#666');
            }
            if (!node.data('original-border-width')) {
                node.data('original-border-width', currentStyle['border-width'] || '2px');
            }
            if (!node.data('original-opacity')) {
                node.data('original-opacity', currentStyle['opacity'] || 1);
            }
        });
        
        // Save original edge styles
        window.cy.edges().forEach(edge => {
            const currentStyle = edge.style();
            if (!edge.data('original-line-color')) {
                edge.data('original-line-color', currentStyle['line-color'] || '#666');
            }
            if (!edge.data('original-target-arrow-color')) {
                edge.data('original-target-arrow-color', currentStyle['target-arrow-color'] || '#666');
            }
            if (!edge.data('original-width')) {
                edge.data('original-width', currentStyle['width'] || '2px');
            }
            if (!edge.data('original-opacity')) {
                edge.data('original-opacity', currentStyle['opacity'] || 1);
            }
        });
    }

    showAllNetworkNodes() {
        if (!window.cy) return;

        console.log('Showing all network nodes');

        window.cy.batch(() => {
            // Reset all nodes to their original styles
            window.cy.nodes().forEach(node => {
                node.removeClass('filtered-out aop-filtered aop-highlighted aop-grouped')
                    .style('opacity', node.data('original-opacity') || 1)
                    .style('border-width', node.data('original-border-width') || '2px')
                    .style('border-color', node.data('original-border-color') || '#666');
            });
            
            // Reset all edges to their original styles
            window.cy.edges().forEach(edge => {
                edge.removeClass('filtered-out')
                    .style('opacity', edge.data('original-opacity') || 1)
                    .style('line-color', edge.data('original-line-color') || '#666')
                    .style('target-arrow-color', edge.data('original-target-arrow-color') || '#666')
                    .style('width', edge.data('original-width') || '2px');
            });
        });

        // Use the global resetNetworkLayout function
        if (window.resetNetworkLayout) {
            setTimeout(() => {
                window.resetNetworkLayout();
            }, 100);
        }
        
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

    renderTable() {
        const tableContainer = document.querySelector('#aop-table-container, .aop-table-container');
        if (!tableContainer) return;

        let table = tableContainer.querySelector('.aop-table');
        if (!table) {
            table = document.createElement('table');
            table.className = 'table table-striped table-hover aop-table';
            
            // Add instructions before the table
            const instructions = document.createElement('div');
            instructions.className = 'aop-table-instructions';
            instructions.innerHTML = `
                <strong>Selection:</strong> Click rows to select • Ctrl+Click for multi-select • Shift+Click for range select
            `;
            
            tableContainer.appendChild(instructions);
            tableContainer.appendChild(table);
        }

        const html = this.generateTableHTML();
        table.innerHTML = html;

        // Add click handlers for node highlighting and row selection
        this.addNodeClickHandlers(table);
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
                
                .aop-table tbody tr {
                    cursor: pointer;
                    transition: background-color 0.2s ease;
                }
                
                .aop-table tbody tr:hover {
                    background-color: #f8f9fa;
                }
                
                .aop-table-selected {
                    background-color: #e3f2fd !important;
                    border-left: 4px solid #2196f3 !important;
                }
                
                .aop-table-selected:hover {
                    background-color: #e1f5fe !important;
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
                
                .disconnected-row {
                    background-color: #fff3cd;
                    border-left: 4px solid #ffc107;
                }
                
                .disconnected-row.aop-table-selected {
                    background-color: #e3f2fd !important;
                    border-left: 4px solid #2196f3 !important;
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
                    display: inline-block;
                    margin: 1px;
                }
                
                .aop-link:hover, .aop-title-link:hover {
                    background-color: #e7f3ff;
                    text-decoration: underline;
                }
                
                .aop-link.selected-aop, .aop-title-link.selected-aop {
                    background-color: #ff6b35;
                    color: white;
                    font-weight: bold;
                    box-shadow: 0 2px 4px rgba(255, 107, 53, 0.3);
                }
                
                .aop-link.grouped-aop, .aop-title-link.grouped-aop {
                    background-color: #4CAF50;
                    color: white;
                    font-weight: bold;
                    box-shadow: 0 2px 4px rgba(76, 175, 80, 0.3);
                }
                
                .aop-link.selected-aop.grouped-aop, .aop-title-link.selected-aop.grouped-aop {
                    background: linear-gradient(45deg, #ff6b35, #4CAF50);
                }
                
                .aop-highlighted {
                    border-color: #ff6b35 !important;
                    border-width: 4px !important;
                    box-shadow: 0 0 10px rgba(255, 107, 53, 0.5);
                }
                
                .aop-grouped {
                    border-width: 4px !important;
                    box-shadow: 0 0 8px rgba(0, 0, 0, 0.3);
                }
                
                /* Selection instructions */
                .aop-table-instructions {
                    font-size: 0.8rem;
                    color: #6c757d;
                    margin-bottom: 10px;
                    padding: 8px;
                    background-color: #f8f9fa;
                    border-radius: 4px;
                    border-left: 3px solid #007bff;
                }
            `;
            document.head.appendChild(styles);
        }
    }

    filterNetworkNodes() {
        if (!window.cy) return;

        // Save original styles before filtering
        this.saveOriginalStyles();

        // Get visible node IDs from filtered data
        const visibleNodeIds = new Set();
        this.filteredData.forEach(row => {
            if (row.source_id !== 'N/A') visibleNodeIds.add(row.source_id);
            if (row.target_id !== 'N/A') visibleNodeIds.add(row.target_id);
        });

        // Animate network filtering
        window.cy.batch(() => {
            window.cy.nodes().forEach(node => {
                if (visibleNodeIds.has(node.id())) {
                    node.removeClass('filtered-out').style('opacity', 1);
                } else {
                    node.addClass('filtered-out').style('opacity', 0.1);
                }
            });
            
            // Also handle edges
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

        // Re-layout visible nodes with animation
        this.relayoutVisibleNodes(visibleNodeIds);
    }

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

    updateTable(aopData) {
        this.currentData = aopData;
        this.filteredData = [...aopData];
        this.renderTable();
    }

    toggleRowSelection(row, rowData) {
        const rowIndex = parseInt(row.dataset.rowIndex);
        
        if (this.selectedRows.has(rowIndex)) {
            this.selectedRows.delete(rowIndex);
            row.classList.remove('aop-table-selected');
        } else {
            this.selectedRows.add(rowIndex);
            row.classList.add('aop-table-selected');
        }
        
        console.log(`Toggled row selection. Selected rows: ${this.selectedRows.size}`);
    }

    selectSingleRow(row, rowData) {
        // Clear all previous selections
        this.clearTableSelection();
        
        // Select this row
        const rowIndex = parseInt(row.dataset.rowIndex);
        this.selectedRows.add(rowIndex);
        row.classList.add('aop-table-selected');
        
        console.log(`Selected single row: ${rowData.source_label} -> ${rowData.target_label}`);
    }

    selectRowRange(row, rowData) {
        const currentRowIndex = parseInt(row.dataset.rowIndex);
        const selectedIndices = Array.from(this.selectedRows);
        
        if (selectedIndices.length === 0) {
            this.selectSingleRow(row, rowData);
            return;
        }
        
        // Find the range between last selected and current
        const lastSelected = Math.max(...selectedIndices);
        const start = Math.min(lastSelected, currentRowIndex);
        const end = Math.max(lastSelected, currentRowIndex);
        
        // Select all rows in range
        for (let i = start; i <= end; i++) {
            this.selectedRows.add(i);
            const tableRow = document.querySelector(`tr[data-row-index="${i}"]`);
            if (tableRow) {
                tableRow.classList.add('aop-table-selected');
            }
        }
        
        console.log(`Selected row range ${start}-${end}. Total selected: ${this.selectedRows.size}`);
    }

    clearTableSelection() {
        // Clear visual selection
        document.querySelectorAll('.aop-table-selected').forEach(row => {
            row.classList.remove('aop-table-selected');
        });
        
        // Clear internal tracking
        this.selectedRows.clear();
    }

    syncTableToNetwork() {
        if (!window.cy) return;
        
        // Get all network element IDs from selected rows
        const networkElementIds = new Set();
        
        this.selectedRows.forEach(rowIndex => {
            const rowData = this.filteredData[rowIndex];
            if (!rowData) return;
            
            // Add source and target node IDs
            if (rowData.source_id && rowData.source_id !== 'N/A') {
                networkElementIds.add(rowData.source_id);
            }
            if (rowData.target_id && rowData.target_id !== 'N/A') {
                networkElementIds.add(rowData.target_id);
            }
            
            // Try to find the corresponding edge if it exists
            const sourceNode = window.cy.getElementById(rowData.source_id);
            const targetNode = window.cy.getElementById(rowData.target_id);
            
            if (sourceNode.length && targetNode.length) {
                // Find edges between these nodes
                const edges = sourceNode.edgesWith(targetNode);
                edges.forEach(edge => {
                    networkElementIds.add(edge.id());
                });
            }
        });
        
        console.log(`Syncing table selection to network: ${networkElementIds.size} elements`);
        
        // Update network selection
        window.cy.batch(() => {
            // Clear current network selection
            window.cy.$(':selected').unselect();
            
            // Select corresponding network elements
            networkElementIds.forEach(elementId => {
                const element = window.cy.getElementById(elementId);
                if (element.length) {
                    element.select();
                }
            });
        });
        
        // Update selection info
        this.updateSelectionInfo();
    }

    syncNetworkToTable() {
        if (!window.cy || this.isUpdating) return;
        
        const selectedElements = window.cy.$(':selected');
        const selectedNodeIds = new Set();
        
        // Get all selected node IDs
        selectedElements.nodes().forEach(node => {
            selectedNodeIds.add(node.id());
        });
        
        // Get all edge node IDs
        selectedElements.edges().forEach(edge => {
            selectedNodeIds.add(edge.source().id());
            selectedNodeIds.add(edge.target().id());
        });
        
        if (selectedNodeIds.size === 0) {
            this.clearTableSelection();
            this.updateSelectionInfo();
            return;
        }
        
        // Find rows that contain any of the selected nodes
        const rowsToSelect = new Set();
        
        this.filteredData.forEach((rowData, index) => {
            const hasSelectedNode = 
                selectedNodeIds.has(rowData.source_id) || 
                selectedNodeIds.has(rowData.target_id);
            
            if (hasSelectedNode) {
                rowsToSelect.add(index);
            }
        });
        
        console.log(`Syncing network selection to table: ${rowsToSelect.size} rows`);
        
        // Update table selection
        this.clearTableSelection();
        rowsToSelect.forEach(rowIndex => {
            this.selectedRows.add(rowIndex);
            const tableRow = document.querySelector(`tr[data-row-index="${rowIndex}"]`);
            if (tableRow) {
                tableRow.classList.add('aop-table-selected');
            }
        });
        
        this.updateSelectionInfo();
    }

    updateSelectionInfo() {
        // Update the existing selection controls with table selection info
        const selectionInfo = document.getElementById('selection-info');
        const selectionControls = document.getElementById('selection-controls');
        
        if (selectionInfo && selectionControls) {
            const networkSelected = window.cy ? window.cy.$(':selected').length : 0;
            const tableSelected = this.selectedRows.size;
            
            if (networkSelected > 0 || tableSelected > 0) {
                selectionControls.style.display = 'flex';
                selectionControls.style.visibility = 'visible';
                
                if (tableSelected > 0) {
                    selectionInfo.textContent = `${networkSelected} network, ${tableSelected} table rows selected`;
                } else {
                    selectionInfo.textContent = `${networkSelected} selected`;
                }
            } else {
                selectionControls.style.display = 'none';
            }
        }
        
        // Trigger the main selection controls update
        if (window.updateSelectionControls) {
            window.updateSelectionControls();
        }
    }
}

// Initialize the AOP Table Manager immediately
console.log('Initializing Enhanced AOP Table Manager...');
window.aopTableManager = new AOPTableManager();

// Enhanced global functions that work with both table systems
window.populateAopTable = function(immediate = false) {
    if (!window.aopTableManager) {
        console.warn("AOP Table Manager not initialized");
        return Promise.resolve();
    }

    if (immediate) {
        // For immediate updates (like manual triggers)
        return window.aopTableManager.performTableUpdate();
    } else {
        // For network change events, use debounced version
        window.aopTableManager.debouncedUpdateTable();
        return Promise.resolve();
    }
};

// Legacy function support (from table_aop.js)
window.initializeAopTable = function() {
    console.log('Initializing AOP table functionality (legacy support)');
    
    // Set up listeners if Cytoscape is ready
    if (window.cy) {
        window.aopTableManager.setupNetworkListeners();
        window.aopTableManager.performTableUpdate(); // Initial population
    } else {
        // Wait for Cytoscape to be ready
        const checkCytoscape = setInterval(() => {
            if (window.cy) {
                clearInterval(checkCytoscape);
                window.aopTableManager.setupNetworkListeners();
                window.aopTableManager.performTableUpdate();
            }
        }, 500);
        
        // Clear interval after 10 seconds to avoid infinite checking
        setTimeout(() => {
            clearInterval(checkCytoscape);
        }, 10000);
    }
};

window.setupAopTableListeners = function() {
    if (window.aopTableManager) {
        window.aopTableManager.setupNetworkListeners();
    }
};

// Handle CURIE link clicks (from table_aop.js)
$(document).on('click', '.curie-link', function(e) {
    e.preventDefault();
    const curie = $(this).data('curie');
    console.log('CURIE clicked:', curie);
    
    // Navigate to AOP Wiki or other actions
    if (curie && curie.includes('aop.relationships:')) {
        const kerId = curie.split(':')[1];
        const aopWikiUrl = `https://aopwiki.org/relationships/${kerId}`;
        window.open(aopWikiUrl, '_blank');
    }
});

// Initialize when DOM is ready (legacy support)
$(document).ready(function() {
    // Ensure enhanced table manager is available
    if (!window.aopTableManager) {
        window.aopTableManager = new AOPTableManager();
    }
    
    // Initialize with legacy support
    window.initializeAopTable();
});
