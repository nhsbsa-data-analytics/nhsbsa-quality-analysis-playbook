#!/usr/bin/env python3
"""Check that the diagrams the playbook carries are what it says they are, and that the service
design board which quotes the role pages still does.

    python3 checks/diagrams.py

The playbook carries six diagrams, each written by `build/diagrams.py` as a draw.io source and
rendered by `build/render-diagrams.py`. NHSBSA asked for visuals that support understanding of
processes, decisions and actions, and for those that only describe the structure of the content to
go. An earlier set of twelve was removed because each one repeated a table or list beside it, at a
size nobody could read. These six are where a picture is quicker than the words: a circuit, a
decision with three outcomes, a sequence of handoffs, a grid of when each step happens, the matrix
that gives a level, and a grid of who owns which document. Each carries the steps, so the page says
less, and the full wording sits in an expander under it. A list of steps or documents stays a list.

With no diagram on disk:

  0. nothing refers to a diagram that is not there: no `diagram-*` partial, no page that includes
     one, no reference to a file under `static/diagrams`

With one or more:

  1. every diagram on disk is referenced by a page or a partial
  2. every reference resolves to a file that exists
  3. every diagram has both a .png, which the page embeds, and a .svg, which it links to full size
  4. the numbering runs 01 upward with no gaps and no duplicates
  5. every partial named `diagram-*` actually carries a picture
  6. every one of those partials is included by a page, so the picture reaches a reader
  6. where a diagram has a .drawio source, re-rendering it reproduces the committed .svg
  7. every diagram's own title, the one drawn across the top of the picture, is in its alt text
  9. every diagram is simple enough to read at a glance and large enough to read: drawn on a 680px
     canvas, which the page shows at its own size, with no label under 14px, and within a budget
     of 90 words and 20 boxes
  10. the text in every drawing, the playbook's six and the eleven service design boards, reaches
     7:1 on the fill it sits on, as the site's text does. The boards were drawn with a grey that
     read 3.8:1 on white at 10px, in 5 to 11 places on each of them
  11. the assurance level matrix drawing gives each of the sixteen impact and likelihood pairs the
     level the matrix table on the Read your level page gives it

Always, where `build/` is present:

  8. every cell of the phases-and-roles board is still a line of the phase page it claims to copy

Assertion 1 is the one that caused this file to exist. An inventory that read only the partials
reported `bca-documentation-stack` as used by nothing, because that one diagram was embedded
directly in section 8 rather than through a partial like the other twenty-four. It was one step
from being archived as dead. A scan that looks in one place is not a scan.

Assertion 4 exists because the numbering had drifted into fiction. The set ran 13 to 42 with 14,
18 and 20 to 23 missing, so the highest number was 42 and the number of diagrams was 25. Anybody
counting the playbook's diagrams by looking at the files would have been wrong by seventeen.

Assertion 5 exists because six partials called `diagram-*` held no picture at all. They are tables,
and good ones, but counting them made the playbook look as though it carried thirty diagrams when
it carried twenty-five. They are `table-*` now, and this keeps it that way.

Assertion 7 is the one a length test could never catch. Each of these drawings opens with a title
set at 20px across the top, written as the question the reader arrives with: "Does the playbook
apply to this at all?", "Where a disagreement goes", "Deciding the assurance level". Twenty one of
the twenty five had that sentence nowhere in their text alternative, and four more carried it only
inside the collapsed description rather than in the alt text. That is text inside a raster image
with no equivalent, which is 1.1.1 Non-text Content at Level A, and nothing could see it: axe reads
the page, not the pixels, and `checks/accessibility.py` tests alt text against a minimum *length*,
which every one of them passed. The title is in the .drawio source as a string, so the alt text can
be checked against the picture rather than against a word count.

Assertion 8 exists because the board said one thing and the page said another for a fortnight.
`build/build-service-design.py` declares each cell of the phases-and-roles grid to be the matching
row of "Who does what in this phase" on that phase's own page, shortened to the length a wall
reads at. Two of them said "score the assurance level" and "agree the assurance level" long after
the pages moved to "score the impact" and "agree the impact score", because the claim was a
comment and nothing tested it. A service design board is the artefact NHSBSA takes into a workshop, so a
board that contradicts the guidance is worse than no board.

The test is substring, not equality: a cell is the row cut at a sentence or clause boundary, so it
has to appear in the row but need not be all of it. Trailing full stops and whitespace are
normalised, because a cell ends a sentence where a table cell does not. A cell that paraphrases
rather than quotes fails, which is the point: paraphrase is how the drift happened.

Assertions 6 and 8 need `build/`, which the release package does not carry, so they are skipped
there and say so rather than passing quietly.

It is also only the second link in a chain of three, and on its own it was not enough. A
`.drawio` that matches the `.svg` beside it can still be stale, because both are downstream of
`build/diagrams.py`, which writes the `.drawio` in the first place. That is what
`checks/generated.py` asserts, and it exists because the gap shipped a wrong picture. The PNGs are deliberately not compared: they are rasterised,
and two rasterisers differ on anti-aliasing by a percent or two of pixels without either being
wrong. The SVG is the exact artefact, so that is what is compared.
"""
import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
DIAG = ROOT / 'static' / 'diagrams'
PART = ROOT / 'guidance' / '_partials'
SKIP_DIRS = {'docs', '_site', '.quarto', '__pycache__', 'dist', 'review', 'artefacts', '.git'}

