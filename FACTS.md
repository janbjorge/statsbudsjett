# FACTS

Read this first on a cold start. Facts were checked on 2026-10-07 unless a section says otherwise. If this file and the code disagree, the code wins.

## 1. What this is

A public explainer of Norway's 2027 state budget proposal (Prop. 1 S (2026–2027), presented 7 October 2026) for people without budget knowledge. It is jb's project, built in one session on 2026-10-07 and meant to be hosted on Fly.io.

- `/` is the explorer: overview, "For deg" (what the budget means for you), tax receipt, income sources, a treemap of every post, biggest changes, your kommune, and oil money.
- `/flyt` is the Sankey page: money flows for 2026 and 2027 and the 2026→2027 diff.
- `/visste-du` holds the 2027 totals in everyday units: per innbygger, per day, per second, and per innbygger for each spending group and income source (src/core/budget.py, `everyday`).
- Stack (jb 2026-10-07): Python 3.14, FastAPI + uvicorn + Jinja + HTMX. The server renders all HTML. d3 is used only for four chart islands in src/adapters/web/static/charts.js (treemap, kommune dots, fund line) and the Sankey page.

### Layout

- `src/core/`: the pure domain. tax.py (the tax engine), facts.py ("For deg" selection), budget.py (tree, search, changes, kommune), ports.py. It imports only the standard library; tests/test_boundary.py enforces this.
- `src/app/queries.py`: read-only queries with frozen-dataclass results; this is what the web adapter calls.
- `src/adapters/datasets.py`: reads `datasets/*.json` into core types at startup (implements core.ports.Datasets).
- `src/adapters/web/`: FastAPI app (main.py), number formatting (fmt.py), Jinja templates (`_*.html` are HTMX fragments), and static files.
- `src/pipeline/`: offline scripts, run from the repo root. download.py fetches sources, flows.py and datasets.py build `datasets/` with polars, and verify.py checks the facts.
- `datasets/`: the build output the app reads (budget.json, meg.json, plus CSV downloads served under /data). It is committed.

### HTMX and URLs

- Every fragment route (/meg, /kvittering, /utforsk, /kommune) redirects to the full page with the same query when called without the `HX-Request` header, so links and no-JS visits work.
- /meg answers with `HX-Replace-Url: /?meg=…&barn=…&lonn=…&pensjon=…#meg`, so the address bar always holds a shareable link (src/adapters/web/main.py:161). The form's visible inputs are turned into these four parameters in charts.js (`htmx:configRequest`).
- Query parsing never fails: unknown personas are dropped, numbers are digits-only and capped (src/adapters/web/main.py:100).

## 2. Sources on regjeringen.no

| What | Where | Fetched by |
|---|---|---|
| Budget landing page | https://www.regjeringen.no/no/statsbudsjett/2027/id3172975/ | src/pipeline/download.py:77 |
| Gul bok datagrunnlag 2027 (every post, 2027 amounts only) | https://www.regjeringen.no/no/statsbudsjett/2027/statsbudsjettet-2027-tallgrunnlag-gul-bok/id3173280/ | src/pipeline/download.py:77 |
| Gul bok datagrunnlag 2026 (baseline for the diff) | https://www.regjeringen.no/no/statsbudsjett/2026/statsbudsjettet-2026-tallgrunnlag-gul-bok/id3120937/ | src/pipeline/download.py:31 |
| Nasjonalbudsjettet and tax figure data (Excel) | the two "tallene bak figurene" pages linked from the landing page | src/pipeline/download.py:77 |
| All Prop. 1 S, Prop. 1 LS, Meld. St. 1 PDFs | https://www.regjeringen.no/no/statsbudsjett/2027/dokumenter-og-pressemeldinger/id3173039/ | src/pipeline/download.py:77 |
| Grønt hefte 2027 (per-kommune tables, .ods) | https://www.regjeringen.no/no/tema/kommuner-og-regioner/kommuneokonomi/gront-hefte/id547024/ | src/pipeline/download.py:32 |
| Frie inntekter per kommune (JSON API) | `https://www.regjeringen.no/api/FrieInntekter/{countycollection/2027, data/2027/<id>}` | src/pipeline/download.py:34 |
| Budget-day press releases | https://www.regjeringen.no/no/statsbudsjett/2027/saker-om-statsbudsjettet-for-2027/id3173041/ | src/pipeline/download.py:129 |

Site quirks:
- The landing page does not link Grønt hefte. It was only found on the second pass.
- The frie inntekter page is a JS app; the API above is what it calls. It takes a kommune or fylkeskommune number.
- The press release listing is 1-based (`?page=0` equals `?page=1`, src/pipeline/download.py:132). Articles drop off the listing over time while staying online, so the crawl also fetches every article a fact cites (src/pipeline/download.py:141).
- Some 2027 press releases left out because they are not budget data: the national security strategy and the Utsira Nord reports.

## 3. Local data layout

`data/` is gitignored except the verified facts. `uv run python -m pipeline.download` recreates the rest (about 140 MB).

- `data/excel/`: Gul bok and NB/tax figure workbooks; `data/excel/2026/` holds the 2026 Gul bok.
- `data/pdf/`: 25 PDFs. `data/text/`: their text with `=== SIDE N ===` page markers (src/pipeline/download.py:167). `data/text/SOURCES.txt` maps each text file to its document URL and explains the department codes in the file names.
- `data/saker/`: press releases as text with `TITLE:`, `URL:` and `DATE:` headers.
- `data/gront_hefte/`, `data/frie_inntekter/`, `data/html/`: kommune data and page snapshots.
- `data/persona/*.json`: verified facts for "For deg" (committed). See §6.

