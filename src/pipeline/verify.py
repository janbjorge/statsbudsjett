"""Check the persona fact catalogue against its sources.

For every item: the quote must occur in source_file, the page must match the
"=== SIDE N ===" marker before it, and every amount must appear in the quote.
Exits non-zero if anything fails, so a bad fact never reaches the page. See FACTS.md §6.
"""

import re
import sys
from pathlib import Path

import orjson

ROOT = Path(__file__).parents[2]
PERSONA = ROOT / "data/persona"


def norm(s: str) -> str:
    # PDF text breaks words over lines ("skatte-\nfradrag") and uses odd spaces
    s = re.sub(r"[\uf000-\uf8ff]", " ", s)  # private-use glyphs from PDF fonts
    s = s.replace("­", "").replace("\xa0", " ").replace(" ", " ").replace(" ", " ")
    s = re.sub(r"(?<=[a-zæøå]) ?-\s+(?!(?:og|eller|til|enn)\b)(?=[a-zæøå])", "", s)
    # A capital on either side is a real hyphen ("Nord-\nNorge", "NAV-\nkontor"): keep it, drop the break
    s = re.sub(r"(?<=[a-zæøåA-ZÆØÅ0-9])-\s+(?!(?:og|eller|til|enn)\b)(?=[a-zæøåA-ZÆØÅ])", "-", s)
    s = re.sub(r"[‐‑‒–—−]", "-", s)
    s = re.sub(r"[«»“”„\"]", '"', s).replace("’", "'")
    return re.sub(r"\s+", " ", s).strip().lower()


def page_at(text: str, pos: int) -> int | None:
    pages = [(m.start(), int(m.group(1))) for m in re.finditer(r"=== SIDE (\d+) ===", text)]
    before = [p for start, p in pages if start <= pos]
    return before[-1] if before else None


def number_forms(v: float) -> list[str]:
    """Ways a number can be written in Norwegian text: 1 200, 1200, 1,2, 22 pst."""
    out = set()
    if float(v).is_integer():
        i = int(v)
        out |= {str(i), f"{i:,}".replace(",", " "), f"{i:,}".replace(",", ".")}
    else:
        for d in (1, 2, 3):
            s = f"{v:.{d}f}".rstrip("0").rstrip(".")
            ip, _, fp = s.partition(".")
            grouped = f"{int(ip):,}".replace(",", " ")
            out |= {s.replace(".", ","), f"{grouped},{fp}" if fp else grouped}
    if abs(v) >= 1e6:
        # "21,5 mill." / "14 mill."
        m = f"{v / 1e6:.2f}".rstrip("0").rstrip(".").replace(".", ",")
        out |= {m + " mill", m + " millioner"}
    return sorted(out)


def check_item(item: dict, cache: dict) -> list[str]:
    errs = []
    src: str = item.get("source_file") or ""
    path = ROOT / src
    if not src or not path.exists():
        return [f"source_file missing: {src}"]
    raw = cache.setdefault(src, path.read_text())
    text = cache.setdefault(src + "#norm", norm(raw))
    quote = norm(item.get("quote", ""))
    if len(quote) < 15:
        return ["quote too short"]
    if quote not in text:
        # Long PDF quotes may span a page marker or table noise: accept if all 60-char chunks match in order
        chunks = [quote[i : i + 60] for i in range(0, len(quote), 60)]
        at, ok = 0, True
        for c in chunks:
            at = text.find(c, at)
            if at < 0:
                ok = False
                break
        if not ok:
            return [f"quote not found in {src}"]
    if item.get("page") is not None:
        # Map normalized position back to the raw text by searching the first quote words
        # Table rows repeat ("Personer ... 22 pst."), so any occurrence on the cited page counts
        nk = cache.setdefault(src + "#markers", text.replace("=== side", "=== SIDE"))
        head = norm(item["quote"])[:40]
        pages = {page_at(nk, m.start()) for m in re.finditer(re.escape(head), nk)}
        if pages and item["page"] not in pages:
            errs.append(f"page {item['page']} but quote is on page(s) {sorted(p for p in pages if p is not None)}")
    # Facts spread over two places (e.g. 2026 and 2027 values on different pages) carry extra quotes
    for extra in item.get("extra_quotes", []):
        sub = {"source_file": src, "quote": extra["quote"], "page": extra.get("page"), "amounts": []}
        errs += [f"extra quote: {e}" for e in check_item(sub, cache)]
        quote += " " + norm(extra["quote"])
    qn = quote.replace(" ", "")
    for a in item.get("amounts", []):
        for year in ("y2026", "y2027"):
            v = a.get(year)
            if v is None:
                continue
            forms = number_forms(v)
            if not any(f.replace(" ", "") in qn for f in forms):
                errs.append(f"{a.get('label_nb')} {year}={v} not in quote")
    return errs


def main() -> int:
    cache: dict = {}
    bad = 0
    total = 0
    for f in sorted(PERSONA.glob("*.json")):
        if f.name == "tax.json":
            items = orjson.loads(f.read_bytes())["params"]
            for p in items:
                p.setdefault("source_file", "data/text/prp202620270001ls0dddpdfs.txt")
                p["amounts"] = [{"label_nb": p.get("label_nb"), "y2026": p.get("y2026"), "y2027": p.get("y2027")}]
        else:
            items = orjson.loads(f.read_bytes())
        for it in items:
            total += 1
            errs = check_item(it, cache)
            if errs:
                bad += 1
                print(f"FAIL {f.name} {it.get('id') or it.get('key')}: " + "; ".join(errs))
    print(f"{total - bad}/{total} items verified")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