fail, skip = [], []


def scanned_files():
    for f in sorted(ROOT.rglob('*')):
        if not f.is_file() or f.suffix not in {'.qmd', '.md', '.html', '.css', '.yml', '.py'}:
            continue
        if SKIP_DIRS & set(f.parts):
            continue
        yield f


CANVAS_W = 680      # the width the page shows a diagram at, so a label is shown at the size drawn
MIN_LABEL_PX = 14   # the smallest label, where the page text is 20.8px
MAX_WORDS = 90      # visible words in one drawing, the title included
MAX_BOXES = 20      # labelled boxes in one drawing


def label_sizes(value, style_px):
    """Every run of words in a label, with the font size it is drawn at.

    A label is HTML. A run of words takes the size of the nearest enclosing element that sets one,
    and the cell's own style where none does, which is 11px for a plain box and is how a caption
    written without a size ends up the smallest thing in a drawing.
    """
    from html.parser import HTMLParser

    runs, stack = [], [style_px]

    class P(HTMLParser):
        def handle_starttag(self, tag, attrs):
            m = re.search(r'font-size:\s*(\d+)px', dict(attrs).get('style') or '')
            if tag not in ('br', 'img'):
                stack.append(int(m.group(1)) if m else stack[-1])

        def handle_endtag(self, tag):
            if tag not in ('br', 'img') and len(stack) > 1:
                stack.pop()

        def handle_data(self, data):
            if data.strip():
                runs.append((data.strip(), stack[-1]))

    P().feed(value)
    return runs


def check_simple(sources):
    """Assertion 9. Simple enough to read at a glance, and large enough to read.

    A diagram earns its place by being quicker than the text it replaces. The first set of twelve
    was drawn on a 1,600px canvas with labels of 10 to 15px and shown at about 930px, so the
    smallest label reached the reader at about 6px, and most of them held a table's worth of words.
    The limits here are what the replacements are drawn to: the canvas is the width the page shows
    them at, no label is under 14px, and a drawing that needs more than 90 words or 20 boxes is a
    table with boxes round it and belongs on the page as one.
    """
    import xml.etree.ElementTree as ET
    stats = []
    for s in sources:
        root = ET.parse(s).getroot()
        model = root.find('.//mxGraphModel')
        if int(model.get('pageWidth')) != CANVAS_W:
            fail.append('%s is drawn %s px wide. The page shows a diagram at %d px, so any other '
                        'width is shrunk or stretched and its labels are not the size they were '
                        'drawn' % (s.name, model.get('pageWidth'), CANVAS_W))
        words, boxes, smallest = 0, 0, 99
        for cell in model.iter('mxCell'):
            value = cell.get('value') or ''
            if not re.sub(r'<[^>]+>', '', value).strip():
                continue
            st = dict(kv.split('=', 1) for kv in (cell.get('style') or '').split(';') if '=' in kv)
            style_px = int(float(st.get('fontSize', 11)))
            for text, px in label_sizes(value, style_px):
                words += len(text.split())
                smallest = min(smallest, px)
            if cell.get('vertex') == '1':
                boxes += 1
        stats.append((s.name, words, boxes, smallest))
        if smallest < MIN_LABEL_PX:
            fail.append('%s has a label drawn at %dpx. Nothing in a diagram is under %dpx, because '
                        'the page shows it at the size it was drawn' % (s.name, smallest, MIN_LABEL_PX))
        if words > MAX_WORDS:
            fail.append('%s carries %d words, over the %d a diagram is allowed. Move the wording '
                        'to the text description under it, or put it on the page as a table'
                        % (s.name, words, MAX_WORDS))
        if boxes > MAX_BOXES:
            fail.append('%s has %d boxes, over the %d a diagram is allowed. A drawing with that many '
                        'is not simple to read at a glance' % (s.name, boxes, MAX_BOXES))
    return stats


