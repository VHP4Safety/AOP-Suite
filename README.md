# AOP-Suite
<img src="https://github.com/VHP4Safety/AOP-Suite/blob/aop_app/static/images/app_screenshot.png" width="850px"/>

This repository contains a web-based tool for building, visualizing, and analyzing Adverse Outcome Pathway (AOP) networks. It serves as an extended user interface for [pyAOP](https://github.com/jmillanacosta/pyaop) and the [AOP-Wiki RDF SPARQL endpoint](https://aopwiki.rdf.bigcat-bioinformatics.org/sparql/).

## Overview

The AOP Network Builder allows to:

- **Build AOP Networks**: Query AOP Wiki RDF data and construct biological pathway networks
- **Integrate Multiple Data Sources**: Combine data from AOP Wiki, UniProt, Ensembl, Bgee, OpenTargets, and more (work in progress)
- **Interactive Visualization**: Use Cytoscape.js for dynamic network visualization with customizable layouts
- **Data Enhancement**: Add gene expression data, QSPR predictions, and GO process annotations. Uses [BridgeDb](https://www.bridgedb.org/) to map identifiers across sources and query using [BioDataFuse](http://biodatafuse.org) and other [VHP4Safety](https://www.sciencrew.com/c/6586?title=VHP4Safety) API resouces (see full cloud repository [here](https://cloud.vhp4safety.nl/))


### Data Integration

- **Bgee Expression Data**: Add tissue-specific gene expression information
- **OpenTargets**: Query drug-target associations and disease relationships  
- **QSPR Predictions**: Generate bioactivity predictions for chemical compounds
- **GO Processes**: Integrate Gene Ontology biological process hierarchies (work in progress)


### Data Tables
- **AOP Table**: Browse and filter pathway information with enhanced search
- **Compounds Table**: Add chemical entities and their interactions with genes, key events and AOP components.
- **Genes Table**: Display gene/protein data with expression levels

## Requirements

The application is built as a Flask app and requires the following Python modules, including [`pyBiodatafuse`](https://pypi.org/project/pyBiodatafuse/) for BioDataFuse and BridgeDB queries.

```bash
(uv) pip install -r requirements.txt
```

## Usage

1. **Start Building**: Use the Query mode to search AOP Wiki or add elements manually
2. **Enhance Networks**: Switch to Enhance mode to add expression data, predictions, or annotations  
3. **Explore Data**: Use the interactive tables to browse and filter network components
4. **Analyze Results**: Leverage the visualization tools to identify biological relationships (work in progress)
5. **Save Work**: Export networks or save current state for future sessions

## Funding

VHP4Safety – the Virtual Human Platform for safety assessment project [NWA 1292.19.272](https://www.nwo.nl/projecten/nwa129219272) is part of the NWA research program ‘Research along Routes by Consortia (ORC)’, which is funded by the Netherlands Organization for Scientific Research (NWO). The project started on June 1, 2021 with a budget of over 10 million Euros and will last for the duration of 5 years.
