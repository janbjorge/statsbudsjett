# METHOD

Every simplification and judgement call behind the numbers on the pages. Add to it whenever you make one. Facts about the sources are in FACTS.md.

## 1. The non-oil budget

The pages show the budget the way Finansdepartementet presents it, without oil money.

- Removed: kap. 2440/5440 (SDØE), 5507 (petroleum tax), 5508/5509 (emission taxes on the shelf), 5685 (Equinor dividend), 2800 (transfer to the fund). The list is in src/pipeline/flows.py:19.
- Removed: all posts 90–99 (loan transactions such as student loans and Husbanken).
- The transfer from the fund (kap. 5800) stays as an income source, so income equals spending exactly.
- Why: about 570 mrd. kr goes to the fund and about 560 mrd. kr comes back. Showing both would double-count and drown out everything else.

## 2. Years and prices

- Both years are the government's original proposal: Gul bok 2026 and Gul bok 2027. Neither is the adopted (saldert) budget.
- All amounts are nominal kroner. "+5,7 %" is before price growth, and the page says so.

## 3. Grouping

- Spending is grouped into 8 groups with about 33 sub-groups by programområde, programkategori and a few chapters (src/pipeline/flows.py:52 and :64). The group names are ours, not official.
- Choices worth knowing:
  - Folketrygden is omr. 28, 29, 30 and 33.
  - Kommunesektoren is only kat. 13.70.
  - Momskompensasjon (kap. 1632/1633) goes under "Øvrige formål".
  - Forsvar has no sub-groups.
- Income is grouped into 6 sources by chapter (src/pipeline/flows.py:43).
- The first seven groups get a palette colour; "Øvrige formål" is grey, because the palette has 8 slots and income takes slot 1.

## 4. Comparing 2026 and 2027

- Groups and sub-groups compare exact sums for both years.
- Chapters and posts are matched on number. Renumbered or merged chapters show up as new or missing. The "biggest changes" lists leave them out and say how many there are (12).
- The treemap lays out with negative posts set to 0 but shows exact sums (src/adapters/web/main.py:69).
- Per person = amount / 5 636 995 (population on 1.7.2026).

## 5. Tax calculator

- Covers wage and pension income with standard deductions: minstefradrag, personfradrag, trygdeavgift with the phase-in rule, trinnskatt, and the pension tax credit.
- Not covered: business income (trygdeavgift 10,6 % instead of 7,4 %), uføretrygd, interest deductions, wealth tax, Finnmark/Nord-Troms rules, and the skattebegrensning for low incomes. The page lists these.
- The headline is 2027 rules against the reference system: 2026 amounts × 1,04 for wage-related amounts and × 1,0335 for pension amounts (src/pipeline/datasets.py:115). That is the government's own yardstick.
- Assumption: personfradrag and the trygdeavgift lower limit are indexed by wage growth in the reference system. The source does not state this; it matches the official −1 800 kr example.

## 6. "For deg" facts

- The effect (pluss/minus/uendret/blandet) is the extracting agent's reading of the source, from the citizen's side. It is a judgement, not a number.
- Unchanged facts are shown as compact lines, not hidden, because "barnehage still costs 1 200 kr" matters to families.
- Items tagged with a child age band (0-1, 1-5, 6-15, 16-18) show only when the household has a child in that band, once any child is entered.
- A child over 18 has no facts of its own. Many still live at home or study with help from their parents, so entering one shows the student facts under "Barn over 18 år som studerer" (src/core/facts.py). They only apply if the child studies, hence the label. Borteboerstipend stays in the 16-18 band, so an adult child still in videregående does not see it.
- Barnetrygd is hidden when every child entered is over 18. The quote says "barn 0–18 år", and the build stops if it no longer does (src/pipeline/datasets.py, `under_18`). Other cards with an age limit are left on until a source states the limit.
- Foreldrefradrag stays on for every age. The usual limits (15 000 / 10 000 kr) are for younger children; Prop. 1 LS fotnote 13 (page 30) gives 25 000 / 15 000 kr for children 12 and older with særskilt behov for omsorg og pleie, with no upper age. Both sets of limits are shown and verified. The source does not state the age limit for the usual limits, so the card does not either.
- The tax receipt (Skatten din) splits your tax in proportion to non-oil spending. Money is fungible; the page says this is a simplification.

## 7. Kommuner

- Frie inntekter (tax plus rammetilskudd) per person compares kommuner, and the national average is total frie inntekter divided by total population. It is not all money a kommune has. Earmarked grants, fees and VAT compensation are left out, as on the government's own page.
