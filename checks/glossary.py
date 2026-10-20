#!/usr/bin/env python3
"""Check that the glossary is what its own page says it is.

    python3 checks/glossary.py

Standard library only.

Four assertions:

  1. every term sits in the lettered section its initial belongs to
  2. the terms inside each section are in alphabetical order
  3. no term is defined here and used nowhere else in the playbook
  4. the scan reached the glossary, found all five sections, and found terms in each

The glossary opens by telling the reader it is "in alphabetical order", and a reader who has been
told that stops scanning the moment they pass where their word should have been. That claim went
untrue without anybody noticing: the Analytical Assurance Decision Tool entry sat between
*Assurance level* and *Assurance plan*, four rows below where a reader would give up looking for
it. Nothing rendered wrong, no link broke, and the page went on making the claim. A reader
following the promise would have concluded the playbook does not define its own central term.

So assertions 1 and 2 hold the promise rather than the appearance of it. The sort key is the term
up to its first comma, lowercased, with punctuation removed, because the glossary writes an
abbreviation after the term it abbreviates: **Quality assurance, QA** is filed under *quality
assurance*, which puts it before **Quality assurance log** where a reader expects it, and not
after it where a plain character sort would put it. Stripping punctuation is the same decision:
*Critical friend, analytical assurer* files under *critical friend*.

Assertion 3 is the other half. A glossary is a promise in both directions, and an entry for a term
the playbook no longer uses is a worse fault than a missing one: it tells the reader a concept is
live when the guidance has moved on. The word *tier* was in here after the playbook had settled on
*Level* everywhere else, and *band* with it. Both read as current vocabulary to anybody who met
them here first. A term is counted as used if the term itself, or any of the names listed after
its comma, appears in any other page the playbook ships; that is deliberately generous, because
this is here to catch a concept that has been retired, not to police how often a word appears.

What this cannot do is tell whether the glossary is complete. No check can: the terms that ought
to be in it are the ones a reader does not know, and nothing in the source says which those are.
Assertion 4 is the honest substitute. It fails if the parse found no glossary, lost a section, or
found a section with nothing in it, so a glossary emptied by a bad edit reads differently from one
that passes.
"""
import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
GLOSSARY = ROOT / 'guidance' / '09-resources' / 'r1-glossary.qmd'
SKIP_DIRS = {'docs', '_site', '.quarto', '__pycache__', 'dist', 'review', '.git', 'build',
             'checks', 'elearn', 'tools', 'artefacts'}

SECTION = re.compile(r'^## ([A-Z]) to ([A-Z])\s*$')
ROW = re.compile(r'^\| \*\*(.+?)\*\* \|')


def key(term):
    """The name a reader would look the term up under: everything before the abbreviation."""
    return re.sub(r'[^a-z0-9 ]', '', term.split(',')[0].strip().lower())


def read():
    """Return [(section, term, line number)], in the order the page lists them."""
    out = []
    section = None
    for n, line in enumerate(GLOSSARY.read_text(encoding='utf-8').splitlines(), 1):
        found = SECTION.match(line)
        if found:
            section = (found.group(1), found.group(2))
            continue
        found = ROW.match(line)
        if found:
            out.append((section, found.group(1), n))
    return out


def pages():
    """Every page the playbook ships, apart from the glossary itself."""
    out = []
    for path in sorted(ROOT.rglob('*.qmd')):
        if any(part in SKIP_DIRS for part in path.relative_to(ROOT).parts):
            continue
        if path != GLOSSARY:
            out.append(path)
    return out


def main():
    fail = []
    entries = read()

    # Assertion 1. Every term is under the right letter.
    for section, term, line in entries:
        if section is None:
            fail.append('r1-glossary.qmd:%d defines **%s** before any lettered section, so a '
                        'reader scanning the headings never reaches it' % (line, term))
            continue
        first = key(term)[:1].upper()
        if not section[0] <= first <= section[1]:
            fail.append('r1-glossary.qmd:%d files **%s** under "%s to %s", and it begins with %s'
                        % (line, term, section[0], section[1], first))

    # Assertion 2. Alphabetical inside each section, which is what the page promises.
    for before, after in zip(entries, entries[1:]):
        if before[0] == after[0] and key(after[1]) < key(before[1]):
            fail.append('r1-glossary.qmd:%d puts **%s** after **%s**. The page says it is in '
                        'alphabetical order, and a reader who passes where their word should be '
                        'stops looking' % (after[2], after[1], before[1]))

    # Assertion 3. Nothing defined here and retired everywhere else.
    corpus = '\n'.join(p.read_text(encoding='utf-8') for p in pages()).lower()
    for section, term, line in entries:
        names = [n.strip().lower() for n in term.split(',') if n.strip()]
        if not any(n in corpus for n in names):
            fail.append('r1-glossary.qmd:%d defines **%s**, which no other page uses. An entry '
                        'for a retired term reads as current vocabulary to a reader who meets it '
                        'here first' % (line, term))

    # Assertion 4. The scan reached something, so a pass means something.
    if not GLOSSARY.exists():
        fail.append('%s is missing, and the three assertions above all pass against no glossary'
                    % GLOSSARY.relative_to(ROOT))
    sections = {s for s, _, _ in entries if s}
    if len(sections) != 5:
        fail.append('the glossary parsed into %d lettered sections rather than 5, so either a '
                    'section heading changed shape or a section was lost' % len(sections))
    for section in sorted(sections):
        if not [t for s, t, _ in entries if s == section]:
            fail.append('section "%s to %s" carries no terms' % section)
    if len(entries) < 40:
        fail.append('the glossary parsed into %d terms, which is fewer than the playbook has '
                    'needed at any point. Either the row shape changed or the table was emptied'
                    % len(entries))

    print('  %d terms, in %d lettered sections, read against %d other pages'
          % (len(entries), len(sections), len(pages())))
    if fail:
        print()
        for line in fail:
            print('  %s' % line)
        print('\n  %d problem%s' % (len(fail), '' if len(fail) == 1 else 's'))
        return 1
    print('  the glossary is in the order it says it is, and every term is still in use')
    return 0


if __name__ == '__main__':
    sys.exit(main())
