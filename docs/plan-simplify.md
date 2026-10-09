# Plan: fewer sections, each thing said once, insight first

Status: built 2026-10-09 (jb: "lets do the recommendations"), after a full re-check of every page. See "Results" at the end. Follows docs/plan-density.md, whose step 4 left `/` at 21.7 phone screens and asked jb for the next cut.

## Why

jb 2026-10-09: drop the Ordliste, simplify, focus on insight, and say each thing once. The site should answer three questions: what does the budget mean for me, what changes from 2026, and where does the money go. A section that answers none of them goes. A number shown in two places keeps one place.

## How the re-check was done

WebKit at 390×664, local server, on 2026-10-09. A throwaway script measured each section (height in phone screens, words), dumped the visible text, and listed numbers that appear in more than one section. Each page was read as full-page screenshots. `/` was checked twice: with the default profile, and with the "Familie med to små barn" example. A second script checked datasets/meg.json for facts that repeat their own numbers or cover the same thing as another fact.

## Findings

### 1. The same thing gets two different numbers

The front page and `/flyt` use Gul bok amounts, which are nominal. The cards on `/tilbud` quote press releases, which often give "extra" or real growth. No page explains the difference, so the numbers seem to disagree:

- Folketrygden: 794,1 mrd. kr, +50,1 on `/`, against "Folketrygden koster 708 mrd. kr, 44 mrd. kr mer" on `/tilbud` (that one covers only Arbeids- og inkluderingsdepartementet's part).
- Forsvar: +11,9 mrd. in the treemap, against "Forsvarsbudsjettet øker med 6,5 mrd. kr" on `/tilbud`.
- Sykehus: regionale helseforetak +13,3 mrd. in "Hva endres", against "Sykehusene får 2,6 mrd. kr mer til drift".
- Kommunene: rammetilskudd +13,7 mrd., against "Kommunene får 3,2 mrd. kr mer i frie inntekter" (that is growth on top of prices and wages).

This also points to the main insight the site is missing: no page says how much of the 122,3 mrd. kr increase is price and wage growth and how much is new policy. The press-release figures suggest most of it is price and wage growth, but that has not been checked. TODO.md already lists "Real-terms change next to nominal".

### 2. Each card says its number three times

- A typical card has a title ("Egenandelstaket øker til 3 406 kr"), a summary ("Taket øker fra 3 278 kr i 2026 til 3 406 kr i 2027") and an amount line ("Egenandelstak: 3 278 → 3 406 kr"). In datasets/meg.json, 21 of 145 facts repeat the same number in all three, and 53 more repeat it in two of them.
- The direction is given up to four times: the group heading ("Du betaler mer eller får mindre"), the badge ("Du betaler mer"), the title ("øker") and the arrow in the amount line.
- On `/tilbud` the badge uses different words for the same thing: "Styrkes", "Mer penger", "Svekkes".

### 3. Facts that repeat or overlap other facts

- Parts shown next to their whole: "Forsvarsbudsjettet øker med 6,5 mrd." plus "2,8 mrd. til drift" and "1,6 mrd. til bygg". Folketrygden 708 plus alderspensjon +26, uføretrygd +9 and sykepenger +5, which "Hva endres" on `/` also shows (+26,1, +9,6, +5,7).
- For a family with a car, "For deg" shows two trafikkforsikringsavgift cards (one for ordinary cars, one for electric cars), and under "Står fast" both "Avgiftene på bensin og diesel holdes reelt uendret" and its parts.
- "Står fast" lists things that do change: veibruksavgift 3,77 → 3,37 and CO2-avgift 3,8 → 4,4 kr/liter.

### 4. Sections and pages that repeat each other

- Spending by area is shown four times: the receipt's stacked bar plus legend (per 100 kr), the receipt itself (in kr), the treemap and its table on `/`, and "Utgiftene per innbygger" on `/visste-du`. `/flyt`'s change chart shows it a fifth time.
- Income by source is shown four times: the bars on `/`, the Sankey, the treemap's Inntekter tab, and `/visste-du`.
- The total, the change and the oil money: the hero tiles on `/`, three of the four tiles on `/flyt`, and the lede of "Hva endres".
- The oil fund is explained in five places: the hero tile, the note under the income bars, the `/flyt` lede, `#olje` and `/oljefondet`. In `#olje` every number is in the text and again as a label on the chart. `/oljefondet` states its four totals four times: in the title, the lede, the tiles and the chart's end labels.
- `/visste-du` has four tiles where two are the other two divided by a constant (per day against per year, per second against per day).
- "Fant du en feil?" takes 1.7 screens to say what the footer says in one line. The Ordliste takes 0.6 screens. The footer and `/ki` both list the downloads.
- Navigation lists each front-page section twice, and every subpage has "← Budsjettlupa" next to the brand link.

### 5. Sections that show data but state no finding

- "Hvor kommer pengene fra?" does not say what the bars show: the oil fund is the single largest source, and income tax falls from 507,8 to 486,6 mrd. kr (both on `/flyt`).
- The oil transfer grows by 109,5 mrd. kr while spending grows by 122,3 mrd. kr. Only `/flyt` shows the first number, in a tile, without comment.
- "Kommunen din" for Oslo shows tax income at 131 % of the national average but frie inntekter under average. The page does not say why. Skatteutjevning is the likely reason, but that has not been checked against Grønt hefte yet.
- "For deg" lists every change at the same weight. The tax card is the only one with a kroner amount for the household. Elavgift going from 7,13 to 7,32 øre per kWh gets the same kind of card as the tax cut.

### 6. Page length (phone screens)

- `/` 21.7 by default, 27.8 with the family example. "For deg" alone is 5.7 by default and 11.8 for the family.
- `/tilbud` 35.2, of which the chip lists are 1.4 before the first fact. `/flyt` 7.2.

### 7. Broken on a phone (separate fixes, not part of this plan)

- `/flyt`: the Sankey has a large blank band above and below, and the change chart's 2026 → 2027 column is cut off at the right edge.
- `#olje`: the "Forventet realavkastning, 4 %" label sits on top of the line and the "2001: 3,9 %" label.

## Steps

Each step ships on its own, with `tools/density.py` before and after.

### Step 1: cut what answers none of the questions

- Remove `#ordliste`. Each term is explained where it is used: "utenom olje" in the hero, the oil fund in `#olje`, frie inntekter in the kommune lede.
- Remove `#feil`. The footer keeps one line linking to the new-issue page.
- Remove both from the nav, the phone sheet and tests/test_web.py. Remove "← Budsjettlupa" from subpages.

### Step 2: a card says each thing once

- Title: the change in plain words. Amount line: the numbers. The summary keeps only what neither of those says (who, when, why); drop it when nothing is left.
- The group heading carries the direction; the badge goes inside "For deg". On `/tilbud` there is one set of badge words.
- Merge parts into their whole (forsvar, folketrygden, the car fees) as amount lines on one card, in the data build (src/pipeline/datasets.py curation), logged in METHOD.md §6.
- Move things that change out of "Står fast".

### Step 3: one number per thing, and say which kind

- Every change on the site says whether it is nominal ("før prisvekst") or on top of price and wage growth, in the amount label.
- Where a card covers the same thing as a Gul bok amount (folketrygden, forsvar, sykehus, kommunene), the card says how the two relate in one line, or uses the Gul bok amount. Which one is jb's call (question 1).

### Step 4: one home per view

- Spending by area: the receipt on `/`, with the stacked bar and legend removed. The treemap moves to `/flyt`, so `/flyt` is "the whole budget" (Sankey, explore, changes) and drops its tiles.
- Income by source: one line in the hero and the Sankey on `/flyt`.
- Oil: `#olje` on `/` is one chart and one sentence; `/oljefondet` takes the other two charts and the table, and states its totals once.
- `/visste-du` keeps the per-person and playful units and drops both tables.

### Step 5: insight first

- Each section opens with a sentence built from the data that states the finding, for example: "Overføringen fra oljefondet øker med 109,5 mrd. kr, utgiftene med 122,3", "Skatt på inntekt og formue går ned". The kommune sentence waits until the skatteutjevning reason is checked.
- "For deg" opens with what changes most for the household in kroner (the tax change today), then the rest in order of size, with small changes collapsed.
- Front page order: hero, For deg, Hva endres, the receipt, Kommunen din, Oljepengene.

## Done when

- `/` is under 15 phone screens (21.7 today) and under 20 with the family example (27.8 today).
- No concept is explained in two places, and no amount is given twice on one page.
- No two numbers on the site describe the same thing without saying how they differ.
- METHOD.md, FACTS.md §1 and the sitemap match the pages.

## Questions for jb

1. Gul bok against press-release numbers (finding 1): show the Gul bok amount on the card and drop the press-release figure, or keep both with one line explaining the difference?
2. Is it fine to move the treemap to `/flyt` and make that page "the whole budget"? Then `/tilbud` needs a new name, for example "Alle endringene".
3. Step 5 writes findings as sentences. That is a judgement about what matters; each one goes in METHOD.md. Fine, or keep the sections neutral?

## Decisions (jb 2026-10-09: "lets do the recommendations")

1. Cards keep the Gul bok number and the press-release figure, and say which kind each is. Forsvar's press release states the nominal increase itself (11,9 mrd. kr, the same as Gul bok), so that card needed no explanation of our own.
2. The treemap moved to `/flyt`, now "Hele budsjettet". `/tilbud` is "Alle endringene". The URLs stay.
3. Findings are written as sentences, worked out from the data, and logged in METHOD.md §4.

## Results (2026-10-09, tools/density.py, WebKit, phone screens)

| | before | after |
|---|---|---|
| `/` | 21.7 | 14.1 |
| `/` with the family example | 27.8 | 19.1 |
| `/tilbud` | 35.2 | 31.8 |
| `/flyt` | 7.2 | 8.1 (the treemap moved in) |
| `/visste-du` | 4.4 | 3.1 |
| `/oljefondet` | 3.1 | 4.0 (the withdrawal chart moved in) |

Built: the Ordliste and "Fant du en feil?" are gone; 7 part facts merged into their whole; 96 summaries changed (trimmed, or rewritten on the merged and conflicting cards), 15 now empty; the badge on "For deg" only where it adds to the heading; forsvar, folketrygden and sykehusene say which kind of number they give; the income bars, the stacked tax bar and the fund-value chart are gone (the Sankey, the receipt and the `/oljefondet` chart show the same); each front-page section opens with a finding.

Not done, and why:

- "For deg" still shows every change the profile selects. docs/plan-density.md step 4 kept it that way (jb 2026-10-08), so collapsing small changes needs jb's say.
- `/flyt` shows the group changes twice: in the treemap table and in the "Endring fra 2026 til 2027" chart. Dropping one is jb's call.
- The badge words on `/tilbud` ("Styrkes", "Mer penger") differ on purpose (METHOD.md §6: more money for folketrygden is not a better service), so finding 2's last point was wrong and they stay.
- The Oslo finding (skatteutjevning) waits for a check against Grønt hefte.
- The two phone bugs in finding 7 are separate fixes.