## 4. Gul bok datagrunnlag

- Sheet `Data`, one row per post. Columns: gdep/avs/fdep (department levels), `omr_nr`/`omr_navn` (programområde), `kat_nr`/`kat_navn` (programkategori), `kap_nr`, `post_nr`, `kap_navn`, `post_navn`, `stikkord`, `beløp` (kroner).
- `kap_nr` below 3000 is spending, 3000 and above is income. Posts 90–99 are loan transactions.
- The 2027 file has 1 595 rows with amounts for 2027 only. The 2026 file has the same layout.
- Non-oil totals (METHOD.md §1): 2 286,8 mrd. kr in 2027 and 2 164,5 mrd. kr in 2026. Income equals spending to the krone in both years; src/pipeline/flows.py asserts it.
- The transfer from the oil fund (kap. 5800) is 561,7 mrd. kr in 2027 and 452,2 mrd. kr in 2026.
- Matching 2026 and 2027 by kap+post leaves 64 posts of 2027 without a 2026 match (new or renumbered).

## 5. Other numbers used on the pages

- Population 5 636 995: the sum of "innbyggartal per 1.7.2026" in Grønt hefte tabell F, over 357 kommuner (src/pipeline/datasets.py:78).
- Frie inntekter per kommune 2026 and 2027 come from Grønt hefte tabell 3, in 1 000 kr. The two tables spell some kommune names differently, so they are joined on the 4-digit number.
- The oil fund share of budget spending (26,6 % in 2027, 3,0 % in 2001) is NB 2027 figure 3.4, sheet `Fig3-4` in kap_3_nb_2027.xlsx (src/pipeline/datasets.py:100). Our own Sankey ratio differs (different denominator), so the page quotes the official figure.

## 6. "For deg" facts and verification

- 94 facts in data/persona/{families,welfare,business}.json and 56 tax parameters in data/persona/tax.json. Four agent sessions extracted them on 2026-10-07 from the press releases and the propositions.
- Each fact has personas, a plain bokmål title and summary, an effect (pluss/minus/uendret/blandet), a kind for changes (betaler/far/tilbud/regel), amounts for 2026/2027, a verbatim quote, `source_file`, `source_url` and `page`. `extra_quotes` holds evidence that sits elsewhere (e.g. the 2026 value on another page).
- src/pipeline/verify.py:52 checks every quote against its source file, the page against the page marker, and that every amount appears in the quote. src/pipeline/datasets.py:122 refuses to build if anything fails.
- PDF text quirks the checker normalises (src/pipeline/verify.py:17): words broken across lines ("tryg-\ndeinntekter", "jus -\ntert"), private-use glyphs (U+F020), table rows that repeat on several pages, and amounts written as "21,5 mill.".
- Curation happens in the build, not in the agent files (src/pipeline/datasets.py:136): duplicates, items the tax calculator already covers, and one item that was spending growth worded as a personal change.
- Known source conflict: the parykk press release (id3175764) gives the old rates as if they were new. Prop. 1 S AID p. 25 has 6 265 → 7 455 and 16 220 → 19 302; the facts use the proposition.
- No source states småbarnstillegg for 2026, so that fact shows only the 2027 rate.

## 7. Tax rules and the calculator

- Source: Prop. 1 LS (2026–2027) tabell 1.5 "Skattesatser, fradrag og beløpsgrenser i 2026 og forslag for 2027", pp. 26–30. https://www.regjeringen.no/no/dokumenter/prop.-1-ls-20262027/id3176120/
- Key 2027 changes: personfradrag 114 540 → 120 180; trygdeavgift on wages 7,6 → 7,4 %; trinnskatt thresholds +4,0 % with unchanged rates; the pension tax credit max 39 100 → 40 750.
- Official comparisons use the reference system, meaning 2026 rules adjusted for expected wage growth (4,0 %, p. 80) and pension growth (3,35 %, p. 79). Compared at the same nominal income instead, the cut looks several times larger.
- The calculator (src/core/tax.py:88 and :139) reproduces tabell 2.1 (2026 tax at 200 000 / 650 000 / 1 000 000 kr: 15 200 / 160 983 / 305 870) exactly. It also gives −1 738 kr at 750 000 kr (official: "om lag 1 800"), and −998 kr for a pension between 350 000 and 450 000 kr (pension relief "inntil 750 kr" plus the general personfradrag increase).

## 8. Hosting

- uvicorn serves the app directly (Dockerfile: python:3.14-slim plus uv, runtime dependencies only, runs as `nobody`). Fly config is in fly.toml: region arn, health check /helse, machines stop when idle. The Fly app is not created or deployed yet.
- The app adds gzip, security headers and cache headers itself (src/adapters/web/main.py:32). Static files and data are cached for 1 hour, full pages for 5 minutes. The front page is about 115 KB, or 21 KB gzipped.
- The security policy allows inline scripts, because both pages embed their code.

## 9. Known gaps

See TODO.md for what is planned. Facts that are missing in the sources:
- No G value or 2027 kroner amounts for pensions (only "regulated from 1 May 2027").
- No rule changes for dagpenger, AAP or hjelpestønad; only spending.
- No official household examples with tax for both years, apart from the 750 000 kr wage earner, a couple with two such incomes (−3 500 kr), and the minimum pensioner (stays tax-free).
