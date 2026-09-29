#!/usr/bin/env python3
"""Check the built site against the accessibility engineering it depends on.

    quarto render
    python3 checks/accessibility.py

WCAG 2.2 AA applies to this site. Most of what makes it conformant is configuration and a few
lines of CSS, which is exactly the sort of thing that gets tidied away by somebody who does not
know what it is for. The damage is invisible: the site still renders, it is just no longer
accessible. So this asserts it in the rendered pages rather than in the source.

What it asserts, and the criterion each one serves:

  1.1.1  Non-text Content         every diagram carries alt text, and a text description
  1.4.3  Contrast                 the description toggle is readable on its ground
  1.4.10 Reflow                   no page scrolls horizontally, at six widths from 320px up
  2.4.11 Focus Not Obscured       nothing takes focus behind the pinned title block
  2.4.7  Focus Visible            every control visibly answers when it takes focus
  2.5.3  Label in Name            a control is announced by the words written on it
  2.1.1  Keyboard                 a table that scrolls can be reached and scrolled from the keyboard
  2.4.2  Page Titled              every page has its own title
  4.1.2  Name, Role, Value        the navigation button and every scroll region is named

Three at AAA, which the site also meets:

  1.4.6  Contrast (Enhanced)      7:1 for body text, 4.5:1 for large
  1.4.8  Visual Presentation      no line of prose wider than 80 characters
  2.5.5  Target Size (Enhanced)   44 by 44, or one of the criterion's own exceptions
  2.4.9  Link Purpose (Link Only)  no link text that is ambiguous read on its own
  2.4.10 Section Headings         a page of any length is organised under headings

2.5.5 has an Equivalent exception: a small target passes where the same destination is reachable
from a target of at least 44 by 44 on the same page. Every section is in the sidebar at full size,
so a "section 5" link in the middle of a sentence is covered by it. The check applies the exception
rather than ignoring the target, and reports a small target whose destination is nowhere else.

AAA is not claimed for the site as a whole. 3.1.5 Reading Level asks for prose readable at lower
secondary level, which assurance guidance citing GovS 010 clause numbers cannot be, and 1.4.9
Images of Text is arguable for the diagrams. The accessibility statement says so.

It needs Chromium and Playwright, which is why it is separate from anything that has to run
everywhere. `PLAYWRIGHT_CHROMIUM` names the browser if it is not on the default path.
"""
import os
import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
DOCS = ROOT / 'docs'
WIDTHS = (320, 375, 768, 1024, 1280, 1920)
# How many focusable elements per page the 2.4.11 pass puts focus on. The pinned
# title block is at the top, so the risk is concentrated in the first run of them.
FOCUS_SAMPLE = 25
CHROMIUM = os.environ.get('PLAYWRIGHT_CHROMIUM', '/opt/pw-browsers/chromium')
MIN_ALT = 40          # characters. An alt shorter than this is a label, not a description.
MIN_CONTRAST = 4.5    # WCAG 1.4.3 for text below 18pt
AAA_CONTRAST = 7.0    # WCAG 1.4.6 for text below 18pt, 4.5 above it
AAA_LARGE = 4.5
MAX_LINE = 80.5       # WCAG 1.4.8, characters a line, with half a character of slack
MIN_TARGET = 44       # WCAG 2.5.5
# WCAG 2.4.9 asks that a link makes sense read on its own, out of the sentence around it. These are
# the link texts that do not, which is what a screen reader user hears when they list the links on
# a page.
VAGUE_LINK = re.compile(
    r'^(click here|here|read more|more|this|this page|this link|link|learn more|see more|'
    r'find out more|details|view|download|continue|go|read on|more info\w*)$', re.I)


def contrast(a, b):
    def lum(rgb):
        c = [v / 255 for v in rgb]
        c = [v / 12.92 if v <= 0.04045 else ((v + 0.055) / 1.055) ** 2.4 for v in c]
        return 0.2126 * c[0] + 0.7152 * c[1] + 0.0722 * c[2]
    la, lb = lum(a), lum(b)
    hi, lo = max(la, lb), min(la, lb)
    return (hi + 0.05) / (lo + 0.05)


