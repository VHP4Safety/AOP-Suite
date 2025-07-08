// Utility function to fetch data from endpoint
async function fetchData(endpoint, params) {
    try {
        const queryString = new URLSearchParams(params).toString();
        const response = await fetch(`${endpoint}?${queryString}`, { method: 'GET' });
        if (!response.ok) {
            throw new Error(`Failed to fetch data: ${response.status} ${response.statusText}`);
        }

        // Get raw response text and clean NaN values
        const text = await response.text();
        const cleanText = text.replace(/NaN/g, 'null');
        const data = JSON.parse(cleanText);

        return data;
    } catch (error) {
        console.error('There was a problem with the fetch operation:', error);
        return null;
    }
}

// Function to fetch BridgeDb data
async function fetchBridgeDbXref(identifiers, inputSpecies = "Human", inputDatasource = "PubChem Compound", outputDatasource = "All") {
    try {
        const response = await fetch('/get_bridgedb_xref', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                identifiers,
                input_species: inputSpecies,
                input_datasource: inputDatasource,
                output_datasource: outputDatasource
            })
        });
        if (!response.ok) {
            throw new Error(`Failed to fetch BridgeDb data: ${response.status} ${response.statusText}`);
        }
        const data = await response.json();
        return data.bridgedb_df || [];
    } catch (error) {
        console.error('Error fetching BridgeDb data:', error);
        return [];
    }
}

// Function to handle OpenTargets query
async function addBdfOT(cids) {
    const data = await fetchData('/add_bdf_opentargets', { cids: cids.join(',') });
    if (data) {
        populateBdfTableOT(data);
    }
}

// Function to handle OpenTargets query with BridgeDb data
async function addBdfOTWithBridgeDb(cids) {
    const bridgedbData = await fetchBridgeDbXref(cids, "Human", "PubChem Compound", "All");
    try {
        const response = await fetch('/add_bdf_opentargets', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ bridgedb_data: bridgedbData })
        });

        if (!response.ok) {
            throw new Error(`HTTP ${response.status}: ${response.statusText}`);
        }

        const text = await response.text();
        console.log("Raw OpenTargets response:", text);

        const sanitizedText = text.replace(/\bNaN\b/g, 'null');
        const data = JSON.parse(sanitizedText);
        populateBdfTableOT(data);
    } catch (error) {
        console.error('Error fetching OpenTargets data:', error);
    }
}

// Function to handle Bgee query
async function addBdfBgee(genes) {
    const data = await fetchData('/add_bdf_bgee', { genes: genes.join(',') });
    if (data) {
        populateBdfTableBgee(data);
    }
}

// Function to handle Bgee query with BridgeDb data
async function addBdfBgeeWithBridgeDb(genes) {
    const bridgedbData = await fetchBridgeDbXref(genes, "Human", "Ensembl", "All");
    try {
        const response = await fetch('/add_bdf_bgee', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ bridgedb_data: bridgedbData })
        });
        if (!response.ok) {
            throw new Error(`Failed to fetch Bgee data: ${response.status} ${response.statusText}`);
        }
        const data = await response.json();
        populateBdfTableBgee(data);
    } catch (error) {
        console.error('Error fetching Bgee data:', error);
    }
}

// Event listener for OpenTargets query button
document.addEventListener('DOMContentLoaded', function () {
    document.getElementById('query_opentargets').addEventListener('click', async () => {
        try {
            const cids = await getAllCIDs();
            if (cids.length === 0) {
                alert("No compound IDs found. Please ensure compounds are loaded.");
                return;
            }
            await addBdfOTWithBridgeDb(cids);
        } catch (error) {
            console.error("Error getting CIDs:", error);
            alert("Error getting compound data: " + error.message);
        }
    });

    // Event listener for Bgee query button
    document.getElementById('query_bgee').addEventListener('click', async () => {
        try {
            const genes = await getAllGenes();
            if (genes.length === 0) {
                alert("No genes found. Please ensure genes are loaded in the network.");
                return;
            }
            await addBdfBgeeWithBridgeDb(genes);
        } catch (error) {
            console.error("Error getting genes:", error);
            alert("Error getting gene data: " + error.message);
        }
    });
});

// Function to populate the OpenTargets table
function populateBdfTableOT(data) {
    const table = $("#compound_table");
    const tableHead = table.find("thead tr");
    const tableBody = table.find("tbody");

    // Add header if not already present
    if (!tableHead.find("th:contains('Therapeutic Areas')").length) {
        tableHead.append('<th>Therapeutic Areas</th>');
    }

    const matchedRows = new Set();

    // Process each row asynchronously
    data.forEach(async (row) => {
        const compoundRow = findCompoundRow(tableBody, row.identifier);
        if (compoundRow.length) {
            matchedRows.add(row.identifier);

            // Format therapeutic areas with proper CURIE conversion
            const therapeuticAreas = await formatTherapeuticAreas(row.OpenTargets_diseases || []);
            compoundRow.append(`<td>${therapeuticAreas}</td>`);
        }
    });

    // Add empty cells for unmatched rows after a short delay
    setTimeout(() => {
        addEmptyCellsForUnmatchedRows(tableBody, matchedRows);
    }, 1000);
}

