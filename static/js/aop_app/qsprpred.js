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
                    if (model && proteinName && uniprotId) {
                        window.modelToProteinInfo[model] = { proteinName, uniprotId };
                    }
                });
                console.log("Loaded protein info:", window.modelToProteinInfo);
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
        window.genesVisible = true;
        await window.toggleGenes();
        positionNodes(window.cy);
    }
    
    try {
        const container = document.querySelector("#compound-container");
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
        
        // Get SMILES from compound table using the old approach
        const smilesList = [];
        $("#compound_table tbody tr").each((_, tr) => {
            const img = $(tr).find("td img");
            const smiles = img.attr("alt") && img.attr("alt").trim();
            if (smiles) smilesList.push(smiles);
        });
        
        if (smilesList.length === 0) {
            alert("No compounds found. Please ensure compound data is loaded.");
            return;
        }
        
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
        
        // Use the old populateQsprPredMies function
        populateQsprPredMies(window.cy, window.compoundMapping, window.modelToProteinInfo, modelToMIEResponse, predictions);
        if (window.fetched_preds === false) window.fetched_preds = true;
        
    } catch (error) {
        console.error("Error fetching predictions:", error);
        alert("Error fetching predictions.");
    }
}

function populateQsprPredMies(cy, compoundMapping, modelToProteinInfo, modelToMIE, response) {
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

    if (Array.isArray(response)) {
        const grouped = response.reduce((acc, pred) => {
            const s = pred.smiles;
            (acc[s] = acc[s] || []).push(pred);
            return acc;
        }, {});

        const cyElements = [];
        Object.entries(grouped).forEach(([smiles, predictions]) => {
            const compound = compoundMapping[smiles];
            const compoundCell = compound ? `<a href="${compound.url}">${compound.term}</a>` : smiles;
            const targetCells = [];
            const pChEMBLCells = [];

            predictions.forEach(prediction => {
                Object.entries(prediction).forEach(([model, value]) => {
                    if (model !== "smiles" && parseFloat(value) >= 6.5) {
                        const proteinInfo = modelToProteinInfo[model] || { proteinName: "Unknown Protein", uniprotId: "" };
                        const proteinLink = proteinInfo.uniprotId ? `<a href="https://www.uniprot.org/uniprotkb/${proteinInfo.uniprotId}" target="_blank">${proteinInfo.proteinName}</a>` : proteinInfo.proteinName;
                        targetCells.push(`${proteinLink} (${model})`);
                        pChEMBLCells.push(value);

                        const compoundId = compound ? compound.term : smiles;
                        const uniprotNodeId = `uniprot_${proteinInfo.uniprotId}`;
                        
                        // Add compound node if it doesn't exist
                        if (!cy.getElementById(compoundId).length) {
                            cyElements.push({
                                data: { 
                                    id: compoundId, 
                                    label: compoundId, 
                                    type: "chemical", 
                                    smiles: smiles 
                                }, 
                                classes: "chemical-node" 
                            });
                        }
                        
                        // Only add edge if the target UniProt node exists
                        if (cy.getElementById(uniprotNodeId).length > 0) {
                            const edgeId = `${compoundId}-${uniprotNodeId}-${model}`;
                            if (!cy.getElementById(edgeId).length) {
                                cyElements.push({
                                    data: { 
                                        id: edgeId,
                                        source: compoundId, 
                                        target: uniprotNodeId, 
                                        value: value, 
                                        type: "interaction", 
                                        label: `pChEMBL: ${value}`,
                                        model: model
                                    }
                                });
                            }
                        }
                    }
                });
            });

            // Update compound_data and populate the table
            window.compound_data[smiles] = {
                compoundCell,
                targetCells: targetCells.join('<br>'),
                pChEMBLCells: pChEMBLCells.join('<br>')
            };

            tableBody.append(`
                <tr>
                    <td>
                        <img src="https://cdkdepict.cloud.vhp4safety.nl/depict/bot/svg?w=-1&h=-1&abbr=off&hdisp=bridgehead&showtitle=false&zoom=.4&annotate=cip&r=0&smi=${encodeURIComponent(smiles)}" 
                             alt="${smiles}" />
                        <br />
                        ${compoundCell}
                    </td>
                    <td>${window.compound_data[smiles].targetCells}</td>
                    <td>${window.compound_data[smiles].pChEMBLCells}</td>
                </tr>
            `);
        });

        if (cyElements.length) {
            cy.add(cyElements);
            positionNodes(cy);
        }
    } else {
        console.error("Unexpected API response format:", response);
        alert("Error: Unexpected response format from server.");
    }
}