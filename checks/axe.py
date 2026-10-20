"""Run an accessibility engine over every built page, and fail on anything it finds.

    quarto render
    python3 checks/axe.py

`accessibility.py` beside this file checks the things this site's own engineering can get wrong:
the contrast pairs it chose, the skip link, the focus indicator, the collapsible sidebar, the
scrollable tables. Those were written by reading the success criteria and then testing for them,
which catches what the author thought to test for.

This catches what nobody thought of. It runs axe-core over the built site: an ARIA attribute
pointing at an id that does not exist, a control with no accessible name, a landmark nested where
it cannot be. It found three diagrams shipping with no alternative text at all, because a straight
quotation mark inside a `fig-alt` closes the attribute early and Quarto then emits no attribute.
Nothing written by hand had noticed, and nothing written by hand would have.

Scope is WCAG 2.0, 2.1 and 2.2 at A and AA, which is the line the accessibility statement commits
to. Axe's own `best-practice` rules are deliberately excluded: they are advice rather than
conformance, and a suite that fails on advice is a suite somebody switches off. Three of them are
open on this site and are named below, so that excluding them is a decision on the record.

Each page is run at three window sizes: a laptop (1280 by 900), a phone (375 by 667) and a phone
at 400 percent zoom (320 by 256). The phone layout is a different page: the sidebar becomes a
drawer, the tables scroll inside a box, the menu opens in the page. A violation that exists
only there, such as a scrolling box no keyboard can reach, is invisible at laptop width.

Every `<details>` is opened before the engine runs, because a diagram's text description is the
accessible alternative to the picture and a closed disclosure hides it.

Axe finds roughly a third to a half of WCAG issues by machine. It cannot judge whether alternative
text is *right*, whether a heading describes what is under it, or whether a route makes sense to
somebody using a screen reader. Passing this is necessary and is not sufficient, and
`accessibility.qmd` says so in its own words.

Needs playwright and a Chromium. The engine is cached under `checks/.cache/` and fetched once;
without a network and without the cache this says so and stops, because a green tick from a test
that did not run is worse than a red one.
"""
import json, os, pathlib, subprocess, sys, urllib.request

ROOT = pathlib.Path(__file__).resolve().parent.parent
# AXE_SITE points the check at a render made somewhere else, so that a change can be proved
# without rebuilding docs/ under anything that is reading it.
DOCS = pathlib.Path(os.environ['AXE_SITE']) if os.environ.get('AXE_SITE') else ROOT / 'docs'
CACHE = ROOT / 'checks' / '.cache'
AXE = CACHE / 'axe.min.js'
AXE_URL = 'https://cdnjs.cloudflare.com/ajax/libs/axe-core/4.10.2/axe.min.js'

TAGS = ['wcag2a', 'wcag2aa', 'wcag21a', 'wcag21aa', 'wcag22aa']

# Axe best-practice rules that fire here. Not conformance failures, recorded so that leaving them
# is a decision rather than an oversight:
#   landmark-no-duplicate-banner, landmark-unique  Quarto nests a navbar inside the page header,
#       so two elements resolve to the banner landmark. Fixing it means rewriting Quarto's own
#       page template.
#   empty-table-header  the contents table's first column holds section numbers and has no
#       heading, which is what it should be.

if not DOCS.is_dir():
    print('FAIL: no built site. Run: quarto render')
    sys.exit(1)

if not AXE.exists():
    CACHE.mkdir(parents=True, exist_ok=True)
    try:
        with urllib.request.urlopen(AXE_URL, timeout=30) as r:
            AXE.write_bytes(r.read())
        print('  fetched the engine into %s' % AXE.relative_to(ROOT))
    except Exception as e:
        print('FAIL: no accessibility engine, and it could not be fetched: %s' % e)
        print('      Put axe-core at %s and run this again.' % AXE.relative_to(ROOT))
        sys.exit(1)

PAGES = sorted(DOCS.rglob('*.html'))
if not PAGES:
    print('FAIL: no built pages. Run: quarto render')
    sys.exit(1)

RUNNER = r'''
import asyncio, json, pathlib, sys
from playwright.async_api import async_playwright
AXE = pathlib.Path(sys.argv[1]).read_text()
TAGS = json.loads(sys.argv[2])
PAGES = sys.argv[3:]
VIEWPORTS = [(1280, 900), (375, 667), (320, 256)]
async def main():
    out = {}
    async with async_playwright() as pw:
        b = await pw.chromium.launch(executable_path=__import__('os').environ.get(
            'PLAYWRIGHT_CHROMIUM', '/opt/pw-browsers/chromium'))
        for path in PAGES:
          for w, h in VIEWPORTS:
            p = await b.new_page(viewport={'width': w, 'height': h})
            await p.goto(pathlib.Path(path).resolve().as_uri())
            await p.wait_for_timeout(500)
            await p.evaluate("() => document.querySelectorAll('details')"
                             ".forEach(d => d.open = true)")
            await p.evaluate(AXE)
            res = await p.evaluate(
                "async (tags) => await axe.run(document, {runOnly: {type: 'tag', values: tags}})",
                TAGS)
            out['%s@%dx%d' % (path, w, h)] = [
                {'id': v['id'], 'impact': v['impact'], 'help': v['help'],
                 'nodes': [n['html'][:150] for n in v['nodes'][:3]]}
                for v in res['violations']]
            await p.close()
        await b.close()
    print(json.dumps(out))
asyncio.run(main())
'''

runner = CACHE / 'axe-runner.py'
CACHE.mkdir(parents=True, exist_ok=True)
runner.write_text(RUNNER)
proc = subprocess.run([sys.executable, str(runner), str(AXE), json.dumps(TAGS)]
                      + [str(p) for p in PAGES], capture_output=True, text=True)
if proc.returncode != 0:
    print('FAIL: the engine could not run:\n%s' % proc.stderr[-1500:])
    sys.exit(1)

try:
    results = json.loads(proc.stdout.strip().splitlines()[-1])
except Exception:
    print('FAIL: the engine returned nothing readable:\n%s' % proc.stdout[-800:])
    sys.exit(1)

fail, clean = [], 0
for key, violations in sorted(results.items()):
    path, size = key.rsplit('@', 1)
    rel = pathlib.Path(path).relative_to(DOCS).as_posix() + ' @ ' + size
    if not violations:
        clean += 1
        continue
    for v in violations:
        fail.append((rel, v))

print('  %d page(s) at 3 window sizes, %d runs through axe-core, WCAG 2.0, 2.1 and 2.2 at A and AA'
      % (len(PAGES), len(results)))
print('  %d clean' % clean)
print()
if fail:
    print('FAIL: %d violation(s) across %d page(s) and window size(s)' % (len(fail), len({r for r, _ in fail})))
    for rel, v in fail:
        print('  %-56s [%s] %s' % (rel, v['impact'], v['id']))
        print('      %s' % v['help'])
        for n in v['nodes']:
            print('        %s' % n)
    sys.exit(1)
print('PASS: no WCAG A or AA violation on any page, with every diagram description open')
