class CustomTableManager {
    constructor() {
        this.uploadedTables = new Map();
        this.setupEventHandlers();
    }

    setupEventHandlers() {
        // File upload
        $("#upload-table-file").on("change", (e) => {
            this.handleFileUpload(e.target.files[0]);
        });

        // Map table button
        $("#map-table-btn").on("click", () => {
            this.showMappingDialog();
        });

        // Apply mapping button
        $("#apply-mapping-btn").on("click", () => {
            this.applyTableMapping();
        });
    }

    async handleFileUpload(file) {
        if (!file) return;

        const formData = new FormData();
        formData.append('file', file);

        try {
            $("#table-upload-status").html('<i class="fas fa-spinner fa-spin"></i> Uploading...');
            
            const response = await fetch('/upload_custom_table', {
                method: 'POST',
                body: formData
            });

            const result = await response.json();
            
            if (response.ok) {
                this.uploadedTables.set(result.table_id, {
                    id: result.table_id,
                    name: result.message,
                    columns: result.columns,
                    rowCount: result.row_count,
                    preview: result.preview
                });
                
                this.updateTablesList();
                this.showTablePreview(result.table_id);
                $("#table-upload-status").html('<i class="fas fa-check text-success"></i> Upload successful!');
            } else {
                throw new Error(result.error);
            }
        } catch (error) {
            console.error("Upload error:", error);
            $("#table-upload-status").html(`<i class="fas fa-exclamation-triangle text-danger"></i> ${error.message}`);
        }
    }

    updateTablesList() {
        const tableSelect = $("#uploaded-tables-select");
        tableSelect.empty().append('<option value="">Select a table...</option>');
        
        this.uploadedTables.forEach((table, id) => {
            tableSelect.append(`<option value="${id}">${table.name} (${table.rowCount} rows)</option>`);
        });
    }

    showTablePreview(tableId) {
        const table = this.uploadedTables.get(tableId);
        if (!table) return;

        const preview = $("#table-preview");
        let html = `
            <h4>Table Preview: ${table.name}</h4>
            <p>${table.rowCount} rows, ${table.columns.length} columns</p>
            <div class="table-wrapper">
                <table class="table table-sm">
                    <thead>
                        <tr>
                            ${table.columns.map(col => `<th>${col.name}</th>`).join('')}
                        </tr>
                    </thead>
                    <tbody>
        `;
        
        table.preview.forEach(row => {
            html += '<tr>';
            table.columns.forEach(col => {
                html += `<td>${row[col.name] || ''}</td>`;
            });
            html += '</tr>';
        });
        
        html += `
                    </tbody>
                </table>
            </div>
        `;
        
        preview.html(html);
        $("#map-table-btn").prop('disabled', false);
    }

    showMappingDialog() {
        const selectedTableId = $("#uploaded-tables-select").val();
        if (!selectedTableId) return;

        const table = this.uploadedTables.get(selectedTableId);
        this.currentMappingTable = table;
        
        // Populate column selectors
        this.populateColumnSelectors(table.columns);
        
        // Show mapping modal
        $("#table-mapping-modal").modal('show');
    }

    populateColumnSelectors(columns) {
        const selectors = [
            "#node-id-column", "#node-label-column", "#edge-source-column", 
            "#edge-target-column", "#edge-label-column"
        ];
        
        selectors.forEach(selector => {
            const $select = $(selector);
            $select.empty().append('<option value="">Select column...</option>');
            columns.forEach(col => {
                $select.append(`<option value="${col.name}">${col.name}</option>`);
            });
        });

        // Property columns (multi-select)
        const propertySelect = $("#property-columns");
        propertySelect.empty();
        columns.forEach(col => {
            propertySelect.append(`
                <div class="form-check">
                    <input class="form-check-input" type="checkbox" value="${col.name}" id="prop-${col.name}">
                    <label class="form-check-label" for="prop-${col.name}">${col.name}</label>
                </div>
            `);
        });
    }

    async applyTableMapping() {
        const mappingConfig = this.buildMappingConfig();
        
        try {
            const response = await fetch('/map_table_to_network', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    table_id: this.currentMappingTable.id,
                    mapping_config: mappingConfig
                })
            });

            const result = await response.json();
            
            if (response.ok) {
                // Update network with new elements
                if (result.network_elements && window.cy) {
                    window.cy.elements().remove();
                    window.cy.add(result.network_elements);
                    positionNodes(window.cy);
                }
                
                $("#table-mapping-modal").modal('hide');
                
                if (window.networkState) {
                    window.networkState.showNotification(
                        `Table mapped: ${result.results.nodes_created} nodes, ${result.results.edges_created} edges created`,
                        "success"
                    );
                }
            } else {
                throw new Error(result.error);
            }
        } catch (error) {
            console.error("Mapping error:", error);
            if (window.networkState) {
                window.networkState.showNotification(`Mapping failed: ${error.message}`, "error");
            }
        }
    }

    buildMappingConfig() {
        const config = {};
        
        // Node creation config
        if ($("#create-nodes-checkbox").is(':checked')) {
            config.create_nodes = {
                node_type: $("#node-type-select").val(),
                id_column: $("#node-id-column").val(),
                label_column: $("#node-label-column").val(),
                property_columns: this.getSelectedPropertyColumns()
            };
        }
        
        // Edge creation config
        if ($("#create-edges-checkbox").is(':checked')) {
            config.create_edges = {
                edge_type: $("#edge-type-select").val(),
                source_column: $("#edge-source-column").val(),
                target_column: $("#edge-target-column").val(),
                label_column: $("#edge-label-column").val(),
                property_columns: this.getSelectedPropertyColumns()
            };
        }
        
        return config;
    }

    getSelectedPropertyColumns() {
        return $("#property-columns input:checked").map(function() {
            return this.value;
        }).get();
    }
}

// Initialize custom table manager
let customTableManager;

document.addEventListener("DOMContentLoaded", function() {
    customTableManager = new CustomTableManager();
});

// Make available globally
window.customTableManager = customTableManager;
