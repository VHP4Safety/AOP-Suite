document.addEventListener('DOMContentLoaded', function() {
    const dropdown = document.getElementById('data-type-dropdown');
    if (dropdown) {
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
    
    // Show the selected section and trigger appropriate population
    if (selectedValue === 'qsprpred_opt') {
        document.getElementById('qsprpred').style.display = 'block';
        return;
    } else if (selectedValue === 'qaop_div') {
        document.getElementById('qaop_div').style.display = 'block';
        // Trigger QAOP table population
        if (window.populateQaopTable) {
            window.populateQaopTable();
        }
        return;
    } else if (selectedValue === 'bdf_opt') {
        document.getElementById('bdf_div').style.display = 'block';
        return;
    }
}
