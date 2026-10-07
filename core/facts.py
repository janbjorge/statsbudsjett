"""Which budget facts matter to a household, given who they are. METHOD.md §6 has the rules."""

from dataclasses import dataclass, field
from enum import StrEnum

from core.tax import Adult


class Effect(StrEnum):
    PLUSS = "pluss"
    MINUS = "minus"
    BLANDET = "blandet"
    UENDRET = "uendret"


EFFECT_LABEL = {
    Effect.PLUSS: "▲ Bedre for deg",
    Effect.MINUS: "▼ Dårligere for deg",
    Effect.BLANDET: "◆ Både og",
    Effect.UENDRET: "■ Uendret",
}

# Persona keys match data/persona/*.json; "husholdning" applies to everyone and is not selectable
PERSONAS = {
    "barnefamilie": "Har barn",
    "student": "Student",
    "arbeidstaker": "I jobb",
    "pensjonist": "Pensjonist",
    "syk_ufor": "Syk eller ufør",
    "arbeidsledig": "Arbeidsledig",
    "bonde": "Bonde",
    "fisker": "Fisker eller havbruk",
    "naeringsdrivende": "Driver egen bedrift",
    "bilist": "Har bil",
    "distrikt_nord": "Bor i Nord-Norge",
    "sparer": "Sparer eller har formue",
}
EVERYONE = "husholdning"
KID_BANDS = {"0-1": "Under 1 år", "1-5": "1–5 år (barnehage)", "6-15": "6–15 år (skole)", "16-18": "16–18 år"}


@dataclass(frozen=True, slots=True)
class Amount:
    label: str
    y2026: float | None
    y2027: float | None
    unit: str


@dataclass(frozen=True, slots=True)
class Fact:
    id: str
    personas: tuple[str, ...]
    detail: str | None
    title: str
    summary: str
    effect: Effect
    amounts: tuple[Amount, ...]
    source_title: str
    source_url: str
    page: int | None
    caveat: str | None

    @property
    def effect_label(self) -> str:
        return EFFECT_LABEL[self.effect]


@dataclass(frozen=True, slots=True)
class Profile:
    personas: frozenset[str] = frozenset()
    kids: dict[str, int] = field(default_factory=dict)
    adults: tuple[Adult, ...] = (Adult(wage=500_000),)

    @property
    def has_kids(self) -> bool:
        return any(n > 0 for n in self.kids.values())


@dataclass(frozen=True, slots=True)
class Section:
    label: str
    changed: tuple[Fact, ...]
    unchanged: tuple[Fact, ...]


ORDER = {Effect.MINUS: 0, Effect.PLUSS: 1, Effect.BLANDET: 2, Effect.UENDRET: 3}


def select(facts: list[Fact], profile: Profile) -> list[Section]:
    """Facts for the chosen situations plus those for everyone, each shown once under its first match."""
    chosen = [p for p in PERSONAS if p in profile.personas] + [EVERYONE]

    def fits(f: Fact) -> bool:
        # Child-age facts only for ages present, once any child is entered
        return not (f.detail in KID_BANDS and profile.has_kids and not profile.kids.get(f.detail))

    seen: set[str] = set()
    sections = []
    for p in chosen:
        mine = [
            f for f in facts
            if f.id not in seen and fits(f)
            and (f.personas[0] == p or (p in f.personas and f.personas[0] not in chosen))
        ]
        mine.sort(key=lambda f: ORDER[f.effect])
        seen |= {f.id for f in mine}
        if mine:
            sections.append(Section(
                label="Gjelder alle" if p == EVERYONE else PERSONAS[p],
                changed=tuple(f for f in mine if f.effect is not Effect.UENDRET),
                unchanged=tuple(f for f in mine if f.effect is Effect.UENDRET),
            ))
    return sections