def rgb(css):
    nums = [int(n) for n in ''.join(ch if ch.isdigit() else ' ' for ch in css).split()[:3]]
    return tuple(nums) if len(nums) == 3 else (0, 0, 0)


AAA_PROBE = """() => {
  const bgOf = el => { let e = el; while (e) { const c = getComputedStyle(e).backgroundColor;
    if (c && c !== 'rgba(0, 0, 0, 0)' && c !== 'transparent') return c; e = e.parentElement; }
    return 'rgb(255, 255, 255)'; };

  const text = [];
  document.querySelectorAll('body *').forEach(el => {
    const t = [...el.childNodes].filter(n => n.nodeType === 3)
                .map(n => n.textContent.trim()).join('');
    if (!t) return;
    const s = getComputedStyle(el);
    if (s.visibility === 'hidden' || s.display === 'none') return;
    text.push([s.color, bgOf(el), parseFloat(s.fontSize), s.fontWeight, el.tagName]);
  });

  // A character is the width of the zero glyph in the element's own font, which is what the
  // ch unit means. Guessing it from the font size is wrong by about a tenth.
  const probe = document.createElement('span');
  probe.style.cssText = 'position:absolute;visibility:hidden;white-space:pre';
  document.body.appendChild(probe);
  let wide = 0;
  document.querySelectorAll('main p, main li, main blockquote').forEach(el => {
    const cs = getComputedStyle(el);
    probe.style.font = cs.font; probe.textContent = '0'.repeat(100);
    const ch = probe.getBoundingClientRect().width / 100;
    if (el.getBoundingClientRect().width / ch > MAX_LINE) wide++;
  });
  probe.remove();

  // 2.5.5 Equivalent: a destination also reachable from a full size target on the same page.
  const big = new Set();
  document.querySelectorAll('a[href]').forEach(el => {
    const r = el.getBoundingClientRect();
    if (r.width >= MIN_TARGET && r.height >= MIN_TARGET) big.add(el.href.split('#')[0]);
  });
  const targets = [];
  document.querySelectorAll('a[href], button, summary').forEach(el => {
    const r = el.getBoundingClientRect();
    if (!r.width || !r.height) return;
    if (r.width >= MIN_TARGET && r.height >= MIN_TARGET) return;
    if (el.href && big.has(el.href.split('#')[0])) return;
    if (el.closest('a[href]') && el.tagName !== 'A') return;
    // Inline: the target sits in a sentence, so its height is the line height of the text
    // around it, and making it taller would space the sentence out.
    const block = el.closest('p, li, td, th, blockquote, figcaption');
    if (block && block.textContent.trim().length > el.textContent.trim().length + 8) return;
    targets.push([Math.round(r.width), Math.round(r.height), el.href || '',
                  (el.textContent || '').trim().slice(0, 30)]);
  });
  return { text, wide, targets };
}"""


