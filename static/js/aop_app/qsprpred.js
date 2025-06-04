// Load the model to protein name mapping
$.ajax({
    url: "/static/data/caseMieModel.csv",
    dataType: "text",
    success: data => {
        Papa.parse(data, {
            header: true,
            skipEmptyLines: true,
            complete: results => {
                window.modelToProteinInfo = {};
                results.data.forEach(row => {
                    const model = row["qsprpred_model"];
                    const proteinName = row["protein name uniprot"];
                    const uniprotId = row["uniprot ID inferred from qspred name"];
                    window.modelToProteinInfo[model] = { proteinName, uniprotId };
                });
            }
        });
    }
});

$(document).ready(() => {
    $("#fetch_predictions").on("click", () => {
        fetchAndDisplayPredictions();
    });
});

async function fetchAndDisplayPredictions() {
    if (!window.cy) {
        console.error("Cytoscape instance not available");
        alert("Network not initialized. Please wait and try again.");
        return;
    }

    if (!window.genesVisible) {
        await window.toggleGenes();
    }
    
    try {
        // Use the dashboard container with the correct data attributes
        const container = document.querySelector(".dashboard-container");
        const mieQuery = container ? container.dataset.mies : null;
        
        if (!mieQuery) {
            alert("Error: No MIE data available.");
            return;
        }
        
        // Get model to MIE mapping
        const modelToMIEResponse = await $.ajax({
            url: "/get_case_mie_model",
            type: "GET",
            data: { mie_query: mieQuery }
        });
        
        // Get SMILES from compound table
        const smilesList = [];
        $("#compound_table tbody tr").each((_, tr) => {
            const img = $(tr).find("td img");
            const smiles = img.attr("alt") && img.attr("alt").trim();
            if (smiles) smilesList.push(smiles);
        });
        
        const models = Object.keys(modelToMIEResponse);
        if (!models.length) {
            alert("Error: No models available for prediction.");
            return;
        }
        
        const thresholdElement = document.getElementById("threshold_pchembl");
        const thresholdValue = parseFloat(thresholdElement ? thresholdElement.value : "6.5");
        
        // Get predictions
        const predictions = await $.ajax({
            url: "/get_predictions",
            type: "POST",
            contentType: "application/json",
            data: JSON.stringify({ 
                smiles: smilesList, 
                models, 
                metadata: {}, 
                threshold: thresholdValue 
            })
        });
        
        // Add predictions to network via backend
        const cyElements = window.cy.elements().jsons();
        const updatedElements = await $.ajax({
            url: "/add_qsprpred_compounds",
            type: "POST",
            contentType: "application/json",
            data: JSON.stringify({
                compound_mapping: window.compoundMapping,
                model_to_protein_info: window.modelToProteinInfo,
                model_to_mie: modelToMIEResponse,
                response: predictions,
                cy_elements: cyElements
            })
        });
        
        // Update Cytoscape with new elements
        if (updatedElements && Array.isArray(updatedElements)) {
            updatedElements.forEach(element => {
                try {
                    window.cy.add(element);
                } catch (error) {
                    console.warn("Skipping duplicate element");
                }
            });
        }
        
        // Update table
        populateQsprPredTable(predictions, modelToMIEResponse);
        
        window.compoundsVisible = true;
        $("#toggle_compounds").text("Hide Compounds");
        if (window.positionNodes && window.cy) {
            window.positionNodes(window.cy);
        }
        window.fetched_preds = true;
        
    } catch (error) {
        console.error("Error fetching predictions:", error);
        alert("Error fetching predictions.");
    }
}

function populateQsprPredTable(predictions, modelToMIE) {
    const table = $("#compound_table");
    const tableHead = table.find("thead").empty();
    const tableBody = table.find("tbody").empty();

    tableHead.append(`
        <tr>
            <th>Compound</th>
            <th>Target</th>
            <th>Predicted pChEMBL</th>
        </tr>
    `);

    if (Array.isArray(predictions)) {
        const grouped = predictions.reduce((acc, pred) => {
            const s = pred.smiles;
            (acc[s] = acc[s] || []).push(pred);
            return acc;
        }, {});

        Object.entries(grouped).forEach(([smiles, predictionList]) => {
            const compound = window.compoundMapping[smiles];
            const compoundName = compound ? compound.term : smiles;
            const compoundCell = compound ? 
                `<a href="${compound.url}" class="compound-link">${compound.term}</a>` : 
                smiles;
            
            const targetCells = [];
            const pChEMBLCells = [];

            predictionList.forEach(prediction => {
                Object.entries(prediction).forEach(([model, value]) => {
                    if (model !== "smiles" && parseFloat(value) >= 6.5) {
                        const proteinInfo = window.modelToProteinInfo[model] || 
                            { proteinName: "Unknown Protein", uniprotId: "" };
                        const proteinLink = proteinInfo.uniprotId ? 
                            `<a href="https://www.uniprot.org/uniprotkb/${proteinInfo.uniprotId}" target="_blank">${proteinInfo.proteinName}</a>` : 
                            proteinInfo.proteinName;
                        targetCells.push(`${proteinLink} (${model})`);
                        pChEMBLCells.push(value);
                    }
                });
            });

            if (targetCells.length > 0) {
                tableBody.append(`
                    <tr data-compound-name="${compoundName}" data-smiles="${smiles}">
                        <td>
                            <img src="https://cdkdepict.cloud.vhp4safety.nl/depict/bot/svg?w=-1&h=-1&abbr=off&hdisp=bridgehead&showtitle=false&zoom=.4&annotate=cip&r=0&smi=${encodeURIComponent(smiles)}" 
                                 alt="${smiles}" />
                            <br />
                            ${compoundCell}
                        </td>
                        <td>${targetCells.join('<br>')}</td>
                        <td>${pChEMBLCells.join('<br>')}</td>
                    </tr>
                `);
            }
        });
    }
}