"""Read-only queries behind every page and HTMX fragment. Results are frozen dataclasses."""

from dataclasses import dataclass

from core import budget as b
from core.facts import Profile, Section, select
from core.ports import Datasets
from core.tax import TaxEffect, household_effect


@dataclass(frozen=True, slots=True)
class Overview:
    total: float
    total_2026: float
    fund: float
    fund_share: float
    top_group: str
    top_amount: float

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

    @property
    def n_changed(self) -> int:
        return sum(len(s.changed) for s in self.sections)

    @property
    def n_unchanged(self) -> int:
        return sum(len(s.unchanged) for s in self.sections)


@dataclass(frozen=True, slots=True)
class IncomeRow:
    name: str
    amount: float


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
        return Overview(
            total=total,
            total_2026=bud.total(2026),
            fund=bud.income_amount(2027, "Overføring fra oljefondet"),
            fund_share=next(f.share for f in bud.fund if f.year == 2027),
            top_group=top.target,
            top_amount=top.amount,
        )

    def meg(self, profile: Profile) -> MegView:
        table = self.data.tax_table()
        return MegView(
            profile=profile,
            tax=household_effect(table, list(profile.adults)),
            sections=tuple(select(self.data.facts(), profile)),
            growth_wage=table.growth.wage,
            growth_pension=table.growth.pension,
        )

    def receipt(self, tax_kroner: float) -> list[b.ReceiptGroup]:
        return b.receipt(self.budget, tax_kroner)

    def everyday(self) -> b.Everyday:
        return b.everyday(self.budget)

    def income(self) -> list[IncomeRow]:
        bud = self.budget
        return [IncomeRow(s, bud.income_amount(2027, s)) for s in bud.income]

    def tree(self, side: b.Side, path: str) -> b.TreeLevel:
        return b.tree(self.budget, side, path)

    def search(self, query: str) -> list[b.Hit]:
        return b.search(self.budget, query)

    def chapter_path(self, kap: int) -> tuple[b.Side, str]:
        return b.path_to_chapter(self.budget, kap)

    def changes(self) -> b.Changes:
        return b.changes(self.budget)

    def kommune(self, text: str) -> b.KommuneView:
        found = b.find_kommune(self.budget, text) if text else None
        return b.kommune_view(self.budget, found.nr if found else "0301")
