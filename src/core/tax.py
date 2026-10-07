"""Income tax for wage, pension and business income under 2026 rules, 2027 rules and the 2027 reference system.

The rules come from Prop. 1 LS (2026–2027) tabell 1.5 (datasets/meg.json). The engine reproduces
tabell 2.1 and the official example of about −1 800 kr at 750 000 kr; see tests/test_tax.py.
What it leaves out is listed in METHOD.md §5.
"""

from dataclasses import dataclass
from enum import StrEnum

type Year = int


class Business(StrEnum):
    """What kind of business income, which sets the trygdeavgift rate and the special deduction (FACTS.md §7)."""

    ANNEN = "annen"
    JORDBRUK = "jordbruk"
    FISKE = "fiske"


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
    trygdeavgift_naering: float
    trygdeavgift_fiske: float
    trygdeavgift_nedre: float
    trygdeavgift_opptrapping: float
    trinnskatt: tuple[Bracket, ...]
    pensjonsfradrag_max: float
    pensjonsfradrag_grense1: float
    pensjonsfradrag_sats1: float
    pensjonsfradrag_grense2: float
    pensjonsfradrag_sats2: float
    jordbruksfradrag_bunn: float
    jordbruksfradrag_sats: float
    jordbruksfradrag_maks: float
    fiskerfradrag_sats: float
    fiskerfradrag_maks: float


@dataclass(frozen=True, slots=True)
class Growth:
    """Expected growth used to carry 2026 amounts into the 2027 reference system, in percent."""

    wage: float
    pension: float
    wage_page: int | None = None
    pension_page: int | None = None


@dataclass(frozen=True, slots=True)
class TaxPages:
    """The Prop. 1 LS page (PDF page) for each rule shown under "Slik er skatten regnet"."""

    alminnelig: int
    personfradrag: int
    minstefradrag: int
    trygdeavgift: int
    trinnskatt: int
    pensjonsfradrag: int
    jordbruksfradrag: int
    fiskerfradrag: int


@dataclass(frozen=True, slots=True)
class TaxTable:
    """Raw parameters for both years, as extracted from Prop. 1 LS."""

    params: dict[str, dict[str, float | None]]
    trinnskatt: dict[str, list[dict[str, float]]]
    growth: Growth
    pages: TaxPages
    source_url: str = ""

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
            trygdeavgift_naering=g("trygdeavgift_annen_naering"),
            trygdeavgift_fiske=g("trygdeavgift_fiske_barnepass"),
            trygdeavgift_nedre=g("trygdeavgift_nedre_grense") * wage_index,
            trygdeavgift_opptrapping=g("trygdeavgift_opptrappingssats"),
            trinnskatt=tuple(Bracket(b["from"] * wage_index, b["rate"]) for b in self.trinnskatt[y]),
            pensjonsfradrag_max=g("pensjonsskattefradrag_maks") * pension_index,
            pensjonsfradrag_grense1=g("pensjonsskattefradrag_trinn1_grense") * pension_index,
            pensjonsfradrag_sats1=g("pensjonsskattefradrag_trinn1_sats"),
            pensjonsfradrag_grense2=g("pensjonsskattefradrag_trinn2_grense") * pension_index,
            pensjonsfradrag_sats2=g("pensjonsskattefradrag_trinn2_sats"),
            jordbruksfradrag_bunn=g("jordbruksfradrag_inntektsuavhengig") * wage_index,
            jordbruksfradrag_sats=g("jordbruksfradrag_sats"),
            jordbruksfradrag_maks=g("jordbruksfradrag_maks") * wage_index,
            fiskerfradrag_sats=g("fiskerfradrag_sats"),
            fiskerfradrag_maks=g("fiskerfradrag_ovre") * wage_index,
        )

    def reference_2027(self) -> TaxRules:
        """2026 rules carried forward with expected wage and pension growth, the government's yardstick."""
        return self.rules(2026, 1 + self.growth.wage / 100, 1 + self.growth.pension / 100)


def special_deduction(rules: TaxRules, business: float, kind: Business) -> float:
    """Jordbruksfradrag (skatteloven § 8-1 femte ledd) or fiskerfradrag (§ 6-60), in alminnelig inntekt only."""
    match kind:
        case Business.JORDBRUK:
            above = max(0, business - rules.jordbruksfradrag_bunn) * rules.jordbruksfradrag_sats / 100
            return min(min(business, rules.jordbruksfradrag_bunn) + above, rules.jordbruksfradrag_maks)
        case Business.FISKE:
            return min(business * rules.fiskerfradrag_sats / 100, rules.fiskerfradrag_maks)
        case Business.ANNEN:
            return 0.0


