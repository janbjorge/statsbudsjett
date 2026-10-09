"""Read-only queries behind every page and HTMX fragment. Results are frozen dataclasses."""

from dataclasses import dataclass

from core import budget as b
from core.facts import Fact, Group, Profile, Section, by_wallet, general, is_general, select
from core.ports import Datasets
from core.tax import TaxEffect, TaxPages, household_effect


@dataclass(frozen=True, slots=True)
class Overview:
    total: float
    total_2026: float
    fund: float
    fund_2026: float
    fund_share: float
    top_group: str
    top_amount: float
    grew_most: str  # the spending group with the largest increase from 2026, in kroner
    grew_most_by: float

    @property
    def change(self) -> float:
        return self.total - self.total_2026

    @property
    def change_pct(self) -> float:
        return self.change / self.total_2026 * 100


@dataclass(frozen=True, slots=True)
class MegView:
    profile: Profile
    tax: TaxEffect
    sections: tuple[Section, ...]
    growth_wage: float
    growth_pension: float
    tax_pages: TaxPages
    n_general: int = 0  # changes to services and sectors for this profile, shown on /tilbud
    tax_source: str = ""
    growth_pages: tuple[int | None, int | None] = (None, None)

    @property
    def groups(self) -> list[Group]:
        return by_wallet(list(self.sections))

    @property
    def n_changed(self) -> int:
        return sum(len(s.changed) for s in self.sections)

    @property
    def n_unchanged(self) -> int:
        return sum(len(s.unchanged) for s in self.sections)

    @property
    def tax_kroner(self) -> int:
        """The 2027 tax in whole kroner, the amount the receipt starts from."""
        return round(self.tax.tax_2027)


@dataclass(frozen=True, slots=True)
class IncomeRow:
    name: str
    amount: float
    amount_2026: float

    @property
    def change(self) -> float:
        return self.amount - self.amount_2026


class Queries:
    def __init__(self, data: Datasets) -> None:
        self.data = data

    @property
    def budget(self) -> b.Budget:
        return self.data.budget()

    def overview(self) -> Overview:
        bud = self.budget
        total = bud.total(2027)
        top = max(bud.level(2027, 1), key=lambda f: f.amount)
        before = {f.target: f.amount for f in bud.level(2026, 1)}
        grew = max(bud.level(2027, 1), key=lambda f: f.amount - before.get(f.target, 0.0))
        return Overview(
            total=total,
            total_2026=bud.total(2026),
            fund=bud.income_amount(2027, "Overføring fra oljefondet"),
            fund_2026=bud.income_amount(2026, "Overføring fra oljefondet"),
            fund_share=next(f.share for f in bud.fund if f.year == 2027),
            top_group=top.target,
            top_amount=top.amount,
            grew_most=grew.target,
            grew_most_by=grew.amount - before.get(grew.target, 0.0),
        )

    def meg(self, profile: Profile) -> MegView:
        table = self.data.tax_table()
        facts = self.data.facts()
        return MegView(
            profile=profile,
            tax=household_effect(table, list(profile.adults)),
            sections=tuple(select([f for f in facts if not is_general(f)], profile)),
            n_general=sum(len(s.changed) for s in select([f for f in facts if is_general(f)], profile)),
            growth_wage=table.growth.wage,
            growth_pension=table.growth.pension,
            tax_source=table.source_url,
            growth_pages=(table.growth.wage_page, table.growth.pension_page),
            tax_pages=table.pages,
        )

    def facts(self) -> list[Fact]:
        return self.data.facts()

    def general(self) -> list[Section]:
        return general(self.data.facts())

    def receipt(self, tax_kroner: int) -> list[b.ReceiptGroup]:
        return b.receipt(self.budget, tax_kroner)

    def everyday(self) -> b.Everyday:
        return b.everyday(self.budget)

    def income(self) -> list[IncomeRow]:
        bud = self.budget
        return [IncomeRow(s, bud.income_amount(2027, s), bud.income_amount(2026, s)) for s in bud.income]

    def tree(self, side: b.Side, path: str) -> b.TreeLevel:
        return b.tree(self.budget, side, path)

    def flow_detail(self, name: str) -> b.FlowDetail | None:
        return b.flow_detail(self.budget, name)

    def search(self, query: str) -> list[b.Hit]:
        return b.search(self.budget, query)

    def chapter_path(self, kap: int) -> tuple[b.Side, str]:
        return b.path_to_chapter(self.budget, kap)

    def changes(self) -> b.Changes:
        return b.changes(self.budget)

    def kommune(self, text: str) -> b.KommuneView:
        found = b.find_kommune(self.budget, text) if text else None
        return b.kommune_view(self.budget, found.nr if found else "0301")
