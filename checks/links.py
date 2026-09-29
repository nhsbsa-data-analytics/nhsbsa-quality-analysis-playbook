"""Check that every link in the playbook goes somewhere.

    python3 checks/links.py
    python3 checks/links.py --online

The playbook is a cross-referenced site with three hundred internal links and sixty citations, and
a link that has quietly died is a defect a reader finds before we do. Two kinds were found by
measurement on 27 September 2026: a citation for the GRADE scale that had 404'd, and a reference
carried over from another playbook that was still on plain http.

Neither is visible in a render. The page builds, the link is blue, and it goes nowhere.

This reads the source rather than the built site, so it needs neither Quarto nor a render. The
offline part always runs and needs nothing at all. The liveness part needs the network, so it is
opt-in behind --online.

A 403 is reported but not failed. Several of the hosts cited here refuse an automated HEAD or GET,
and a 403 usually means a bot block rather than a dead page, so failing on it would train people
to ignore the check. A 404, or a name that does not resolve, is a real failure.
"""
import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
# The same file sits in the release repository, where the playbook is the repository rather than a
# directory inside it. CONTRIBUTE.md exists only there and held two of the links this was written
# for, so the check has to reach it.
PB = ROOT / 'playbook' if (ROOT / 'playbook').is_dir() else ROOT
# Built output, the review pack, and the Quarto extension are not the playbook's own prose.
SKIP = ('docs', 'review', '_extensions', '_site', '.git', '.quarto')

# Markdown links, but not images: an image with a missing file is check 18's business.
LINK = re.compile(r'(?<!!)\[([^\]\n]*)\]\(([^)\s]+)(?:\s+"[^"]*")?\)')
# Quarto's explicit identifier, as in `## Phase 1 {#phase-1}`.
EXPLICIT = re.compile(r'\{#([A-Za-z0-9_-]+)[^}]*\}')
HEADING = re.compile(r'^#{1,6}\s+(.*?)\s*$', re.M)

fail = []
broken, insecure, anchorless = [], [], []
pages = sorted(f for f in list(PB.rglob('*.qmd')) + list(PB.rglob('*.md'))
               if not any(part in SKIP for part in f.relative_to(PB).parts))


def slug(heading):
    """Approximate Quarto's heading identifier: lowercase, punctuation out, spaces to hyphens."""
    text = EXPLICIT.sub('', heading)
    text = re.sub(r'`([^`]*)`', r'\1', text)
    text = re.sub(r'\[([^\]]*)\]\([^)]*\)', r'\1', text)
    text = re.sub(r'[*_]', '', text).strip().lower()
    text = re.sub(r'[^a-z0-9\s-]', '', text)
    return re.sub(r'\s+', '-', text).strip('-')


def anchors(path):
    text = path.read_text(encoding='utf-8')
    found = set(EXPLICIT.findall(text))
    for heading in HEADING.findall(text):
        s = slug(heading)
        if s:
            found.add(s)
    return found


targets, anchors_seen, external = 0, 0, {}
for f in pages:
    rel = f.relative_to(ROOT)
    for text, target in LINK.findall(f.read_text(encoding='utf-8')):
        if target.startswith('http://'):
            insecure.append('%s: %r is on plain http, which a government site should not ship: %s'
                            % (rel, text, target))
            continue
        if target.startswith('https://'):
            external.setdefault(target, set()).add(str(rel))
            continue
        if target.startswith(('mailto:', 'tel:')):
            continue
        path, _, frag = target.partition('#')
        # A leading slash is the site root, which is the Quarto project directory. The shared
        # partials are written that way on purpose: a partial is included into pages at different
        # depths, so a relative link out of one would be right on some pages and wrong on others.
        # Quarto rewrites these into the correct relative path for each page it renders.
        if path.startswith('/'):
            page = PB / path.lstrip('/')
        elif path:
            page = f.parent / path
        else:
            page = f
        if path:
            targets += 1
            if not page.exists():
                broken.append('%s: %r points at %s, which is not in the repository'
                              % (rel, text, target))
                continue
        if frag and page.suffix in ('.qmd', '.md') and page.exists():
            anchors_seen += 1
            if frag not in anchors(page):
                anchorless.append('%s: %r points at #%s on %s, and no heading there makes '
                                  'that anchor'
                                  % (rel, text, frag, page.resolve().relative_to(ROOT)))

print('    %s %-52s %s' % ('ok ' if not broken else 'X  ',
                           'every internal link resolves',
                           '%d links across %d pages' % (targets, len(pages))))
print('    %s %-52s %s' % ('ok ' if not anchorless else 'X  ',
                           'every anchor is made by a heading on its page',
                           '%d cross-page anchors' % anchors_seen))
print('    %s %-52s %s' % ('ok ' if not insecure else 'X  ',
                           'nothing is linked over plain http',
                           '%d external links, all https' % len(external)))
fail += broken + anchorless + insecure

if '--online' in sys.argv:
    import concurrent.futures
    import os
    import ssl
    import urllib.error
    import urllib.request

    bundle = '/root/.ccr/ca-bundle.crt'
    ctx = ssl.create_default_context(cafile=bundle) if os.path.exists(bundle) \
        else ssl.create_default_context()
    handlers = [urllib.request.HTTPSHandler(context=ctx)]
    proxy = os.environ.get('HTTPS_PROXY') or os.environ.get('https_proxy')
    if proxy:
        handlers.append(urllib.request.ProxyHandler({'https': proxy, 'http': proxy}))
    opener = urllib.request.build_opener(*handlers)
    opener.addheaders = [('User-Agent', 'Mozilla/5.0 (playbook link check)')]

    def probe(url):
        for method in ('HEAD', 'GET'):
            try:
                with opener.open(urllib.request.Request(url, method=method), timeout=30) as r:
                    return url, r.status
            except urllib.error.HTTPError as e:
                if method == 'HEAD' and e.code in (403, 405, 501):
                    continue
                return url, e.code
            except Exception as e:
                if method == 'HEAD':
                    continue
                return url, type(e).__name__
        return url, 'unreachable'

    refused, dead = 0, 0
    with concurrent.futures.ThreadPoolExecutor(max_workers=12) as pool:
        for url, status in pool.map(probe, sorted(external)):
            if isinstance(status, int) and 200 <= status < 300:
                continue
            if status == 403:
                refused += 1
                continue
            dead += 1
            fail.append('%s answers %s, and it is cited on %s'
                        % (url, status, ', '.join(sorted(external[url]))))
    print('    %s %-52s %s'
          % ('ok ' if not dead else 'X  ', 'every citation is still there',
             '%d checked, %d refused an automated request' % (len(external), refused)))
else:
    print('    -   %-52s %s' % ('citations not checked for liveness',
                                'pass --online to check them'))

if fail:
    print()
    for f in sorted(set(fail)):
        print('  ' + f)
    print()
    print('FAIL')
    sys.exit(1)
print()
print('PASS: every link in the playbook resolves')
