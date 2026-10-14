#!/usr/bin/env python3
"""Check the punctuation the playbook has committed to, across every page it ships.

    python3 checks/house-voice.py

Standard library only.

Seven assertions, over every page the playbook ships and every diagram drawn on it:

  1. no curly quotation marks or apostrophes in prose
  2. no em dashes in prose
  3. no straight double quote inside a `fig-alt="..."`, where it ends the attribute
  4. no page names a file path on a machine, a build script or a check
  5. the scan actually reached the pages and the diagrams, so a passing run means something
  6. no phrase that talks down to the reader, whatever their role
  7. no table cell with a run of words too long to read in a narrow column

The first is here because the playbook had twelve curly characters in five files and nobody saw
them. They arrive one paste at a time, from a Word document or a web page, and they are invisible
in a diff viewer that renders them the same width as the straight ones. Mixed quotation marks in a
document that quotes a standard are a small wrongness that makes a reader wonder what else was not
checked, which is the same reason the page counts in the review README are checked.

The second holds a rule the delivery already keeps: no em dashes in the prose. It is zero today,
and a check that starts at zero is the cheapest kind to add, because it never has to be paid down.

The third exists because straightening the first broke three diagrams. Three `fig-alt` values
quoted a label out of the picture, and used curly marks to do it. Straightening those put a
straight double quote inside a double-quoted attribute, which ends the attribute: Quarto then
emitted three images with no alt text at all, and axe reported three critical `image-alt`
violations on three pages. The accessibility checks caught it, which is what they are for, but
they can only catch it after a render. This catches it in the source, where the mistake is. Nest
with single quotes instead.

The fourth is here because 1,035 characters of reviewer commentary were written into section 5a and
shipped. A review proposed an edit, its verifier replied explaining why the proposed footnote was
wrong, and the applier wrote the reply into the page as though it were the edit. What reached the
playbook was a paragraph addressed to whoever was editing it, naming a path on this machine and a
numbered task. No check saw it: it is grammatical British English, it breaks no rule above, and the
page still renders. What gives it away is that playbook prose never names a file path, a build
script or a check, because none of those exist for the analyst reading it.

The pages are not the only thing NHSBSA receives. The diagrams ship too, as draw.io sources they
can open and edit and as the SVG renders beside them, and their labels are prose by any measure: a
reader sees them on the page exactly as they see a paragraph. For as long as this check read only
`*.qmd` they were outside it, and eleven curly apostrophes and quotation marks sat in four service
design boards and one playbook diagram, in text drawn on a wall for NHSBSA to read. Nothing was
wrong with the check; its scope was. It now covers every shipped file whose text a reader sees,
which is the pages and the drawings.

Where the fix belongs depends on the file. Every `.svg` here is a render of the `.drawio` beside
it, so the `.drawio` is the one to change. Most of those are authored by hand and committed, but
sixteen of them are written by a script under `build/`, where editing the file is undone by the
next build. The failure says so rather than guessing which is which.

`search.qmd` is excluded, and only `search.qmd`. Its curly characters are inside JavaScript string
literals: the ellipsis that truncates a result snippet, and the quotation marks the page puts
around the reader's own search term when it reports what it found. Those are output, they are
correct typography in that position, and straightening them would make the search results worse.
Excluding a file by name is a thing worth being nervous about, so the exclusion is asserted: if
those literals ever leave `search.qmd`, assertion 3 fails rather than quietly covering nothing.
"""
import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
SKIP_DIRS = {'docs', '_site', '.quarto', '__pycache__', 'dist', 'review', '.git', 'build',
             'checks', 'elearn', 'tools', 'artefacts'}

# The page whose curly characters are JavaScript output rather than prose, and why.
EXCLUDED = {'search.qmd': 'its curly characters are inside JavaScript string literals, which are '
                          'what the search results show the reader'}

# A label in a .drawio file is HTML, and so is a fig-alt and anything inside a ```{=html} block.
# The character can therefore arrive written as an entity and reach the reader looking exactly
# the same. Matching the character alone is how `&#8212;` sat in the `empty()` cell of every
# service design board for a month and passed this check every time. What the reader sees is
# the rule, so both spellings are matched.
CURLY = re.compile('[‘’“”]|&#82(?:1[6789]|2[01]);|&#x201[89a-fA-F];|&[lr]squo;|&[lr]dquo;')
EM_DASH = re.compile('—|&#8212;|&#x2014;|&mdash;', re.I)
# The attribute runs to the next double quote, so one inside the value truncates it.
FIG_ALT = re.compile(r'fig-alt="(.*?)"\}', re.S)
# Prose that is addressed to whoever is editing the playbook rather than to whoever is reading it.
INWARD = re.compile(r'(/home/\S+|\b(?:checks|build)/[\w.-]+\.(?:py|sh)\b|\btask #\d+)', re.I)

