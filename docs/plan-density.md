# Plan: make the pages calmer to read

Status: approved by jb 2026-10-08. Steps 1 to 4 are built; step 4 missed its page-length targets (see "Results"). See "Decisions" for the answers to the open questions.

## Why

jb tested the site on an iPhone: "when i look at the content on my screen my head just explodes there is so much information". The layout bugs and the phone menu are fixed (commits 10a909f and d8f8624). This plan covers what is left: how dense the pages are.

## What we measured

Measured in WebKit at 390×664 (phone) and 1280×720 (desktop), on 2026-10-08, with a throwaway script.

- Page length on a phone, in screens: `/` 22, `/tilbud` 44, `/flyt` 7, `/visste-du` 4, `/ki` 4, `/oljefondet` 3.
- Words per screen on a phone: 93 to 126 on every page. That is not high. The amount of text per screen is not the problem.
- Text styles (font size and weight combinations) on `/`: 24. They use 13 font sizes (36, 28, 24, 21, 17, 16, 15.12, 15, 14.5, 14, 13, 12.5 and 12 px) and 4 weights (400, 600, 650 and 700). `app.css` sets `font-size` 77 times; charts.js and flyt.js set font sizes and weights 9 more times.
- Most text on `/` is small: 1 354 words are 14 px, against 531 words at the 16 px base size.
- Text colours on `/`: 9.
- Line length on desktop: fact cards and notes run to roughly 150 characters per line. This is an estimate from width and font size, not a count.
- A fact card has up to seven parts: title, badge, summary, amounts, tag, caveat and source. `/tilbud` has 84 cards in 22 sections. No card appears twice.

What this points to is too many kinds of text, too much small grey text, lines that are too long on desktop, and pages that are very long. The amount of text on each screen is fine.

## What the research says

These are the sources found on 2026-10-08, with what each one supports. Where only the abstract or a summary was read, it says so.

1. People scan more than they read. The first lines and the first words of each line get the attention. Source: NN/g eye-tracking, 232 users, 2006, confirmed in 2017. https://www.nngroup.com/articles/f-shaped-pattern-reading-web-content-discovered/
   Supports: the title and first sentence of a card carry the message, so the rest can be quieter.
2. Visual clutter can be measured as "feature congestion": variation in colour, orientation and contrast. Colour variation matters. Source: Rosenholtz, Li and Nakano, Journal of Vision 2007. https://jov.arvojournals.org/article.aspx?articleid=2122001. Code is at https://persci.mit.edu/research/clutter/.
   Supports: fewer colours and styles, not only fewer words. It also gives us a before and after number.
3. Body text should be at least 16 px. GOV.UK uses 19 px on all screens and removed 14 px from its scale. Their reasons are the British Dyslexia Association's 12 pt minimum and reading at arm's length on a phone. Sources: https://design-system.service.gov.uk/styles/paragraphs, https://designnotes.blog.gov.uk/2022/12/12/making-the-gov-uk-frontend-typography-scale-more-accessible
   Supports: moving our 14 px body text up.
4. Line length: 55 characters per line gave the best comprehension on screen, against 25 and 100. Source: Dyson and Haselgrove 2001; only the abstract was read. https://www.semanticscholar.org/paper/The-influence-of-reading-speed-and-line-length-on-Dyson-Haselgrove/602a53a86c84dcdf8b5024c3a2abd2950389b55a. GOV.UK's old guide caps lines at 75 characters. Studies do not all agree.
   Supports: a cap around 68 characters on running text.
5. Progressive disclosure means showing the most important things first and the rest on request. Hidden things get used less. Sources: summaries only, https://ixdf.org/literature/book/the-glossary-of-human-computer-interaction/progressive-disclosure and https://theconceptlibrary.com/concept/progressive-disclosure (cites NN/g's 2016 study of hidden navigation).
   Supports: "Vis alle" under long lists, but no key numbers behind a click.
6. Klarspråk: most important first, short and airy text, informative subheadings, no large blocks of text on screen. Sources: https://sprakradet.no/klarsprak/ and KS, "Klarspråk for alle", https://www.ks.no/globalassets/fagomrader/digitalisering/klart-sprak/klarsprak---veiledning-a4_f41.pdf

The research gives no number for "how much per screen". The steps below are grounded in it. Where a step depends on our own judgement, it is marked as such.

## Steps

Each step ships on its own, with screenshots in WebKit at 390, 834 and 1280 px before it is ticked.

### Step 1: one type scale and shorter lines (looks only; no wording changes)

- Define the scale once in `app.css` as custom properties, and use only these:
  - `--t-display` 36 px / 650: the big number on `/`.
  - `--t-title` 28 px / 650: h1.
  - `--t-heading` 21 px / 650: h2 and tile values.
  - `--t-body` 17 px / 400 and 17 px / 650: all reading text, card titles, the summary in fact cards, and emphasis.
  - `--t-small` 14 px / 400 and 14 px / 650: sources, tags, badges, chips, table headers, notes.
  - `--t-chart` 12 px: tick labels inside SVG charts only.
- Weights are only 400 and 650. The 600 and 700 weights go.
- Grey (`--text-muted`) is only for small text. Body text is always `--text-primary` or `--text-secondary`.
- Running text gets `max-width: 68ch`: `p`, `.lede`, `.note`, `li`, and the summary in fact cards. Charts, tables and grids keep their full width.
- charts.js and flyt.js set SVG text sizes through CSS classes that use the same tokens, not numbers in the code.
- Judgement: 17 px rather than GOV.UK's 19 px. It is a compromise between the research and the page length on a phone.