def _lum(hexcol):
    v = [int(hexcol[i:i + 2], 16) / 255 for i in (1, 3, 5)]
    v = [x / 12.92 if x <= 0.04045 else ((x + 0.055) / 1.055) ** 2.4 for x in v]
    return 0.2126 * v[0] + 0.7152 * v[1] + 0.0722 * v[2]


def _ratio(a, b):
    la, lb = _lum(a), _lum(b)
    return (max(la, lb) + 0.05) / (min(la, lb) + 0.05)


def _run_colours(value, base):
    """The colour of every run of words in a label: the nearest enclosing inline colour, else the
    cell's own fontColor."""
    from html.parser import HTMLParser
    out, stack = set(), [base]

    class P(HTMLParser):
        def handle_starttag(self, tag, attrs):
            if tag in ('br', 'img'):
                return
            m = re.search(r'(?<![-\w])color:\s*(#[0-9A-Fa-f]{6})', dict(attrs).get('style') or '')
            stack.append(m.group(1) if m else stack[-1])

        def handle_endtag(self, tag):
            if tag not in ('br', 'img') and len(stack) > 1:
                stack.pop()

        def handle_data(self, data):
            if data.strip():
                out.add(stack[-1])

    P().feed(value)
    return out


def check_text_contrast(sources, floor):
    """Assertion 10. Every run of text in a drawing against the fill it sits on.

    A label's colour is its cell's fontColor, or an inline colour on a run inside it. The fill is
    the cell's own, or, for a label with none, the smallest filled box that contains the label's
    middle, or white. Boxes are read from the same file, so the check needs nothing rendered."""
    import xml.etree.ElementTree as ET
    low = []
    checked = 0
    for src in sources:
        root = ET.parse(src).getroot()
        cells = []
        for c in root.iter('mxCell'):
            if c.get('vertex') != '1':
                continue
            g = c.find('mxGeometry')
            if g is None:
                continue
            st = dict(kv.split('=', 1) for kv in (c.get('style') or '').split(';') if '=' in kv)
            cells.append((float(g.get('x') or 0), float(g.get('y') or 0), float(g.get('width') or 0),
                          float(g.get('height') or 0), st, c.get('value') or ''))
        fills = [(x, y, w, h, st.get('fillColor')) for x, y, w, h, st, _ in cells
                 if (st.get('fillColor') or '').startswith('#') and w and h]
        for x, y, w, h, st, value in cells:
            text = re.sub(r'<[^>]+>', '', value).strip()
            if not text:
                continue
            fill = st.get('fillColor') if (st.get('fillColor') or '').startswith('#') else None
            if fill is None:
                cx, cy = x + w / 2, y + h / 2
                inside = [(fw * fh, col) for fx, fy, fw, fh, col in fills
                          if fx <= cx <= fx + fw and fy <= cy <= fy + fh]
                fill = min(inside)[1] if inside else '#FFFFFF'
            for col in _run_colours(value, st.get('fontColor', '#231F20')):
                checked += 1
                r = _ratio(col, fill)
                if r < floor:
                    low.append((src.name, col, fill, round(r, 2), text[:24]))
    return low, checked


