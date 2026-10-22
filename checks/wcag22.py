#!/usr/bin/env python3
"""Check the built site for the WCAG 2.2 failures that a rule engine cannot see.

    quarto render
    python3 checks/wcag22.py

`axe.py` runs a rule engine over every page, and `accessibility.py` tests the engineering this
site chose for itself. Both pass on a site that a keyboard user cannot use on a phone, so this
asserts the things they never looked at. Each assertion below exists because an audit of the built
site found the failure it names, so each of them was seen failing before it was written to pass.

  1.3.1  Info and Relationships   every table has a caption and a header row, and a table's row
                                   labels are row headers, not bold cells
  1.1.1  Non-text Content         no image or icon is announced by the name of its icon set
  2.4.4  Link Purpose             no link is named "Anchor", and none has no name at all
  2.4.1  Bypass Blocks            the skip link is the first stop, and takes a keyboard user into
                                   the main content rather than to the top of the sidebar
  4.1.2  Name, Role, Value        the current page is the page marked as current; the controls
                                   Quarto adds carry roles that exist for them; the navigation
                                   landmarks are named and are not named alike
  1.4.1  Use of Colour            the current page in the sidebar differs by more than its colour;
                                   a link in the footer or in running text is not told apart by
                                   colour alone; a disclosure is shown as one
  2.4.7  Focus Visible            the ring on every kind of control changes at least 3:1 against
         1.4.11, 2.4.13           what it replaced, over an area as large as the control's outline
  2.4.11 Focus Not Obscured       at every Tab stop, on a laptop, a tablet, a phone and a phone at
         2.4.12 (AAA)             400 percent zoom, the focused control is wholly on screen and
                                   nothing fixed is drawn over it
  1.4.10 Reflow                   at 320 by 256, what is fixed or sticky leaves room to read
  1.4.13 Content on Hover         a footnote opens the Sources list and does not float over the text
  2.3.3  Animation (AAA)          with reduced motion asked for, nothing slides or fades
  2.5.8  Target Size (Minimum)    nothing a pointer must hit is under 24 by 24, except in a sentence
  1.4.8  Visual Presentation      no line of prose is longer than 80 characters. The test counts the
         (AAA, claimed)           characters on each rendered line. The earlier test counted widths
                                   of the digit zero, and 80 of those is 93 to 116 ordinary
                                   characters

It needs Playwright and a Chromium. It walks the keyboard on a sample of page types rather than on
every page, because it presses Tab several thousand times; set WCAG22_ALL_PAGES=1 to walk all 44.
"""
import http.server
import os
import pathlib
import re
import socketserver
import sys
import threading

ROOT = pathlib.Path(__file__).resolve().parent.parent
# WCAG22_SITE points the check at a render made somewhere else, so that a change can be proved
# without rebuilding docs/ under anything that is reading it.
DOCS = pathlib.Path(os.environ['WCAG22_SITE']) if os.environ.get('WCAG22_SITE') else ROOT / 'docs'
CHROMIUM = os.environ.get('PLAYWRIGHT_CHROMIUM', '/opt/pw-browsers/chromium')
MAX_CHARS = 80
MIN_TARGET_AA = 24
RING_MIN = 3.0
# Where the keyboard is walked. A page of each kind the site has.
WALK_PAGES = ['index.html', 'guidance/07-deciding-your-assurance-level/check-it-applies.html', 'guidance/analytical-cycle/index.html',
              'guidance/01-engagement-and-scoping/index.html', 'guidance/06-roles/analyst.html',
              'guidance/07-deciding-your-assurance-level/index.html',
              'guidance/09-resources/r5-quality-assurance-statement.html',
              'guidance/09-resources/r19-worked-examples.html',
              'guidance/09-resources/r1-glossary.html', 'search.html', 'accessibility.html']
WALK_VIEWPORTS = [(1280, 720), (768, 1024), (375, 667), (640, 512), (320, 256)]
fail = []
notes = []


def contrast(a, b):
    def lum(c):
        v = [x / 255 for x in c[:3]]
        v = [x / 12.92 if x <= 0.04045 else ((x + 0.055) / 1.055) ** 2.4 for x in v]
        return 0.2126 * v[0] + 0.7152 * v[1] + 0.0722 * v[2]
    la, lb = lum(a), lum(b)
    return (max(la, lb) + 0.05) / (min(la, lb) + 0.05)


