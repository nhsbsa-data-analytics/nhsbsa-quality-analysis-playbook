# NHSBSA Producing Quality Analysis Playbook

This repository contains the framework for writing and deploying the NHSBSA Producing Quality Analysis Playbook. 
The Playbook is used to give detailed guidance on producing quality analysis.

The live version of The Playbook can be found [here](https://nhsbsa-data-analytics.github.io/nhsbsa-quality-analysis-playbook/).

## Getting started

The Playbook is created using [Quarto](https://quarto.org/docs/get-started/). 
You can run the document by:
1. Opening the repository in Rstudio or VS Code
    - For Rstudio usage, you simply require the latest version of Rstudio. 
    - For VS Code, you must install the Quarto extension and install the Quarto CLI. When running Quarto for the first time, you will be prompted with instructions on how to install this. **Please note this is not currently possible with the Azure Virtual Desktop (AVD)**.
1. Opening [index.qmd](/index.qmd) in the repository root
1. Click 'Compile' or 'Preview' respectively. 
    - Note: for Rstudio usage, you must also load the `quality-analysis-playbook.Rproj` project to be able to compile the document. 

## Folder Structure

The playbook is structured into a series of sections and sub-sections. The home page first greets the users with the tabs to navigate to the four main sections. Then, once the user has clicked on a section, they are then provided with additional tabs to navigate to a page about each sub-section. The following folder structure highlights how this is setup up from a coding perspective. Each section and sub-section is populated by a `.qmd` file and supporting `.jpeg` file to provide the image for each tab.

```
NHSBSA Producing Quality Analysis Playbook
├───guidance ............................# Folder containing all of the playbook content separated by pages
|   ├───_metadata.yml ...................# Additional settings applied to the quarto document
├───static ..............................# A folder containing the the BSA visual settings for the quarto document
├───_quarto.yml .........................# A file that controls the page layout and settings for the quarto document
├───about.qmd ...........................# An additional .qmd that populates the 'About' button within the document
├───quality-analysis-playbook.Rproj .................# The R Project file
├───index.qmd ...........................# The primary .qmd file, used to compile the entire document.
├───README.md ...........................# The README file
├───styles.css ..........................# A file containing some additional settings for the quarto document
```

## Contributing to The Playbook
We welcome contributions from community members. 
Please see our [contributing guide](./CONTRIBUTE.md) for information on how you can get involved!
