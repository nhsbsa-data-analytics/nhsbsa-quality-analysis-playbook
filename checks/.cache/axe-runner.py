
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
