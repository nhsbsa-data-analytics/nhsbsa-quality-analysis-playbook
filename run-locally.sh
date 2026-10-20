#!/usr/bin/env bash
#
# Run the playbook on your own machine.
#
#   bash run-locally.sh            opens the site and reloads it as you edit
#   bash run-locally.sh render     renders once into docs/ and stops
#   bash run-locally.sh checks     renders, then runs every check
#
# The site is not committed. docs/ is in .gitignore, because a rendered copy in the repository
# goes stale the moment anybody edits a page and then nobody can tell which version is true. So a
# fresh clone has the sources and no site, and this script is how you get one.
set -euo pipefail
cd "$(dirname "$0")"

if ! command -v quarto > /dev/null 2>&1; then
  cat <<'MISSING'
Quarto is not on your PATH, and it is the one thing this needs.

  macOS            brew install --cask quarto
  Windows, Linux   https://quarto.org/docs/get-started/

The site was built with Quarto 1.6.39. A later 1.x renders it too. Install it, open a new terminal
so the PATH is picked up, and run this again.
MISSING
  exit 1
fi

echo "Quarto $(quarto --version)"

case "${1:-preview}" in
  preview)
    echo
    echo "Rendering, then opening the site in your browser."
    echo "Edit any .qmd and the page reloads on its own. Ctrl-C stops the server."
    echo
    exec quarto preview
    ;;
  render)
    quarto render
    echo
    echo "Done. Open docs/index.html in a browser."
    ;;
  checks)
    quarto render
    echo
    # Sixteen checks hold up what the site claims. Three of them need Python packages the site
    # itself does not: see the Accessibility section of README.md for the one pip command.
    bash checks/run-all.sh
    ;;
  *)
    echo "Unknown argument '$1'. Use no argument, or 'render', or 'checks'." >&2
    exit 2
    ;;
esac
