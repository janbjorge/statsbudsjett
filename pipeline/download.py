"""Download published data for Statsbudsjettet 2027 from regjeringen.no."""

import html
import json
import re
import time
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from urllib.parse import urljoin

BASE = "https://www.regjeringen.no"
ROOT = "/no/statsbudsjett/2027/id3172975/"
OUT = Path(__file__).parent.parent / "data"
UA = {"User-Agent": "Mozilla/5.0 (statsbudsjett-2027 downloader)"}

DATA_PAGES = [
    "/no/statsbudsjett/2027/statsbudsjettet-2027-tallgrunnlag-gul-bok/id3173280/",
    "/no/statsbudsjett/2027/nasjonalbudsjettet-2027-tallene-bak-figurene/id3173281/",
    "/no/statsbudsjett/2027/skatter-og-avgifter-2027-tallene-bak-figurene/id3173282/",
    "/no/statsbudsjett/2027/dokumenter-og-pressemeldinger/id3173039/",
]
HTML_PAGES = [
    ROOT,
    "/no/statsbudsjett/2027/statsbudsjettet-2027-statens-inntekter-og-utgifter/id3173250/",
    "/no/statsbudsjett/2027/statsbudsjettet-2027-skatter-og-avgifter/id3173278/",
    "/no/statsbudsjett/2027/a-til-a/id3173017/",
    "/no/statsbudsjett/2027/fylkesoversikten/id3173015/",
    "/no/aktuelt/nokkeltall-i-nasjonalbudsjettet-2027/id3174610/",
]
GUL_BOK_2026 = "/no/statsbudsjett/2026/statsbudsjettet-2026-tallgrunnlag-gul-bok/id3120937/"
GRONT_HEFTE = "/no/tema/kommuner-og-regioner/kommuneokonomi/gront-hefte/id547024/"
FILE_RE = re.compile(r'href="([^"]+\.(?:xlsx?|csv|pdf|zip))"', re.IGNORECASE)
FRIE_API = f"{BASE}/api/FrieInntekter"
SAKER = "/no/statsbudsjett/2027/saker-om-statsbudsjettet-for-2027/id3173041/"


def get(url: str) -> bytes:
    for attempt in range(4):
        try:
            req = urllib.request.Request(url, headers=UA)
            with urllib.request.urlopen(req, timeout=120) as r:
                return r.read()
        except Exception:
            if attempt == 3:
                raise
            time.sleep(2**attempt)
    raise AssertionError


def save(path: Path, data: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)
    print(f"{len(data):>12,}  {path.relative_to(OUT)}")


def slug(path: str) -> str:
    parts = [p for p in path.strip("/").split("/") if p and not p.startswith("id")]
    return "_".join(parts[-1:]) or "index"


def files_on(page: str) -> set[str]:
    html = get(urljoin(BASE, page)).decode("utf-8")
    return {urljoin(BASE, u) for u in FILE_RE.findall(html)}


def download_files(urls: set[str], subdir: str) -> None:
    def one(url: str) -> None:
        dest = OUT / subdir / url.rsplit("/", 1)[1]
        if not dest.exists():
            save(dest, get(url))

    with ThreadPoolExecutor(4) as pool:
        list(pool.map(one, sorted(urls)))


