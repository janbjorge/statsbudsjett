# Done

Finished requests from jb, newest first. Each quotes the request and says what was built.

## 2026-10-07

- [x] **Children over 18** ("Du mangler barn i husstanden over 18 år. Mange over 18 som bor hjemme/trenger støtte fra foreldrene pga studier."): new band "Over 18 år" under "Barn i husstanden". Entering one shows the student facts (studielån, studentboliger, folkehøgskole) under "Barn over 18 år som studerer" and hides the barnehage and school facts. Follow-up ("we must be make sure that the numbers are right, if not, lets dont do it"): barnetrygd is hidden when every child is over 18 (the quote says 0–18 år), and foreldrefradrag now shows the verified 25 000 / 15 000 kr limits for children 12 and older with særskilt behov (Prop. 1 LS fotnote 13). Reasons are in METHOD.md §6. Old links with four `barn` values still work.
- [x] **Explain open source and bug reports** ("if ppl. find bugs, they can repot it there, so we need a section that explains this concept"): section "Fant du en feil?" (#feil) with what open source means, steps for reporting on GitHub (a free account is needed), what is useful to report, and links in the nav, footer and README.
- [x] **Python + HTMX** ("lets make sure we convert to; python htmx and use python 314, use uvicorn / fastapi to service IF we need some kind of backend"): rebuilt as FastAPI + Jinja + HTMX on Python 3.14 with a pure `core/`. The tax engine and fact selection moved from JS to Python and are tested against the official figures (19 tests). d3 remains only for chart islands. Caddy and the static `site/` are gone; uvicorn serves the app. The results match the earlier JS version exactly (family 3 076 kr, farmer 1 338 kr, 23 + 10 facts).
- [x] **No employer references in the public repo** ("This project will be open, so make sure there anre NO refs."): removed one mention and rewrote the pushed commit with jb's approval; AGENTS.md now has the rule.

- [x] **Project docs** ("i need a way to store our facts and or fidings that might be usefull later"): CLAUDE.md, AGENTS.md, FACTS.md, METHOD.md, TODO.md and this file. download.py now also recreates the press release and PDF text sources, and the verified facts are in git.
- [x] **"How does this affect me?"** ("We are a fameliy of 4, two small children, how does it affect me? Or im a farmer"): "For deg" section with a profile, child age bands, a tax calculator for one or two adults, cards per situation with sources, presets, and a shareable URL. 94 facts and 56 tax parameters are machine-verified against the sources.
- [x] **Fly.io-ready static site** ("I'm going to host it in fly.io"): `site/` with aggregated JSON and CSV downloads, Caddy, Dockerfile and fly.toml. Tested in a local container.
- [x] **Explorer page for the general public** ("a Statsbudsjettet explorer page, that should help the person the street"): hero, tax receipt, income sources, zoomable treemap with search, biggest changes, kommune view, oil-fund chart, glossary. Works on mobile, light and dark.
- [x] **Switch to polars** ("lets use https://pola.rs/").
- [x] **Income/outcome graphs plus a diff** (reference: a Sankey from Reddit): Sankey for 2026 and 2027 on a shared scale, and a diverging diff chart with a NOK/% toggle (NOK is the default; % explodes on small items).
- [x] **Commit** ("lets qcheck in"): first commit dffdf5d. data/ is gitignored.
- [x] **Did we get everything?** Second pass found Grønt hefte (not linked from the budget page) and added it.
- [x] **Download all 2027 budget data** from regjeringen.no: download.py.
