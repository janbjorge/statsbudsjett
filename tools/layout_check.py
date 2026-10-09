"""Check the layout in three browser engines at phone, tablet and desktop widths.

Run by hand against a running server; it needs browsers, so it is not part of the tests:

    uv run uvicorn adapters.web.main:app --app-dir src --port 8765 &
    uvx --with playwright python -m playwright install webkit chromium firefox   # once
    uvx --with playwright python tools/layout_check.py [http://localhost:8765]

Per engine, width and page it reports what breaks on some devices and not others:
- the page scrolls sideways,
- a chart that scrolls sideways in its own box has no "Sveip sideveis" hint after it,
- two labels in one chart overlap, or a label sits on a chart line.
It prints nothing for a page that passes and exits non-zero if anything failed.
"""

import sys

from playwright.sync_api import sync_playwright  # ty: ignore[unresolved-import]

PAGES = ["/", "/?meg=bilist&barn=0,2,0,0,0&lonn=650000,650000", "/flyt", "/tilbud", "/visste-du", "/oljefondet", "/ki"]
WIDTHS = [(320, 640), (390, 664), (834, 1112), (1280, 720)]
ENGINES = ["webkit", "chromium", "firefox"]

JS = r"""() => {
  const out = [];
  const doc = document.documentElement;
  if (doc.scrollWidth > innerWidth + 1) out.push(`page scrolls sideways: ${doc.scrollWidth} px wide`);
  // Charts that scroll sideways need the hint; tables scroll in their own box everywhere and need none
  for (const box of document.querySelectorAll('.hscroll')) {
    if (!box.querySelector(':scope > div > svg') || box.scrollWidth <= box.clientWidth + 1) continue;
    const shown = h => h && h.classList.contains('swipe') && getComputedStyle(h).display !== 'none';
    if (!shown(box.nextElementSibling) && !shown(box.previousElementSibling))
      out.push(`#${box.firstElementChild?.id || box.className} scrolls sideways without a swipe hint`);
  }
  const hit = (a, b) => a.left < b.right - 1 && b.left < a.right - 1 && a.top < b.bottom - 1 && b.top < a.bottom - 1;
  for (const svg of document.querySelectorAll('main svg')) {
    const where = svg.closest('[id]')?.id || svg.parentElement.className;
    // Tick labels sit on their own axis and never collide by construction; check the labels we place
    const labels = [...svg.querySelectorAll('text')].filter(t => !t.closest('.axis, .tick') && t.textContent.trim())
      .map(t => ({ t: t.textContent.trim(), r: t.getBoundingClientRect() })).filter(l => l.r.width);
    for (let i = 0; i < labels.length; i++) for (let j = i + 1; j < labels.length; j++)
      if (hit(labels[i].r, labels[j].r)) out.push(`${where}: "${labels[i].t}" overlaps "${labels[j].t}"`);
    // A label on top of a drawn line (not a link or area): sample the path and look for points inside the label
    const m = svg.getScreenCTM();
    for (const p of svg.querySelectorAll('path[fill="none"]:not(.link)')) {
      if (p.closest('.axis')) continue;
      const n = p.getTotalLength();
      for (const l of labels) {
        for (let s = 0; s <= n; s += 3) {
          const q = p.getPointAtLength(s), x = q.x * m.a + m.e, y = q.y * m.d + m.f;
          if (x > l.r.left + 2 && x < l.r.right - 2 && y > l.r.top + 2 && y < l.r.bottom - 2) { out.push(`${where}: "${l.t}" sits on a line`); break; }
        }
      }
    }
  }
  return out;
}"""


def main() -> int:
    base = sys.argv[1] if len(sys.argv) > 1 else "http://localhost:8765"
    failed = 0
    with sync_playwright() as p:
        for engine in ENGINES:
            try:
                browser = getattr(p, engine).launch()
            except Exception as e:  # noqa: BLE001 - a browser that will not start here should not hide the other two
                print(f"{engine:8} skipped, it did not start: {str(e).splitlines()[0]}")
                continue
            for w, h in WIDTHS:
                page = browser.new_page(viewport={"width": w, "height": h})
                for path in PAGES:
                    page.goto(base + path, wait_until="networkidle")
                    page.wait_for_timeout(400)
                    for problem in page.evaluate(JS):
                        failed += 1
                        print(f"{engine:8} {w:4}  {path:14.14}  {problem}")
                page.close()
            browser.close()
    print(f"{failed} problems" if failed else "no problems")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