@dataclass(frozen=True, slots=True)
class TaxLines:
    """One person's income tax line by line, as shown under "Slik er skatten regnet"."""

    personinntekt: float
    minstefradrag: float
    special_deduction: float
    personfradrag: float
    alminnelig_inntekt: float
    alminnelig: float
    trygdeavgift: float
    trinnskatt: float
    pensjonsfradrag: float
    """The pension tax credit actually used, at most the tax it is set against."""

    @property
    def total(self) -> float:
        return self.alminnelig + self.trygdeavgift + self.trinnskatt - self.pensjonsfradrag


def tax_lines(rules: TaxRules, wage: float = 0, pension: float = 0, business: float = 0, kind: Business = Business.ANNEN) -> TaxLines:
    """Income tax for one person with standard deductions, line by line.

    Business income gets no minstefradrag and counts in full as personinntekt; the skjermingsfradrag
    is left out (METHOD.md §5). The special deduction lowers alminnelig inntekt only (skatteloven § 12-11 (2) b).
    """
    minstefradrag = min(wage * rules.minstefradrag_lonn / 100, rules.minstefradrag_lonn_max) + min(
        pension * rules.minstefradrag_pensjon / 100, rules.minstefradrag_pensjon_max
    )
    special = special_deduction(rules, business, kind)
    alminnelig_inntekt = max(0, wage + pension + business - minstefradrag - special - rules.personfradrag)

    personinntekt = wage + pension + business
    business_rate = rules.trygdeavgift_fiske if kind is Business.FISKE else rules.trygdeavgift_naering
    raw = wage * rules.trygdeavgift_lonn / 100 + pension * rules.trygdeavgift_pensjon / 100 + business * business_rate / 100
    # Phase-in: never more than the opptrappingssats of income above the lower limit
    trygdeavgift = 0.0 if personinntekt <= rules.trygdeavgift_nedre else min(
        raw, (personinntekt - rules.trygdeavgift_nedre) * rules.trygdeavgift_opptrapping / 100
    )

    trinnskatt = 0.0
    for i, bracket in enumerate(rules.trinnskatt):
        top = rules.trinnskatt[i + 1].start if i + 1 < len(rules.trinnskatt) else float("inf")
        trinnskatt += max(0, min(personinntekt, top) - bracket.start) * bracket.rate / 100

    alminnelig = alminnelig_inntekt * rules.alminnelig / 100
    pensjonsfradrag = 0.0
    if pension > 0:
        reduction = (
            max(0, min(pension, rules.pensjonsfradrag_grense2) - rules.pensjonsfradrag_grense1) * rules.pensjonsfradrag_sats1 / 100
            + max(0, pension - rules.pensjonsfradrag_grense2) * rules.pensjonsfradrag_sats2 / 100
        )
        pensjonsfradrag = min(max(0, rules.pensjonsfradrag_max - reduction), alminnelig + trygdeavgift + trinnskatt)

    return TaxLines(
        personinntekt=personinntekt,
        minstefradrag=minstefradrag,
        special_deduction=special,
        personfradrag=rules.personfradrag,
        alminnelig_inntekt=alminnelig_inntekt,
        alminnelig=alminnelig,
        trygdeavgift=trygdeavgift,
        trinnskatt=trinnskatt,
        pensjonsfradrag=pensjonsfradrag,
    )


def tax(rules: TaxRules, wage: float = 0, pension: float = 0, business: float = 0, kind: Business = Business.ANNEN) -> float:
    """Total income tax for one person with standard deductions (see tax_lines)."""
    return tax_lines(rules, wage, pension, business, kind).total


@dataclass(frozen=True, slots=True)
class Adult:
    wage: float = 0
    pension: float = 0
    business: float = 0
    business_kind: Business = Business.ANNEN


@dataclass(frozen=True, slots=True)
class TaxEffect:
    tax_2027: float
    tax_reference: float
    income: float
    lines: tuple[TaxLines, ...] = ()
    """2027 tax for each adult, in the order given."""

    @property
    def change(self) -> float:
        return self.tax_2027 - self.tax_reference

    @property
    def rate(self) -> float:
        return self.tax_2027 / self.income * 100 if self.income else 0.0


def household_effect(table: TaxTable, adults: list[Adult]) -> TaxEffect:
    """Tax in 2027 for the household and the change against the reference system."""
    r27, ref = table.rules(2027), table.reference_2027()
    lines = tuple(tax_lines(r27, a.wage, a.pension, a.business, a.business_kind) for a in adults)
    return TaxEffect(
        tax_2027=sum(line.total for line in lines),
        tax_reference=sum(tax(ref, a.wage, a.pension, a.business, a.business_kind) for a in adults),
        income=sum(a.wage + a.pension + a.business for a in adults),
        lines=lines,
    )
