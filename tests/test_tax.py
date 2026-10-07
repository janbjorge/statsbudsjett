"""The tax engine against the law and the figures the government published.

Every test names its source. Short forms used below:
- LS: Prop. 1 LS (2026–2027) Skatter og avgifter 2027, https://www.regjeringen.no/no/dokumenter/prop.-1-ls-20262027/id3176120/
  Page numbers are the PDF pages, as in data/persona/tax.json. Tabell 1.5 is on pp. 26–30.
- skl: skatteloven (lov 26. mars 1999 nr. 14), https://lovdata.no/dokument/NL/lov/1999-03-26-14

Expected amounts are worked out by hand from the rates in the cited source, never by calling the engine,
so a wrong rate or a wrong rule in the engine makes the test fail.
"""

from itertools import pairwise

import pytest

from adapters.datasets import JsonDatasets
from core.tax import Adult, Business, household_effect, special_deduction, tax

TABLE = JsonDatasets().tax_table()
R26 = TABLE.rules(2026)
R27 = TABLE.rules(2027)


def marginal(rules, step: float = 1_000, kind: Business = Business.ANNEN, **income: float) -> float:
    """Marginal tax in percent on the next `step` kroner of the one income given in `income`."""
    ((name, amount),) = income.items()
    return (tax(rules, kind=kind, **{name: amount + step}) - tax(rules, kind=kind, **{name: amount})) / step * 100


# --- Parameters: the engine reads the right rows of tabell 1.5 -----------------------------------


@pytest.mark.parametrize(
    ("field", "y2026", "y2027"),
    [
        # LS tabell 1.5 p. 26
        ("alminnelig", 22, 22),
        ("trygdeavgift_nedre", 99_650, 99_650),
        ("trygdeavgift_opptrapping", 25, 25),
        ("trygdeavgift_lonn", 7.6, 7.4),
        ("trygdeavgift_fiske", 7.6, 7.4),  # "Fiske, fangst og barnepass", fotnote 7
        ("trygdeavgift_naering", 10.8, 10.6),  # "Annen næringsinntekt"
        ("trygdeavgift_pensjon", 5.1, 5.1),
        # LS tabell 1.5 p. 27
        ("personfradrag", 114_540, 120_180),
        ("minstefradrag_lonn", 46, 46),
        ("minstefradrag_lonn_max", 95_700, 99_550),
        ("minstefradrag_pensjon", 40, 40),
        ("minstefradrag_pensjon_max", 75_400, 77_950),
        ("pensjonsfradrag_max", 39_100, 40_750),
        # LS tabell 1.5 p. 28, and skl § 8-1 femte ledd / § 6-60 første ledd
        ("jordbruksfradrag_bunn", 99_600, 99_600),
        ("jordbruksfradrag_sats", 38, 38),
        ("jordbruksfradrag_maks", 208_900, 208_900),
        ("fiskerfradrag_sats", 30, 30),
        ("fiskerfradrag_maks", 160_000, 160_000),
    ],
)
def test_rules_carry_tabell_1_5(field: str, y2026: float, y2027: float) -> None:
    assert getattr(R26, field) == y2026
    assert getattr(R27, field) == y2027


def test_trinnskatt_carries_tabell_1_5() -> None:
    # LS tabell 1.5 p. 26, also skattevedtaket § 3-1 (LS pp. 256–257)
    assert [(b.start, b.rate) for b in R26.trinnskatt] == [
        (226_100, 1.7), (318_300, 4.0), (725_050, 13.7), (980_100, 16.8), (1_467_200, 17.8)
    ]
    assert [(b.start, b.rate) for b in R27.trinnskatt] == [
        (235_150, 1.7), (331_050, 4.0), (754_050, 13.7), (1_019_300, 16.8), (1_525_900, 17.8)
    ]


# --- Official totals -------------------------------------------------------------------------------


@pytest.mark.parametrize(("wage", "expected"), [(200_000, 15_200), (650_000, 160_983), (1_000_000, 305_870)])
def test_2026_tax_matches_tabell_2_1(wage: int, expected: int) -> None:
    # LS tabell 2.1: tax for a wage earner with standard deductions, 2026 rules
    assert round(tax(R26, wage=wage)) == expected


def test_wage_earner_at_750_000_gets_about_1_800_kr_lower_tax() -> None:
    # Press release "Foreslår milliardkutt i inntektsskatten": om lag 1 800 kroner
    change = household_effect(TABLE, [Adult(wage=750_000)]).change
    assert -1_850 < change < -1_700


def test_couple_with_two_750_000_incomes_gets_about_3_500_kr() -> None:
    # Same press release: a couple with two such incomes, om lag 3 500 kroner
    change = household_effect(TABLE, [Adult(wage=750_000), Adult(wage=750_000)]).change
    assert -3_550 < change < -3_400


