"""Output ports: what the core needs from the outside world."""

from typing import Protocol

from core.budget import Budget
from core.facts import Fact
from core.tax import TaxTable


class Datasets(Protocol):
    def budget(self) -> Budget: ...

    def facts(self) -> list[Fact]: ...

    def tax_table(self) -> TaxTable: ...
