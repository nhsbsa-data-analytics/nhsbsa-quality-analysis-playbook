"""The search finds the words NHSBSA uses, and every synonym still earns its place.

    quarto render
    python3 checks/search.py

`search.qmd` carries a map from what a reader types to what this playbook calls it. It exists
because the playbook writes most of its terms out in full, so the abbreviation everybody actually
says returned nothing at all. Measured against the index on 5 October 2026, before the map:
`SRO`, `PQ`, `HoP`, `AQAL`, `SDC`, `V&V`, `tiering` and `signoff` each returned zero results, and
`IG` returned 104 pages, every one of them from matching inside des-IG-n, d-IG-ram and
s-IG-nificant.

Two things are checked, and both are about the map going stale rather than about it being wrong
today.

**Every phrase on the right still appears in the playbook.** A synonym pointing at a phrase the
playbook no longer uses sends a reader somewhere empty, which is worse than the gap it was added
to close, because the reader now believes they have searched.

**Every entry still changes the answer.** If searching the abbreviation alone finds everything the
synonym would, the entry is dead weight and the next person to read the map has to work out why it
is there. This caught `DPIA` on the day the map was written: the one page using the abbreviation
was the same page writing it out.

The map is strict JSON inside the script so it can be read here without running JavaScript, and
`needle()` is reimplemented below to the same rule the page uses. The two are kept honest by a
third assertion: the rule stated in this file has to still be the one in the page.
"""
import json, pathlib, re, sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
PAGE = ROOT / 'search.qmd'
INDEX = ROOT / 'docs' / 'search.json'

fail = []
src = PAGE.read_text(encoding='utf-8')
m = re.search(r'var ALSO = (\{.*?\n  \});', src, re.S)
if not m:
    print('FAIL: search.qmd no longer carries a readable ALSO map')
    sys.exit(1)
try:
    ALSO = json.loads(m.group(1))
except json.JSONDecodeError as e:
    print('FAIL: the ALSO map is not strict JSON, so this check cannot read it: %s' % e)
    sys.exit(1)

# The page's own rule: a match starts at a word, and a query of three characters or fewer has to
# be the whole word. If the page stops saying this, the measurements below describe a search that
# is not the one shipping.
RULE = 'q.length <= 3 && /^[a-z0-9]+$/i.test(q) ? "\\\\b" : ""'
if RULE not in src:
    print('FAIL: search.qmd no longer matches on word starts the way this check assumes.')
    print('      Update both, or this measures a search that is not shipping.')
    sys.exit(1)

if not INDEX.exists():
    print('FAIL: no built search index at docs/search.json. Run: quarto render')
    sys.exit(1)
index = json.loads(INDEX.read_text(encoding='utf-8'))


def needle(q):
    esc = re.escape(q)
    if not re.match(r'[a-z0-9]', q, re.I):
        return re.compile(esc, re.I)
    end = r'\b' if len(q) <= 3 and re.fullmatch(r'[a-z0-9]+', q, re.I) else ''
    return re.compile(r'\b' + esc + end, re.I)


def pages(q):
    """The pages a query reaches, as a set. Counting instead of comparing sets is what let the
    dead weight assertion below pass on an entry that was dead: it added the two numbers, so any
    synonym with pages of its own made the total bigger whether or not those pages were already
    found by typing the key. Measured on 16 October 2026, "foi" was in that state. It was added
    when the playbook wrote Freedom of Information out in full everywhere; the playbook has since
    started using the abbreviation, so typing it already finds every page the synonym reaches, and
    the entry had become the dead weight this check exists to catch."""
    r = needle(q)
    return {e['href'].split('#')[0] for e in index
            if r.search(e.get('title') or '') or r.search(e.get('section') or '')
            or r.search(e.get('text') or '')}


for key, alts in sorted(ALSO.items()):
    if key != key.lower() or key != ' '.join(key.split()):
        fail.append('"%s" is not lower case and single spaced, so a reader typing it never '
                    'matches the key' % key)
    direct = pages(key)
    via = set()
    for a in alts:
        reach = pages(a)
        if not reach:
            fail.append('"%s" points at "%s", which no page carries any more' % (key, a))
        via |= reach
    if via <= direct:
        fail.append('"%s" reaches no page the bare word does not, so the entry is dead weight'
                    % key)
    print('  %-26s %3d page(s) typed, %3d reached' % (key, len(direct), len(direct | via)))

print()
print('  %d synonym(s) across %d page(s) of index' % (len(ALSO), len(index)))
if fail:
    print()
    print('FAIL: %d problem(s) with the search vocabulary' % len(fail))
    for f in fail:
        print('  %s' % f)
    sys.exit(1)
print('PASS: every synonym points somewhere real and still changes the answer')
