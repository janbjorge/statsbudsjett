# TODO

Every request from jb, with status. Newest first. An item is ticked only when it is done and verified; finished items move to docs/done.md.

## Open

- [ ] **Business income in the tax calculator.** The "Bonde" preset treats farm income as wages, so its tax figure is wrong for a farmer (trygdeavgift 10,6 % on business income vs 7,4 % on wages). The rates are already in data/persona/tax.json. Found 2026-10-07.
- [ ] **Deploy to Fly.io** (jb 2026-10-07: "Im going to host it in fly.io"). Caddy, Dockerfile and fly.toml are ready and tested locally. Waiting for jb's go-ahead and an app name, because deploying makes the page public.
- [ ] **Read through the user-facing texts** before publishing: the cards for each preset, the glossary, and the footer disclaimer ("ikke en offisiell side").

## Ideas not yet requested

- Map of kommuner coloured by frie inntekter per person (needs a Kartverket GeoJSON).
- Real-terms change next to nominal, using the NB price forecast.
- Tax by income decile and the top 0,1 % over time (kap_2_2027.xlsx).
- Long-term pressure to 2060 (NB figures 3.10 and 3.12).
- More "For deg" facts: Ryfast toll discount ending, reindrift, hurtigbåt programme (left out by the extractors, see FACTS.md §9).

## Done

Moved to docs/done.md.
