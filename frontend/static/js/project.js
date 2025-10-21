        // Extract position and style data from original elements
        const elements = cy.elements().jsons();
        const styles = cy.style().json(); // Get actual styles
        
        const requestData = {
            elements: elements,
            styles: styles, // Send styles directly, not wrapped
            name: networkName,
            description: `AOP Network exported from ${new Date().toLocaleDateString()}`
        };