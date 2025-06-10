document.addEventListener('DOMContentLoaded', function() {
    const dropdown = document.getElementById('data-type-dropdown');
    if (dropdown) {
        // Add QAOP option to dropdown
        dropdown.innerHTML = `
            <option value="">Select data source...</option>
            <option value="qsprpred_opt">QSPR Predictions</option>
            <option value="bdf_opt">Biodatafuse</option>
            <option value="custom_table_opt">Custom Tables</option>
            <option value="qaop_div">QAOP Table</option>
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
        document.getElementById('qsprpred').style.display = 'block';
        return;
    } else if (selectedValue === 'bdf_opt') {
        document.getElementById('bdf_div').style.display = 'block';
        return;
    } else if (selectedValue === 'custom_table_opt') {
        document.getElementById('custom_table_div').style.display = 'block';
        return;
    } else if (selectedValue === 'qaop_div') {
        document.getElementById('qaop_div').style.display = 'block';
        if (window.populateQaopTable) {
            window.populateQaopTable();
        }
        return;
    }
}