def check_set(stems):
    # manifest.json is written beside the renders by render-diagrams.py and is not a
    # diagram. Counting it would report it as an unreferenced file for ever.
    refs = {}
    for f in scanned_files():
        txt = f.read_text(encoding='utf-8', errors='ignore')
        for m in re.findall(r'/static/diagrams/([A-Za-z0-9-]+)\.(?:png|svg|drawio)', txt):
            refs.setdefault(m, set()).add(str(f.relative_to(ROOT)))

    for s in stems:                                                           # 1
        if s not in refs:
            fail.append('%s is on disk and nothing references it. Either a page lost its picture '
                        'or the file is dead' % s)
    for s in sorted(set(refs) - set(stems)):                                  # 2
        fail.append('%s is referenced by %s and is not on disk'
                    % (s, ', '.join(sorted(refs[s]))))
    for s in stems:                                                           # 3
        for ext in ('png', 'svg'):
            if not (DIAG / ('%s.%s' % (s, ext))).exists():
                fail.append('%s has no .%s. The page embeds the PNG and links the SVG full size, '
                            'so a reader loses one or the other' % (s, ext))

    nums = sorted(int(s.split('-')[0]) for s in stems if s[:2].isdigit())     # 4
    if len(nums) != len(stems):
        fail.append('%d of %d diagrams do not start with a number'
                    % (len(stems) - len(nums), len(stems)))
    expected = list(range(1, len(stems) + 1))
    if nums != expected:
        gaps = sorted(set(expected) - set(nums))
        dupes = sorted({n for n in nums if nums.count(n) > 1})
        fail.append('the numbering is %s, not 01 to %02d. Missing: %s. Duplicated: %s'
                    % ('%02d to %02d' % (min(nums), max(nums)) if nums else 'empty', len(stems),
                       ', '.join('%02d' % g for g in gaps) or 'none',
                       ', '.join('%02d' % d for d in dupes) or 'none'))

    for p in sorted(PART.glob('diagram-*.qmd')):                              # 5
        if '/static/diagrams/' not in p.read_text(encoding='utf-8'):
            fail.append('%s is named as a diagram and carries no picture. If it is a table, name '
                        'it table-*, so counting the diagrams gives the number of diagrams'
                        % p.name)

    import xml.etree.ElementTree as ET                                        # 7
    import unicodedata

    def flatten(s):
        s = unicodedata.normalize('NFKC', s).replace('\u2019', "'")
        return re.sub(r'\s+', ' ', s).strip().lower()

    def drawn_title(src):
        """The topmost 20px label, which is how `title()` in build/drawio.py writes a title."""
        best = None
        for cell in ET.parse(src).getroot().iter('mxCell'):
            value = cell.get('value') or ''
            if 'font-size:20px' not in value:
                continue
            geo = cell.find('mxGeometry')
            y = float(geo.get('y') or 0) if geo is not None else 0.0
            words = re.sub(r'<[^>]+>', '', value)
            for entity, char in (('&#39;', "'"), ('&amp;', '&'), ('&quot;', '"'),
                                 ('&nbsp;', ' '), ('&lt;', '<'), ('&gt;', '>')):
                words = words.replace(entity, char)
            words = re.sub(r'\s+', ' ', words).strip()
            if words and (best is None or y < best[0]):
                best = (y, words)
        return best[1] if best else None

    alts, titled = {}, 0
    for f in scanned_files():
        if f.suffix != '.qmd':
            continue
        for stem, alt in re.findall(
                # The picture carries the NHS images component's class before its alt
                # text, so anything but a closing brace may sit between the two.
                r'/static/diagrams/([A-Za-z0-9-]+)\.png\)\{[^}]*fig-alt="([^"]*)"',
                f.read_text(encoding='utf-8')):
            alts.setdefault(stem, []).append(alt)
    for src in sorted(DIAG.glob('*.drawio')):
        title = drawn_title(src)
        if not title:
            continue
        titled += 1
        found = alts.get(src.stem)
        if not found:
            fail.append('%s is drawn with the title %r and no figure embeds it with alt text'
                        % (src.stem, title[:60]))
        elif not any(flatten(title) in flatten(a) for a in found):
            fail.append('%s is drawn with the title %r across the top of the picture, and that '
                        'sentence is in no alt text for it. A reader who cannot see the picture '
                        'never gets the question it answers' % (src.stem, title[:60]))

    sources = sorted(DIAG.glob('*.drawio'))                                   # 6
    if not (ROOT / 'build').is_dir():
        skip.append('the .drawio sources were not re-rendered: build/ is not in the release '
                    'package, so the renderer is not here')
    elif not sources:
        skip.append('no .drawio sources to re-render')
    else:
        import importlib.util
        import shutil
        import tempfile
        spec = importlib.util.spec_from_file_location('rd', ROOT / 'build' / 'render-diagrams.py')
        rd = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(rd)
        with tempfile.TemporaryDirectory() as tmp:
            src = pathlib.Path(tmp) / 'src'
            out = pathlib.Path(tmp) / 'out'
            src.mkdir()
            out.mkdir()
            for s in sources:
                shutil.copy(s, src / s.name)
            rd.main(src=src, out=out)
            for s in sources:
                fresh = out / (s.stem + '.svg')
                live = DIAG / (s.stem + '.svg')
                if not fresh.exists():
                    fail.append('%s did not render' % s.name)
                elif fresh.read_bytes() != live.read_bytes():
                    fail.append('%s does not match its source. The .drawio has been edited and '
                                'the .svg beside it has not been rebuilt' % live.name)

    simple = check_simple(sources) if sources else []

    for s in skip:
        print('  --  %s' % s)
    if fail:
        print('diagrams FAILED')
        for f in fail:
            print('  X   %s' % f)
        sys.exit(1)
    print('  ok  %d diagrams, numbered 01 to %02d with no gaps' % (len(stems), len(stems)))
    # Assertion 6. A partial nothing includes is a diagram nobody sees.
    #
    # Assertion 1 asks whether a diagram is referenced, and a partial referencing it satisfies
    # that. It says nothing about whether any page includes the partial. The restructure to five
    # phases deleted the sections that included three of them, and all five assertions above
    # still passed while the lifecycle diagram, the review cycle and the recurring output were on
    # no page at all. The PDF build caught it, by counting descriptions that reached paper, which
    # is a long way downstream of the mistake.
    pages = [f for f in sorted(ROOT.glob('guidance/*/*.qmd'))] + [ROOT / 'index.qmd']
    included = set()
    for f in pages:
        if f.is_file():
            for m in re.finditer(r'_partials/(diagram-[\w-]+)\.qmd', f.read_text(encoding='utf-8')):
                included.add(m.group(1))
    orphans = sorted(f.stem for f in sorted(PART.glob('diagram-*.qmd'))
                     if f.stem not in included)
    if orphans:
        print('diagrams FAILED')
        print('  X   %d diagram partial(s) are included by no page, so the picture and its text '
              'description reach nobody: %s' % (len(orphans), ', '.join(orphans)))
        sys.exit(1)

    print('  ok  every one referenced by a page or a partial, every reference resolving')
    print('  ok  all %d diagram partial(s) are included by a page' % len(included))
    print('  ok  every one has a PNG to embed and an SVG to open full size')
    print('  ok  every diagram-* partial carries a picture')
    if not titled:
        raise SystemExit('no diagram was found to carry a drawn title, so assertion 7 tested '
                         'nothing. The title is written by title() in build/drawio.py at 20px')
    print('  ok  all %d drawn titles appear in the alt text of the figure that embeds them'
          % titled)
    if sources and (ROOT / 'build').is_dir():
        print('  ok  %d .drawio source(s) re-render to the committed SVG' % len(sources))
    if simple:
        print('  ok  %d diagram(s) drawn at %dpx, no label under %dpx, at most %d words (most: %d) '
              'and %d boxes (most: %d)'
              % (len(simple), CANVAS_W, MIN_LABEL_PX, MAX_WORDS, max(s[1] for s in simple),
                 MAX_BOXES, max(s[2] for s in simple)))


