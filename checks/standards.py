#!/usr/bin/env python3
"""Check that the playbook still carries what it claims to carry from the standards.

    python3 checks/standards.py

Standard library only.

Four assertions:

  1. the guidance pages carry no citation markers, because the compliance evidence is in one place
  2. every clause named in the appendix mapping points at a page that exists
  3. the mapping covers every standard the playbook is built on
  4. the three substantive GovS 010 requirements are stated somewhere in the playbook

**Why the evidence is in one place.** The guidance used to carry seventy-two citation markers
through its prose. A reader working through a phase met a superscript every few sentences, which is
how an academic paper reads and not how a toolkit reads. NHSBSA asked for the markers out and the
compliance kept, so the mapping in the appendix is now the whole of it: every clause of GovS 010,
the AQuA Book and the NHSBSA documents, and the page that meets it, read as one table rather than
assembled by a reader from footnotes across eleven pages.

That makes assertion 1 load-bearing. If a marker creeps back into a guidance page, the evidence is
in two places and they will disagree.

**What this cannot do.** It cannot tell whether the prose on the page actually satisfies the clause.
No check can. What it can do is make sure the claim is not empty: that the page named exists, that
every standard the playbook rests on appears, and that the three requirements GovS 010 places on
NHSBSA itself are still written down somewhere. A restructure once removed eleven citations, eight
of them carrying obligations, while the suite stayed green and the appendix went on claiming
coverage of clauses whose text had gone.
"""
import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
PB = ROOT / 'guidance'
# The mapping was one section of a single long appendix page, sliced out between its own
# heading and the next. The appendices are a page each now, so the whole of this file is the
# mapping and there is no following heading to slice against.
MAPPING_PAGE = PB / '09-resources' / 'r14-meeting-the-standards.qmd'

# What the playbook is built on. Each has to appear as a group in the mapping.
STANDARDS = ('GovS 010', 'AQuA Book', 'Code of Practice', 'NHSBSA')

# The three requirements GovS 010 places on the organisation rather than on a piece of work.
SUBSTANTIVE = (
    ('a senior officer accountable', 'NHSBSA shall have a senior officer accountable for analysis'),
    ('shall be assured', 'all analysis shall be assured'),
    # Both halves, in one sentence: defining the roles and assigning them to people are one
    # requirement, and a page that states only the first has not met it. Matching on a single
    # fixed phrase was too brittle: removing the fifth role reworded the sentence that happened
    # to carry "defined and assigned" and the requirement read as gone when it was still there.
    (r'defin\w*[^.]{0,80}governance[^.]{0,60}assign|assign\w*[^.]{0,80}governance[^.]{0,60}defin',
     'analytical roles shall be defined and assigned'),
)

fail = []


def main():
    global fail
    pages = {f: f.read_text(encoding='utf-8') for f in sorted(PB.rglob('*.qmd'))}
    whole = '\n'.join(pages.values())
    if not MAPPING_PAGE.exists():
        print('standards FAILED')
        print('  X   %s is not there, so there is no mapping to check and nothing below this '
              'is testing anything' % MAPPING_PAGE.relative_to(ROOT))
        sys.exit(1)
    ap = MAPPING_PAGE.read_text(encoding='utf-8')

    # Assertion 1. No citation marker outside the appendix. A marker at the start of a line is a
    # definition; anywhere else it is a reference, whether or not a colon follows it.
    stray = []
    for f, t in pages.items():
        if f.parent.name == '09-resources':
            continue
        for m in re.finditer(r'(?<!^)\[\^src-[\w-]+\]', t, re.M):
            stray.append('%s %s' % (f.relative_to(ROOT), m.group(0)))
    if stray:
        fail.append('%d citation marker(s) in the guidance. The compliance evidence lives in the '
                    'appendix mapping, and a marker in the prose puts it in two places:'
                    % len(stray))
        fail += ['      ' + s for s in stray[:8]]

    # Assertion 2. Every page the mapping names is a page that exists.
    rows = re.findall(r'^\|(?! Clause)(?!-)(.+?)\|(.+?)\|\s*$', ap, re.M)
    missing = []
    for clause, cell in rows:
        for target in re.findall(r'\]\(\.\./([^)#]+)', cell):
            if not (PB / target).exists():
                missing.append('%s points at %s, which is not a page' % (clause.strip(), target))
    if missing:
        fail.append('%d mapping row(s) point at a page that does not exist:' % len(missing))
        fail += ['      ' + m for m in missing[:8]]
    if len(rows) < 25:
        fail.append('the mapping has %d row(s). It had more, so either it has been cut or this '
                    'is not reading it' % len(rows))

    # Assertion 3. Every standard appears.
    for s in STANDARDS:
        if s not in ap:
            fail.append('the mapping does not mention %s, which the playbook is built on' % s)

    # Assertion 4. The three organisational requirements are still stated.
    for pattern, what in SUBSTANTIVE:
        if not re.search(pattern, whole, re.I):
            fail.append('the playbook no longer says that %s, which is one of the three '
                        'requirements GovS 010 places on NHSBSA itself' % what)

    if fail:
        print('standards FAILED')
        for f in fail:
            print(('  X   %s' % f) if not f.startswith('    ') else f)
        sys.exit(1)
        rows = re.findall(r'^\|(?! Clause)(?!-)(.+?)\|(.+?)\|\s*$', ap, re.M)
    print('  ok  no citation marker in the guidance, so the evidence is in one place')
    print('  ok  %d clause(s) mapped, every one naming a page that exists' % len(rows))
    print('  ok  all %d standard(s) the playbook rests on appear in the mapping' % len(STANDARDS))
    print('  ok  the three requirements GovS 010 places on NHSBSA are all still stated')


if __name__ == '__main__':
    main()
