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
# Directories that are not playbook pages. docs/ is build output, review/ is written to a
# reviewer of this delivery, and elearn/ is the e-learning deliverable, which has its own
# structure and its own numbering and is not shipped in the playbook package. The assertions
# below are about the playbook's own prose, and applying them to any of these reports a defect
# in a document the rule was never written for.
SKIP = ('docs', 'review', 'elearn', '_extensions', '_site', '.git', '.quarto')

# Markdown links, but not images: an image with a missing file is check 18's business.
LINK = re.compile(r'(?<!!)\[([^\]\n]*)\]\(([^)\s]+)(?:\s+"[^"]*")?\)')
# A link written as HTML rather than as markdown. The front page builds its phase cards and
# its role cards in a raw `{=html}` block, because they are a list of cards rather than a
# list of links, and those hrefs end in `.html` because they are not going through Quarto's
# link rewriting. Reading only markdown links left six of them pointing at pages the
# restructure to five phases had deleted: the front page offered a reader Phase 1 to Phase 4
# and getting help, and every one of them was a 404. The accessibility check noticed, two
# criteria away, because two links with one name went to two places and one of the two did
# not exist.
HTML_LINK = re.compile(r'<a\s[^>]*href="([^"]+)"[^>]*>(.*?)</a>', re.S)
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
    body = f.read_text(encoding='utf-8')
    found = list(LINK.findall(body))
    # An .html href in a source file is a built-site path, so it is resolved against the source
    # tree by mapping it back to the .qmd it is rendered from.
    for target, text in HTML_LINK.findall(body):
        found.append((re.sub(r'<[^>]+>', '', text).strip(),
                      re.sub(r'(^|/)index\.html$', r'\1index.qmd', target)
                      if target.endswith('index.html') else
                      re.sub(r'\.html($|#)', r'.qmd\1', target)))
    for text, target in found:
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

    # A machine that reaches the internet through a proxy needs that proxy's certificate
    # authority, and says where it is in the environment. Reading it from there rather than from
    # a path written in: a literal path is correct on the one machine it was typed on, wrong
    # everywhere else, and a detail of a build machine in a file NHSBSA receives. Without any of
    # these set, the system trust store is used, which is right on a machine with no proxy.
    bundle = next((v for v in (os.environ.get('SSL_CERT_FILE'),
                               os.environ.get('REQUESTS_CA_BUNDLE'),
                               os.environ.get('CURL_CA_BUNDLE'),
                               os.environ.get('NODE_EXTRA_CA_CERTS'))
                   if v and os.path.exists(v)), None)
    ctx = ssl.create_default_context(cafile=bundle) if bundle \
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

# ---------------------------------------------------------------------------- 4
# A section number in prose is a link that nothing checks. When the playbook went
# from fifteen sections to eleven, every one of them silently started pointing at
# the wrong page, or at no page at all, and the suite passed. Cross-references
# are links now, and this keeps them that way: a bare "section 6" is only allowed
# where it names a clause of a standard, a numbered policy, or the project
# record's own numbered sections.
NAMES_A_SOURCE = re.compile(
    r'(GovS\s*0?10|AQuA\s*Book|Code of Practice|Magenta Book|Green Book|RIGOUR'
    r'|Policy v?\d|Assurance Journey|public sector bodies|project record'
    r'|completes sections|directory name carries the number)', re.I)
# a dotted clause (6.10, 1.3.5) is a standard's numbering, never the playbook's
BARE = re.compile(r'\b[Ss]ections?\s+(\d+)(?!\s*\.\s*\d|\.\d|\s*and\s+\d+\.\d)')

numbered = []
for page in pages:
    # Working notes are excluded from the package by shape, so skip them by the
    # same shape rather than by name: an all-capitals .md that is not one of the
    # two the package ships.
    if re.fullmatch(r'(?!README\.md|CONTRIBUTE\.md)[A-Z][A-Z0-9_]*\.md', page.name):
        continue
    lines = page.read_text().split('\n')
    for n, line in enumerate(lines, 1):
        # Prose wraps, so "section" can sit at the end of one line with its number at the
        # start of the next. Read each line together with the one below it and keep only the
        # matches that start on this line, so a wrapped reference is caught once and here.
        below = lines[n] if n < len(lines) else ''
        # A line ending in "section" above a numbered list item is not a cross-reference: the
        # "1." below it is the list marker. Those two lines are not joined.
        if re.match(r'\s*\d+\.\s', below):
            below = ''
        window = line + ' ' + below
        for m in BARE.finditer(window):
            if m.start() >= len(line) + 1:
                continue
            # what the number belongs to can sit either side of it, and a citation
            # wraps, so read the window and the line above it
            if NAMES_A_SOURCE.search((lines[n - 2] if n > 1 else '') + ' ' + window):
                continue
            numbered.append('%s:%d names a playbook section by number (%r). Link to the page '
                            'instead, so a restructure cannot leave it pointing nowhere'
                            % (page.relative_to(PB), n, m.group(0)))
print('    %s %-52s %s'
      % ('ok ' if not numbered else 'X  ', 'no cross-reference by section number',
         '%d page(s) read' % len(pages)))
fail.extend(numbered)

# ---------------------------------------------------------------------------- 5
# A guidance page that is not in the sidebar is reachable only by a link from another page.
# It misses the sidebar, the Guidance menu, the offline PDF and the Word copy, and nothing
# says so: build-pdf.py checks that every page the sidebar names was read, which is the
# opposite direction. Splitting the appendices and the Resources page added fifteen pages to
# that list by hand, which is exactly the edit this catches when somebody forgets it.
nav = (ROOT / '_quarto.yml').read_text(encoding='utf-8')
sidebar = nav[nav.index('  sidebar:'):]
listed = set(re.findall(r'[\w./-]+\.qmd', sidebar))
orphans = []
for page in sorted((PB / 'guidance').rglob('*.qmd')):
    rel = page.relative_to(ROOT).as_posix()
    if '_partials' in page.parts:          # included, never rendered on its own
        continue
    if rel not in listed:
        orphans.append(rel)
print('    %s %-52s %s'
      % ('ok ' if not orphans else 'X  ', 'every guidance page is in the sidebar',
         '%d page(s) listed' % len([x for x in listed if x.startswith('guidance/')])))
if orphans:
    fail.extend('%s is rendered but is in neither the sidebar nor a band, so it is missing '
                'from the sidebar, the offline PDF and the Word copy' % o for o in orphans)

if fail:
    print()
    for f in sorted(set(fail)):
        print('  ' + f)
    print()
    print('FAIL')
    sys.exit(1)
print()
print('PASS: every link in the playbook resolves')