def check_board():
    """Assertion 8. The phases-and-roles board quotes the role pages, so it has to still quote them."""
    builder = ROOT / 'build' / 'build-service-design.py'
    if builder.is_file():
        # The five phase pages each carry a "Who does what in this phase" table, one row per role,
        # and the board's lane cells run in phase order. A cell is checked against the row for
        # its own role on the page for its own phase, so a cell that is true of a different phase
        # fails as well as one that paraphrases.
        phases = ['01-engagement-and-scoping', '02-design', '03-analysis',
                  '04-delivery-and-sign-off', '05-review']
        roles = ['Analyst', 'Critical friend', 'Commissioner',
                 'Analysis Senior Responsible Officer']
        tidy = lambda s: re.sub(r'\s+', ' ', s).strip().rstrip('.')
        rows = {}
        for ph in phases:
            page = (ROOT / 'guidance' / ph / 'index.qmd').read_text(encoding='utf-8')
            table = page.split('## Who does what in this phase', 1)[-1]
            for m in re.finditer(r'^\|\s*\*\*([^*|]+)\*\*\s*\|\s*(.+?)\s*\|\s*$', table, re.M):
                rows[(ph, m.group(1).strip())] = tidy(m.group(2))
        src = builder.read_text(encoding='utf-8')
        grid = re.search(r'^GRID\s*=\s*dict\(', src, re.M)
        if grid is None:
            print('diagrams FAILED')
            print('  X   build/build-service-design.py no longer defines GRID, so nothing holds '
                  'the phases-and-roles board to the pages it quotes')
            sys.exit(1)
        block = src[grid.end():]
        end = re.search(r'\n\S', block)
        block = block[:end.start()] if end else block
        checked = 0
        quoted = re.compile(r"'((?:[^'\\]|\\.)*)'")
        for name in roles:
            lane = re.search(r"dict\(name='%s'.*?cells=\[(.*?)\]\)" % re.escape(name),
                             block, re.S)
            if lane is None:
                fail.append('the phases-and-roles board has no %s lane, so five of its cells '
                            'are no longer read against the phase pages' % name)
                continue
            cells = [''.join(quoted.findall(c))
                     for c in re.split(r',\s*\n', lane.group(1))]
            cells = [c.strip() for c in cells if c.strip()]
            if len(cells) != len(phases):
                fail.append('the %s lane has %d cell(s) and there are %d phases'
                            % (name, len(cells), len(phases)))
                continue
            for ph, cell in zip(phases, cells):
                checked += 1
                row = rows.get((ph, name))
                if row is None:
                    fail.append('guidance/%s/index.qmd has no "Who does what in this phase" row '
                                'for the %s' % (ph, name))
                elif tidy(cell) not in row:
                    fail.append('the phases-and-roles board puts %r in the %s lane under %s, and '
                                'that page\'s row for the role does not say it. The board quotes '
                                'the phase pages; a cell that paraphrases one is how it last went '
                                'out of step' % (cell[:70], name, ph))
        if fail:
            print('diagrams FAILED')
            for f in fail:
                print('  X   %s' % f)
            sys.exit(1)
        print('  ok  all %d phases-and-roles cell(s) still quote their role page' % checked)


