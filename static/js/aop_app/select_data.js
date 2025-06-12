document.addEventListener('DOMContentLoaded', function() {
    const dropdown = document.getElementById('data-type-dropdown');
    if (dropdown) {
        // Remove AOP table from dropdown since it's now always visible
        dropdown.innerHTML = `
            <option value="">Select data source...</option>
            <option value="qsprpred_opt">QSPR Predictions</option>
            <option value="custom_table_opt">Custom Tables</option>
        `;
        
        dropdown.addEventListener('change', handleDataTypeChange);
        handleDataTypeChange(); // Initialize on load
    }
});

function handleDataTypeChange() {
    var dropdown = document.getElementById('data-type-dropdown');
    if (!dropdown) return;
    
    var selectedValue = dropdown.value;
    var dataSections = document.getElementsByClassName('data-section');
    
    // Hide all sections first
    for (var i = 0; i < dataSections.length; i++) {
        dataSections[i].style.display = 'none';
    }
    
    // Show the selected section
    if (selectedValue === 'qsprpred_opt') {
        const qsprElement = document.getElementById('qsprpred');
        if (qsprElement) {
            qsprElement.style.display = 'block';
        }
        return;
    } else if (selectedValue === 'custom_table_opt') {
        const customElement = document.getElementById('custom_table_div');
        if (customElement) {
            customElement.style.display = 'block';
        }
        return;
    }
}