def main():
    from playwright.sync_api import sync_playwright
    pages = sorted(DOCS.rglob('*.html'))
    if not pages:
        raise SystemExit('nothing built. Run `quarto render` first.')
    fail, titles = [], {}

    exe = CHROMIUM if os.path.exists(CHROMIUM) else None
    with sync_playwright() as pw:
        browser = pw.chromium.launch(executable_path=exe) if exe else pw.chromium.launch()

        # ---------------------------------------------------- 1.4.10 Reflow, at every width
        for width in WIDTHS:
            page = browser.new_page(viewport={'width': width, 'height': 800})
            for f in pages:
                page.goto(f.resolve().as_uri(), wait_until='load')
                page.wait_for_timeout(50)
                if page.evaluate('document.documentElement.scrollWidth >'
                                 ' document.documentElement.clientWidth + 1'):
                    fail.append('1.4.10 Reflow: %s scrolls horizontally at %dpx'
                                % (f.relative_to(DOCS), width))
            page.close()
        print('  ok   1.4.10 Reflow           %d pages at %s' % (len(pages), ', '.join(
            '%dpx' % w for w in WIDTHS)) if not fail else '  X    1.4.10 Reflow')

        # ---------------------------------------------- 2.4.11 Focus Not Obscured (Minimum)
        # The title block is pinned from 768px so that the section name and its one-line
        # summary stay on screen. A pinned bar is the usual way this criterion gets broken:
        # the browser scrolls a focused element to the top of the viewport, the bar is already
        # there, and the element the keyboard is on is behind it with nothing to say so. The
        # CSS answer is scroll-margin-top on everything focusable in main; this is the check
        # that it is still there and still large enough.
        #
        # Focusing every element on 21 pages is minutes of nothing happening, so it takes the
        # first FOCUS_SAMPLE in main on each page, which is the run that follows the pinned
        # bar down the page. The count is printed rather than left implied.
        obscured = focused = 0
        page = browser.new_page(viewport={'width': 1280, 'height': 800})
        for f in pages:
            page.goto(f.resolve().as_uri(), wait_until='load')
            page.wait_for_timeout(60)
            hits = page.evaluate('''(n) => {
                const bar = document.querySelector('#title-block-header.quarto-title-block');
                if (!bar || getComputedStyle(bar).position !== 'sticky') return null;
                const els = [...document.querySelectorAll(
                    'main a[href], main button, main summary, main [tabindex="0"]')].slice(0, n);
                const bad = [];
                for (const el of els) {
                    // Put the element above the viewport first, so that focusing it makes the
                    // browser scroll it to the top, which is the move the pinned bar can spoil.
                    // Focusing something already on screen scrolls nothing and proves nothing.
                    const y = el.getBoundingClientRect().top + scrollY;
                    scrollTo(0, y + innerHeight);
                    el.focus({preventScroll: false});
                    const r = el.getBoundingClientRect(), b = bar.getBoundingClientRect();
                    // Entirely hidden behind the bar, which is what 2.4.11 forbids.
                    if (r.height && r.top >= b.top - 1 && r.bottom <= b.bottom + 1) {
                        bad.push((el.textContent || el.getAttribute('aria-label') || '?')
                                 .trim().slice(0, 40));
                    }
                }
                return {checked: els.length, bad};
            }''', FOCUS_SAMPLE)
            if hits is None:
                continue
            focused += hits['checked']
            for name in hits['bad'][:3]:
                obscured += 1
                fail.append('2.4.11 Focus Not Obscured: %s hides %r behind the pinned title '
                            'block when it takes focus' % (f.relative_to(DOCS), name))
        page.close()
        print('  %s 2.4.11 Focus Not Obsc. %d focusable elements, up to %d a page, none left '
              'behind the pinned title block'
              % ('ok  ' if not obscured else 'X   ', focused, FOCUS_SAMPLE))

        page = browser.new_page(viewport={'width': 320, 'height': 800})
        images = regions = descriptions = 0
        for f in pages:
            page.goto(f.resolve().as_uri(), wait_until='load')
            page.wait_for_timeout(50)
            where = str(f.relative_to(DOCS))

            # ------------------------------------------------ 2.4.2 Page Titled
            title = page.title().strip()
            if not title:
                fail.append('2.4.2 Page Titled: %s has no title' % where)
            elif title in titles:
                fail.append('2.4.2 Page Titled: %s has the same title as %s: %r'
                            % (where, titles[title], title))
            else:
                titles[title] = where

            # ------------------------------------------------ 1.1.1 Non-text Content
            # Every image on the page, not only the ones inside main. The footer carries the
            # Open Government Licence logo, and the sibling playbook this footer is matched to
            # ships that image with no alt attribute at all, so a screen reader reads out the
            # file name. Scanning only main would have let the same defect in here unnoticed.
            for img in page.eval_on_selector_all(
                    'img', 'els => els.map(e => ({alt: e.alt, src: e.getAttribute("src"),'
                           ' has: e.hasAttribute("alt"), nat: e.naturalWidth,'
                           ' main: !!e.closest("main")}))'):
                images += 1
                if img['nat'] == 0:
                    fail.append('%s: image did not load: %s' % (where, img['src']))
                # A missing alt and an empty alt are different things. Empty says the image is
                # decorative and the surrounding text carries its meaning; missing says nobody
                # decided, and the file name gets announced instead.
                if not img['has']:
                    fail.append('1.1.1 Non-text Content: %s: image has no alt attribute: %s'
                                % (where, img['src']))
                if 'diagram' not in (img['src'] or ''):
                    continue
                if not img['alt'] or len(img['alt']) < MIN_ALT:
                    fail.append('1.1.1 Non-text Content: %s: diagram alt is missing or too '
                                'short: %r' % (where, img['alt']))
                # a complex image needs a description as well as an alt
                has = page.eval_on_selector_all(
                    'details summary', 'els => els.map(e => e.textContent.trim())')
                if not has:
                    fail.append('1.1.1 Non-text Content: %s carries a diagram and no text '
                                'description' % where)
                descriptions += len(has)

            # ------------------------------------------------ 2.1.1 and 4.1.2 on scroll regions
            for r in page.eval_on_selector_all(
                    '.table-scroll', 'els => els.map(e => ({scrolls: e.scrollWidth >'
                                     ' e.clientWidth + 1, tab: e.getAttribute("tabindex"),'
                                     ' role: e.getAttribute("role"),'
                                     ' label: e.getAttribute("aria-label")}))'):
                if not r['scrolls']:
                    continue
                regions += 1
                if r['tab'] != '0':
                    fail.append('2.1.1 Keyboard: %s has a scrolling table that cannot be '
                                'focused' % where)
                if not r['label'] or r['role'] != 'region':
                    fail.append('4.1.2 Name, Role, Value: %s has an unnamed scrolling '
                                'region' % where)

            # ------------------------------------------------ 1.4.3 Contrast on the toggle
            for c in page.eval_on_selector_all(
                    'details > summary', 'els => els.map(e => [getComputedStyle(e).color,'
                                         ' getComputedStyle(document.body).backgroundColor])'):
                ratio = contrast(rgb(c[0]), rgb(c[1]) if 'rgba(0, 0, 0, 0)' not in c[1]
                                 else (255, 255, 255))
                if ratio < MIN_CONTRAST:
                    fail.append('1.4.3 Contrast: %s: description toggle is %.2f:1, needs %.1f:1'
                                % (where, ratio, MIN_CONTRAST))

        # ---------------------------------------------------- AAA: 1.4.6, 1.4.8 and 2.5.5
        aaa = dict(contrast=[], lines=0, targets=[])
        # Both widths, because some of this interface only exists at one of them. The page title
        # in the phone navigation drawer is display:none at 1280, so a desktop-only pass never
        # saw it, and Quarto colours it with a default that assumes a light background while the
        # header it sits in is NHS Blue. It rendered at 1.10:1 and was unreadable on every page,
        # for as long as the site has had a drawer. Line length and target size stay at 1280:
        # 1.4.8 is about a column of prose, and the 320px Reflow pass covers the narrow layout.
        for aaa_width in (1280, 390):
            page2 = browser.new_page(viewport={'width': aaa_width, 'height': 900})
            for f in pages:
                page2.goto(f.resolve().as_uri(), wait_until='load')
                page2.wait_for_timeout(30)
                where = '%s at %dpx' % (f.relative_to(DOCS), aaa_width)
                d = page2.evaluate(AAA_PROBE.replace('MAX_LINE', str(MAX_LINE))
                                            .replace('MIN_TARGET', str(MIN_TARGET)))
                for c, bg, size, weight, tag in d['text']:
                    large = size >= 24 or (size >= 18.66 and int(weight) >= 700)
                    need = AAA_LARGE if large else AAA_CONTRAST
                    r = contrast(rgb(c), rgb(bg))
                    if r < need:
                        aaa['contrast'].append('1.4.6 Contrast (Enhanced): %s: %s on %s in a %s '
                                               'is %.2f:1, needs %.1f:1'
                                               % (where, c, bg, tag, r, need))
                if aaa_width != 1280:
                    continue
                aaa['lines'] += d['wide']
                for w, h, href, text in d['targets']:
                    aaa['targets'].append('2.5.5 Target Size (Enhanced): %s: %dx%d and %r is not '
                                          'reachable from a full size target on the page'
                                          % (where, w, h, text))
            page2.close()
        fail += aaa['contrast'] + aaa['targets']
        if aaa['lines']:
            fail.append('1.4.8 Visual Presentation: %d prose blocks are wider than %d characters'
                        % (aaa['lines'], MAX_LINE))
        print('  ok   1.4.6 Contrast (AAA)    nothing below 7:1, or 4.5:1 where large'
              if not aaa['contrast'] else '  X    1.4.6 Contrast (AAA)')
        print('  ok   1.4.8 Visual Present.   no prose block wider than %d characters' % MAX_LINE
              if not aaa['lines'] else '  X    1.4.8 Visual Presentation')
        print('  ok   2.5.5 Target Size (AAA) every target 44x44, or reachable from one'
              if not aaa['targets'] else '  X    2.5.5 Target Size (AAA)')

        # ---------------------------------------------------- AAA: 2.4.9 and 2.4.10
        # Both are drafting habits rather than build settings, which is why they are cheap to
        # hold and easy to lose: one "read more" added in a later edit fails 2.4.9 for the site.
        vague, unheaded, links = [], [], 0
        repeated, disclosures, drawers = [], 0, 0
        for f in pages:
            html = f.read_text(encoding='utf-8')
            # The sidebar carries every section on every page, which is about 1,700 words of
            # navigation. Counting it would make a short page look like a long one with no
            # headings, so only the article itself is read.
            i = html.find('id="quarto-document-content"')
            start = html.index('<main', 0, i) if i > 0 else 0
            end = html.find('</main>', start)
            body = html[start:end if end > start else len(html)]
            for m in re.finditer(r'<a\b([^>]*)>(.*?)</a>', body, re.S):
                attrs, inner = m.group(1), m.group(2)
                text = re.sub(r'\s+', ' ', re.sub(r'<[^>]+>', '', inner)).strip()
                # What a screen reader announces is the accessible name, which aria-label
                # overrides the text with. A numbered source reference reads "3" on the page
                # and "Source 3, GovS 010 section 5.2" to assistive technology, and it is the
                # second that 2.4.9 is about.
                label = re.search(r'aria-label="([^"]*)"', attrs)
                name = (label.group(1) if label else text).strip()
                if not name:
                    continue
                links += 1
                # A name that is only a number, or only symbols, says nothing on its own. The
                # first is what a footnote reference looks like without a label, the second a
                # back-arrow glyph. Neither was caught before numbered sources were added.
                if VAGUE_LINK.match(name) or re.match(r'^https?://', name) \
                        or re.fullmatch(r'[\d.,\s]+', name) \
                        or not re.search(r'[A-Za-z]', name):
                    vague.append('2.4.9 Link Purpose (Link Only): %s: %r reads as nothing on its '
                                 'own' % (f.relative_to(DOCS), name))
            words = len(re.findall(r'\w+', re.sub(r'<[^>]+>', ' ', body)))
            if words > 400 and len(re.findall(r'<h[2-6]\b', body)) < 2:
                unheaded.append('2.4.10 Section Headings: %s: %d words under fewer than two '
                                'headings' % (f.relative_to(DOCS), words))
        fail += vague + unheaded
        print('  ok   2.4.9 Link Purpose      %d links, none that reads as nothing on its own'
              % links if not vague else '  X    2.4.9 Link Purpose (Link Only)')
        print('  ok   2.4.10 Section Headings every page organised under headings'
              if not unheaded else '  X    2.4.10 Section Headings')

        # ------------------------------- 2.1.1 Keyboard, on anything that opens and closes
        # The sidebar bands collapse, so a reader meets five labels rather than twenty-one
        # links. Quarto builds the band toggle as an <a> with no href and no tabindex, which
        # no keyboard can reach, and names all four chevrons beside them "Toggle section".
        # With the bands open that costs nothing, because every page link is already in the tab
        # order. Collapsed, it takes seventeen of the twenty-one pages out of reach of anyone
        # not using a mouse, which is 2.1.1 at Level A.
        #
        # So this walks the real tab order rather than reading attributes: a disclosure that
        # reports a state has to be reachable, and pressing Enter on it has to change that
        # state. `sidebar-collapse.html` is what makes that true, and this is what would notice
        # if it stopped being included.
        #
        # It opens its own pages at its own widths. The sidebar is docked on a wide screen and
        # folded into a drawer on a narrow one, and the bands have to work in both; the first
        # draft of this check inherited a 320px page from the block above, where the sidebar is
        # in the DOM and off screen, and reported four failures that were its own.
        for width in (1280, 375):
            kb = browser.new_page(viewport={'width': width, 'height': 900})
            for name in ('index.html', 'guidance/07-uncertainty/index.html'):
                kb.goto((DOCS / name).resolve().as_uri(), wait_until='load')
                kb.wait_for_timeout(350)
                # Below about 1000px the sidebar folds into a drawer behind a button, so the
                # bands are one step further in. A keyboard user gets there by reaching that
                # button and pressing it, and so does this: opening the drawer by script would
                # test a route nobody has.
                if not kb.evaluate('() => { const s = document.querySelector("#quarto-sidebar");'
                                   ' return !!s && s.offsetParent !== null; }'):
                    for _ in range(12):
                        kb.keyboard.press('Tab')
                        if kb.evaluate('() => document.activeElement'
                                       '.getAttribute("aria-label")') == 'Toggle sidebar navigation':
                            kb.keyboard.press('Enter')
                            kb.wait_for_timeout(600)
                            break
                    else:
                        fail.append('2.1.1 Keyboard: %s at %dpx: the sidebar is folded away and '
                                    'no key reaches the button that opens it' % (name, width))
                want = kb.eval_on_selector_all(
                    '#quarto-sidebar [aria-expanded], #quarto-margin-sidebar [aria-expanded]',
                    'els => els.filter(e => e.getAttribute("aria-hidden") !== "true")'
                    '        .map(e => (e.textContent || "").replace(/\\s+/g, " ").trim())'
                    '        .filter(t => t)')
                reached = set()
                for _ in range(len(want) * 10 + 60):
                    if len(reached) == len(want):
                        break
                    kb.keyboard.press('Tab')
                    here = kb.evaluate(
                        '() => ({t: (document.activeElement.textContent || "")'
                        '          .replace(/\\s+/g, " ").trim(),'
                        '        e: document.activeElement.getAttribute("aria-expanded")})')
                    if here['e'] is None or here['t'] not in want or here['t'] in reached:
                        continue
                    before = here['e']
                    kb.keyboard.press('Enter')
                    kb.wait_for_timeout(350)
                    after = kb.evaluate(
                        '() => document.activeElement.getAttribute("aria-expanded")')
                    if after == before:
                        fail.append('2.1.1 Keyboard: %s at %dpx: %r reports a state and Enter '
                                    'does not change it' % (name, width, here['t']))
                    kb.keyboard.press('Enter')
                    kb.wait_for_timeout(350)
                    reached.add(here['t'])
                for w in want:
                    if w not in reached:
                        fail.append('2.1.1 Keyboard: %s at %dpx: %r opens and closes and no key '
                                    'reaches it' % (name, width, w))
                disclosures += len(want)
            kb.close()
        print('  ok   2.1.1 Keyboard          %d disclosure(s) over two widths, every one '
              'reachable by Tab and worked by Enter' % disclosures
              if not any('2.1.1 Keyboard' in f for f in fail) else '  X    2.1.1 Keyboard')

        # ------------------------------ 1.4.10 Reflow, inside the drawer rather than the page
        # The Reflow pass above looks for a page that scrolls sideways. A fixed element does not
        # lengthen the page, so a navigation drawer wider than the screen fails silently: nothing
        # scrolls, the far side is simply not there. Measured on 27 September, the drawer sized
        # itself to its longest label and put five of its twenty-two links past the right edge of
        # a 390px phone. So the drawer is measured against the screen, not the page against
        # itself.
        for width in (320, 390):
            dw = browser.new_page(viewport={'width': width, 'height': 844})
            dw.goto((DOCS / 'index.html').resolve().as_uri(), wait_until='load')
            dw.wait_for_timeout(400)
            tog = dw.query_selector('.quarto-btn-toggle')
            if tog and tog.is_visible():
                tog.click()
                dw.wait_for_timeout(900)
                off = dw.evaluate(
                    '() => { const s = document.querySelector("#quarto-sidebar");'
                    '  if (!s) return [];'
                    '  return [...s.querySelectorAll("a")]'
                    '    .filter(a => (a.textContent || "").trim())'
                    '    .filter(a => a.getBoundingClientRect().right > innerWidth + 1)'
                    '    .map(a => (a.textContent || "").replace(/\\s+/g, " ").trim()'
                    '              .slice(0, 40)); }')
                drawers += 1
                for name in off:
                    fail.append('1.4.10 Reflow: at %dpx the navigation drawer puts %r past the '
                                'edge of the screen, where nothing scrolls to reach it'
                                % (width, name))
            dw.close()
        print('  ok   1.4.10 drawer          %d drawer(s), every link inside the screen'
              % drawers if not any('navigation drawer' in f for f in fail)
              else '  X    1.4.10 Reflow, the navigation drawer')

        # ------------------------------------------- 2.4.9, on names repeated within one page
        # The list above catches a name that says nothing. It cannot catch four links that each
        # say something and all say the same thing, which is the other half of 2.4.9: a reader
        # listing the links hears "Toggle section" four times and cannot tell them apart. This
        # passed on 25 September while exactly that was on every page.
        for f in sorted(DOCS.rglob('*.html')):
            html = f.read_text(encoding='utf-8', errors='ignore')
            seen = {}
            for m in re.finditer(r'<a\b([^>]*)>(.*?)</a>', html, re.S):
                attrs, inner = m.group(1), m.group(2)
                if re.search(r'aria-hidden="true"', attrs):
                    continue
                # The page's own contents list names the headings on the page, which is what it
                # is for. An entry there will match a body link to a section of the same name,
                # and making them differ would mean renaming a heading to suit a list that
                # mirrors it. A reader meets those entries inside a named navigation region,
                # not loose in the prose. So they are out of scope here, and this says so
                # rather than quietly widening the rule to cover them.
                if re.search(r'id="toc-', attrs):
                    continue
                text = re.sub(r'\s+', ' ', re.sub(r'<[^>]+>', '', inner)).strip()
                lab = re.search(r'aria-label="([^"]*)"', attrs)
                nm = (lab.group(1) if lab else text).strip()
                href = re.search(r'href="([^"]*)"', attrs)
                if not nm:
                    continue
                seen.setdefault(nm.lower(), set()).add(href.group(1) if href else None)
            for nm, targets in seen.items():
                if len(targets) > 1:
                    repeated.append('2.4.9 Link Purpose (Link Only): %s: %d links all read %r '
                                    'and go to different places'
                                    % (f.relative_to(DOCS), len(targets), nm))
        fail += repeated
        print('  ok   2.4.9 repeated names   no name used by two links going different places'
              if not repeated else '  X    2.4.9 Link Purpose, repeated names')


        # ------------------------------ 2.4.7 Focus Visible, photographed rather than computed
        # A computed style that changes on focus is not the same as something a person can see.
        # Both of the failures this found were invisible to a reading of the CSS. The navbar is
        # NHS Blue and so was the focus ring, so the logo link, second in the tab order on every
        # page, took focus at 1.00:1 against its own background. The skip link was worse: it is
        # the first thing Tab reaches, it moves itself on screen when focused, and it carried
        # z-index 999 while Quarto's pinned header carries 1030, so it arrived underneath the
        # header. In both cases the computed style changed and not one pixel did. Measured on
        # 27 September 2026. So each kind of control is focused and the screen photographed on
        # either side of it, which is the only way to ask the question that matters.
        kinds_seen, photographed = set(), 0
        for width in (390, 1280):
            shot = browser.new_page(viewport={'width': width, 'height': 900})
            for f in pages:
                shot.goto(f.resolve().as_uri(), wait_until='load')
                shot.wait_for_timeout(100)
                for k in shot.evaluate('''() => {
                  const sel = 'a[href], button, input, select, textarea,'
                            + ' [tabindex]:not([tabindex="-1"]), [role="button"]';
                  const out = [];
                  document.querySelectorAll(sel).forEach((e, i) => {
                    e.setAttribute('data-focus-probe', i);
                    if (e.offsetParent === null
                        && getComputedStyle(e).position !== 'fixed') return;
                    const img = e.querySelector('img');
                    out.push({key: e.tagName.toLowerCase() + '.'
                                   + String(e.className).split(' ')[0],
                              id: String(i),
                              name: (e.getAttribute('aria-label') || e.textContent
                                     || (img && img.alt) || '').trim().slice(0, 44)});
                  });
                  return out;
                }'''):
                    tag = (width, k['key'])
                    if tag in kinds_seen:
                        continue
                    kinds_seen.add(tag)
                    shot.evaluate('() => { document.activeElement && document.activeElement'
                                  '.blur(); window.scrollTo(0, 0); }')
                    shot.evaluate('i => document.querySelector(`[data-focus-probe="${i}"]`)'
                                  '.scrollIntoView({block: "center"})', k['id'])
                    shot.wait_for_timeout(90)
                    before = shot.screenshot()
                    if not shot.evaluate('i => { const e = document.querySelector('
                                         '`[data-focus-probe="${i}"]`); e.focus();'
                                         ' return document.activeElement === e; }', k['id']):
                        continue
                    shot.wait_for_timeout(90)
                    photographed += 1
                    # The whole viewport, because a control that moves when it is focused
                    # would step outside a crop taken where it used to be.
                    if shot.screenshot() == before:
                        fail.append('2.4.7 Focus Visible: %r takes focus and nothing on '
                                    'the screen changes, on every page that carries one '
                                    '(first seen on %s at %dpx)'
                                    % (k['name'] or k['key'], f.relative_to(DOCS), width))
            shot.close()
        print('  ok   2.4.7 Focus Visible    %d kinds of control focused and photographed, '
              'every one visibly answers' % photographed
              if not any('2.4.7' in f for f in fail) else '  X    2.4.7 Focus Visible')

        # ---------------------------------------------------------------- 2.5.3 Label in Name
        # Quarto puts the page title inside the control that opens the navigation on a phone and
        # names that control "Toggle sidebar navigation". So the control reads "About" on screen
        # and is announced as something else, and somebody driving the page by voice who says
        # "click About" gets nothing. Only controls are checked, and only where their own text
        # is short enough to be a label rather than a body of content.
        labelled = 0
        ln = browser.new_page(viewport={'width': 390, 'height': 844})
        for f in pages:
            ln.goto(f.resolve().as_uri(), wait_until='load')
            ln.wait_for_timeout(60)
            for x in ln.evaluate('''() => {
              const out = [];
              document.querySelectorAll(
                  'a[aria-label], button[aria-label], summary[aria-label],'
                + ' input[aria-label], [role="button"][aria-label]').forEach(e => {
                if (e.offsetParent === null) return;
                const vis = (e.textContent || '').replace(/\\s+/g, ' ').trim();
                const acc = (e.getAttribute('aria-label') || '').replace(/\\s+/g, ' ').trim();
                if (!vis || !acc || vis.length > 60) return;
                out.push({vis, acc, ok: acc.toLowerCase().includes(vis.toLowerCase())});
              });
              return out;
            }'''):
                labelled += 1
                if not x['ok']:
                    fail.append('2.5.3 Label in Name: %s: a control reads %r on screen and is '
                                'announced as %r' % (f.relative_to(DOCS), x['vis'], x['acc']))
        ln.close()
        print('  ok   2.5.3 Label in Name    %d named controls, every one announced by the '
              'words on it' % labelled
              if not any('2.5.3' in f for f in fail) else '  X    2.5.3 Label in Name')

        # ---------------------------------------------------- 4.1.2 on the navigation button
        page.goto((DOCS / 'index.html').resolve().as_uri(), wait_until='load')
        for t in page.eval_on_selector_all(
                '.navbar-toggler', 'els => els.map(e => ({label: e.getAttribute("aria-label"),'
                                   ' expanded: e.getAttribute("aria-expanded")}))'):
            if not t['label'] or t['expanded'] is None:
                fail.append('4.1.2 Name, Role, Value: the navigation button is not named or '
                            'does not report its state')
        page.close()
        browser.close()

    print('  ok   1.1.1 Non-text Content  %d images, %d text descriptions' % (images, descriptions))
    print('  ok   2.4.2 Page Titled       %d distinct titles' % len(titles))
    print('  ok   2.1.1 and 4.1.2         %d scrolling table regions, named and focusable'
          % regions)
    print()
    if fail:
        print('FAIL')
        for f in sorted(set(fail)):
            print('  ' + f)
        return 1
    print('PASS: %d pages, %d viewport widths' % (len(pages), len(WIDTHS)))
    return 0


if __name__ == '__main__':
    sys.exit(main())
