# FACTS

Read this first on a cold start. Facts were checked on 2026-10-07 unless a section says otherwise. If this file and the code disagree, the code wins.

## 1. What this is

A public explainer of Norway's 2027 state budget proposal (Prop. 1 S (2026–2027), presented 7 October 2026) for people without budget knowledge. It is jb's project, built in one session on 2026-10-07 and meant to be hosted on Fly.io.

- `site/index.html` is the explorer: overview, "For deg" (what the budget means for you), tax receipt, income sources, a treemap of every post, biggest changes, your kommune, and oil money.
- `site/flyt.html` is the Sankey page: money flows for 2026 and 2027 and the 2026→2027 diff.
- Everything is static. The pages fetch `site/data/*.json`.

## 2. Sources on regjeringen.no

| What | Where | Fetched by |
|---|---|---|
| Budget landing page | https://www.regjeringen.no/no/statsbudsjett/2027/id3172975/ | download.py:77 |
| Gul bok datagrunnlag 2027 (every post, 2027 amounts only) | https://www.regjeringen.no/no/statsbudsjett/2027/statsbudsjettet-2027-tallgrunnlag-gul-bok/id3173280/ | download.py:77 |
| Gul bok datagrunnlag 2026 (baseline for the diff) | https://www.regjeringen.no/no/statsbudsjett/2026/statsbudsjettet-2026-tallgrunnlag-gul-bok/id3120937/ | download.py:31 |
| Nasjonalbudsjettet and tax figure data (Excel) | the two "tallene bak figurene" pages linked from the landing page | download.py:77 |
| All Prop. 1 S, Prop. 1 LS, Meld. St. 1 PDFs | https://www.regjeringen.no/no/statsbudsjett/2027/dokumenter-og-pressemeldinger/id3173039/ | download.py:77 |
| Grønt hefte 2027 (per-kommune tables, .ods) | https://www.regjeringen.no/no/tema/kommuner-og-regioner/kommuneokonomi/gront-hefte/id547024/ | download.py:32 |
| Frie inntekter per kommune (JSON API) | `https://www.regjeringen.no/api/FrieInntekter/{countycollection/2027, data/2027/<id>}` | download.py:34 |
| Budget-day press releases | https://www.regjeringen.no/no/statsbudsjett/2027/saker-om-statsbudsjettet-for-2027/id3173041/ | download.py:129 |

Site quirks:
- The landing page does not link Grønt hefte. It was only found on the second pass.
- The frie inntekter page is a JS app; the API above is what it calls. It takes a kommune or fylkeskommune number.
- The press release listing is 1-based (`?page=0` equals `?page=1`, download.py:132). Articles drop off the listing over time while staying online, so the crawl also fetches every article a fact cites (download.py:141).
- Some 2027 press releases left out because they are not budget data: the national security strategy and the Utsira Nord reports.

## 3. Local data layout

`data/` is gitignored except the verified facts. `uv run python download.py` recreates the rest (about 140 MB).

- `data/excel/`: Gul bok and NB/tax figure workbooks; `data/excel/2026/` holds the 2026 Gul bok.
- `data/pdf/`: 25 PDFs. `data/text/`: their text with `=== SIDE N ===` page markers (download.py:166). `data/text/SOURCES.txt` maps each text file to its document URL and explains the department codes in the file names.
- `data/saker/`: press releases as text with `TITLE:`, `URL:` and `DATE:` headers.
- `data/gront_hefte/`, `data/frie_inntekter/`, `data/html/`: kommune data and page snapshots.
- `data/persona/*.json`: verified facts for "For deg" (committed). See §6.

## 4. Gul bok datagrunnlag

- Sheet `Data`, one row per post. Columns: gdep/avs/fdep (department levels), `omr_nr`/`omr_navn` (programområde), `kat_nr`/`kat_navn` (programkategori), `kap_nr`, `post_nr`, `kap_navn`, `post_navn`, `stikkord`, `beløp` (kroner).
- `kap_nr` below 3000 is spending, 3000 and above is income. Posts 90–99 are loan transactions.
- The 2027 file has 1 595 rows with amounts for 2027 only. The 2026 file has the same layout.
- Non-oil totals (METHOD.md §1): 2 286,8 mrd. kr in 2027 and 2 164,5 mrd. kr in 2026. Income equals spending to the krone in both years; viz/build.py asserts it.
- The transfer from the oil fund (kap. 5800) is 561,7 mrd. kr in 2027 and 452,2 mrd. kr in 2026.
- Matching 2026 and 2027 by kap+post leaves 64 posts of 2027 without a 2026 match (new or renumbered).

