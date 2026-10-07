"""Which budget facts matter to a household, given who they are. METHOD.md §6 has the rules."""

from dataclasses import dataclass, field
from enum import StrEnum

from core.tax import Adult, Business


class Effect(StrEnum):
    PLUSS = "pluss"
    MINUS = "minus"
    BLANDET = "blandet"
    UENDRET = "uendret"


class Kind(StrEnum):
    """What a change touches. Only money in or out of the household is called better or worse (METHOD.md §6)."""

    BETALER = "betaler"
    FAR = "far"
    TILBUD = "tilbud"
    REGEL = "regel"


# {} is "Du" or "Dere"
LABEL = {
    (Kind.BETALER, Effect.PLUSS): "▼ {} betaler mindre",
    (Kind.BETALER, Effect.MINUS): "▲ {} betaler mer",
    (Kind.BETALER, Effect.BLANDET): "◆ Noen betaler mer, andre mindre",
    (Kind.FAR, Effect.PLUSS): "▲ {} får mer",
    (Kind.FAR, Effect.MINUS): "▼ {} får mindre",
    (Kind.FAR, Effect.BLANDET): "◆ Noen får mer, andre mindre",
    (Kind.TILBUD, Effect.PLUSS): "● Mer til tilbudet",
    (Kind.TILBUD, Effect.MINUS): "● Mindre tilbud",
    (Kind.TILBUD, Effect.BLANDET): "◆ Endret tilbud",
    (Kind.REGEL, Effect.PLUSS): "◆ Romsligere regler",
    (Kind.REGEL, Effect.MINUS): "◆ Strengere regler",
    (Kind.REGEL, Effect.BLANDET): "◆ Endrede regler",
}
# Same kroner while prices rise: the amount itself does not change, its value does
REAL_LABEL = {Kind.BETALER: "▲ Billigere etter prisvekst", Kind.FAR: "▼ Verdt mindre etter prisvekst"}

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
    "bilkjoper": "Skal kjøpe eller lease ny bil",
    "distrikt_nord": "Bor i Nord-Norge",
    "sparer": "Sparer eller har formue",
}
EVERYONE = "husholdning"
# The form asks only for these; Profile.situations reads the rest from the incomes and children.
# "naeringsdrivende" is still asked, since an aksjeselskap owner has wage, not næringsinntekt
ASKED = ("student", "syk_ufor", "arbeidsledig", "naeringsdrivende", "bilist", "bilkjoper", "distrikt_nord", "sparer")
KID_BANDS = {"0-1": "Under 1 år", "1-5": "1–5 år (barnehage)", "6-15": "6–15 år (skole)", "16-18": "16–18 år", "18+": "Over 18 år"}
ADULT_KIDS = "18+"


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
    under_18: bool = False
    kind: Kind | None = None
    same_kroner: bool = False

    def label(self, you: str) -> str:
        if self.effect is Effect.UENDRET or self.kind is None:
            return "■ Står fast"
        if self.same_kroner:
            return REAL_LABEL[self.kind]
        return LABEL[self.kind, self.effect].format(you.capitalize())

    @property
    def tone(self) -> str:
        """Badge colour: good or bad only for money in or out of the household."""
        return self.effect if self.kind in (Kind.BETALER, Kind.FAR) else "blandet"


@dataclass(frozen=True, slots=True)
class Profile:
    personas: frozenset[str] = frozenset()
    kids: dict[str, int] = field(default_factory=dict)
    adults: tuple[Adult, ...] = (Adult(wage=500_000),)

    @property
    def has_kids(self) -> bool:
        return any(n > 0 for n in self.kids.values())

    @property
    def you(self) -> str:
        """How the page addresses the household: "dere" once more than one person lives there."""
        return "dere" if len(self.adults) > 1 or self.has_kids else "deg"

    @property
    def has_minors(self) -> bool:
        return any(n > 0 for b, n in self.kids.items() if b != ADULT_KIDS)

    @property
    def situations(self) -> frozenset[str]:
        """The chosen personas plus those the incomes and children already tell, so the form need not ask twice."""
        told = {
            "barnefamilie": self.has_kids,
            "arbeidstaker": any(a.wage for a in self.adults),
            "pensjonist": any(a.pension for a in self.adults),
            "naeringsdrivende": any(a.business for a in self.adults),
            "bonde": any(a.business and a.business_kind is Business.JORDBRUK for a in self.adults),
            "fisker": any(a.business and a.business_kind is Business.FISKE for a in self.adults),
        }
        return self.personas | {p for p, yes in told.items() if yes}


@dataclass(frozen=True, slots=True)
class Section:
    label: str
    changed: tuple[Fact, ...]
    unchanged: tuple[Fact, ...]


ORDER = {Effect.MINUS: 0, Effect.PLUSS: 1, Effect.BLANDET: 2, Effect.UENDRET: 3}


def select(facts: list[Fact], profile: Profile) -> list[Section]:
    """Facts for the chosen situations plus those for everyone, each shown once under its first match."""
    # Children over 18 often study with help from their parents, so they bring the student facts along
    situations = profile.situations
    adult_kids = bool(profile.kids.get(ADULT_KIDS)) and "student" not in situations
    personas = situations | {"student"} if adult_kids else situations
    chosen = [p for p in PERSONAS if p in personas] + [EVERYONE]

    def fits(f: Fact) -> bool:
        # Child-age facts only for ages present, once any child is entered
        if f.under_18 and profile.has_kids and not profile.has_minors:
            return False
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
                label="Gjelder alle" if p == EVERYONE else "Barn over 18 år som studerer" if adult_kids and p == "student" else PERSONAS[p],
                changed=tuple(f for f in mine if f.effect is not Effect.UENDRET),
                unchanged=tuple(f for f in mine if f.effect is Effect.UENDRET),
            ))
    return sections