# --------------------------------------------------------------------------- what one page says
PAGE_PROBE = r"""() => {
  const q = (s, r = document) => [...r.querySelectorAll(s)];
  const shown = e => !!(e.offsetWidth || e.offsetHeight || e.getClientRects().length);
  const out = {};

  // 1.3.1 tables
  out.tables = q('table').map(t => {
    const cap = t.querySelector(':scope > caption');
    const body = q(':scope > tbody > tr', t);
    const firsts = body.map(r => r.cells[0]).filter(Boolean);
    const boldNode = n => n && n.nodeType === 1 && (/^(STRONG|B)$/.test(n.tagName) ||
      (n.tagName === 'A' && n.querySelector('strong,b') && n.textContent.trim() === (n.querySelector('strong,b').textContent || '').trim()));
    // A cell that names its row: a short piece of text or a link, or a bold label with a description
    // under it. The same two tests _filters/table-headers.lua applies, read back from the page.
    const isLabel = c => {
      if (c.tagName !== 'TD' || c.colSpan !== 1 || c.rowSpan !== 1) return false;
      const text = c.textContent.trim();
      if (!text || c.querySelector('p, ul, ol, table, div')) return false;
      const nodes = [...c.childNodes].filter(n => !(n.nodeType === 3 && !n.textContent.trim()));
      const boldThenBreak = boldNode(nodes[0]) && (nodes.length === 1 || (nodes[1].nodeType === 1 && nodes[1].tagName === 'BR'));
      return boldThenBreak || text.split(/\s+/).length <= 30;
    };
    const headFirst = t.querySelector(':scope > thead th');
    // A table is owed row headers when its header row names the first column and every row opens
    // with a label. One that does not, an empty header cell or a row opening with a sentence, is not.
    const labelled = firsts.length > 0 && firsts.length === body.length && !!headFirst &&
      !!headFirst.textContent.trim() && body.every(r => r.cells.length > 1) && firsts.every(isLabel);
    return {
      caption: !!(cap && cap.textContent.trim()),
      header: !!t.querySelector(':scope > thead th'),
      labelsAreCells: labelled,
      first: (t.previousElementSibling ? t.previousElementSibling.textContent : t.parentElement.textContent).trim().slice(0, 40),
    };
  });

  // headings
  const hs = q('h1,h2,h3,h4,h5,h6').filter(shown);
  out.h1 = hs.filter(h => h.tagName === 'H1').length;
  out.emptyHeading = q('h1,h2,h3,h4,h5,h6').filter(h => shown(h) && !h.textContent.trim()).length;
  let prev = 0; out.skips = [];
  hs.forEach(h => { const l = +h.tagName[1]; if (prev && l > prev + 1) out.skips.push(prev + '>' + l); prev = l; });

  // names: links and images
  const nameOf = a => (a.getAttribute('aria-label') || a.textContent || '').trim() ||
    q('img', a).map(i => i.alt).join('').trim();
  out.linkNames = q('a[href]').filter(shown).map(a => nameOf(a));
  out.iconNames = q('[aria-label]').filter(e => /Icon .* from .*Iconify/i.test(e.getAttribute('aria-label')) && !e.closest('[aria-hidden=true]')).length;
  out.noAlt = q('img').filter(i => i.getAttribute('alt') === null).length;

  // skip link, current page, landmarks
  const skip = q('a').find(a => /skip/i.test(a.textContent) && /#/.test(a.getAttribute('href') || ''));
  out.skip = skip ? { href: skip.getAttribute('href'), first: q('a[href],button,input,summary,[tabindex]').filter(e => e.tabIndex >= 0 && shown(e) || e === skip)[0] === skip } : null;
  const norm = p => p.replace(/\/$/, '/index.html');
  out.current = q('[aria-current]').map(e => ({ tag: e.tagName, cur: e.getAttribute('aria-current'), path: norm(e.pathname || ''), text: e.textContent.trim().slice(0, 30) }));
  out.here = norm(location.pathname);
  out.selfNav = q('.navbar a[href], #quarto-sidebar a[href]').filter(a => !a.hash && !a.matches('[data-bs-toggle]') && !(a.getAttribute('href') || '').endsWith('#') && norm(a.pathname) === norm(location.pathname)).length;
  out.navs = q('nav').filter(n => shown(n) || n.closest('#quarto-sidebar')).map(n => n.getAttribute('aria-label') || n.getAttribute('aria-labelledby') || '');
  out.banners = q('header').filter(h => !h.closest('main, article, section')).filter(h => (h.getAttribute('role') || 'banner') === 'banner' && shown(h)).length;
  out.badRoles = q('button[role=menu], a[role=link][aria-expanded]').length;

  // colour-only: the current sidebar link, footer links, links in prose, summaries
  const act = document.querySelector('#quarto-sidebar a.sidebar-link.active, #quarto-sidebar a[aria-current]');
  if (act) {
    const o = q('#quarto-sidebar a.sidebar-link').find(a => a !== act && !a.classList.contains('active'));
    const sa = getComputedStyle(act), so = o ? getComputedStyle(o) : sa;
    out.sidebarCue = sa.fontWeight !== so.fontWeight || sa.textDecorationLine !== so.textDecorationLine ||
      parseFloat(sa.borderLeftWidth) > parseFloat(so.borderLeftWidth) || sa.backgroundColor !== so.backgroundColor ||
      (getComputedStyle(act, '::before').content !== 'none' && getComputedStyle(act, '::before').content !== 'normal');
  } else out.sidebarCue = null;
  const nact = document.querySelector('.navbar a.nav-link.active');
  if (nact) {
    const o = q('.navbar a.nav-link').find(a => a !== nact && !a.classList.contains('active') && !a.classList.contains('dropdown-toggle') && shown(a));
    out.navCue = getComputedStyle(nact).textDecorationLine !== (o ? getComputedStyle(o).textDecorationLine : 'none');
  } else out.navCue = null;
  // a link to a place on this page, written as a link to the folder: pressing Enter loads the page again
  const strip = x => x.replace(/index\.html$/, '').replace(/\/+$/, '/');
  out.hashRewritten = q('a[href*="#"]').filter(a => a.hash && a.origin === location.origin && strip(a.pathname) === strip(location.pathname) && (a.getAttribute('href') || '').charAt(0) !== '#').length;
  out.footerLinksPlain = q('.nav-footer a').filter(shown).filter(a => getComputedStyle(a).textDecorationLine === 'none').length;
  out.proseLinksPlain = q('main p a[href], main li a[href]').filter(shown).filter(a => getComputedStyle(a).textDecorationLine === 'none' && !a.closest('.nav-link, .pb-cards, .pb-phase-cards, .pb-phases, nav, .step-links, .more-detail') && !a.querySelector('img')).length;
  out.summaries = q('details > summary').filter(shown).map(s => {
    const cs = getComputedStyle(s), b = getComputedStyle(s, '::before'), m = getComputedStyle(s, '::marker');
    const marker = (cs.display === 'list-item' && cs.listStyleType !== 'none') || (b.content && b.content !== 'none' && b.content !== 'normal') || (cs.backgroundImage && cs.backgroundImage !== 'none');
    return marker;
  });

  // the seven diagrams: the link says where it goes and what it shows, the picture only what it shows
  out.diagrams = q('a.diagram-open').map(a => {
    const img = a.querySelector('img'), fig = a.closest('figure');
    const cap = fig && fig.querySelector('figcaption strong');
    return { label: a.getAttribute('aria-label') || '', alt: img ? img.alt : '', title: cap ? cap.textContent.trim() : '' };
  });

  // 1.4.13 footnote popups
  out.popups = q('a.footnote-ref, a[role=doc-noteref]').filter(a => a._tippy || a.hasAttribute('data-tippy-root') || a.getAttribute('aria-describedby')).length;

  // 2.5.8 target size
  out.smallTargets = q('a[href], button, summary, input, select').filter(shown).filter(e => {
    if (e.closest('[aria-hidden=true]') || e.matches('.skip')) return false;
    const r = e.getBoundingClientRect();
    if (r.width >= 24 && r.height >= 24) return false;
    const blk = e.closest('p, li, td, th, blockquote, figcaption, dd');
    if (blk && blk.textContent.trim().length > e.textContent.trim().length + 8) return false;   // inline in a sentence
    return true;
  }).map(e => Math.round(e.getBoundingClientRect().width) + 'x' + Math.round(e.getBoundingClientRect().height) + ' ' + (e.textContent || e.getAttribute('aria-label') || '').trim().slice(0, 30));
  return out;
}"""

