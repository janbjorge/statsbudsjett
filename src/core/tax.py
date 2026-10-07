"""Income tax for wage and pension income under 2026 rules, 2027 rules and the 2027 reference system.

The rules come from Prop. 1 LS (2026–2027) tabell 1.5 (datasets/meg.json). The engine reproduces
tabell 2.1 and the official example of about −1 800 kr at 750 000 kr; see tests/test_tax.py.
What it leaves out is listed in METHOD.md §5.
"""

from dataclasses import dataclass

type Year = int


@dataclass(frozen=True, slots=True)
class Bracket:
    start: float
    rate: float


@dataclass(frozen=True, slots=True)
class TaxRules:
    alminnelig: float
    personfradrag: float
    minstefradrag_lonn: float
    minstefradrag_lonn_max: float
    minstefradrag_pensjon: float
    minstefradrag_pensjon_max: float
    trygdeavgift_lonn: float
    trygdeavgift_pensjon: float
    trygdeavgift_nedre: float
    trygdeavgift_opptrapping: float
    trinnskatt: tuple[Bracket, ...]
    pensjonsfradrag_max: float
    pensjonsfradrag_grense1: float
    pensjonsfradrag_sats1: float
    pensjonsfradrag_grense2: float
    pensjonsfradrag_sats2: float


@dataclass(frozen=True, slots=True)
class Growth:
    """Expected growth used to carry 2026 amounts into the 2027 reference system, in percent."""

    wage: float
    pension: float


@dataclass(frozen=True, slots=True)
class TaxTable:
    """Raw parameters for both years, as extracted from Prop. 1 LS."""

    params: dict[str, dict[str, float | None]]
    trinnskatt: dict[str, list[dict[str, float]]]
    growth: Growth

    def rules(self, year: Year, wage_index: float = 1.0, pension_index: float = 1.0) -> TaxRules:
        y = f"y{year}"

        def g(key: str) -> float:
            value = self.params[key][y]
            if value is None:
                raise KeyError(f"{key} has no value for {year}")
            return value

        return TaxRules(
            alminnelig=g("skatt_alminnelig_inntekt"),
            personfradrag=g("personfradrag") * wage_index,
            minstefradrag_lonn=g("minstefradrag_lonn_sats"),
            minstefradrag_lonn_max=g("minstefradrag_lonn_ovre") * wage_index,
            minstefradrag_pensjon=g("minstefradrag_pensjon_sats"),
            minstefradrag_pensjon_max=g("minstefradrag_pensjon_ovre") * pension_index,
            trygdeavgift_lonn=g("trygdeavgift_lonn"),
            trygdeavgift_pensjon=g("trygdeavgift_pensjon"),
            trygdeavgift_nedre=g("trygdeavgift_nedre_grense") * wage_index,
            trygdeavgift_opptrapping=g("trygdeavgift_opptrappingssats"),
            trinnskatt=tuple(Bracket(b["from"] * wage_index, b["rate"]) for b in self.trinnskatt[y]),
            pensjonsfradrag_max=g("pensjonsskattefradrag_maks") * pension_index,
            pensjonsfradrag_grense1=g("pensjonsskattefradrag_trinn1_grense") * pension_index,
            pensjonsfradrag_sats1=g("pensjonsskattefradrag_trinn1_sats"),
            pensjonsfradrag_grense2=g("pensjonsskattefradrag_trinn2_grense") * pension_index,
            pensjonsfradrag_sats2=g("pensjonsskattefradrag_trinn2_sats"),
        )

    def reference_2027(self) -> TaxRules:
        """2026 rules carried forward with expected wage and pension growth, the government's yardstick."""
        return self.rules(2026, 1 + self.growth.wage / 100, 1 + self.growth.pension / 100)


def tax(rules: TaxRules, wage: float = 0, pension: float = 0) -> float:
    """Total income tax for one person with standard deductions."""
    minstefradrag = min(wage * rules.minstefradrag_lonn / 100, rules.minstefradrag_lonn_max) + min(
        pension * rules.minstefradrag_pensjon / 100, rules.minstefradrag_pensjon_max
    )
    alminnelig = max(0, wage + pension - minstefradrag - rules.personfradrag) * rules.alminnelig / 100

    personinntekt = wage + pension
    raw = wage * rules.trygdeavgift_lonn / 100 + pension * rules.trygdeavgift_pensjon / 100
    # Phase-in: never more than the opptrappingssats of income above the lower limit
    trygdeavgift = 0.0 if personinntekt <= rules.trygdeavgift_nedre else min(
        raw, (personinntekt - rules.trygdeavgift_nedre) * rules.trygdeavgift_opptrapping / 100
    )

    trinnskatt = 0.0
    for i, bracket in enumerate(rules.trinnskatt):
        top = rules.trinnskatt[i + 1].start if i + 1 < len(rules.trinnskatt) else float("inf")
        trinnskatt += max(0, min(personinntekt, top) - bracket.start) * bracket.rate / 100

    pensjonsfradrag = 0.0
    if pension > 0:
        reduction = (
            max(0, min(pension, rules.pensjonsfradrag_grense2) - rules.pensjonsfradrag_grense1) * rules.pensjonsfradrag_sats1 / 100
            + max(0, pension - rules.pensjonsfradrag_grense2) * rules.pensjonsfradrag_sats2 / 100
        )
        pensjonsfradrag = max(0, rules.pensjonsfradrag_max - reduction)

    return max(0, alminnelig + trygdeavgift + trinnskatt - pensjonsfradrag)


@dataclass(frozen=True, slots=True)
class Adult:
    wage: float = 0
    pension: float = 0


@dataclass(frozen=True, slots=True)
class TaxEffect:
    tax_2027: float
    tax_reference: float
    income: float

    @property
    def change(self) -> float:
        return self.tax_2027 - self.tax_reference

    @property
    def rate(self) -> float:
        return self.tax_2027 / self.income * 100 if self.income else 0.0


def household_effect(table: TaxTable, adults: list[Adult]) -> TaxEffect:
    """Tax in 2027 for the household and the change against the reference system."""
    r27, ref = table.rules(2027), table.reference_2027()
    return TaxEffect(
        tax_2027=sum(tax(r27, a.wage, a.pension) for a in adults),
        tax_reference=sum(tax(ref, a.wage, a.pension) for a in adults),
        income=sum(a.wage + a.pension for a in adults),
    )
