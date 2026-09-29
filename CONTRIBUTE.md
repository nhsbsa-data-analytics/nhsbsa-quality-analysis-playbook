# How to contribute

Hi there! 
Thank you for considering contributing to the [published NHSBSA Producing Quality Analysis Playbook site](https://nhsbsa-data-analytics.github.io/nhsbsa-quality-analysis-playbook/). 
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
- Write [good commit messages](https://tbaggery.com/2008/04/19/a-note-about-git-commit-messages.html).

## Getting started with development

### Environments
#### Github Codespaces
The **easiest way is just to open the repo in [Github Codespaces](https://github.com/features/codespaces)** - you can then make your changes, run the website to check it, and commit those back all within a VSCode environment.

#### Working locally
If you don't want to use Github codespaces (or can't because it's blocked, or you've run out of credits), then you can make changes to the repo locally on your machine.

### Installing dependencies
See the [README](./README.md) for guidance on installing the dependencies and getting started with development.

### Adding or editing content
Each section is one directory under `guidance`, numbered so the order is visible, holding a single
`index.qmd`. So section 5 is `guidance/05-deciding-your-assurance-level/index.qmd`. Two pages that
belong to no section sit directly in `guidance`.

Four things are named in one place each, and all four need updating together when a section is
added or renamed. Miss one and the page still builds, so nothing tells you:

| | Where |
|---|---|
| Whether the page is rendered at all | the `render:` list in `_quarto.yml` |
| Where it appears in the left sidebar | the `sidebar:` section of `_quarto.yml` |
| Where it appears in the Guidance menu | the `navbar:` section of `_quarto.yml` |
| Where it appears in the contents table | `guidance/_partials/section-contents.qmd` |

#### To edit an existing page
1. Open the `index.qmd` in that section's directory and edit it as markdown.
1. Text that belongs on more than one page lives in `guidance/_partials/` and is pulled in with
   `{{< include /guidance/_partials/name.qmd >}}`. Edit the partial, not the copies. The include
   path starts from the project root, because a partial is included at more than one depth.
1. Once you are happy with your changes [submit a pull request!](#submitting-a-pull-request)

#### To add a new section
1. Create a subfolder within `guidance`, numbered so it sorts where you want it (e.g.
   `14-something-new`).
1. Add an `index.qmd` to it with this header:
    ```
    ---
    title: "The title of your page"
    description: "One sentence saying what the page is for"
    ---
    ```
   The title, the sidebar label and the navbar label should all say the same thing, so a reader
   arrives at the page they expected. The description is the browser meta description.
1. Add the content below the header using standard markdown syntax.
1. Add the page in all four places in the table above.
1. Render locally with `quarto render` and check the page appears in the sidebar, in the menu and
   in the contents table.
1. Once you are happy with your changes [submit a pull request!](#submitting-a-pull-request)

#### Before you open the pull request
Run the checks. They are quick and they assert things that are easy to break without noticing:

```
python3 checks/accessibility.py    # needs a `quarto render` first
python3 checks/deliverables.py
```

## Resources

- [Contributing to Projects](https://docs.github.com/en/get-started/exploring-projects-on-github/contributing-to-a-project)
- [Using Pull Requests](https://docs.github.com/en/pull-requests/reference/pull-requests)
- [GitHub Help](https://help.github.com)

[fork]: https://github.com/nhsbsa-data-analytics/nhsbsa-quality-analysis-playbook/fork
[pr]: https://github.com/nhsbsa-data-analytics/nhsbsa-quality-analysis-playbook/pulls
[issues]: https://github.com/nhsbsa-data-analytics/nhsbsa-quality-analysis-playbook/issues

## Acknowledgements
Thank you to the [NHS England RAP Community of Practice](https://github.com/NHSDigital/rap-community-of-practice/blob/35adb3c15ba3c34fe7d5ab3baede760504ceb7a1/CONTRIBUTE.md) from which this guide took heavy inspiration!
