#!/usr/bin/env python3
"""Check that nothing in a diagram runs over anything else.

    python3 checks/diagram-layout.py

Needs Playwright and a Chromium, the same pair `checks/accessibility.py` already needs.

Six assertions, across every .drawio in `artefacts/service-design`, and in `static/diagrams` if the playbook
carries any:

  1. every cell that carries words carries `whiteSpace=wrap`
  2. no label's text is taller or wider than the box it is drawn in
  3. no text crosses the edge of a shape it does not belong to
  4. no two shapes partly cover each other
  5. no connector runs through a shape it does not join
  6. nothing is drawn outside the canvas

Assertion 1 is the one that was wrong, and it was invisible from the rendered output. The renderer
beside these files lays every label out in a browser, where `overflow-wrap` wraps the words whatever
the style says, so the PNGs and SVGs have always been right. The .drawio files are a deliverable in
their own right: NHSBSA open them in draw.io and import them into Miro, and draw.io wraps a label
only when its style asks it to. The draw.io manual puts it that way round, that line breaks are
possible only with word wrapping enabled and that the way to restore it is to add `whiteSpace=wrap`
to the shape's style. 252 of the 704 cells carrying words did not have it. The worst was a caption
of eighty words in a 1,720px box, which laid out as a single line runs to roughly 2,800px and
straight across everything to its right.

So the first assertion reads the source, and the other five read the render. Neither alone is
enough: the source says what draw.io will do, and the render says what a reader sees.

Assertions 2 to 6 are measured in the browser that lays the text out, not estimated from font
metrics. A guess at the average width of a character in Arial is how a check like this ends up
reporting a problem that is not there, or missing one that is. Chromium knows, so Chromium is
asked: the words' own client rectangle against the box they sit in, every shape's rectangle against
every other, and four hundred points sampled along each connector against every shape.

Two things are deliberately allowed, because both are how these drawings are built:

  - text sitting wholly inside a shape that is not its own. A lane label is a box and a separately
    positioned caption, and a level band is a wide pale rectangle with nodes drawn on top of it.
    Text wholly within a shape is a caption on a panel. Text across a shape's edge is a collision.
  - a shape wholly inside another shape, for the same reason. A partial overlap is a collision.
"""
import json
import pathlib
import re
import sys
import xml.etree.ElementTree as ET

ROOT = pathlib.Path(__file__).resolve().parent.parent
DIRS = [(ROOT / 'static' / 'diagrams', ROOT / 'static' / 'diagrams'),
        (ROOT / 'artefacts' / 'service-design', ROOT / 'artefacts' / 'service-design' / 'png')]

fail, skip = [], []

