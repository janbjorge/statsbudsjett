"""Measure how dense the pages are, on a phone and on a desktop (docs/plan-density.md).

Run by hand against a running server; it needs a browser, so it is not part of the tests:

    uv run uvicorn adapters.web.main:app --app-dir src --port 8765 &
    uvx --with playwright python tools/density.py [http://localhost:8765]

Per page it prints the length in screens, words per screen, text styles (size and weight), text colours,
and the longest line of running text in characters. Text inside closed <details> is not counted.
"""

import sys

from playwright.sync_api import sync_playwright  # ty: ignore[unresolved-import]

PAGES = ["/", "/flyt", "/tilbud", "/visste-du", "/oljefondet", "/ki"]
SIZES = [(390, 664), (1280, 720)]

JS = r"""() => {
  const vis = e => { const s = getComputedStyle(e); return s.display !== 'none' && s.visibility !== 'hidden' && e.getClientRects().length; };
  let words = 0; const styles = new Set(), colours = new Set();
  const w = document.createTreeWalker(document.querySelector('main'), NodeFilter.SHOW_TEXT);
  while (w.nextNode()) {
    const t = w.currentNode, p = t.parentElement;
    if (!p || !vis(p) || p.closest('script, details:not([open]) > :not(summary)')) continue;
    const n = t.textContent.trim().split(/\s+/).filter(Boolean).length;
    if (!n) continue;
    words += n;
    const s = getComputedStyle(p); styles.add(s.fontSize + '/' + s.fontWeight); colours.add(s.color);
  }
  // Longest line: walk the characters of each paragraph and count them until the line breaks
  let cpl = 0; const r = document.createRange();
  for (const e of document.querySelectorAll('main p, main li')) {
    if (!vis(e) || e.textContent.trim().length < 140) continue;
    const tw = document.createTreeWalker(e, NodeFilter.SHOW_TEXT); let top = null, cur = 0;
    while (tw.nextNode()) { const t = tw.currentNode; for (let i = 0; i < t.length; i++) {
      if (/\s/.test(t.data[i]) && /\s/.test(t.data[i - 1] ?? ' ')) continue;
      r.setStart(t, i); r.setEnd(t, i + 1); const b = r.getClientRects()[0]; if (!b) continue;
      if (top !== null && b.top > top + 4) { cpl = Math.max(cpl, cur); cur = 0; }
      top = b.top; cur++;
    } }
  }
  return { screens: document.documentElement.scrollHeight / innerHeight, words, styles: styles.size, colours: colours.size, cpl };
}"""


def main() -> None:
    base = sys.argv[1] if len(sys.argv) > 1 else "http://localhost:8765"
    with sync_playwright() as p:
        browser = p.webkit.launch()
        for w, h in SIZES:
            page = browser.new_page(viewport={"width": w, "height": h})
            print(f"\n{w}x{h}   page          screens  words/screen  text styles  text colours  longest line")
            for path in PAGES:
                page.goto(base + path, wait_until="networkidle")
                page.wait_for_timeout(400)
                r = page.evaluate(JS)
                s = r["screens"]
                print(f"            {path:12} {s:8.1f}  {r['words'] / s:12.0f}  {r['styles']:11}  {r['colours']:12}  {r['cpl']:12}")
            page.close()
        browser.close()


if __name__ == "__main__":
    main()
