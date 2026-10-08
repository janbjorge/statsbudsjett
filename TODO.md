# TODO

Every request from jb, with status. Newest first. An item is ticked only when it is done and verified; finished items move to docs/done.md.

## Open

- [ ] Make the pages less dense (jb 2026-10-08: "my head just explodes there is so much information"). Plan in docs/plan-density.md, approved 2026-10-08. Steps 1 to 4 done. Step 4 missed its targets (/ 21.7 and /tilbud 35.2 phone screens, target under 15); jb to decide on the next cut. Step 5's user test is up to jb.
- [ ] Get 4xx in Logfire to ~0 for real clients (jb 2026-10-08). Scanner probes (`/.env`, `/.git/*`, `/.svn/*`, POST/OPTIONS `/`) should keep getting 404/405. Still open as of 2026-10-08, the rest is fixed (robots.txt a5e4e18, HEAD 52fa0a2, sitemap.xml bb8dfe9, favicon.ico and apple-touch-icon.png d0a7dc2):
  - `/.well-known/security.txt` and `/security.txt`: needs a contact address from jb.

## Ideas not yet requested

- Map of kommuner coloured by frie inntekter per person (needs a Kartverket GeoJSON).
- Real-terms change next to nominal, using the NB price forecast.
- Tax by income decile and the top 0,1 % over time (kap_2_2027.xlsx).
- Long-term pressure to 2060 (NB figures 3.10 and 3.12).
- The parties' alternative budgets next to the government's, starting with oil money use (published in November). From the r/norge thread, 2026-10-08.
- More "For deg" facts: Ryfast toll discount ending, reindrift, hurtigbåt programme (left out by the extractors, see FACTS.md §9).

## Done

Moved to docs/done.md.
