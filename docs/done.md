# Done

Finished requests from jb, newest first. Each quotes the request and says what was built.

## 2026-10-07

- [x] **Project docs** ("i need a way to store our facts and or fidings that might be usefull later"): CLAUDE.md, AGENTS.md, FACTS.md, METHOD.md, TODO.md and this file. download.py now also recreates the press release and PDF text sources, and the verified facts are in git.
- [x] **"How does this affect me?"** ("We are a fameliy of 4, two small children, how does it affect me? Or im a farmer"): "For deg" section with a profile, child age bands, a tax calculator for one or two adults, cards per situation with sources, presets, and a shareable URL. 94 facts and 56 tax parameters are machine-verified against the sources.
- [x] **Fly.io-ready static site** ("I'm going to host it in fly.io"): `site/` with aggregated JSON and CSV downloads, Caddy, Dockerfile and fly.toml. Tested in a local container.
- [x] **Explorer page for the general public** ("a Statsbudsjettet explorer page, that should help the person the street"): hero, tax receipt, income sources, zoomable treemap with search, biggest changes, kommune view, oil-fund chart, glossary. Works on mobile, light and dark.
- [x] **Switch to polars** ("lets use https://pola.rs/").
- [x] **Income/outcome graphs plus a diff** (reference: a Sankey from Reddit): Sankey for 2026 and 2027 on a shared scale, and a diverging diff chart with a NOK/% toggle (NOK is the default; % explodes on small items).
- [x] **Commit** ("lets qcheck in"): first commit dffdf5d. data/ is gitignored.
- [x] **Did we get everything?** Second pass found Grønt hefte (not linked from the budget page) and added it.
- [x] **Download all 2027 budget data** from regjeringen.no: download.py.