# Every drawn thing's geometry, read out of the laid-out document rather than calculated.
MEASURE = r"""() => {
  // The outermost <g> under the <svg> is one drawn object: a shape and its own label. A rhombus
  // nests its label in an inner <g transform>, so comparing immediate parents misses the pairing.
  const top = el => { let n = el; while (n.parentElement && n.parentElement.tagName !== 'svg')
                        n = n.parentElement; return n; };
  const R = el => { const b = el.getBoundingClientRect();
    return {x:b.left, y:b.top, w:b.width, h:b.height, r:b.right, b:b.bottom}; };
  const over = (a,b) => Math.max(0, Math.min(a.r,b.r)-Math.max(a.x,b.x))
                      * Math.max(0, Math.min(a.b,b.b)-Math.max(a.y,b.y));
  const holds = (o,i) => i.x >= o.x-0.5 && i.y >= o.y-0.5 && i.r <= o.r+0.5 && i.b <= o.b+0.5;

  const svg = document.querySelector('svg');
  const page = [...svg.children].filter(e => e.tagName === 'rect');
  const shapes = [], wires = [];
  svg.querySelectorAll('rect, path').forEach(el => {
    if (page.includes(el)) return;
    const fill = el.getAttribute('fill');
    if (el.tagName === 'path' && (!fill || fill === 'none') && el.getAttribute('stroke')) {
      wires.push(el); return;                                  // a connector: stroke, no fill
    }
    if (!fill || fill === 'none') return;
    if (el.tagName === 'rect' && el.getAttribute('rx') === '3' &&
        el.parentElement && el.parentElement.querySelector('foreignObject')) return;  // edge chip
    if (el.tagName === 'path' && !el.getAttribute('stroke-width')) return;            // arrow head
    shapes.push({el, box: R(el), group: top(el)});
  });

  const labels = [];
  svg.querySelectorAll('foreignObject').forEach(fo => {
    const frame = fo.firstElementChild; if (!frame) return;
    const t = frame.firstElementChild || frame;
    const words = (t.textContent || '').trim();
    if (!words) return;
    // The drawn extent of the words themselves, not of the box they are centred in.
    const range = document.createRange(); range.selectNodeContents(t);
    const rs = [...range.getClientRects()];
    const ink = rs.length
      ? {x: Math.min(...rs.map(r=>r.left)), y: Math.min(...rs.map(r=>r.top)),
         r: Math.max(...rs.map(r=>r.right)), b: Math.max(...rs.map(r=>r.bottom))}
      : R(t);
    ink.w = ink.r - ink.x; ink.h = ink.b - ink.y;
    labels.push({fo, ink, group: top(fo), words: words.slice(0, 64),
                 boxW: fo.width.baseVal.value, boxH: fo.height.baseVal.value,
                 textH: t.getBoundingClientRect().height,
                 scrollW: t.scrollWidth, clientW: t.clientWidth});
  });

  const spill = labels.filter(l => l.textH > l.boxH + 0.5 || l.scrollW > l.clientW + 0.5)
    .map(l => ({words: l.words, boxW:+l.boxW.toFixed(0), boxH:+l.boxH.toFixed(0),
                textH:+l.textH.toFixed(0)}));

  const across = [];
  labels.forEach(l => shapes.forEach(s => {
    if (s.group === l.group) return;
    if (over(l.ink, s.box) <= 1) return;
    if (holds(s.box, l.ink)) return;                           // a caption on a panel
    across.push({words: l.words, shape: {w:+s.box.w.toFixed(0), h:+s.box.h.toFixed(0)},
                 text: (s.group.textContent || '').trim().slice(0, 40)});
  }));

  const clash = [];
  for (let i = 0; i < shapes.length; i++)
    for (let j = i + 1; j < shapes.length; j++) {
      const a = shapes[i], b = shapes[j];
      if (a.group === b.group) continue;
      if (over(a.box, b.box) <= 1) continue;
      if (holds(a.box, b.box) || holds(b.box, a.box)) continue;   // one panel inside another
      clash.push({area: +over(a.box, b.box).toFixed(0),
                  a: (a.group.textContent || '').trim().slice(0, 34),
                  b: (b.group.textContent || '').trim().slice(0, 34)});
    }

  const through = [];
  const o = svg.getBoundingClientRect();
  wires.forEach(w => {
    let L; try { L = w.getTotalLength(); } catch (e) { return; }
    if (!L) return;
    const pts = [];
    for (let s = 0; s <= L; s += Math.max(2, L / 400)) pts.push(w.getPointAtLength(s));
    shapes.forEach(sh => {
      // The shapes a connector touches at either end are the ones it joins.
      const ends = q => q.x + o.x >= sh.box.x - 6 && q.x + o.x <= sh.box.r + 6 &&
                        q.y + o.y >= sh.box.y - 6 && q.y + o.y <= sh.box.b + 6;
      if (ends(pts[0]) || ends(pts[pts.length - 1])) return;
      let n = 0;
      pts.forEach(q => { const X = q.x + o.x, Y = q.y + o.y;
        if (X > sh.box.x + 1.5 && X < sh.box.r - 1.5 && Y > sh.box.y + 1.5 && Y < sh.box.b - 1.5) n++; });
      if (n > 1) through.push({points: n, of: pts.length,
                               text: (sh.group.textContent || '').trim().slice(0, 40)});
    });
  });

  const vb = svg.viewBox.baseVal, outside = [];
  const beyond = (b, what) => {
    const x = b.x - o.x, y = b.y - o.y;
    if (x < -0.5 || y < -0.5 || x + b.w > vb.width + 0.5 || y + b.h > vb.height + 0.5)
      outside.push({what, x:+x.toFixed(0), y:+y.toFixed(0), w:+b.w.toFixed(0), h:+b.h.toFixed(0)});
  };
  labels.forEach(l => beyond(l.ink, l.words));
  shapes.forEach(s => beyond(s.box, (s.group.textContent || '').trim().slice(0, 40) || 'a shape'));

  return {spill, across, clash, through, outside,
          labels: labels.length, shapes: shapes.length, wires: wires.length};
}"""


