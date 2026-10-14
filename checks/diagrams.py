#!/usr/bin/env python3
"""Check that the diagram set is what the playbook says it is.

    python3 checks/diagrams.py

Six assertions:

  1. every diagram on disk is referenced by a page or a partial
  2. every reference resolves to a file that exists
  3. every diagram has both a .png, which the page embeds, and a .svg, which it links to full size
  4. the numbering runs 01 upward with no gaps and no duplicates
  5. every partial named `diagram-*` actually carries a picture
  6. every one of those partials is included by a page, so the picture reaches a reader
  6. where a diagram has a .drawio source, re-rendering it reproduces the committed .svg
  7. every diagram's own title, the one drawn across the top of the picture, is in its alt text

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

Assertion 6 needs `build/`, which the release package does not carry, so it is skipped there and
says so rather than passing quietly. The PNGs are deliberately not compared: they are rasterised,
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


def main():
    # manifest.json is written beside the renders by render-diagrams.py and is not a
    # diagram. Counting it would report it as an unreferenced file for ever.
    stems = sorted({f.stem for f in DIAG.iterdir()
                    if f.is_file() and f.suffix in {'.png', '.svg', '.drawio'}})
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
                r'/static/diagrams/([A-Za-z0-9-]+)\.png\)\{fig-alt="([^"]*)"',
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


if __name__ == '__main__':
    main()