Done when:

- `/` has at most 8 text styles. It has 24 today.
- No reading text is under 17 px, and no text at all is under 14 px, except chart ticks.
- No running text is over 70 characters per line at 1280 px.

### Step 2: a test that keeps it that way

- `tests/test_type_scale.py` is plain pytest and needs no browser. It reads `app.css`, `charts.js` and `flyt.js`, and fails when:
  - a `font-size` is not one of the tokens,
  - a `font-weight` is not 400 or 650,
  - a new rule for running text has no width cap.
- `tools/density.py` holds the measuring script, run by hand with `uvx --with playwright python tools/density.py`. It prints screens per page, words per screen, text styles, text colours and characters per line. It is not part of CI, since it needs a browser.
- AGENTS.md gets one line: "Text sizes come from the type scale in app.css; tests/test_type_scale.py enforces it."

### Step 3: a calmer fact card

Today a card has title, badge, summary, amounts, tag, caveat and source. The proposal:

- Always shown: title, badge, summary and amounts. The amounts are the numbers people come for.
- Moved to one small line at the bottom: "Kilde ↗". The tag ("Gjelder alle") goes away where the section heading already says it.
- The caveat ("Gjelder fra 1. juli 2027…") moves into the card behind "Mer om dette". Open question 1 is whether that is acceptable.
- Badge colours stay. They carry meaning (more, less, mixed).

Done when a typical card on `/` is at most 4 visible parts plus the source line, and it is still clear where every number comes from (AGENTS.md: every number cites its source).

### Step 4: shorter pages (changes what readers see first)

- `/tilbud`: each of the 22 sections shows its 3 most important changes, and the rest sit behind "Vis alle (n)" (`<details>`, so no JavaScript is needed). Open question 2 is how "most important" is decided.
- `/`, "Hva endres fra 2026?": 5 increases and 5 decreases instead of 10 and 10, with "Vis alle" for the rest.
- `/`, "For deg": unchanged. It already shows only what the form selects.
- Nothing that answers the page's main question goes behind a click: totals, your own tax, your kommune's numbers.

Done when `/tilbud` is under 15 phone screens (it is 44 today) and `/` is under 15 (it is 22).

### Step 5: measure again, and watch real use

- Run `tools/density.py` again and put the numbers before and after into docs/done.md.
- Optional: score screenshots before and after with Rosenholtz's feature congestion, using MIT's code. A Python port has not been checked yet; the original is MATLAB.
- Best evidence: three people do three tasks on their own phone while jb watches without helping:
  1. find what the budget changes for your own tax,
  2. find what your kommune gets,
  3. find the biggest change from 2026.
  Note where they stop or scroll past.

## Decisions (jb 2026-10-08)

1. The caveat goes behind "Mer om dette".
2. "Most important" on `/tilbud` is the largest amount in kroner. Facts without an amount come after, in today's order. Logged in METHOD.md.
3. Body text is 17 px.
4. The `/tilbud` chips stay as they are.

Changes while building step 1:

- `--t-display`, `--t-title` and `--t-heading` stay fluid (36→60, 28→40 and 21→26 px with the window), as before. At any one width each is still one size.
- The cap is `46ch`, not `68ch`: in this font a `ch` (the width of "0") is wider than an average letter, and 68ch gave about 95 characters a line. 46ch gives at most 69, measured.
- SVG labels on marks (Sankey nodes, the change chart, end labels) are 14 px; 12 px is for ticks and axis notes. The Sankey's narrow width went from 720 to 880 px and the change chart's label column from 220 to 256 px, so the bigger labels don't run into the bars. The Sankey labels already overlapped by 25 px before.

## Open questions for jb (answered above)

1. Is the caveat (when something takes effect, what is not included) fine behind "Mer om dette", or does it have to stay visible?
2. How do we rank "most important" on `/tilbud`? Options: by amount in kroner (most objective, but not every fact has an amount), by how many people it affects (not in the data today), or a hand-set order in data/persona/*.json. Logged in METHOD.md whichever way we go, since it is a judgement about the content.
3. 17 px body text, or go all the way to GOV.UK's 19 px? 19 px makes pages longer on a phone.
4. Should the `/tilbud` chips also show only sections with changes, or stay as they are?

## Not in this plan

- New content, or cutting facts from the data.
- The chart label overlaps on phones ("Uttak av fondet", small treemap cells). These are separate fixes.
- A phone-specific Sankey and change chart. Today they scroll sideways in their own box.

## Results (2026-10-08, tools/density.py, WebKit)

| | before | after |
|---|---|---|
| Text styles on `/` | 24 | 8 |
| Text styles, other pages | | 5 to 7 |
| Longest running line, 1280 px | about 95 characters | 69 |
| `/` on a phone, screens | 22 (23.4 with 17 px text) | 21.7 |
| `/tilbud` on a phone, screens | 44 (50.1 with 17 px text) | 35.2 |

Step 4 missed its target of under 15 phone screens:

- `/tilbud` has 22 sections. With one card per section it would still be 17.9 screens; two per section gives 27.2. Getting under 15 needs a different page, for example collapsing each section to its heading.
- On `/`, "For deg" alone is 5.7 screens, and this plan leaves it as it is. Then come the tax receipt (2.1), "Hva endres" (2.3), Kommunen din (2.1) and the oil fund (2.2).