fail = []


# ------------------------------------------------------------------ assertions 6 and 7
# NHSBSA asked for language that is simple and does not talk down to any role. Two shapes do
# that, and both were in the playbook. The first corrects an instinct the reader never showed:
# "a document nobody opens", "the one to read twice", "read rather than assumed". The second is
# the playbook commenting on its own editorial choices at the reader: "deliberately thin", "on
# purpose", "why this playbook exists". Neither carries a rule, so neither costs anything to
# drop, and both read as a lecture when they accumulate. Phrases, not a tone model: a phrase
# list is checkable and a tone is not.
PATRONISING = [
    'nobody opens', 'nobody reads', 'nobody finds', 'the one to read twice', 'read it twice',
    'commonest way', 'people get wrong', 'the mistake people make', 'a fresh coat',
    'not a tidy-up', 'is finding it too late', 'only that you looked', 'rather than assumed',
    "don't forget", 'do not forget', 'resist the temptation', 'needless to say',
    'it goes without saying', 'as you know', 'obviously,', 'of course,',
    'why this playbook exists', 'exists to prevent', 'deliberately thin', 'deliberately short',
    'on this table on purpose', 'nested on purpose', 'the test a stop had to pass',
    'all you need to do', 'all you have to do',
]

# A table cell is read in a narrow column, so a long unbroken run in one is harder going than
# the same words in a paragraph. The worst in the playbook was 101 words in a two-column grid,
# which is a paragraph wearing a table's clothes. 40 is the ceiling; `<br>` breaks a cell into
# runs, so a long cell that is laid out in short lines passes, which is the behaviour wanted.
CELL_RUN = 40


def table_runs(text):
    """Every stretch of words a reader meets without a line break, inside a table cell."""
    rows, out = [], []
    for line in text.splitlines():
        s = line.strip()
        if not s.startswith('|'):
            continue
        if re.fullmatch(r'\|[-: |]+\|', s):
            continue
        rows.append(s)
    for s in rows:
        for cell in s.strip('|').split('|'):
            for run in re.split(r'<br\s*/?>', cell):
                out.append(' '.join(run.split()))
    return out


def pages():
    for f in sorted(ROOT.rglob('*.qmd')):
        if SKIP_DIRS & set(f.relative_to(ROOT).parts):
            continue
        yield f


def drawings():
    """The diagrams, which ship and whose labels a reader reads as prose.

    Two directories, named rather than walked: `artefacts` is in SKIP_DIRS because everything
    else under it is a binary or a note, and `static/diagrams` holds the playbook's own. Both
    the draw.io source and the SVG render are read. The two carry the same words, so a mark
    appears twice and is reported twice, which is right: both files go to NHSBSA."""
    for d in (ROOT / 'artefacts' / 'service-design', ROOT / 'static' / 'diagrams'):
        for f in sorted(d.rglob('*')):
            if f.suffix in ('.drawio', '.svg'):
                yield f