def check_matrix():
    """Assertion 11. The matrix picture gives every combination the level the matrix table gives it.

    The picture and the table beside it are the same sixteen facts, drawn twice, and the picture
    merges neighbouring cells that agree, so a wrong level in one of them is a wrong level for a
    run of likelihoods and nothing on the page looks off. The picture is read back to sixteen
    (impact, likelihood) pairs from where its boxes sit under its own column and row headings, and
    each pair is held against the table. A level that drifted in one place and not the other is
    the one fault in this playbook that sends somebody to the wrong amount of assurance."""
    import html
    import xml.etree.ElementTree as ET
    src = DIAG / '05-assurance-level-matrix.drawio'
    page = ROOT / 'guidance' / '07-deciding-your-assurance-level' / 'read-your-level.qmd'
    if not src.is_file() or not page.is_file():
        print('diagrams FAILED')
        print('  X   the assurance level matrix has to be drawn as well as tabled: %s or %s is '
              'missing' % (src.relative_to(ROOT), page.relative_to(ROOT)))
        sys.exit(1)
    text = page.read_text(encoding='utf-8')
    if 'diagram-assurance-level-matrix.qmd' not in text:
        fail.append('read-your-level.qmd does not include the matrix diagram')

    tabled = {}
    for m in re.finditer(r'^\|\s*\*\*(\d)\s[^*]+\*\*\s*\|(.+)\|\s*$', text, re.M):
        cells = [c.strip() for c in m.group(2).split('|')]
        for lik, cell in enumerate(cells, start=1):
            level = re.match(r'Level (\d)\b', cell)
            if level:
                tabled[(int(m.group(1)), lik)] = int(level.group(1))
    if len(tabled) != 16:
        fail.append('read-your-level.qmd tables %d of the 16 impact and likelihood pairs' % len(tabled))

    heads = {'likelihood': {}, 'impact': {}}
    levels = []
    for cell in ET.parse(src).getroot().iter('mxCell'):
        geo = cell.find('mxGeometry')
        if cell.get('vertex') != '1' or geo is None:
            continue
        words = html.unescape(re.sub(r'<[^>]+>', '', re.sub(r'<br\s*/?>', ' ', cell.get('value') or '')))
        words = re.sub(r'\s+', ' ', words).strip()
        x, y = float(geo.get('x') or 0), float(geo.get('y') or 0)
        w, h = float(geo.get('width') or 0), float(geo.get('height') or 0)
        m = re.match(r'(likelihood|impact) (\d)\b', words, re.I)
        if m:
            heads[m.group(1).lower()][int(m.group(2))] = (x + w / 2, y + h / 2)
            continue
        m = re.match(r'level (\d)\b', words, re.I)
        if m:
            levels.append((int(m.group(1)), x, y, w, h))

    drawn = {}
    for level, x, y, w, h in levels:
        cols = [n for n, (cx, _) in heads['likelihood'].items() if x <= cx <= x + w]
        rows = [n for n, (_, cy) in heads['impact'].items() if y <= cy <= y + h]
        for imp in rows:
            for lik in cols:
                if (imp, lik) in drawn:
                    fail.append('the matrix drawing covers impact %d, likelihood %d twice' % (imp, lik))
                drawn[(imp, lik)] = level
    if len(heads['likelihood']) != 4 or len(heads['impact']) != 4:
        fail.append('the matrix drawing has %d likelihood and %d impact headings, not 4 and 4'
                    % (len(heads['likelihood']), len(heads['impact'])))
    for pair in sorted(set(tabled) | set(drawn)):
        if tabled.get(pair) != drawn.get(pair):
            fail.append('impact %d, likelihood %d is Level %s in the table and Level %s in the '
                        'picture' % (pair + (tabled.get(pair, 'missing'), drawn.get(pair, 'missing'))))
    if fail:
        print('diagrams FAILED')
        for f in fail:
            print('  X   %s' % f)
        sys.exit(1)
    print('  ok  the matrix drawing and the matrix table agree on all %d combinations' % len(drawn))


