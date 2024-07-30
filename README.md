# NHSBSA Producing Quality Analysis Playbook

This repository contains the framework for writing and deploying the NHSBSA Producing Quality Analysis Playbook. The playbook is used to give detailed guidance on producing quality analysis.

The playbook can be found [here](https://nhsbsa-data-analytics.github.io/quality-analysis-playbook/).

## Requirements

To run the document, open `index.qmd`, within the root folder, using either Rstudio or VS Code and click 'Compile' or 'Preview' respectively. For Rstudio usage, you must also load the `quality-analysis-playbook.Rproj` project to be able to compile the document. 

For Rstudio usage, you simply require the latest version of Rstudio. For VS Code, you must install the Quarto extension and install the Quarto CLI. When running Quarto for the first time, you will be prompted with instructions on how to install this. **Please note this is not currently possible with the Azure Virtual Desktop (AVD)**.

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
