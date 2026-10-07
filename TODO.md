# TODO

Every request from jb, with status. Newest first. An item is ticked only when it is done and verified; finished items move to docs/done.md.

## Open

- [ ] **Switch on the canonical redirect** once budsjettlupa.no is old enough for corporate web filters (jb 2026-10-07: "My zscaler blocks the domain due to being to new"): `fly secrets set CANONICAL_HOST=budsjettlupa.no -a statsbudsjett`. Then statsbudsjett.fly.dev and www. redirect to budsjettlupa.no (src/adapters/web/main.py).
- [ ] **Read through the user-facing texts** before publishing: the cards for each preset, the glossary, and the footer disclaimer ("ikke en offisiell side").

## Ideas not yet requested

- Map of kommuner coloured by frie inntekter per person (needs a Kartverket GeoJSON).
- Real-terms change next to nominal, using the NB price forecast.
- Tax by income decile and the top 0,1 % over time (kap_2_2027.xlsx).
- Long-term pressure to 2060 (NB figures 3.10 and 3.12).
- More "For deg" facts: Ryfast toll discount ending, reindrift, hurtigbåt programme (left out by the extractors, see FACTS.md §9).

## Done

Moved to docs/done.md.
