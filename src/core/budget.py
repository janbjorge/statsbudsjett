"""The non-oil budget for 2026 and 2027 and the views the explorer shows of it.

Amounts are in billion kroner. What is left out and how things are grouped: METHOD.md §1–4, §7.
"""

from dataclasses import dataclass
from enum import StrEnum


class Side(StrEnum):
    UTGIFT = "utgift"
    INNTEKT = "inntekt"


@dataclass(frozen=True, slots=True)
class Flow:
    level: int
    source: str
    target: str
    amount: float


@dataclass(frozen=True, slots=True)
class Post:
    side: Side
    group: str
    area: str
    kap: int
    kap_name: str
    post: int
    post_name: str
    v2027: float
    v2026: float | None


@dataclass(frozen=True, slots=True)
class Chapter:
    kap: int
    name: str
    side: Side
    v2027: float | None
    v2026: float | None


@dataclass(frozen=True, slots=True)
class Kommune:
    nr: str
    name: str
    fylke: str | None
    population: int
    frie2026: float
    frie2027: float
    growth: float
    tax_index: float

    @property
    def per_person(self) -> float:
        return self.frie2027 / self.population

    @property
    def label(self) -> str:
        return f"{self.name} ({self.fylke})" if self.fylke else self.name


@dataclass(frozen=True, slots=True)
class FundYear:
    year: int
    share: float
    forecast: bool


@dataclass(frozen=True, slots=True)
class Budget:
    groups: tuple[str, ...]
    income: tuple[str, ...]
    population: int
    flows: dict[int, tuple[Flow, ...]]
    posts: tuple[Post, ...]
    chapters: tuple[Chapter, ...]
    kommuner: tuple[Kommune, ...]
    fund: tuple[FundYear, ...]

    def total(self, year: int) -> float:
        return sum(f.amount for f in self.flows[year] if f.level == 1)

    def per_person(self, amount_bn: float) -> float:
        return amount_bn * 1e9 / self.population

    def level(self, year: int, level: int) -> tuple[Flow, ...]:
        return tuple(f for f in self.flows[year] if f.level == level)

    def group_amount(self, year: int, group: str) -> float:
        return next((f.amount for f in self.level(year, 1) if f.target == group), 0.0)

    def income_amount(self, year: int, source: str) -> float:
        return next((f.amount for f in self.level(year, 0) if f.source == source), 0.0)

    def leaves(self, year: int, group: str) -> list[Flow]:
        return sorted((f for f in self.level(year, 2) if f.source == group), key=lambda f: -f.amount)


# ---------- tax receipt ----------

@dataclass(frozen=True, slots=True)
class ReceiptLine:
    name: str
    kroner: float


@dataclass(frozen=True, slots=True)
class ReceiptGroup:
    name: str
    kroner: float
    share: float
    lines: tuple[ReceiptLine, ...]


def receipt(budget: Budget, tax_kroner: float) -> list[ReceiptGroup]:
    """Split a tax payment over spending in proportion to non-oil spending (METHOD.md §6)."""
    total = budget.total(2027)
    out = []
    for g in budget.groups:
        amount = budget.group_amount(2027, g)
        if not amount:
            continue
        lines = tuple(ReceiptLine(f.target, tax_kroner * f.amount / total) for f in budget.leaves(2027, g))
        out.append(ReceiptGroup(g, tax_kroner * amount / total, amount / total * 100, lines))
    return out


# ---------- explore: drill-down tree ----------

@dataclass(frozen=True, slots=True)
class Node:
    key: str
    name: str
    group: str
    v2027: float
    v2026: float | None
    has_children: bool
    kap: int | None = None
    post: int | None = None

    @property
    def change(self) -> float | None:
        return None if self.v2026 is None else self.v2027 - self.v2026


@dataclass(frozen=True, slots=True)
class TreeLevel:
    side: Side
    crumbs: tuple[tuple[str, str], ...]  # (path up to here, name)
    node: Node
    children: tuple[Node, ...]


def _key_parts(path: str) -> list[str]:
    return [p for p in path.split("/") if p]


