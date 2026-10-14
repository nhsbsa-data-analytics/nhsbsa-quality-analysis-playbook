"""Check 32: no wide table leaves its column widths to chance.

A pipe table says how wide each column should be through the dash counts in its separator row.
Pandoc turns those counts straight into percentages on a `<colgroup>`, and a separator written
`|---|---|---|---|---|` says every column is a fifth of the page.

That is almost never what the table means. Measured in the browser on 30 September 2026, every
journey table in the playbook gave 187px to the column holding one tick box and the same 187px to
the column holding the sentence a reader is there to read, which wrapped at 2.3 words a line. The
widths are not a style preference: a route table that reads two words at a time is a route table
people stop following, and the same colgroup carries into the Word copy.

So: a table with four or more columns states its widths. Three columns or fewer are left alone,
because the browser's own distribution is reasonable when there are few enough of them and forcing
a width there would be fussier than the problem.

What counts as stating them is that the dash counts are not all equal. The check does not police
which widths were chosen, because that is a judgement about the content. It polices only that
somebody made the choice.
"""
import pathlib, re, sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
# One copy now. This repository is the playbook.
COPIES = [ROOT]
SEP = re.compile(r'^\s*\|(?:\s*:?-{2,}:?\s*\|)+\s*$')
MIN_COLS = 4

fail, checked, weighted = [], 0, 0
for copy in COPIES:
    if not copy.is_dir():
        continue
    for p in sorted(copy.rglob('*.qmd')):
        if '_site' in p.parts or 'docs' in p.parts:
            continue
        lines = p.read_text(encoding='utf-8').split('\n')
        for i, line in enumerate(lines):
            if not SEP.match(line):
                continue
            widths = [len(c.strip()) for c in line.strip().strip('|').split('|')]
            if len(widths) < MIN_COLS:
                continue
            checked += 1
            if len(set(widths)) == 1:
                head = lines[i - 1].strip()[:64] if i else '?'
                fail.append('%s line %d: %d columns, all %d dashes. "%s"'
                            % (p.relative_to(copy.parent), i + 1, len(widths), widths[0], head))
            else:
                weighted += 1

print('  %d table(s) of %d columns or more across %d playbook copies'
      % (checked, MIN_COLS, sum(1 for c in COPIES if c.is_dir())))
print()
if fail:
    print('FAIL: %d table(s) leave their column widths to pandoc' % len(fail))
    for f in fail:
        print('  X   %s' % f)
    print()
    print('  Weight the dashes in the separator row. The counts become percentages, so a row')
    print('  reading |----------|------|------------------|--------------|--| gives its columns')
    print('  10, 6, 18, 14 and 2 per cent of what they add up to.')
    raise SystemExit(1)
print('PASS: all %d wide tables state their column widths' % weighted)