def wrapping():
    """Assertion 1. Read out of the source, because it is draw.io's behaviour that is at stake."""
    bare, cells = [], 0
    for src, _ in DIRS:
        for f in sorted(src.glob('*.drawio')):
            for c in ET.parse(f).getroot().iter('mxCell'):
                words = re.sub(r'<[^>]+>', ' ', c.get('value') or '').strip()
                if not words:
                    continue
                cells += 1
                if 'whiteSpace=wrap' not in (c.get('style') or ''):
                    bare.append((f.name, len(words.split()), words[:52]))
    if bare:
        fail.append('%d cell(s) carry words and do not wrap. draw.io lays each of them out as one '
                    'line, however wide the box is, so NHSBSA open a drawing we have never seen:'
                    % len(bare))
        for name, n, words in sorted(bare, key=lambda b: -b[1])[:8]:
            fail.append('      %-40s %3d words | %s' % (name, n, words))
        if len(bare) > 8:
            fail.append('      ... and %d more' % (len(bare) - 8))
    return cells


def measure():
    """Assertions 2 to 6, in the browser that lays the diagrams out."""
    from playwright.sync_api import sync_playwright
    exe = next((p for p in ('/opt/pw-browsers/chromium',
                            '/opt/pw-browsers/chromium-1194/chrome-linux/chrome')
                if pathlib.Path(p).exists()), None)
    seen = {}
    with sync_playwright() as pw:
        browser = pw.chromium.launch(executable_path=exe) if exe else pw.chromium.launch()
        for src, out in DIRS:
            for f in sorted(src.glob('*.drawio')):
                svg = out / (f.stem + '.svg')
                if not svg.exists():
                    fail.append('%s has no rendered .svg beside it, so its layout cannot be '
                                'measured' % f.name)
                    continue
                # The window is the size of the drawing. A drawing with no width and height of its
                # own fills whatever window it is opened in, so a bigger window would scale it and
                # every label would measure larger than the box it was drawn in.
                vb = re.search(r'viewBox="0 0 (\d+) (\d+)"', svg.read_text(encoding='utf-8'))
                size = {'width': int(vb.group(1)), 'height': int(vb.group(2))} if vb else {
                    'width': 2400, 'height': 1800}
                page = browser.new_page(viewport=size)
                page.goto(svg.resolve().as_uri(), wait_until='load')
                page.wait_for_timeout(70)
                seen[svg.name] = page.evaluate(MEASURE)
                page.close()
        browser.close()

    if not seen:
        fail.append('no diagrams were measured, so none of the assertions below tested anything')
        return seen
    if not any(v['labels'] for v in seen.values()):
        fail.append('not one label was found in any diagram. Nought labels means the search for '
                    'them is wrong, not that the diagrams have no words in them, and every '
                    'assertion below it would pass without testing anything')
        return seen

    def report(key, line):
        hits = [(name, h) for name, v in seen.items() for h in v[key]]
        if not hits:
            return
        fail.append('%d %s' % (len(hits), line))
        for name, h in hits[:8]:
            fail.append('      %-40s %s' % (name, json.dumps(h)))
        if len(hits) > 8:
            fail.append('      ... and %d more' % (len(hits) - 8))

    report('spill', 'label(s) whose text is bigger than the box it is drawn in')
    report('across', 'label(s) whose words cross the edge of a shape they do not belong to')
    report('clash', 'pair(s) of shapes that partly cover each other')
    report('through', 'connector(s) that run through a shape they do not join')
    report('outside', 'thing(s) drawn outside the canvas, where they are cropped')
    return seen


def main():
    cells = wrapping()
    try:
        import playwright.sync_api  # noqa: F401
    except ImportError:
        skip.append('the layout was not measured: Playwright is not installed here')
        seen = {}
    else:
        seen = measure()

    for s in skip:
        print('  --  %s' % s)
    if fail:
        print('diagram layout FAILED')
        for f in fail:
            print('  X   %s' % f if not f.startswith('    ') else f)
        sys.exit(1)
    print('  ok  %d cell(s) carry words, every one of them wrapping' % cells)
    if seen:
        print('  ok  %d label(s) across %d diagram(s), none bigger than the box it sits in'
              % (sum(v['labels'] for v in seen.values()), len(seen)))
        print('  ok  no words cross a shape they do not belong to')
        print('  ok  %d shape(s), no two of them partly covering each other'
              % sum(v['shapes'] for v in seen.values()))
        print('  ok  %d connector(s), none running through a shape it does not join'
              % sum(v['wires'] for v in seen.values()))
        print('  ok  nothing is drawn outside the canvas')


if __name__ == '__main__':
    main()
