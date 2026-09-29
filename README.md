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

The playbook is 17 pages across 15 sections, with a left sidebar that groups them into four bands
by what a reader has come to do, and a Guidance menu that lists them in order. Each section is one
directory under `guidance`, numbered so the order is visible, holding a single `index.qmd`. Text
that belongs on more than one page lives once in `guidance/_partials/` and is included where it is
needed, so there is no second copy of any rule to fall out of step.

```
NHSBSA Producing Quality Analysis Playbook
├───guidance ...........................# Every page of the playbook, one directory per section
|   ├───_partials ......................# Text written once and included in more than one place
|   ├───_metadata.yml ..................# Settings applied to every page under guidance
├───static .............................# The logo, the favicon, and the diagrams with their draw.io sources
├───_extensions ........................# The iconify extension, used by the navigation bar
├───_filters ...........................# The Lua filter that numbers and names the citations
├───checks .............................# Scripts that assert what the site claims. See Accessibility below
├───.github ............................# The Action that renders and publishes to gh-pages on a push to main
├───_quarto.yml ........................# Page layout, the sidebar, the menu, and what gets rendered
├───index.qmd ..........................# The landing page, and the root of the render
├───about.qmd ..........................# The About page
├───accessibility.qmd ..................# The accessibility statement
├───*.html .............................# Six small accessibility includes, each named for what it does
├───styles.css .........................# Styling, including the accessibility engineering
├───CONTRIBUTE.md ......................# How to contribute
├───README.md ..........................# This file
└───quality-analysis-playbook.Rproj ....# The R project file
```

## Accessibility

The site meets WCAG 2.2 level AA, and five level AAA criteria besides. Much of what makes it
conformant is configuration and a few lines of CSS, which is the sort of thing that gets tidied
away by somebody who does not know what it is for. The damage is invisible: the site still
renders, it is just no longer accessible. Each such setting is commented with the criterion it
serves, so read the comment beside one before removing it.

`accessibility.qmd` holds the published statement. It names three things to settle before the
statement goes live: the compliance status in the Regulations' own terms, the preparation and
testing dates, and the mailbox that accessibility reports should reach.

Two scripts hold the claim up after an edit:

```
python3 checks/links.py
quarto render && python3 checks/accessibility.py
```

`links.py` checks that every internal link resolves, that every cross-page anchor is made by a
heading on the page it points at, and that nothing is linked over plain `http`. Pass `--online` to
fetch the external citations as well. It needs nothing but Python.

`accessibility.py` drives the rendered site and asserts it against the criteria one at a time,
naming the criterion in each message. It needs Playwright and Chromium:

```
pip install playwright && playwright install chromium
```

## Contributing to The Playbook
We welcome contributions from community members. 
Please see our [contributing guide](./CONTRIBUTE.md) for information on how you can get involved!