LINE_PROBE = r"""() => {
  const q = (s, r = document) => [...r.querySelectorAll(s)];
  const shown = e => !!(e.offsetWidth || e.offsetHeight || e.getClientRects().length);
  const out = {};
  // 1.4.8 line length: characters on each rendered line of prose
  let worst = 0, where = '';
  const rng = document.createRange();
  // Every block of text a reader reads, not only paragraphs and list items: the line under the page
  // title, a table's cells and captions, a figure's caption, the licence line in the footer. A table
  // cell is counted line by line like any other block.
  q('main p, main li, main blockquote, main td, main th, main caption, figcaption, #title-block-header .description, .nav-footer-center').filter(shown).forEach(el => {
    if (el.closest('pre, code, .callout-title, nav, #TOC, summary, table.caption-under-heading') && el.tagName === 'CAPTION') return;   // read out, not drawn
    if (el.closest('pre, code, .callout-title, nav, #TOC, summary')) return;
    if (el.matches('td, th, li') && el.querySelector('p, ul, ol, table')) return;   // the blocks inside are counted
    const w = document.createTreeWalker(el, NodeFilter.SHOW_TEXT);
    const lines = new Map();
    let n;
    while ((n = w.nextNode())) {
      if (n.parentElement.closest('details:not([open])')) continue;
      const t = n.textContent; const re = /\S+/g; let m;
      while ((m = re.exec(t))) {
        rng.setStart(n, m.index); rng.setEnd(n, m.index + m[0].length);
        const r = rng.getClientRects()[0]; if (!r) continue;
        const key = Math.round(r.top / 4);
        lines.set(key, (lines.get(key) || 0) + m[0].length + 1);
      }
    }
    lines.forEach(c => { if (c - 1 > worst) { worst = c - 1; where = el.textContent.trim().slice(0, 40); } });
  });
  out.longest = worst; out.longestAt = where;

  // diagrams: the box is as wide as its drawing wherever the column has room for it, and the hint
  // that says to scroll is shown when the box scrolls and not otherwise
  out.boxes = q('a.diagram-open').filter(shown).map(a => {
    const f = a.closest('figure'), h = f && f.querySelector('.diagram-hint');
    return { w: Math.round(a.getBoundingClientRect().width), fig: Math.round(f.getBoundingClientRect().width),
             scrolls: a.scrollWidth > a.clientWidth + 1, hint: h ? getComputedStyle(h).display !== 'none' : null };
  });

  return out;
}"""

# Every fixed or sticky thing in view, and how much of the screen it takes.
FIXED_PROBE = r"""() => {
  let total = 0; const parts = [];
  document.querySelectorAll('body *').forEach(e => {
    const s = getComputedStyle(e);
    if ((s.position === 'fixed' || s.position === 'sticky') && s.display !== 'none' && s.visibility !== 'hidden') {
      const r = e.getBoundingClientRect();
      if (r.width < 100 || r.height < 10) return;
      if (r.bottom <= 0 || r.top >= innerHeight) return;
      if (e.closest('#quarto-sidebar, #quarto-margin-sidebar, #TOC') || e.matches('.skip')) return;
      const h = Math.min(r.bottom, innerHeight) - Math.max(r.top, 0);
      if (h > 0 && r.top <= 1) { total += h; parts.push((e.id || e.className || e.tagName).toString().slice(0, 30) + ' ' + Math.round(h)); }
    }
  });
  return { total: Math.round(total), parts };
}"""

# One Tab stop: is the focused control wholly on screen, and is anything drawn over it?
STOP_PROBE = r"""() => {
  const e = document.activeElement;
  if (!e || e === document.body) return { body: true };
  const r = e.getBoundingClientRect();
  const vw = innerWidth, vh = innerHeight;
  const label = (e.id || e.tagName.toLowerCase()) + ' ' + (e.textContent || e.getAttribute('aria-label') || '').trim().slice(0, 28);
  if (!r.width || !r.height) return { hidden: true, label };
  const tall = r.height > vh * 0.8;
  // wholly on screen, except a control taller than the screen, whose top edge must be.
  const inside = r.left >= -1 && r.right <= vw + 1 && (tall ? r.top >= -1 && r.top < vh : r.top >= -1 && r.bottom <= vh + 1);
  // anything fixed drawn over it: look at the points of the control that are on screen.
  // a link that wraps over two lines is two boxes, and the union's corners fall on the paragraph
  const boxes = [...e.getClientRects()].filter(b => b.width && b.height);
  let covered = 0, n = 0;
  boxes.forEach(b => {
    const x = (b.left + b.right) / 2, y = (Math.max(b.top, 0) + Math.min(b.bottom, vh)) / 2;
    if (x < 0 || x > vw || y < 0 || y > vh) return;
    n++;
    const t = document.elementFromPoint(x, y);
    if (t && t !== e && !e.contains(t) && !t.contains(e)) covered++;
  });
  return { label, inside, covered, n, top: Math.round(r.top), bottom: Math.round(r.bottom), vh };
}"""


def serve():
    class Quiet(http.server.SimpleHTTPRequestHandler):
        def __init__(self, *a, **k):
            super().__init__(*a, directory=str(DOCS), **k)

        def log_message(self, *a):
            pass
    srv = socketserver.ThreadingTCPServer(('127.0.0.1', 0), Quiet)
    srv.daemon_threads = True
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    return srv, srv.server_address[1]


def px(img, x, y):
    return img.getpixel((x, y))[:3]


def ring_area_ok(before, after, rect):
    """2.4.13: the pixels that change on focus, at 3:1 or better against what they replaced, cover
    at least a 2 CSS px outline round the control. Returns (pixels that pass, pixels required)."""
    w, h = before.size
    good = 0
    for y in range(h):
        for x in range(w):
            a, b = before.getpixel((x, y))[:3], after.getpixel((x, y))[:3]
            if a != b and contrast(a, b) >= RING_MIN:
                good += 1
    perimeter = 2 * (rect['width'] + rect['height'])
    return good, int(perimeter * 2 * 0.7)


def ring_sides_missing(after, rect, x0, y0):
    """2.4.7: the yellow band of the ring is there on each of the four sides of the control. The area
    test above is met by a ring cut off on one side if the other three are long enough, and a ring
    that is cut off on a side is not a ring round the control. Returns the sides with no yellow in the
    band within 5 CSS px of the edge, over the middle half of that edge."""
    YELLOW = (255, 184, 28)
    near = lambda c: sum(abs(a - b) for a, b in zip(c, YELLOW)) < 90
    w, h = after.size
    left, top = rect['x'] - x0, rect['y'] - y0
    right, bottom = left + rect['width'], top + rect['height']
    missing = []
    for side in ('top', 'bottom', 'left', 'right'):
        horizontal = side in ('top', 'bottom')
        lo, hi = (left + rect['width'] * 0.25, left + rect['width'] * 0.75) if horizontal else \
                 (top + rect['height'] * 0.25, top + rect['height'] * 0.75)
        edge = {'top': top, 'bottom': bottom, 'left': left, 'right': right}[side]
        if edge - 5 < 0 or edge + 5 >= (h if horizontal else w):
            continue        # the band is off the photograph, so this side cannot be read
        hits = total = 0
        for t in range(int(lo), int(hi) + 1, 2):
            total += 1
            found = False
            for d in range(-5, 6):
                x, y = (t, int(edge) + d) if horizontal else (int(edge) + d, t)
                if 0 <= x < w and 0 <= y < h and near(after.getpixel((x, y))[:3]):
                    found = True
                    break
            hits += found
        if total and hits / total < 0.6:
            missing.append(side)
    return missing