// Function to populate the Bgee table
function populateBdfTableBgee(data) {
    const tableBody = $("#gene_table tbody");
    const tableHead = $("#gene_table thead");

    // Add headers if not already present
    if (tableHead.find("tr").length === 1) {
        tableHead.empty();
        tableHead.append(`
            <tr>
                <th>Gene</th>
                <th>Anatomical Entity</th>
                <th>Confidence Level</th>
                <th>Developmental Stage</th>
                <th>Expression Level</th>
            </tr>
        `);
    }

    // Clear existing rows
    tableBody.empty();

    // Populate the table with data
    Object.entries(data).forEach(([gene, geneData]) => {
        const entries = geneData.Bgee_gene_expression_levels.map(entry => ({
            gene: geneData.identifier,
            anatomical_entity: `${entry.anatomical_entity_name || 'N/A'} (${entry.anatomical_entity_id || 'N/A'})`,
            confidence_level: `${entry.confidence_level_name || 'N/A'} (${entry.confidence_level_id || 'N/A'})`,
            developmental_stage: `${entry.developmental_stage_name || 'N/A'} (${entry.developmental_stage_id || 'N/A'})`,
            expression_level: entry.expression_level !== undefined ? entry.expression_level.toFixed(2) : 'N/A'
        }));

        entries.forEach((entry, index) => {
            const tr = $("<tr></tr>");
            if (index === 0) {
                // Add the gene name with rowspan for the first row of the group
                tr.append(`<td rowspan="${entries.length}" class="gene-cell">${entry.gene}</td>`);
            }
            tr.append(`<td>${entry.anatomical_entity}</td>`);
            tr.append(`<td>${entry.confidence_level}</td>`);
            tr.append(`<td>${entry.developmental_stage}</td>`);
            tr.append(`<td>${entry.expression_level}</td>`);
            tableBody.append(tr);
        });
    });

    console.log("Bgee data populated in the gene table.");
}

// Helper function to find a compound row by identifier
function findCompoundRow(tableBody, identifier) {
    return tableBody.find("tr").filter(function () {
        return $(this).find(".cid-link").text().trim() === identifier;
    });
}

// Helper function to format therapeutic areas using backend conversion
async function formatTherapeuticAreas(diseases) {
    try {
        // Extract all therapeutic area strings
        const therapeuticAreaStrings = diseases
            .map(diseaseObj => diseaseObj.therapeutic_areas || "")
            .filter(areas => areas.trim() !== "");

        if (therapeuticAreaStrings.length === 0) {
            return "";
        }

        // Send to backend for proper CURIE to IRI conversion
        const response = await fetch('/convert_therapeutic_areas', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ therapeutic_areas: therapeuticAreaStrings })
        });

        if (!response.ok) {
            throw new Error(`Backend conversion failed: ${response.status}`);
        }

        const data = await response.json();

        if (data.error) {
            throw new Error(data.error);
        }

        // Create unique areas map by namespace_id
        const uniqueAreas = new Map();

        data.converted_areas.forEach(area => {
            const key = area.namespace_id;
            if (!uniqueAreas.has(key)) {
                uniqueAreas.set(key, area);
            }
        });

        // Return formatted links
        return Array.from(uniqueAreas.values())
            .map(area => area.link)
            .join(", ");

    } catch (error) {
        console.error('Error formatting therapeutic areas:', error);

        // Fallback to simple client-side formatting
        const uniqueAreas = new Map();

        diseases.forEach(diseaseObj => {
            const areas = diseaseObj.therapeutic_areas || "";
            areas.split(",").forEach(area => {
                const [id, name] = area.split(":").map(part => part.trim());
                if (id && name) {
                    uniqueAreas.set(id, {
                        id: id,
                        name: name,
                        link: `<a href="#" title="${name}" target="_blank" style="position: relative; z-index: 10;">${name}</a>`
                    });
                }
            });
        });

        return Array.from(uniqueAreas.values())
            .map(area => area.link)
            .join(", ");
    }
}

// Helper function to format gene expression levels
function formatGeneExpressionLevs(data) {
    return data
        .map(entry => {
            const prettyJson = JSON.stringify(entry, null, 2);
            return `<div class="gene-expression-entry"><pre>${prettyJson}</pre></div>`;
        })
        .join("");
}

// Helper function to add empty cells for unmatched rows
function addEmptyCellsForUnmatchedRows(tableBody, matchedRows) {
    tableBody.find("tr").each(function () {
        const cid = $(this).find(".cid-link").text().trim();
        if (!matchedRows.has(cid)) {
            $(this).append('<td></td>');
        }
    });
}

