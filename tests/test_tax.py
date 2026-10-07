"""The tax engine against figures the government published in Prop. 1 LS (2026–2027)."""

import pytest

from adapters.datasets import JsonDatasets
from core.tax import Adult, household_effect, tax

TABLE = JsonDatasets().tax_table()


@pytest.mark.parametrize(("wage", "expected"), [(200_000, 15_200), (650_000, 160_983), (1_000_000, 305_870)])
def test_2026_tax_matches_tabell_2_1(wage: int, expected: int) -> None:
    assert round(tax(TABLE.rules(2026), wage=wage)) == expected


def test_wage_earner_at_750_000_gets_about_1_800_kr_lower_tax() -> None:
    # Press release "Foreslår milliardkutt i inntektsskatten": om lag 1 800 kroner
    change = household_effect(TABLE, [Adult(wage=750_000)]).change
    assert -1_850 < change < -1_700


def test_couple_with_two_750_000_incomes_gets_about_3_500_kr() -> None:
    change = household_effect(TABLE, [Adult(wage=750_000), Adult(wage=750_000)]).change
    assert -3_550 < change < -3_400


def test_pension_relief_is_phased_out_above_450_000() -> None:
    # Prop. 1 LS p. 79: relief "inntil 750 kroner", "faset ut ved en pensjonsinntekt på drøyt 450 000 kroner".
    # On top comes the personfradrag increase everyone gets (about 233 kr).
    low = household_effect(TABLE, [Adult(pension=400_000)]).change
    high = household_effect(TABLE, [Adult(pension=500_000)]).change
    assert -1_000 < low < -750
    assert -300 < high < -200


def test_no_income_no_tax() -> None:
    effect = household_effect(TABLE, [Adult()])
    assert effect.tax_2027 == 0
    assert effect.change == 0