def main() -> None:
    # Excel data and attachments linked from the data pages
    excel, pdfs = set(), set()
    for page in DATA_PAGES:
        for url in files_on(page):
            (pdfs if url.lower().endswith(".pdf") else excel).add(url)

    # Budget documents (Prop. 1 S per department, Gul bok, Nasjonalbudsjettet, ...)
    docs_html = get(urljoin(BASE, DATA_PAGES[-1])).decode("utf-8")
    doc_pages = sorted(set(re.findall(r'href="(/no/dokumenter/[^"]+)"', docs_html)))
    for page in doc_pages:
        pdfs |= files_on(page)

    download_files(excel, "excel")
    download_files(pdfs, "pdf")

    # Last year's Gul bok datagrunnlag, the baseline for the 2026 -> 2027 diff
    download_files({u for u in files_on(GUL_BOK_2026) if u.endswith(".xlsx")}, "excel/2026")

    # Grønt hefte (inntektssystemet for kommunar og fylkeskommunar), tables per kommune/fylke
    gh_html = get(urljoin(BASE, GRONT_HEFTE)).decode("utf-8")
    for url in re.findall(r'href="(/contentassets/[^"]+/2027/[^"]+\.(?:ods|pdf|xlsx))"', gh_html):
        dest = OUT / "gront_hefte" / url.split("/2027/", 1)[1]
        if not dest.exists():
            save(dest, get(urljoin(BASE, url)))

    # Overview pages, including one page per county
    county_html = get(urljoin(BASE, HTML_PAGES[4])).decode("utf-8")
    counties = sorted(set(re.findall(r'href="(/no/statsbudsjett/2027/fylkesoversikten/statsbudsjettet-2027-[^"]+)"', county_html)))
    for page in HTML_PAGES + counties:
        sub = "html/fylker" if page in counties else "html"
        save(OUT / sub / f"{slug(page)}.html", get(urljoin(BASE, page)))

    # Frie inntekter (rammetilskudd + skatteanslag) per kommune and fylkeskommune
    collection = json.loads(get(f"{FRIE_API}/countycollection/2027"))
    save(OUT / "frie_inntekter" / "countycollection.json", json.dumps(collection, ensure_ascii=False, indent=1).encode())
    units = []
    for county in collection["data"]:
        units.append(county["fylkeskommune"])
        units.extend(county["kommuner"])

    def frie(unit: dict) -> tuple[str, dict]:
        return unit["id"], json.loads(get(f"{FRIE_API}/data/2027/{unit['id']}"))["data"]

    with ThreadPoolExecutor(4) as pool:
        result = dict(pool.map(frie, units))
    save(OUT / "frie_inntekter" / "frie_inntekter_2027.json", json.dumps(result, ensure_ascii=False, indent=1).encode())

    press_releases()
    pdf_text()


def press_releases() -> None:
    """Budget-day press releases as plain text, the main source for data/persona facts."""
    links: list[str] = []
    # The listing is 1-based: ?page=0 and ?page=1 return the same page
    for page in range(1, 50):
        listing = get(f"{BASE}{SAKER}?page={page}").decode("utf-8")
        main = re.search(r"<main.*?</main>", listing, re.DOTALL)
        new = [u for u in dict.fromkeys(re.findall(r'href="(/no/aktuelt/[^"]+/id\d+/)"', main.group(0) if main else "")) if u not in links]
        if not new:
            break
        links += new

    # Articles drop off the listing over time; always fetch the ones our facts cite
    for facts in sorted((OUT / "persona").glob("*.json")):
        for m in re.findall(r'"source_url":\s*"https://www\.regjeringen\.no(/no/aktuelt/[^"]+/id\d+/)"', facts.read_text()):
            if m not in links:
                links.append(m)

    def one(path: str) -> None:
        page = get(BASE + path).decode("utf-8", "replace")
        main = re.search(r"<main.*?</main>", page, re.DOTALL)
        if not main:
            return
        body = re.sub(r"<(script|style|nav|aside|footer)[^>]*>.*?</\1>", " ", main.group(0), flags=re.DOTALL)
        body = re.sub(r"</(p|h\d|li|tr|div)>", "\n", body)
        text = html.unescape(re.sub(r"<[^>]+>", " ", body))
        text = re.sub(r"\n\s*\n+", "\n", re.sub(r"[ \t\xa0]+", " ", text)).strip()
        title_tag = re.search(r"<title>([^<]*)", page)
        title = html.unescape(title_tag.group(1)).replace(" - regjeringen.no", "").strip() if title_tag else path
        date = re.search(r"(\d{2}\.\d{2}\.20\d\d)", text)
        if date and len(text) >= 600:
            out = f"TITLE: {title}\nURL: {BASE}{path}\nDATE: {date.group(1)}\n\n{text}\n"
            save(OUT / "saker" / f"{path.rstrip('/').split('/')[-1]}.txt", out.encode())

    with ThreadPoolExecutor(4) as pool:
        list(pool.map(one, links))


def pdf_text() -> None:
    """Text of every downloaded PDF with "=== SIDE N ===" page markers, for quoting and verification."""
    from pypdf import PdfReader

    for pdf in sorted((OUT / "pdf").glob("*.pdf")):
        dest = OUT / "text" / f"{pdf.stem}.txt"
        if dest.exists():
            continue
        pages = PdfReader(pdf).pages
        save(dest, "".join(f"\n\n=== SIDE {i + 1} ===\n" + (p.extract_text() or "") for i, p in enumerate(pages)).encode())


if __name__ == "__main__":
    main()
