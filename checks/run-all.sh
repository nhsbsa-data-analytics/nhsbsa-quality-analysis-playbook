#!/usr/bin/env bash
# Every check this repository has, in one command.
#
#   quarto render && bash checks/run-all.sh
#
# Three of them read the built site in docs/, so render first. The rest read the sources and skip
# docs/ deliberately, so that a page edited but not rendered still shows up as the problem it is.
# The run stops at nothing: every check runs, and the exit code is non-zero if any of them failed,
# because knowing about one problem is not a reason to hide the next five.
#
# What each needs beyond the standard library:
#   links.py                 nothing. Pass --online to also check that the citations resolve
#   deliverables.py          a git checkout, which is how it asks what is tracked
#   accessibility.py         the built site, playwright, and a Chromium
#   axe.py                   the built site, playwright, and a Chromium
#   wcag22.py                the built site, playwright, and a Chromium. It presses Tab several
#                            thousand times, so it takes a few minutes
#   search.py                the built site
#   properties.py            pypdf, and the review copies in review/
#   responsible-analysis.py  nothing
#   table-widths.py          nothing
#   house-voice.py           nothing
#   standards.py             nothing
#   glossary.py              nothing
#   diagrams.py              nothing. Reads the seven diagrams in static/diagrams against the
#                            partials that embed them (alt text, size, labels, word count), and
#                            the phases-and-roles board against the phase pages when build/ is
#                            present
#   generated.py             nothing, when build/ is present. It runs each generator into a
#                            temporary directory, so it needs playwright and a Chromium for
#                            the one rendering step it owns. Skips without build/
#   diagram-layout.py        nothing
#   package.py               the archive in dist/, and both source clones beside this one
#
# Three of the sixteen are not in the release package that build/build-integrated-package.py writes.
# deliverables.py asks git what is tracked, properties.py reads the review copies, and package.py
# reads dist/ and the clones: the package is a folder of files, not a checkout, and carries none
# of those. Dropping them was deliberate. Leaving this file invoking them was not, and run from
# inside the package it printed FAILED lines naming files that were never meant to be there, so
# the first command the package offers NHSBSA reported their own release as broken.
#
# ABSENT names those three rather than forgiving whatever happens to be missing. An absent script
# fails the suite unless it is one of these and this is not a checkout, so a check lost on the way
# into the package still reads differently from one left out on purpose. `build/` is the test for
# "this is a checkout": the package drops it, and no clone of this repository is without it.
# checks/package.py asserts that this list and the builder's own name the same three files.
set -u
cd "$(dirname "$0")/.."
ABSENT=' deliverables properties package '
status=0
for check in links deliverables accessibility axe wcag22 search properties \
             responsible-analysis table-widths house-voice standards glossary \
             generated diagrams diagram-layout package; do
    printf '\n==============================================================\n'
    printf '  checks/%s.py\n' "$check"
    printf '==============================================================\n'
    if [ ! -f "checks/$check.py" ]; then
        if [ -d build ] || [ "${ABSENT#* $check }" = "$ABSENT" ]; then
            status=1
            printf '\n  checks/%s.py IS MISSING, and this is not a release package\n' "$check"
        else
            printf '\n  --  not part of the release package: it reads the git history, the review\n'
            printf '      copies or dist/, and the package carries none of them\n'
        fi
        continue
    fi
    if python3 "checks/$check.py"; then :; else
        status=1
        printf '\n  checks/%s.py FAILED\n' "$check"
    fi
done
printf '\n==============================================================\n'
if [ "$status" -eq 0 ]; then
    printf '  ALL CHECKS PASSED\n'
else
    printf '  ONE OR MORE CHECKS FAILED\n'
fi
printf '==============================================================\n'
exit "$status"
