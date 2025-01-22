# How to contribute

Hi there! 
Thank you for considering contributing to the [NHSBSA Producing Quality Analysis Playbook](https://nhsbsa-data-analytics.github.io/nhsbsa-quality-analysis-playbook/). 
The Playbook is meant to serve the D&A community, so contributions from community members themselves are super important in making this a reality! 

## Creating an issue

If you think of something worth including, improving, or want to contribute, please [raise an issue on GitHub][issues].

## Submitting a pull request

Please submit new contributions via a [pull request][pr]:

1. [Fork][fork] or clone the repository
1. If you want to run the page on your machine, configure and install the dependencies. 
See the [README](./README.md) for details.
1. Create a new branch: (e.g. `git checkout -b my-branch-name`)
1. [Make your change](#getting-started-with-development)
1. Push to your fork and [submit a pull request][pr]

Your pull request will then be reviewed. 
You may receive some feedback and suggested changes before it can be approved and your pull request merged. 

### To increase the likelihood of your pull request being accepted:

- If you are making visual changes, include a screenshot of what the affected element looks like, both before and after.
<!-- TODO: add a style guide -->
<!-- - Follow the [style guide][style]. -->
- Keep your change as focussed as possible. 
If there are multiple changes you would like to make that are not dependent upon each other, consider submitting them as separate pull requests.
- Write [good commit messages](http://tbaggery.com/2008/04/19/a-note-about-git-commit-messages.html).

## Getting started with development

### Environments
#### Github Codespaces
The **easiest way is just to open the repo in [Github Codespaces](https://github.com/features/codespaces)** - you can then make your changes, run the website to check it, and commit those back all within a VSCode environment.

#### Working locally
If you don't want to use Github codespaces (or can't because it's blocked, or you've run out of credits), then you can make changes to the repo locally on your machine.

### Installing dependencies
See the [README](./README.md) for guidance on installing the dependencies and getting started with development.

### Adding or editing content
#### To add a new page to within the existing structure
1. Navigate to the relevant subfolder within `guidance` (e.g. `guidance/03-responsibilities/pages`)
1. Add a [qmd](https://quarto.org/docs/get-started/hello/rstudio.html) file with the following header fields:
    ```
    ---
    title: "This is the title of your page"
    description: "This is a brief description of your page"
    image-alt: "This text will show if your image can't be displayed"
    image: <name of a .jpg file stored in the same subfolder to use for the card>
    ---
    ```
1. Add the content below the header using standard markdown syntax.
1. A link to the page will be added as a card on the landing page. 
If you want to show an image on the card, add a jpeg file to the same subfolder as the content and include the name in the header fields as above.
1. Once you are happy with your changes [submit a pull request!](#submitting-a-pull-request)

#### To add a new page within a new section
1. Create the a subfolder within `guidance` and name it appropriately (e.g. `04-business-critical-models`). Note that the sections will be ordered in the dropdown on the website according to the numbers in front of the subfolders (i.e. first `01-` then `02-` and so on)
1. Add an `index.qmd` file to the subfolder (you can use one of the existing files as an example!)
1. Follow the steps above to add the new page within the section you've just created.
1. Once you are happy with your changes [submit a pull request!](#submitting-a-pull-request)

## Resources

- [Contributing to Projects](https://docs.github.com/en/get-started/quickstart/contributing-to-projects)
- [Using Pull Requests](https://help.github.com/articles/using-pull-requests/)
- [GitHub Help](https://help.github.com)

[fork]: https://github.com/nhsbsa-data-analytics/nhsbsa-quality-analysis-playbook/fork
[pr]: https://github.com/nhsbsa-data-analytics/nhsbsa-quality-analysis-playbook/pulls
[issues]: https://github.com/nhsbsa-data-analytics/nhsbsa-quality-analysis-playbook/issues

## Acknowledgements
Thank you to the [NHS England RAP Community of Practice](https://github.com/NHSDigital/rap-community-of-practice/blob/35adb3c15ba3c34fe7d5ab3baede760504ceb7a1/CONTRIBUTE.md) from which this guide took heavy inspiration!