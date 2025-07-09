# AOP Network Builder
<img src="https://github.com/user-attachments/assets/a0f99c2b-a29a-40b1-b5c4-14d4d733be07" width="850px"/>

This repository contains a web-based tool for building, visualizing, and analyzing Adverse Outcome Pathway (AOP) networks. 

## Overview

The AOP Network Builder allows researchers to:

- **Build AOP Networks**: Query AOP Wiki RDF data and construct biological pathway networks
- **Integrate Multiple Data Sources**: Combine data from AOP Wiki, UniProt, Ensembl, Bgee, OpenTargets, and more
- **Interactive Visualization**: Use Cytoscape.js for dynamic network visualization with customizable layouts
- **Data Enhancement**: Add gene expression data, QSPR predictions, and GO process annotations

### Data Integration

- **Bgee Expression Data**: Add tissue-specific gene expression information
- **OpenTargets**: Query drug-target associations and disease relationships  
- **QSPR Predictions**: Generate bioactivity predictions for chemical compounds
- **GO Processes**: Integrate Gene Ontology biological process hierarchies (work in progress)


### Data Tables
- **AOP Table**: Browse and filter pathway information with enhanced search
- **Compounds Table**: View chemical entities with network highlighting
- **Genes Table**: Display gene/protein data with expression levels

## Requirements

The application requires the following Python modules:

```bash
pip install -r requirements.txt
```

## Usage

1. **Start Building**: Use the Query mode to search AOP Wiki or add elements manually
2. **Enhance Networks**: Switch to Enhance mode to add expression data, predictions, or annotations  
3. **Explore Data**: Use the interactive tables to browse and filter network components
4. **Analyze Results**: Leverage the visualization tools to identify biological relationships
5. **Save Work**: Export networks or save current state for future sessions