def test_pension_relief_is_phased_out_above_450_000() -> None:
    # LS p. 79: relief "inntil 750 kroner", "faset ut ved en pensjonsinntekt på drøyt 450 000 kroner".
    # On top comes the personfradrag increase everyone gets (about 233 kr).
    low = household_effect(TABLE, [Adult(pension=400_000)]).change
    high = household_effect(TABLE, [Adult(pension=500_000)]).change
    assert -1_000 < low < -750
    assert -300 < high < -200


def test_no_income_no_tax() -> None:
    effect = household_effect(TABLE, [Adult()])
    assert effect.tax_2027 == 0
    assert effect.change == 0


# --- The wage path in LS p. 50 (figur 2.7, 2026 rules) ---------------------------------------------


def test_no_tax_up_to_the_trygdeavgift_lower_limit() -> None:
    # LS p. 50: "Frem til nedre grense for å betale trygdeavgift (99 650 kroner) betales ingen skatt."
    assert tax(R26, wage=99_650) == 0


def test_phase_in_rate_is_25_percent_above_the_lower_limit() -> None:
    # LS p. 50: "Deretter betales opptrappingssats (25 pst.)"
    assert marginal(R26, wage=120_000) == pytest.approx(25)


def test_ordinary_trygdeavgift_takes_over_at_143_175() -> None:
    # LS p. 50: "inntil det lønner seg å betale ordinær trygdeavgift (7,6 pst.) av hele inntekten,
    # i 2026 ved en inntekt på 143 175 kroner". By hand: 25 % × (143 175 − 99 650) = 10 881,25.
    assert tax(R26, wage=143_175) == pytest.approx(10_881.25)
    assert marginal(R26, wage=150_000) == pytest.approx(7.6)


def test_alminnelig_inntekt_is_taxed_from_210_240() -> None:
    # LS p. 50: "Når inntekten overstiger summen av personfradraget og minstefradraget, fra 210 240 kroner,
    # betales skatt av alminnelig inntekt (22 pst.). Marginalskatten øker til 29,6 pst."
    assert marginal(R26, wage=205_000) == pytest.approx(7.6)
    assert marginal(R26, wage=215_000) == pytest.approx(29.6)


def test_trinn_1_from_226_100() -> None:
    # LS p. 50: "Fra 226 100 kroner betales 1,7 pst. i trinnskatt, og marginalskatten øker til 31,3 pst."
    assert marginal(R26, wage=230_000) == pytest.approx(31.3)


# --- Top marginal rates, LS tabell 1.5 p. 27 "Maksimale effektive marginale skattesatser" ----------


@pytest.mark.parametrize(
    ("rules", "income", "expected"),
    [
        (R26, {"wage": 2_000_000}, 47.4),  # "Lønnsinntekt ekskl. arbeidsgiveravgift"
        (R27, {"wage": 2_000_000}, 47.2),
        (R26, {"pension": 2_000_000}, 44.9),  # "Pensjonsinntekt"
        (R27, {"pension": 2_000_000}, 44.9),
        (R26, {"business": 2_000_000}, 50.6),  # "Næringsinntekt"
        (R27, {"business": 2_000_000}, 50.4),
        (R27, {"business": 2_000_000, "kind": Business.JORDBRUK}, 50.4),  # jordbruk has no rate of its own
    ],
)
def test_top_marginal_rate_matches_tabell_1_5(rules, income: dict, expected: float) -> None:
    assert marginal(rules, **income) == pytest.approx(expected)


def test_fiske_top_marginal_rate_uses_the_wage_trygdeavgift() -> None:
    # LS tabell 1.5 p. 26 fotnote 7: fiske og fangst pay 7,4 pst. in 2027. 22 + 17,8 + 7,4 = 47,2
    assert marginal(R27, business=2_000_000, kind=Business.FISKE) == pytest.approx(47.2)


# --- The special deductions ----------------------------------------------------------------------


@pytest.mark.parametrize(
    ("business", "expected"),
    [
        (0, 0),
        (50_000, 50_000),  # skl § 8-1 femte ledd: "et jordbruksfradrag på inntil 99 600 kroner"
        (99_600, 99_600),
        (150_000, 118_752),  # 99 600 + 38 % × 50 400: "fradrag på 38 prosent av inntekten"
        (387_231, 208_899.78),  # just below the cap: 99 600 + 38 % × 287 631
        (387_232, 208_900),  # "opp til samlet fradrag på 208 900 kroner"
        (1_000_000, 208_900),
    ],
)
def test_jordbruksfradrag_follows_skatteloven_8_1(business: float, expected: float) -> None:
    assert special_deduction(R27, business, Business.JORDBRUK) == pytest.approx(expected)