def check_none():
    """Assertion 0. The playbook carries no diagram, so nothing may refer to one."""
    stale = []
    for f in scanned_files():
        if f.suffix not in {'.qmd', '.md', '.html', '.css', '.yml'} or f.name == 'CONTRIBUTE.md':
            continue
        txt = f.read_text(encoding='utf-8', errors='ignore')
        if re.search(r'_partials/diagram-|/static/diagrams/[A-Za-z0-9-]+\.(?:png|svg|drawio)', txt):
            stale.append(str(f.relative_to(ROOT)))
    for p in sorted(PART.glob('diagram-*.qmd')):
        stale.append(str(p.relative_to(ROOT)))
    if stale:
        print('diagrams FAILED')
        print('  X   the playbook carries no diagrams and these still refer to one: %s'
              % ', '.join(sorted(set(stale))))
        sys.exit(1)
    print('  ok  the playbook carries no diagram, and nothing refers to one')


def main():
    stems = []
    if DIAG.is_dir():
        stems = sorted({f.stem for f in DIAG.iterdir()
                        if f.is_file() and f.suffix in {'.png', '.svg', '.drawio'}})
    if stems:
        check_set(stems)
        check_matrix()
    else:
        check_none()
    check_board()
    boards = sorted((ROOT / 'artefacts' / 'service-design').glob('*.drawio'))
    own = sorted(DIAG.glob('*.drawio')) if DIAG.is_dir() else []
    low, n = check_text_contrast(own, 7.0)
    low_b, n_b = check_text_contrast(boards, 7.0)
    if low or low_b:
        print('diagrams FAILED')
        print('  X   text colour is under its contrast floor in %d place(s) in %d drawing(s), for '
              'example %s' % (len(low) + len(low_b), len({x[0] for x in low + low_b}),
                              (low + low_b)[:3]))
        sys.exit(1)
    elif n or n_b:
        print('  ok  text in %d playbook diagram(s) and %d board(s) reaches 7:1, over %d colours'
              % (len(own), len(boards), n + n_b))


if __name__ == '__main__':
    main()