def main():
    scanned, drawn, skipped = 0, 0, []
    curly, dashes = [], []
    for f in pages():
        rel = str(f.relative_to(ROOT))
        if f.name in EXCLUDED:
            skipped.append(f.name)
            continue
        scanned += 1
        text = f.read_text(encoding='utf-8')
        for n, line in enumerate(text.splitlines(), 1):
            for m in CURLY.finditer(line):
                curly.append((rel, n, line.strip()[:72]))
            for m in EM_DASH.finditer(line):
                dashes.append((rel, n, line.strip()[:72]))

    for f in drawings():
        rel = str(f.relative_to(ROOT))
        drawn += 1
        for n, line in enumerate(f.read_text(encoding='utf-8').splitlines(), 1):
            for m in CURLY.finditer(line):
                curly.append((rel, n, line.strip()[:72]))
            for m in EM_DASH.finditer(line):
                dashes.append((rel, n, line.strip()[:72]))

    talking_down, heavy = [], []
    for f in pages():
        rel = str(f.relative_to(ROOT))
        text = f.read_text(encoding='utf-8')
        low = text.lower()
        for phrase in PATRONISING:
            i = low.find(phrase)
            if i >= 0:
                talking_down.append('%s: %r. It corrects an instinct the reader has not shown, '
                                    'or comments on the playbook at them. Say the rule instead'
                                    % (rel, ' '.join(text[max(0, i - 24):i + len(phrase) + 20].split())))
        for run in table_runs(text):
            if len(run.split()) > CELL_RUN:
                heavy.append('%s: a table cell runs %d words without a break. Lead with the '
                             'deciding phrase and put the detail after a <br>, or take it out of '
                             'the table: %r'
                             % (rel, len(run.split()), run[:72]))
    if talking_down:
        fail.append('%d phrase(s) talk down to the reader:' % len(talking_down))
        fail.extend('    ' + x for x in sorted(set(talking_down)))
    if heavy:
        fail.append('%d table cell(s) are too long to read in a column:' % len(heavy))
        fail.extend('    ' + x for x in sorted(set(heavy)))

    broken = []
    for f in pages():
        rel = str(f.relative_to(ROOT))
        for m in FIG_ALT.finditer(f.read_text(encoding='utf-8')):
            if '"' in m.group(1):
                broken.append((rel, m.group(1)[:66]))
    if broken:
        fail.append('%d fig-alt value(s) carry a straight double quote, which ends the attribute. '
                    'The image then renders with no alt text at all. Nest with single quotes:'
                    % len(broken))
        for rel, value in broken[:8]:
            fail.append('      %s  %s' % (rel, value))

    inward = []
    for f in pages():
        if f.name in EXCLUDED:
            continue          # a page of JavaScript, whose comments are for whoever maintains it
        rel = str(f.relative_to(ROOT))
        for n, line in enumerate(f.read_text(encoding='utf-8').splitlines(), 1):
            for m in INWARD.finditer(line):
                inward.append((rel, n, m.group(0), line.strip()[:64]))
    if inward:
        fail.append('%d place(s) where a page talks to whoever is editing it rather than to '
                    'whoever is reading it. A playbook for analysts names no file path, no build '
                    'script and no task number:' % len(inward))
        for rel, n, hit, line in inward[:8]:
            fail.append('      %s:%d  %s  |  %s' % (rel, n, hit, line))

    generated = sorted({rel for rel, _, _ in curly + dashes
                        if rel.endswith(('.drawio', '.svg'))})
    if curly:
        fail.append('%d curly quotation mark(s) or apostrophe(s) in prose. The playbook uses '
                    'straight ones throughout, and a mix of the two in a document that quotes '
                    'standards reads as carelessness:' % len(curly))
        for rel, n, line in curly[:10]:
            fail.append('      %s:%d  %s' % (rel, n, line))
        if len(curly) > 10:
            fail.append('      ... and %d more' % (len(curly) - 10))
    if dashes:
        fail.append('%d em dash(es) in prose. The delivery does not use them:' % len(dashes))
        for rel, n, line in dashes[:10]:
            fail.append('      %s:%d  %s' % (rel, n, line))
    if generated:
        fail.append('%d of the files above %s a drawing. An .svg is a render: fix the .drawio '
                    'beside it and render again, never the .svg. A .drawio may itself be written '
                    'by a script, in which case editing it is undone by the next build, so look '
                    'for its name under build/ before changing it.'
                    % (len(generated), 'is' if len(generated) == 1 else 'are'))

    # Assertion 5. A check that scanned nothing passes, and says nothing.
    if scanned < 10:
        fail.append('only %d page(s) were scanned, which is fewer than the playbook has. A pass '
                    'here would mean the scan missed the pages, not that the pages are clean'
                    % scanned)
    if drawn < 36:
        fail.append('only %d drawing(s) were scanned, which is fewer than the delivery ships. A '
                    'pass here would mean the walk missed them, not that they are clean' % drawn)
    for name in EXCLUDED:
        hits = [f for f in ROOT.rglob(name) if not (SKIP_DIRS & set(f.relative_to(ROOT).parts))]
        if not hits:
            fail.append('%s is excluded by name and is not in the repository. Either it was '
                        'renamed, in which case its curly characters are now unchecked, or the '
                        'exclusion is dead and should go' % name)

    if fail:
        print('house voice FAILED')
        for f in fail:
            print(('  X   %s' % f) if not f.startswith('    ') else f)
        sys.exit(1)
    print('  ok  %d page(s) and %d drawing(s) scanned, no curly quotation marks or apostrophes'
          % (scanned, drawn))
    print('  ok  no em dashes')
    print('  ok  no fig-alt value is cut short by a quote inside it')
    print('  ok  no page names a file path, a build script or a task')
    print('  ok  no phrase that talks down to the reader, over %d listed shape(s)'
          % len(PATRONISING))
    print('  ok  no table cell runs more than %d words without a break' % CELL_RUN)
    for name in skipped:
        print('  --  %s not scanned: %s' % (name, EXCLUDED[name]))


if __name__ == '__main__':
    main()