@pytest.mark.parametrize(
    ("business", "expected"),
    [
        (0, 0),
        (400_000, 120_000),  # skl § 6-60 (1): "inntil 30 prosent av netto arbeidsinntekt"
        (533_333, 159_999.9),
        (700_000, 160_000),  # "begrenset til 160 000 kroner"
    ],
)
def test_fiskerfradrag_follows_skatteloven_6_60(business: float, expected: float) -> None:
    assert special_deduction(R27, business, Business.FISKE) == pytest.approx(expected)


def test_other_business_has_no_special_deduction() -> None:
    # LS tabell 1.5 p. 28 lists special deductions for jordbruk, reindrift, fiske and sjøfolk only
    assert special_deduction(R27, 500_000, Business.ANNEN) == 0


# --- Business income, worked by hand from 2027 rules ---------------------------------------------
# alminnelig 22 % of (income − minstefradrag − special deduction − personfradrag 120 180)
# trygdeavgift on personinntekt, capped at 25 % above 99 650; trinnskatt from LS tabell 1.5 p. 26.


def test_other_business_income_600_000() -> None:
    # No minstefradrag (LS p. 79: "Selvstendig næringsdrivende får fradrag for faktiske kostnader").
    # 22 % × 479 820 = 105 560,40; 10,6 % × 600 000 = 63 600;
    # trinnskatt 1,7 % × 95 900 + 4,0 % × 268 950 = 12 388,30. Sum 181 548,70.
    assert tax(R27, business=600_000) == pytest.approx(181_548.70)


def test_farmer_550_000() -> None:
    # The "Bonde" example. Jordbruksfradrag at its cap 208 900 (skl § 8-1 femte ledd).
    # 22 % × (550 000 − 208 900 − 120 180) = 48 602,40; 10,6 % × 550 000 = 58 300;
    # trinnskatt 1,7 % × 95 900 + 4,0 % × 218 950 = 10 388,30. Sum 117 290,70.
    assert tax(R27, business=550_000, kind=Business.JORDBRUK) == pytest.approx(117_290.70)


def test_small_farm_150_000_pays_only_phased_in_trygdeavgift() -> None:
    # Jordbruksfradrag 118 752 leaves 31 248, under the personfradrag: no tax on alminnelig inntekt.
    # Trygdeavgift min(10,6 % × 150 000 = 15 900, 25 % × 50 350 = 12 587,50) (LS tabell 1.5 p. 26).
    assert tax(R27, business=150_000, kind=Business.JORDBRUK) == pytest.approx(12_587.50)


@pytest.mark.parametrize(("business", "expected"), [(400_000, 69_148.70), (700_000, 160_548.70)])
def test_fisher(business: float, expected: float) -> None:
    # Fiskerfradrag 30 %, max 160 000 (skl § 6-60); trygdeavgift 7,4 % (LS fotnote 7).
    # 400 000: 22 % × 159 820 = 35 160,40; 7,4 % × 400 000 = 29 600; trinnskatt 4 388,30. Sum 69 148,70
    assert tax(R27, business=business, kind=Business.FISKE) == pytest.approx(expected)


def test_business_income_under_the_lower_limit_is_phased_in() -> None:
    # The 25 % cap applies to all personinntekt, business included (LS p. 80, punkt 3.1.3:
    # "Avgiften skal ikke utgjøre mer enn 25 pst. av inntekten som overstiger nedre grense").
    # min(10,6 % × 110 000 = 11 660, 25 % × 10 350 = 2 587,50)
    assert tax(R27, business=110_000) == pytest.approx(2_587.50)


def test_wage_and_farm_income_together() -> None:
    # Minstefradrag only on the wage: min(46 % × 300 000, 99 550) = 99 550 (LS p. 79, tabell 1.5 p. 27).
    # Jordbruksfradrag on the farm income only: 99 600 + 38 % × 100 400 = 137 752.
    # 22 % × (500 000 − 99 550 − 137 752 − 120 180) = 31 353,96
    # trygdeavgift 7,4 % × 300 000 + 10,6 % × 200 000 = 43 400
    # trinnskatt 1,7 % × 95 900 + 4,0 % × 168 950 = 8 388,30. Sum 83 142,26.
    assert tax(R27, wage=300_000, business=200_000, kind=Business.JORDBRUK) == pytest.approx(83_142.26)


# --- Structure of the law ------------------------------------------------------------------------


@pytest.mark.parametrize("business", [300_000, 550_000, 900_000, 2_000_000])
def test_jordbruksfradrag_lowers_only_alminnelig_inntekt(business: float) -> None:
    # skl § 12-11 (2) b adds the jordbruksfradrag back when computing beregnet personinntekt, so it
    # does not lower trinnskatt or trygdeavgift. The whole difference to other business income is 22 %
    # of the deduction.
    gap = tax(R27, business=business) - tax(R27, business=business, kind=Business.JORDBRUK)
    assert gap == pytest.approx(0.22 * special_deduction(R27, business, Business.JORDBRUK))