## 5. Other numbers used on the pages

- Population 5 636 995: the sum of "innbyggartal per 1.7.2026" in Grønt hefte tabell F, over 357 kommuner (viz/explorer.py:77).
- Frie inntekter per kommune 2026 and 2027 come from Grønt hefte tabell 3, in 1 000 kr. The two tables spell some kommune names differently, so they are joined on the 4-digit number.
- The oil fund share of budget spending (26,6 % in 2027, 3,0 % in 2001) is NB 2027 figure 3.4, sheet `Fig3-4` in kap_3_nb_2027.xlsx (viz/explorer.py:99). Our own Sankey ratio differs (different denominator), so the page quotes the official figure.

## 6. "For deg" facts and verification

- 94 facts in data/persona/{families,welfare,business}.json and 56 tax parameters in data/persona/tax.json. Four agent sessions extracted them on 2026-10-07 from the press releases and the propositions.
- Each fact has personas, a plain bokmål title and summary, an effect (pluss/minus/uendret/blandet), amounts for 2026/2027, a verbatim quote, `source_file`, `source_url` and `page`. `extra_quotes` holds evidence that sits elsewhere (e.g. the 2026 value on another page).
- viz/verify_persona.py:52 checks every quote against its source file, the page against the page marker, and that every amount appears in the quote. viz/explorer.py:121 refuses to build if anything fails.
- PDF text quirks the checker normalises (viz/verify_persona.py:17): words broken across lines ("tryg-\ndeinntekter", "jus -\ntert"), private-use glyphs (U+F020), table rows that repeat on several pages, and amounts written as "21,5 mill.".
- Curation happens in the build, not in the agent files (viz/explorer.py:137): duplicates, items the tax calculator already covers, and one item that was spending growth worded as a personal change.
- Known source conflict: the parykk press release (id3175764) gives the old rates as if they were new. Prop. 1 S AID p. 25 has 6 265 → 7 455 and 16 220 → 19 302; the facts use the proposition.
- No source states småbarnstillegg for 2026, so that fact shows only the 2027 rate.

## 7. Tax rules and the calculator

- Source: Prop. 1 LS (2026–2027) tabell 1.5 "Skattesatser, fradrag og beløpsgrenser i 2026 og forslag for 2027", pp. 26–30. https://www.regjeringen.no/no/dokumenter/prop.-1-ls-20262027/id3176120/
- Key 2027 changes: personfradrag 114 540 → 120 180; trygdeavgift on wages 7,6 → 7,4 %; trinnskatt thresholds +4,0 % with unchanged rates; the pension tax credit max 39 100 → 40 750.
- Official comparisons use the reference system, meaning 2026 rules adjusted for expected wage growth (4,0 %, p. 80) and pension growth (3,35 %, p. 79). Compared at the same nominal income instead, the cut looks several times larger.
- The calculator (viz/explorer.html:786 and :800) reproduces tabell 2.1 (2026 tax at 200 000 / 650 000 / 1 000 000 kr: 15 200 / 160 983 / 305 870) exactly. It also gives −1 738 kr at 750 000 kr (official: "om lag 1 800"), and −998 kr for a pension between 350 000 and 450 000 kr (pension relief "inntil 750 kr" plus the general personfradrag increase).

## 8. Hosting

- Caddy serves `site/` (Caddyfile, Dockerfile). Fly config is in fly.toml: region arn, machines stop when idle. The app is not created or deployed yet.
- Over the wire the explorer is about 185 KB compressed. The JSON data and assets are cached for 1 hour, HTML for 5 minutes.
- The security policy allows inline scripts, because both pages embed their code.

## 9. Known gaps

See TODO.md for what is planned. Facts that are missing in the sources:
- No G value or 2027 kroner amounts for pensions (only "regulated from 1 May 2027").
- No rule changes for dagpenger, AAP or hjelpestønad; only spending.
- No official household examples with tax for both years, apart from the 750 000 kr wage earner, a couple with two such incomes (−3 500 kr), and the minimum pensioner (stays tax-free).