def tree(budget: Budget, side: Side, path: str = "") -> TreeLevel:
    """One level of the budget: group → area → chapter → post. Unknown path parts are ignored."""
    posts = [p for p in budget.posts if p.side is side]
    exact26 = _exact_2026(budget)
    parts = _key_parts(path)

    def levels(p: Post) -> list[tuple[str, str]]:
        steps = [(f"g:{p.group}", p.group)]
        if p.area != p.group:
            steps.append((f"l:{p.group}|{p.area}", p.area))
        steps.append((f"k:{p.kap}", p.kap_name))
        steps.append((f"p:{p.kap}.{p.post}", p.post_name))
        return steps

    depth = 0
    crumbs: list[tuple[str, str]] = [("", "Alle utgifter" if side is Side.UTGIFT else "Alle inntekter")]
    scope = posts
    for part in parts:
        narrowed = [p for p in scope if len(levels(p)) > depth and levels(p)[depth][0] == part]
        if not narrowed or part.startswith("p:"):
            break
        scope, depth = narrowed, depth + 1
        crumbs.append(("/".join(parts[:depth]), levels(narrowed[0])[depth - 1][1]))

    children: dict[str, list[Post]] = {}
    names: dict[str, str] = {}
    for p in scope:
        steps = levels(p)
        key, name = steps[depth]
        children.setdefault(key, []).append(p)
        names[key] = name

    def node(key: str, name: str, items: list[Post]) -> Node:
        first = items[0]
        is_post = key.startswith("p:")
        v26: float | None
        if is_post:
            v26 = first.v2026
        elif key in exact26:
            v26 = exact26[key]
        else:
            v26 = sum(p.v2026 or 0 for p in items)
        return Node(
            key=key, name=name, group=first.group,
            v2027=sum(p.v2027 for p in items), v2026=v26, has_children=not is_post,
            kap=first.kap if key[0] in "kp" else None, post=first.post if is_post else None,
        )

    kids = sorted((node(k, names[k], v) for k, v in children.items()), key=lambda n: -n.v2027)
    here_key = parts[depth - 1] if depth else "root"
    here_v26 = exact26.get(here_key) if depth else sum(c.v2026 or 0 for c in kids)
    here = Node(here_key, crumbs[-1][1], scope[0].group if scope else "", sum(p.v2027 for p in scope), here_v26, True)
    return TreeLevel(side, tuple(crumbs), here, tuple(kids))


def _exact_2026(budget: Budget) -> dict[str, float | None]:
    """2026 totals that do not depend on post matching: groups, areas and chapters."""
    out: dict[str, float | None] = {}
    for f in budget.flows[2026]:
        if f.level == 0:
            out[f"g:{f.source}"] = f.amount
        elif f.level == 1:
            out[f"g:{f.target}"] = f.amount
        else:
            out[f"l:{f.source}|{f.target}"] = f.amount
    for c in budget.chapters:
        out[f"k:{c.kap}"] = c.v2026
    return out


def path_to_chapter(budget: Budget, kap: int) -> tuple[Side, str]:
    p = next(p for p in budget.posts if p.kap == kap)
    parts = [f"g:{p.group}"] + ([f"l:{p.group}|{p.area}"] if p.area != p.group else []) + [f"k:{p.kap}"]
    return p.side, "/".join(parts)


# ---------- search ----------

@dataclass(frozen=True, slots=True)
class Hit:
    title: str
    side: Side
    group: str
    area: str
    kap: int
    post: int | None
    v2027: float


def search(budget: Budget, query: str, limit: int = 12) -> list[Hit]:
    q = query.strip().lower()
    if len(q) < 2:
        return []
    hits: dict[str, Hit] = {}
    for p in budget.posts:
        in_kap, in_post = q in p.kap_name.lower(), q in p.post_name.lower()
        if not (in_kap or in_post):
            continue
        key = f"k{p.kap}" if in_kap else f"p{p.kap}.{p.post}"
        prev = hits.get(key)
        title = p.kap_name if in_kap else f"{p.post_name} ({p.kap_name})"
        hits[key] = Hit(title, p.side, p.group, p.area, p.kap, None if in_kap else p.post, (prev.v2027 if prev else 0) + p.v2027)
    return sorted(hits.values(), key=lambda h: -h.v2027)[:limit]


# ---------- changes ----------

@dataclass(frozen=True, slots=True)
class Change:
    name: str
    group: str
    v2026: float
    v2027: float

    @property
    def change(self) -> float:
        return self.v2027 - self.v2026

    @property
    def pct(self) -> float | None:
        return self.change / self.v2026 * 100 if self.v2026 > 0 else None


@dataclass(frozen=True, slots=True)
class Changes:
    up: tuple[Change, ...]
    down: tuple[Change, ...]
    unmatched: int


def changes(budget: Budget, n: int = 10) -> Changes:
    """Chapters that change most. Chapters found in only one year are counted, not ranked (METHOD.md §4)."""
    group_of = {p.kap: p.group for p in budget.posts}
    spend = [c for c in budget.chapters if c.side is Side.UTGIFT]
    both = [Change(c.name, group_of.get(c.kap, ""), c.v2026, c.v2027) for c in spend if c.v2026 is not None and c.v2027 is not None]
    up = sorted((c for c in both if c.change > 0), key=lambda c: -c.change)[:n]
    down = sorted((c for c in both if c.change < 0), key=lambda c: c.change)[:n]
    return Changes(tuple(up), tuple(down), len(spend) - len(both))


# ---------- kommune ----------

@dataclass(frozen=True, slots=True)
class KommuneView:
    kommune: Kommune
    average_per_person: float
    rank: int
    count: int


def kommune_view(budget: Budget, nr: str) -> KommuneView:
    k = next((k for k in budget.kommuner if k.nr == nr), None) or next(k for k in budget.kommuner if k.name == "Oslo")
    ranked = sorted(budget.kommuner, key=lambda x: -x.per_person)
    average = sum(x.frie2027 for x in budget.kommuner) / sum(x.population for x in budget.kommuner)
    return KommuneView(k, average, ranked.index(k) + 1, len(ranked))


def find_kommune(budget: Budget, text: str) -> Kommune | None:
    t = text.strip().lower()
    return next((k for k in budget.kommuner if t in (k.nr, k.name.lower(), k.label.lower())), None)