@pytest.mark.parametrize("business", [300_000, 550_000, 900_000, 2_000_000])
def test_fiskerfradrag_lowers_only_alminnelig_inntekt(business: float) -> None:
    # skl § 12-11 (2) b for the deduction; LS fotnote 7 for the 3,2 points lower trygdeavgift (10,6 − 7,4)
    gap = tax(R27, business=business) - tax(R27, business=business, kind=Business.FISKE)
    expected = 0.22 * special_deduction(R27, business, Business.FISKE) + 0.032 * business
    assert gap == pytest.approx(expected)


@pytest.mark.parametrize("income", [400_000, 800_000, 2_000_000])
def test_business_income_gets_no_minstefradrag(income: float) -> None:
    # LS p. 79: minstefradrag is for "lønns-, trygde- og pensjonsinntekt"; næringsdrivende deduct real costs.
    # Against the same wage: 22 % of the capped minstefradrag 99 550, plus 3,2 points trygdeavgift.
    gap = tax(R27, business=income) - tax(R27, wage=income)
    assert gap == pytest.approx(0.22 * 99_550 + 0.032 * income)


@pytest.mark.parametrize("kind", list(Business))
@pytest.mark.parametrize(("wage", "pension"), [(0, 0), (200_000, 0), (650_000, 0), (0, 320_000), (400_000, 150_000)])
def test_business_kind_does_nothing_without_business_income(kind: Business, wage: float, pension: float) -> None:
    assert tax(R27, wage=wage, pension=pension, kind=kind) == tax(R27, wage=wage, pension=pension)


@pytest.mark.parametrize("kind", list(Business))
@pytest.mark.parametrize("rules", [R26, R27, TABLE.reference_2027()])
def test_tax_never_falls_when_business_income_rises(kind: Business, rules) -> None:
    # Every marginal rate in LS tabell 1.5 is positive, so more income never means less tax
    taxes = [tax(rules, business=x, kind=kind) for x in range(0, 2_000_001, 2_500)]
    assert all(b >= a for a, b in pairwise(taxes))


@pytest.mark.parametrize("kind", [Business.JORDBRUK, Business.FISKE])
def test_special_deduction_never_exceeds_the_income(kind: Business) -> None:
    for x in range(0, 1_000_001, 1_000):
        assert 0 <= special_deduction(R27, x, kind) <= x


# --- The household result ------------------------------------------------------------------------


def test_household_income_counts_business_income() -> None:
    effect = household_effect(TABLE, [Adult(wage=300_000), Adult(business=550_000, business_kind=Business.JORDBRUK)])
    assert effect.income == 850_000
    assert effect.tax_2027 == pytest.approx(tax(R27, wage=300_000) + 117_290.70)


def test_farmer_loses_on_the_nominal_jordbruksfradrag() -> None:
    # LS p. 80, punkt 3.1.6: keeping jordbruksfradraget nominal "innebærer en endring sammenlignet med
    # referansesystemet". The reference system carries the amounts with wage growth (METHOD.md §5 assumption):
    # cap 208 900 × 1,04 = 217 256. At 550 000 the deduction hits the cap in both, so against other business
    # income at the same level the farmer's change is 22 % × (217 256 − 208 900) = 1 838,32 kr worse.
    farmer = household_effect(TABLE, [Adult(business=550_000, business_kind=Business.JORDBRUK)]).change
    other = household_effect(TABLE, [Adult(business=550_000)]).change
    assert farmer - other == pytest.approx(1_838.32)


def test_farmer_change_adds_up_from_its_three_parts() -> None:
    # The "Bonde" example, 550 000 kr from jordbruk, 2027 rules against the reference system:
    # trygdeavgift 10,8 → 10,6 % (LS tabell 1.5 p. 26): −0,2 % × 550 000 = −1 100
    # personfradrag 120 180 against 114 540 × 1,04 (LS tabell 1.5 p. 27, growth p. 80): −22 % × 1 058,40 = −232,85
    # jordbruksfradrag kept at 208 900 against 208 900 × 1,04 (LS p. 80, METHOD.md §5): +22 % × 8 356 = +1 838,32
    # trinnskatt thresholds rounded to 50 kr (LS tabell 1.5 p. 26): trinn 1 at 235 150 against 235 144 and
    # trinn 2 at 331 050 against 331 032: −1,7 % × 6 − (4,0 − 1,7) % × 18 = −0,516
    change = household_effect(TABLE, [Adult(business=550_000, business_kind=Business.JORDBRUK)]).change
    assert change == pytest.approx(-1_100 - 232.848 + 1_838.32 - 0.516, abs=0.001)
