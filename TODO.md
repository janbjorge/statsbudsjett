# TODO

Every request from jb, with status. Newest first. An item is ticked only when it is done and verified; finished items move to docs/done.md.

## Open

- [ ] **Short domain** (jb 2026-10-07: "the domain is to long, can we make an alias somehow?"; 2026-10-07: "We are going to use the domain; budsjettlupa.no from now"). The code is host-neutral and ready: `CANONICAL_HOST` redirects every other host name to the one address and sets `<link rel="canonical">` (src/adapters/web/main.py). Left to do on Fly, in this order: `fly certs add budsjettlupa.no` and `fly certs add www.budsjettlupa.no`, DNS A/AAAA records for the apex and a CNAME for www to the values Fly shows, wait for the certificates, then `fly secrets set CANONICAL_HOST=budsjettlupa.no`. Setting the secret before the certificate is live would redirect visitors to a dead host. Update 2026-10-07 evening: both certificates are issued and budsjettlupa.no and www. serve the site. `CANONICAL_HOST` was set and then removed again (jb: "My zscaler blocks the domain due to being to new"), so statsbudsjett.fly.dev serves without redirect until the domain is old enough for corporate filters. Switch on later with `fly secrets set CANONICAL_HOST=budsjettlupa.no -a statsbudsjett`.
- [ ] **Read through the user-facing texts** before publishing: the cards for each preset, the glossary, and the footer disclaimer ("ikke en offisiell side").

## Ideas not yet requested

- Map of kommuner coloured by frie inntekter per person (needs a Kartverket GeoJSON).
- Real-terms change next to nominal, using the NB price forecast.
- Tax by income decile and the top 0,1 % over time (kap_2_2027.xlsx).
- Long-term pressure to 2060 (NB figures 3.10 and 3.12).
- More "For deg" facts: Ryfast toll discount ending, reindrift, hurtigbåt programme (left out by the extractors, see FACTS.md §9).

## Done

Moved to docs/done.md.