def main():
    from playwright.sync_api import sync_playwright
    from PIL import Image
    import io

    if not DOCS.is_dir() or not list(DOCS.rglob('*.html')):
        print('FAIL: no built site. Run: quarto render')
        return 1
    pages = sorted(p.relative_to(DOCS).as_posix() for p in DOCS.rglob('*.html')
                   if 'site_libs' not in p.parts)
    srv, port = serve()
    base = 'http://127.0.0.1:%d/' % port
    walk_pages = pages if os.environ.get('WCAG22_ALL_PAGES') else [p for p in WALK_PAGES if p in pages]

    with sync_playwright() as pw:
        browser = pw.chromium.launch(executable_path=CHROMIUM)

        # ---------------------------------------------------------- what every page says
        probes = {}
        for rel in pages:
            pg = browser.new_page(viewport={'width': 1280, 'height': 900})
            pg.goto(base + rel)
            pg.wait_for_timeout(250)
            pg.evaluate("document.querySelectorAll('details').forEach(d => d.open = true)")
            probes[rel] = pg.evaluate(PAGE_PROBE)
            pg.close()

        T = [(r, t) for r, p in probes.items() for t in p['tables']]
        nocap = [(r, t['first']) for r, t in T if not t['caption']]
        if nocap:
            fail.append('1.3.1 Table caption: %d of %d table(s) have no caption, on %d page(s), for example %s'
                        % (len(nocap), len(T), len({r for r, _ in nocap}), nocap[:3]))
        nohead = [(r, t['first']) for r, t in T if not t['header']]
        if nohead:
            fail.append('1.3.1 Table header: %d table(s) have no header row: %s' % (len(nohead), nohead[:3]))
        cells = [(r, t['first']) for r, t in T if t['labelsAreCells']]
        if cells:
            fail.append('1.3.1 Row headers: %d table(s) name each row in their first column with cells a screen '
                        'reader cannot tell from data, for example %s' % (len(cells), cells[:3]))
        if not (nocap or nohead or cells):
            print('  ok   1.3.1 Tables          %d table(s), each with a caption, a header row and row headers' % len(T))

        bad = [r for r, p in probes.items() if p['h1'] != 1 or p['emptyHeading'] or p['skips']]
        if bad:
            fail.append('Headings: one h1, no empty heading and no skipped level, and these break it: %s' % bad[:6])
        else:
            print('  ok   Headings          %d pages, one h1 each, no empty heading, no level skipped' % len(pages))

        anchors = sum(1 for p in probes.values() for n in p['linkNames'] if n.strip().lower() == 'anchor')
        empties = [(r, i) for r, p in probes.items() for i, n in enumerate(p['linkNames']) if not n.strip()]
        raw = [n for p in probes.values() for n in p['linkNames']
               if re.match(r'^(https?://|www\.|[\w-]+(\.[\w-]+)*\.(com|org|uk|io|net|gov)(/|$))', n.strip(), re.I)]
        if anchors:
            fail.append('2.4.4 Link Purpose: %d link(s) are named just "Anchor"' % anchors)
        if empties:
            fail.append('2.4.4 Link Purpose: %d link(s) have no name, for example on %s' % (len(empties), empties[0][0]))
        if raw:
            fail.append('2.4.9 Link Purpose: %d link(s) use a web address as their text: %s' % (len(raw), raw[:2]))
        if not (anchors or empties or raw):
            print('  ok   2.4.4 Link names     every link is named, none "Anchor", none a bare address')

        icons = sum(p['iconNames'] for p in probes.values())
        noalt = sum(p['noAlt'] for p in probes.values())
        if icons:
            fail.append('1.1.1 Icons: %d element(s) are announced by the name of their icon set, for example '
                        '"Icon information-outline from mdi Iconify.design set."' % icons)
        if noalt:
            fail.append('1.1.1 Images: %d image(s) have no alt attribute' % noalt)
        if not (icons or noalt):
            print('  ok   1.1.1 Images, icons  no icon is read out by the name of its set, no image lacks alt')

        skipbad = [r for r, p in probes.items() if not p['skip'] or not p['skip']['first']]
        if skipbad:
            fail.append('2.4.1 Skip link: not the first stop on %d page(s), for example %s' % (len(skipbad), skipbad[:3]))

        curbad = []
        for r, p in probes.items():
            cur = p['current']
            if p['selfNav']:
                # The page has its own entry in the navigation: exactly that one is current.
                if len(cur) != 1 or cur[0]['path'] != p['here']:
                    curbad.append((r, 'marks %s as current, and the page is %s'
                                   % ([c['text'] + ' ' + c['path'] for c in cur] or 'nothing', p['here'])))
            elif cur:
                # A page with no entry in the navigation has no current link to mark.
                curbad.append((r, 'has no navigation entry and marks %r as current' % cur[0]['text']))
        if curbad:
            fail.append('4.1.2 Current page: %d page(s) mark the wrong link as current, for example %s' % (len(curbad), curbad[:3]))
        else:
            print('  ok   4.1.2 Current page   one aria-current a page, and it is the page you are on')

        roles = sum(p['badRoles'] for p in probes.values())
        if roles:
            fail.append('4.1.2 Roles: %d control(s) carry a role that does not fit them (a button with role=menu, '
                        'or a link with role=link that opens something)' % roles)
        navs = [r for r, p in probes.items() if any(not n for n in p['navs']) or len(set(p['navs'])) != len(p['navs'])]
        if navs:
            fail.append('4.1.2 Landmarks: %d page(s) have a navigation landmark with no name, or two alike, for example %s'
                        % (len(navs), navs[:3]))
        ban = [r for r, p in probes.items() if p['banners'] != 1]
        if ban:
            fail.append('1.3.1 Landmarks: %d page(s) do not have exactly one banner, for example %s' % (len(ban), ban[:3]))
        if not (roles or navs or ban):
            print('  ok   4.1.2 Landmarks      one banner, every navigation named and distinct, valid roles')

        cue = [r for r, p in probes.items() if p['sidebarCue'] is False]
        ncue = [r for r, p in probes.items() if p['navCue'] is False]
        if not any(p['navCue'] is not None for p in probes.values()):
            fail.append('1.4.1 Use of Colour: no page has a current link in the navigation bar, so its cue was not tested')
        if ncue:
            fail.append('1.4.1 Use of Colour: the current page in the navigation bar differs from the others only in '
                        'colour on %d page(s), for example %s' % (len(ncue), ncue[:3]))
        rew = [(r, p['hashRewritten']) for r, p in probes.items() if p['hashRewritten']]
        if rew:
            fail.append('2.4.3 Focus Order: %d page(s) link to a place on themselves by way of the folder address, so '
                        'Enter on the link loads the page again instead of jumping: %s' % (len(rew), rew[:3]))
        foot = sum(p['footerLinksPlain'] for p in probes.values())
        prose = sum(p['proseLinksPlain'] for p in probes.values())
        summ = sum(1 for p in probes.values() for m in p['summaries'] if not m)
        if cue:
            fail.append('1.4.1 Use of Colour: the current page in the sidebar differs from the others only in '
                        'colour on %d page(s), for example %s' % (len(cue), cue[:3]))
        if foot:
            fail.append('1.4.1 Use of Colour: %d footer link(s) are told apart from the text round them by colour alone' % foot)
        if prose:
            fail.append('1.4.1 Use of Colour: %d link(s) in running text have no underline' % prose)
        if summ:
            fail.append('1.4.1 Disclosures: %d expander(s) show no marker, so they read as bold text' % summ)
        if not (cue or ncue or rew or foot or prose or summ):
            print('  ok   1.4.1 Colour          current page (sidebar and navigation bar), footer links, prose links and expanders do not rely on colour')

        dg = [(r, d) for r, p in probes.items() for d in p['diagrams']]
        dbad = [(r, d['title']) for r, d in dg
                if not (d['label'].startswith(d['alt']) and 'Opens the diagram' in d['label'] and
                        d['alt'] and 'Opens the diagram' not in d['alt'] and d['title'] and
                        d['alt'].lower().startswith(d['title'].rstrip('.').lower()))]
        if dbad:
            fail.append('2.4.9 Diagram links: %d diagram link(s) do not name what they open, or the picture\'s '
                        'alt does not start with the title the figure shows: %s' % (len(dbad), dbad[:3]))
        else:
            print('  ok   2.4.9 Diagram links  %d, each named by what it shows and where it goes' % len(dg))

        pop = sum(p['popups'] for p in probes.values())
        if pop:
            fail.append('1.4.13 Content on Hover or Focus: %d footnote reference(s) open a floating popup that '
                        'cannot be dismissed with Escape while it is hovered' % pop)
        else:
            print('  ok   1.4.13 Footnotes     no floating popup')

        long_, narrow, hint_off = [], [], []
        for w, h in ((1280, 900), (1920, 1080)):
            for rel in pages:
                pg = browser.new_page(viewport={'width': w, 'height': h})
                pg.goto(base + rel)
                pg.wait_for_timeout(120)
                pg.evaluate("document.querySelectorAll('details').forEach(d => d.open = true)")
                m = pg.evaluate(LINE_PROBE)
                pg.close()
                if m['longest'] > MAX_CHARS:
                    long_.append((rel, w, m['longest'], m['longestAt']))
                for bx in m['boxes']:
                    if bx['fig'] >= 690 and bx['scrolls']:
                        narrow.append((rel, w, bx['w'], bx['fig']))
                    if bx['hint'] is not None and bx['hint'] != bx['scrolls']:
                        hint_off.append((rel, w, 'scrolls' if bx['scrolls'] else 'does not scroll',
                                         'hint shown' if bx['hint'] else 'hint hidden'))
        if long_:
            fail.append('1.4.8 Visual Presentation: %d page(s) set a line of prose longer than %d characters, '
                        'longest %d: %s' % (len({x[0] for x in long_}), MAX_CHARS, max(x[2] for x in long_), long_[:2]))
        else:
            print('  ok   1.4.8 Line length    no rendered line over %d characters, counted, at 1280 and at 1920' % MAX_CHARS)

        if narrow:
            fail.append('1.4.10 Reflow: %d diagram box(es) are narrower than their 680px drawing where the column '
                        'is wide enough for it, so the drawing scrolls sideways on a laptop for no reason: %s'
                        % (len(narrow), narrow[:3]))
        elif hint_off:
            fail.append('1.4.10 Reflow: %d diagram box(es) show the scroll hint when they do not scroll, or hide '
                        'it when they do: %s' % (len(hint_off), hint_off[:3]))
        else:
            print('  ok   1.4.10 Diagrams      each box shows its whole drawing at 1280 and 1920, and the scroll hint '
                  'matches the scroll')

        small = [(r, s) for r, p in probes.items() for s in p['smallTargets']]
        if small:
            fail.append('2.5.8 Target Size (Minimum): %d target(s) under 24 by 24 outside a sentence, for example %s'
                        % (len(small), small[:3]))
        else:
            print('  ok   2.5.8 Target size    nothing a pointer must hit is under 24 by 24')

        # ------------------------------------------------ fixed and sticky things at 400 percent zoom
        for w, h in ((320, 256), (375, 667), (640, 512), (768, 384)):
            tall = []
            for rel in walk_pages:
                pg = browser.new_page(viewport={'width': w, 'height': h})
                pg.goto(base + rel)
                pg.wait_for_timeout(200)
                f = pg.evaluate(FIXED_PROBE)
                pg.close()
                if f['total'] > h * 0.2:
                    tall.append((rel, f['total'], f['parts']))
            if tall:
                fail.append('1.4.10 Reflow, 2.4.11: at %dx%d something fixed or sticky takes more than a fifth of '
                            'the screen on %d page(s), for example %s' % (w, h, len(tall), tall[:2]))
            else:
                print('  ok   1.4.10 Fixed bars   at %dx%d nothing fixed takes a fifth of the screen' % (w, h))

        # ---------------------------------------------------------------- reduced motion
        pg = browser.new_page(viewport={'width': 1280, 'height': 800}, reduced_motion='reduce')
        pg.goto(base + 'index.html')
        pg.wait_for_timeout(200)
        moving = pg.evaluate("""() => [...document.querySelectorAll('#quarto-header, #quarto-header *, #quarto-sidebar, .navbar-collapse, details > summary, a')]
            .filter(e => { const s = getComputedStyle(e); const d = s.transitionDuration.split(',').map(parseFloat);
              return Math.max(...d) > 0.01 || (s.animationName !== 'none' && parseFloat(s.animationDuration) > 0.01); })
            .map(e => (e.id || e.className || e.tagName).toString().slice(0, 30)).slice(0, 5)""")
        scroll = pg.evaluate("getComputedStyle(document.documentElement).scrollBehavior")
        pg.close()
        if moving or scroll == 'smooth':
            fail.append('2.3.3 Animation from Interactions: with reduced motion asked for, these still move: %s, '
                        'scroll-behavior %s' % (moving, scroll))
        else:
            print('  ok   2.3.3 Reduced motion nothing transitions or scrolls smoothly')

        # ------------------------------------------------------------ keyboard, stop by stop
        for w, h in WALK_VIEWPORTS:
            bad = []
            stops = 0
            for rel in walk_pages:
                pg = browser.new_page(viewport={'width': w, 'height': h})
                pg.goto(base + rel)
                pg.wait_for_timeout(250)
                seen = set()
                first = None
                for i in range(260):
                    pg.keyboard.press('Tab')
                    s = pg.evaluate(STOP_PROBE)
                    if s.get('body'):
                        break
                    key = s.get('label')
                    if i == 0:
                        first = key
                    elif key == first and i > 3:
                        break
                    stops += 1
                    if s.get('hidden'):
                        continue
                    if not s['inside'] or (s['n'] and s['covered'] > s['n'] / 2):
                        bad.append((rel, s['label'], 'top %d bottom %d of %d' % (s['top'], s['bottom'], s['vh']),
                                    'covered %d of %d' % (s['covered'], s['n'])))
                pg.close()
            if bad:
                fail.append('2.4.11 Focus Not Obscured: at %dx%d, %d of %d Tab stop(s) are off screen or under '
                            'something fixed, for example %s' % (w, h, len(bad), stops, bad[:2]))
            else:
                print('  ok   2.4.11 Tab walk      %dx%d: %d stops on %d page(s), each wholly on screen and uncovered'
                      % (w, h, stops, len(walk_pages)))


        # ------------------------------------------------ paths a keyboard takes on a phone
        # The skip link has to land at the top of the content at any window size. At 400 percent zoom
        # the page is 320 by 256, and Chromium centres a focus target taller than the window when its
        # top is below the fold, which dropped the reader half-way down the page on every page.
        skip_bad = []
        for w, h in ((320, 256), (400, 300), (375, 667), (1280, 720)):
            for rel in ('index.html', 'accessibility.html', 'guidance/03-analysis/index.html',
                        'guidance/09-resources/r1-glossary.html'):
                pg = browser.new_page(viewport={'width': w, 'height': h})
                pg.goto(base + rel)
                pg.wait_for_timeout(250)
                pg.keyboard.press('Tab')
                pg.keyboard.press('Enter')
                pg.wait_for_timeout(200)
                m = pg.evaluate("""() => { const m = document.getElementById('quarto-document-content');
                    const r = m.getBoundingClientRect();
                    return { top: Math.round(r.top), vh: innerHeight, focused: document.activeElement === m }; }""")
                pg.keyboard.press('Tab')
                pg.wait_for_timeout(100)
                inside = pg.evaluate("document.getElementById('quarto-document-content').contains(document.activeElement)")
                pg.close()
                if not (m['focused'] and 0 <= m['top'] <= m['vh'] * 0.5 and inside):
                    skip_bad.append((rel, '%dx%d' % (w, h), 'main top %d of %d' % (m['top'], m['vh']),
                                     'focus in main' if m['focused'] else 'main not focused',
                                     'next Tab in main' if inside else 'next Tab outside main'))
        if skip_bad:
            fail.append('2.4.1 Bypass Blocks: after Tab and Enter on the skip link, the content does not start at the top of '
                        'the window, or the next Tab leaves it, in %d case(s): %s' % (len(skip_bad), skip_bad[:3]))
        else:
            print('  ok   2.4.1 Skip link      lands at the top of the content, and the next Tab is inside it, down to 320x256')

        # A sidebar group that is open shows a chevron pointing down, whether it opened with the page or
        # the reader pressed it. Two rules each turned it a quarter, so a group a reader opened pointed
        # left while the one that opened with the page pointed down. The state is also said in words, by
        # aria-expanded, so this is the visible half of the same fact (1.3.1, 1.4.1).
        chev_bad = []
        pg = browser.new_page(viewport={'width': 1280, 'height': 900})
        pg.goto(base + 'guidance/03-analysis/index.html')
        pg.wait_for_timeout(500)
        pg.locator('#quarto-sidebar .sidebar-item-section > .sidebar-item-container > a.sidebar-item-text').first.click()
        pg.wait_for_timeout(900)
        turns = pg.evaluate("""() => [...document.querySelectorAll('#quarto-sidebar .sidebar-item-toggle')].map(a => {
            const c = a.querySelector('.bi-chevron-right');
            const deg = t => { if (!t || t === 'none') return 0; const m = t.match(/matrix\\(([^)]+)\\)/);
                               const v = m[1].split(',').map(Number); return Math.atan2(v[1], v[0]) * 180 / Math.PI; };
            const total = Math.round(deg(getComputedStyle(c).transform) + deg(getComputedStyle(c, '::before').transform));
            return { open: !a.classList.contains('collapsed'), total: ((total % 360) + 360) % 360 }; })""")
        pg.close()
        for t in turns:
            if t['total'] != (90 if t['open'] else 0):
                chev_bad.append(('open' if t['open'] else 'closed', 'turned %d degrees' % t['total']))
        if not turns:
            chev_bad.append('no sidebar group to test')
        if chev_bad:
            fail.append('1.3.1 Info and Relationships: a sidebar chevron does not show whether its group is open: %s' % chev_bad[:3])
        else:
            print('  ok   1.3.1 Chevrons       %d sidebar group(s), each open one points down and each closed one right' % len(turns))

        # The links in a Sources list are targets in their own right, and their boxes must not share
        # pointer area or draw a ring through a neighbour (2.5.8, 2.4.7).
        pg = browser.new_page(viewport={'width': 1280, 'height': 720})
        pg.goto(base + 'guidance/09-resources/r10-uncertainty.html')
        pg.wait_for_timeout(400)
        n_links, n_over = pg.evaluate("""() => { const r = [...document.querySelectorAll('#footnotes li a')].map(a => a.getBoundingClientRect());
            let n = 0; for (let i = 0; i < r.length; i++) for (let j = i + 1; j < r.length; j++) {
              const a = r[i], b = r[j]; if (a.left < b.right && b.left < a.right && a.top < b.bottom - 1 && b.top < a.bottom - 1) n++; }
            return [r.length, n]; }""")
        pg.close()
        if not n_links:
            fail.append('2.5.8 Target Size: r10-uncertainty has no Sources list links to measure')
        elif n_over:
            fail.append('2.5.8 Target Size: %d pair(s) of links in the Sources list share pointer area' % n_over)
        else:
            print('  ok   2.5.8 Sources links  %d links in a Sources list, none overlapping another' % n_links)

        # 1.4.12 Text Spacing: the reader's own line, letter, word and paragraph spacing, applied at the
        # width of a phone at 400 percent zoom, must not take the page sideways.
        SPACING = '* { line-height: 1.5 !important; letter-spacing: 0.12em !important; word-spacing: 0.16em !important; } p { margin-bottom: 2em !important; }'
        spaced = []
        for rel in pages:
            pg = browser.new_page(viewport={'width': 320, 'height': 568})
            pg.goto(base + rel)
            pg.add_style_tag(content=SPACING)
            pg.wait_for_timeout(200)
            sw = pg.evaluate("document.documentElement.scrollWidth")
            pg.close()
            if sw > 320:
                spaced.append((rel, sw))
        if spaced:
            fail.append('1.4.12 Text Spacing: %d page(s) scroll sideways at 320 wide once the reader\'s spacing is applied, '
                        'for example %s' % (len(spaced), spaced[:3]))
        else:
            print('  ok   1.4.12 Text spacing   %d pages stay inside 320 pixels with line, letter, word and paragraph spacing applied' % len(pages))

        # 1.4.4 Resize Text: at 200 percent text the bar wraps, and the logo must still be what is under a press
        # on its middle, not the box of a link that lies over it.
        logo_bad = []
        for w, h in ((1280, 720), (1366, 768)):
            pg = browser.new_page(viewport={'width': w, 'height': h})
            pg.goto(base + 'index.html')
            pg.add_style_tag(content='html { font-size: 200% !important; }')
            pg.wait_for_timeout(300)
            top = pg.evaluate("""() => { const a = document.querySelector('a.navbar-brand'); const r = a.getBoundingClientRect();
                const e = document.elementFromPoint(r.left + r.width / 2, r.top + r.height / 2);
                return !!e && !!e.closest('a.navbar-brand'); }""")
            pg.close()
            if not top:
                logo_bad.append('%dx%d' % (w, h))
        if logo_bad:
            fail.append('1.4.4 Resize Text: at 200 percent text a press on the middle of the logo reaches another link at %s' % logo_bad)
        else:
            print('  ok   1.4.4 Logo           at 200 percent text the logo is what a press on its middle reaches')

        # 1.4.10: on a phone the line that says a diagram scrolls comes before the diagram.
        pg = browser.new_page(viewport={'width': 375, 'height': 667})
        pg.goto(base + 'guidance/analytical-cycle/index.html')
        pg.wait_for_timeout(300)
        cap_first = pg.evaluate("""() => { const c = document.querySelector('figure figcaption'), a = document.querySelector('a.diagram-open');
            return !!c && !!a && c.getBoundingClientRect().bottom <= a.getBoundingClientRect().top + 1; }""")
        pg.close()
        if not cap_first:
            fail.append('1.4.10 Reflow: on a phone the diagram\'s caption, which says it scrolls, comes after the diagram')
        else:
            print('  ok   1.4.10 Diagram hint  on a phone the line that says a diagram scrolls comes before it')

        # Forced colours (a Windows contrast theme): the current sidebar link differs from the others by more
        # than bold, and a disclosure still shows a triangle and not a square.
        ctx = browser.new_context(viewport={'width': 1280, 'height': 900}, forced_colors='active')
        pg = ctx.new_page()
        pg.goto(base + 'guidance/03-analysis/index.html')
        pg.wait_for_timeout(400)
        fc = {'bar': pg.evaluate("""() => {
            const links = [...document.querySelectorAll('#quarto-sidebar a.sidebar-link')];
            const cur = links.find(a => a.classList.contains('active') || a.getAttribute('aria-current') === 'page');
            const oth = links.find(a => a !== cur);
            return cur && oth ? getComputedStyle(cur).borderLeftColor !== getComputedStyle(oth).borderLeftColor : null; }""")}
        pg.goto(base + 'guidance/09-resources/r19-worked-examples.html')
        pg.wait_for_timeout(400)
        fc['triangle'] = pg.evaluate("""() => {
            const sum = document.querySelector('details > summary');
            if (!sum) return null;
            const b = getComputedStyle(sum, '::before');
            const clear = c => /rgba\(0, 0, 0, 0\)|transparent/.test(c);
            return !clear(b.borderLeftColor) && clear(b.borderTopColor) && clear(b.borderBottomColor); }""")
        ctx.close()
        if fc['bar'] is not True or fc['triangle'] is not True:
            fail.append('1.4.11 / 1.4.1 Forced colours: the current sidebar link has a bar the others do not: %s; a disclosure draws a '
                        'triangle: %s' % (fc['bar'], fc['triangle']))
        else:
            print('  ok   1.4.11 Forced colours the current sidebar link keeps its bar and a disclosure keeps its triangle')

        # Tab goes through the navigation bar in the order it is drawn: left to right.
        order_bad = []
        for w, h in ((375, 667), (768, 1024), (1280, 900)):
            pg = browser.new_page(viewport={'width': w, 'height': h})
            pg.goto(base + 'guidance/03-analysis/index.html')
            pg.wait_for_timeout(300)
            stops = []
            for _ in range(5):
                pg.keyboard.press('Tab')
                stops.append(pg.evaluate("""() => { const e = document.activeElement;
                    return { bar: !!e.closest('nav.navbar'), left: Math.round(e.getBoundingClientRect().left),
                             name: (e.getAttribute('aria-label') || e.textContent || e.tagName).trim().slice(0, 24) }; }"""))
            pg.close()
            bar = [s_ for s_ in stops if s_['bar']]
            if any(b['left'] < a['left'] for a, b in zip(bar, bar[1:])):
                order_bad.append(('%dx%d' % (w, h), [(s_['name'], s_['left']) for s_ in bar]))
        if order_bad:
            fail.append('2.4.3 Focus Order: Tab goes through the navigation bar in a different order from the one it is '
                        'drawn in: %s' % order_bad)
        else:
            print('  ok   2.4.3 Focus order    Tab goes through the navigation bar left to right at 375, 768 and 1280')

        # The Guidance menu inside the open phone menu must stay inside the window.
        menu_bad = []
        for w, h in ((320, 256), (320, 568), (360, 640)):
            pg = browser.new_page(viewport={'width': w, 'height': h})
            pg.goto(base + 'index.html')
            pg.wait_for_timeout(250)
            pg.click('button.navbar-toggler')
            pg.wait_for_timeout(500)
            pg.click('a.dropdown-toggle')
            pg.wait_for_timeout(400)
            m = pg.evaluate("""() => ({ sw: document.documentElement.scrollWidth, iw: innerWidth,
                over: [...document.querySelectorAll('.dropdown-menu.show .dropdown-item')]
                      .filter(a => a.getBoundingClientRect().right > innerWidth + 1).length })""")
            pg.close()
            if m['sw'] > m['iw'] or m['over']:
                menu_bad.append(('%dx%d' % (w, h), 'page %d wide in %d' % (m['sw'], m['iw']), '%d item(s) past the edge' % m['over']))
        if menu_bad:
            fail.append('1.4.10 Reflow: the open Guidance menu takes the page sideways or runs past the edge: %s' % menu_bad)
        else:
            print('  ok   1.4.10 Phone menu    the open Guidance menu stays inside a 320 pixel window')

        # The drawer and its dimmed backdrop open together but not at the same moment. Closing in
        # between left the backdrop up over a page with no drawer, and it took every press. Whenever it
        # is settled, the backdrop is up exactly when the drawer is.
        glass_bad = []
        for delay in (10, 50, 100, 150, 400):
            pg = browser.new_page(viewport={'width': 375, 'height': 667})
            pg.goto(base + 'guidance/03-analysis/index.html')
            pg.wait_for_timeout(300)
            pg.focus('button.quarto-btn-toggle')
            pg.keyboard.press('Enter')
            pg.wait_for_timeout(delay)
            pg.keyboard.press('Escape')
            pg.wait_for_timeout(900)
            if pg.evaluate("document.getElementById('quarto-sidebar').classList.contains('show')"):
                pg.keyboard.press('Escape')
                pg.wait_for_timeout(900)
            m = pg.evaluate("""() => { const g = document.getElementById('quarto-sidebar-glass');
                const t = document.elementFromPoint(innerWidth / 2, innerHeight / 2);
                return { glass: !!g && g.classList.contains('show'), shown: g ? getComputedStyle(g).display : 'none',
                         drawer: document.getElementById('quarto-sidebar').classList.contains('show'),
                         inert: document.querySelectorAll('[inert]').length, over: !!t && t.id === 'quarto-sidebar-glass' }; }""")
            pg.close()
            if m['glass'] != m['drawer'] or m['drawer'] or m['over'] or m['inert']:
                glass_bad.append(('closed %dms after opening' % delay, m))
        if glass_bad:
            fail.append('2.4.3 Focus Order: the drawer is closed but its backdrop or its lock is not, in %d case(s): %s'
                        % (len(glass_bad), glass_bad[:2]))
        else:
            print('  ok   2.4.3 Drawer        closed 10 to 400ms after opening, the backdrop goes with it and the page is live')

        # 2.5.5 Target Size (Enhanced) for the links that sit alone on a line: the home page cards and
        # the search results.
        tgt_bad = []
        for w, h in ((1280, 900), (375, 667)):
            pg = browser.new_page(viewport={'width': w, 'height': h})
            pg.goto(base + 'index.html')
            pg.wait_for_timeout(250)
            low = pg.evaluate("""() => [...document.querySelectorAll('.pb-cards h3 a, .pb-phases h3 a')]
                .filter(a => a.getBoundingClientRect().height < 43.5).map(a => a.textContent.trim().slice(0, 24))""")
            pg.goto(base + 'search.html')
            pg.wait_for_timeout(250)
            pg.fill('#pb-q', 'uncertainty')
            pg.wait_for_timeout(600)
            hits = pg.evaluate("""() => [...document.querySelectorAll('.pb-hits > li > a:first-child')]
                .map(a => a.getBoundingClientRect().height)""")
            pg.close()
            if low:
                tgt_bad.append(('home', '%dx%d' % (w, h), low[:3]))
            if not hits:
                tgt_bad.append(('search', '%dx%d' % (w, h), 'no result links to measure'))
            elif min(hits) < 43.5:
                tgt_bad.append(('search', '%dx%d' % (w, h), 'a result link %d px high' % min(hits)))
        if tgt_bad:
            fail.append('2.5.5 Target Size (Enhanced): links alone on a line are under 44px high: %s' % tgt_bad[:3])
        else:
            print('  ok   2.5.5 Target size    home page cards and search results are 44px high or more')

        # --------------------------------------------------- the focus ring of each kind of control
        KINDS = [
            ('navbar link', 'index.html', '.navbar .nav-link, .navbar-nav .nav-item a'),
            ('sidebar link', 'guidance/09-resources/r5-quality-assurance-statement.html', '#quarto-sidebar a.sidebar-link'),
            ('on this page link', 'guidance/09-resources/r5-quality-assurance-statement.html', '#TOC a'),
            ('footer link', 'index.html', '.nav-footer a'),
            ('pagination link', 'guidance/01-engagement-and-scoping/index.html', 'nav.page-navigation a'),
            ('summary', 'guidance/09-resources/r19-worked-examples.html', 'details > summary'),
            ('phase card', 'guidance/analytical-cycle/index.html', '.pb-phase-cards a'),
            ('diagram link', 'guidance/analytical-cycle/index.html', 'a.diagram-open'),
            ('search box', 'search.html', 'input[type=search], input'),
            ('body link', 'guidance/07-deciding-your-assurance-level/index.html', 'main p a[href]'),
            # the controls that only a phone shows
            ('sidebar button, phone', 'guidance/03-analysis/index.html', 'button.quarto-btn-toggle', (375, 667)),
            ('sidebar button, tablet', 'guidance/03-analysis/index.html', 'button.quarto-btn-toggle', (768, 1024)),
            ('menu button, phone', 'index.html', 'button.navbar-toggler', (375, 667)),
            # the on-this-page list scrolls from 992 to about 1100 wide, and its right-hand edge cut the ring
            ('on this page link, 1024', 'guidance/08-business-critical/index.html', '#TOC a.nav-link', (1024, 768), 2),
            ('source number', 'guidance/09-resources/r5-quality-assurance-statement.html', 'a.footnote-ref', (1280, 900), 0),
            ('last sidebar link', 'guidance/09-resources/r5-quality-assurance-statement.html', '#quarto-sidebar a.sidebar-link', (1280, 900), -1),
        ]
        weak = []
        for name, rel, sel, *size in KINDS:
            vw, vh = size[0] if size else (1280, 900)
            nth = size[1] if len(size) > 1 else 0
            pg = browser.new_page(viewport={'width': vw, 'height': vh})
            pg.goto(base + rel)
            pg.wait_for_timeout(250)
            loc = pg.locator(sel + ':visible').nth(nth)
            if loc.count() == 0:
                pg.close()
                weak.append((name, 'no such control on ' + rel))
                continue
            loc.evaluate("e => e.scrollIntoView({block: 'center', inline: 'nearest'})")
            pg.keyboard.press('Shift')
            pg.mouse.move(2, 2)
            vp = pg.viewport_size

            def photograph(rect):
                """The control unfocused and then focused, in the same clip. Focusing from a script
                does not need a Tab first, and a Tab moves focus to the top of the page and scrolls
                it, so the clip would then be of somewhere else. The Shift above is what tells the
                browser the last input was the keyboard, so that :focus-visible matches."""
                pad = 10
                x0, y0 = max(rect['x'] - pad, 0), max(rect['y'] - pad, 0)
                clip = {'x': x0, 'y': y0, 'width': min(rect['width'] + 2 * pad, vp['width'] - x0),
                        'height': min(rect['height'] + 2 * pad, vp['height'] - y0)}
                pg.evaluate("document.activeElement && document.activeElement.blur()")
                b_ = Image.open(io.BytesIO(pg.screenshot(clip=clip))).convert('RGB')
                loc.focus()
                pg.wait_for_timeout(150)
                a_ = Image.open(io.BytesIO(pg.screenshot(clip=clip))).convert('RGB')
                return b_, a_, x0, y0

            rect = loc.bounding_box()
            before, after, x0, y0 = photograph(rect)
            moved = loc.bounding_box()
            if abs(moved['x'] - rect['x']) > 1 or abs(moved['y'] - rect['y']) > 1:
                # focusing scrolled the page to bring the control into view: photograph it where it is now
                rect = moved
                before, after, x0, y0 = photograph(rect)
            good, need = ring_area_ok(before, after, rect)
            if good < need:
                weak.append((name, '%d pixels change at 3:1 or better, %d needed' % (good, need)))
            gaps = ring_sides_missing(after, rect, x0, y0)
            if gaps:
                weak.append((name, 'no yellow band on the %s side(s) of the control' % ', '.join(gaps)))
            pg.close()
        if weak:
            fail.append('2.4.7 Focus Visible, 1.4.11, 2.4.13: the focus ring is weaker than 3:1 on %d of %d kinds of '
                        'control: %s' % (len(weak), len(KINDS), weak))
        else:
            print('  ok   2.4.7 Focus ring     %d kinds of control, each ring changes at least 3:1 round the control'
                  % len(KINDS))
        browser.close()
    srv.shutdown()

    print()
    if fail:
        print('FAIL')
        for f in fail:
            print('  X ' + f)
        return 1
    print('PASS: %d pages' % len(pages))
    return 0


if __name__ == '__main__':
    sys.exit(main())
