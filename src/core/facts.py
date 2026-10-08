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
    UTGIFT = "utgift"  # a spending total (folketrygden, forsvaret): more money, not a better service


# {} is the subject: "Du", "Dere", or who a general change hits
LABEL = {
    (Kind.BETALER, Effect.PLUSS): "▼ {} betaler mindre",
    (Kind.BETALER, Effect.MINUS): "▲ {} betaler mer",
    (Kind.BETALER, Effect.BLANDET): "◆ Noen betaler mer, andre mindre",
    (Kind.FAR, Effect.PLUSS): "▲ {} får mer",
    (Kind.FAR, Effect.MINUS): "▼ {} får mindre",
    (Kind.FAR, Effect.BLANDET): "◆ Noen får mer, andre mindre",
    (Kind.TILBUD, Effect.PLUSS): "▲ Styrkes",
    (Kind.TILBUD, Effect.MINUS): "▼ Svekkes",
    (Kind.TILBUD, Effect.BLANDET): "◆ Endres",
    (Kind.REGEL, Effect.PLUSS): "◆ Romsligere regler",
    (Kind.REGEL, Effect.MINUS): "◆ Strengere regler",
    (Kind.REGEL, Effect.BLANDET): "◆ Endrede regler",
    (Kind.UTGIFT, Effect.PLUSS): "▲ Mer penger",
    (Kind.UTGIFT, Effect.MINUS): "▼ Mindre penger",
    (Kind.UTGIFT, Effect.BLANDET): "◆ Mer og mindre",
}
# Same kroner while prices rise: the amount itself does not change, its value does
REAL_LABEL = {Kind.BETALER: "▼ Reelt billigere", Kind.FAR: "▼ Reelt mindre verdt"}

# Persona keys match data/persona/*.json; "husholdning" applies to everyone and is not selectable
PERSONAS = {
    "barnefamilie": "Har barn",
    "student": "Student",
    "arbeidstaker": "I jobb",
    "pensjonist": "Pensjonist",
    "syk_ufor": "Syk eller ufør",
    "arbeidsledig": "Arbeidsledig",
    "bonde": "Bonde",
    "fisker": "Fisker eller oppdretter",
    "naeringsdrivende": "Driver egen bedrift",
    "bilist": "Har bil",
    "bilkjoper": "Skal kjøpe eller lease ny bil",
    "distrikt_nord": "Bor i Nord-Norge",
    "sparer": "Sparer eller har formue",
}
EVERYONE = "husholdning"
# Parts of the budget no household profile covers, in the order /tilbud shows them after the profiles.
# Keys match `area` in data/persona/*.json; a fact with an area has no personas and never shows on "For deg"
AREAS = {
    "kommune": "Kommunene",
    "helse": "Helse og omsorg",
    "forsvar": "Forsvar og beredskap",
    "justis": "Politi og rettsvesen",
    "samferdsel": "Samferdsel",
    "klima": "Klima, energi og miljø",
    "naering": "Næringsliv",
    "trygd": "Folketrygd og Nav",
    "forskning": "Utdanning og forskning",
    "kultur": "Kultur, medier og idrett",
    "utenriks": "Bistand og utenriks",
}
# The form asks only for these; Profile.situations reads the rest from the incomes and children.
# "naeringsdrivende" is still asked, since an aksjeselskap owner has wage, not næringsinntekt
ASKED = ("student", "syk_ufor", "arbeidsledig", "naeringsdrivende", "bilist", "bilkjoper", "distrikt_nord", "sparer")
KID_BANDS = {"0-1": "Under 1 år", "1-5": "1–5 år (barnehage)", "6-15": "6–15 år (skole)", "16-18": "16–17 år", "18+": "18 år og eldre"}
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
    who: str | None = None  # a sector, organisation or companies, when the change is not a household's
    area: str | None = None  # a part of the budget (AREAS) for facts that concern no household profile

    def label(self, subject: str) -> str:
        """Badge text; `subject` is "du" or "dere" (Profile.subject), never "deg"."""
        if self.effect is Effect.UENDRET or self.kind is None:
            return "■ Står fast"
        if self.same_kroner:
            return REAL_LABEL[self.kind]
        return LABEL[self.kind, self.effect].format(self.who or subject.capitalize())

    @property
    def tone(self) -> str:
        """Badge colour (jb 2026-10-08): green for more, red for less, yellow for mixed. Rules stay yellow,
        since a stricter rule is not less of anything."""
        return "blandet" if self.kind is Kind.REGEL else self.effect


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
    def subject(self) -> str:
        """The same as the subject of a sentence: "Du betaler mer", not "Deg betaler mer"."""
        return "dere" if self.you == "dere" else "du"

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
            "bonde": any(a.business and a.business_kind == Business.JORDBRUK for a in self.adults),
            "fisker": any(a.business and a.business_kind == Business.FISKE for a in self.adults),
        }
        return self.personas | {p for p, yes in told.items() if yes}


@dataclass(frozen=True, slots=True)
class Section:
    label: str
    changed: tuple[Fact, ...]
    unchanged: tuple[Fact, ...]


ORDER = {Effect.MINUS: 0, Effect.PLUSS: 1, Effect.BLANDET: 2, Effect.UENDRET: 3}


class Wallet(StrEnum):
    """What a change does to the household's money; the page groups the facts by it (METHOD.md §6)."""

    UT = "ut"
    INN = "inn"
    BEGGE = "begge"
    REGEL = "regel"
    FAST = "fast"


# {} is "Du" or "Dere"; in the order the page shows them
WALLET_LABEL = {
    Wallet.UT: "{} betaler mer eller får mindre",
    Wallet.INN: "{} betaler mindre eller får mer",
    Wallet.BEGGE: "Både mer og mindre",
    Wallet.REGEL: "Nye regler",
    Wallet.FAST: "Står fast",
}
MONEY = {Effect.MINUS: Wallet.UT, Effect.PLUSS: Wallet.INN, Effect.BLANDET: Wallet.BEGGE}


@dataclass(frozen=True, slots=True)
class Tagged:
    """A fact with the situation it was picked for, shown as a tag on the card."""

    fact: Fact
    situation: str


@dataclass(frozen=True, slots=True)
class Group:
    wallet: Wallet
    items: tuple[Tagged, ...]

    def label(self, subject: str) -> str:
        return WALLET_LABEL[self.wallet].format(subject.capitalize())


def is_general(f: Fact) -> bool:
    """A change to a public service (more money to barnevernet) or to a sector or companies (fiskeflåten, konsern).
    It does not change what a household pays, gets or must follow, so it has its own page, not "For deg" (METHOD.md §6)."""
    return (f.kind is Kind.TILBUD and f.effect is not Effect.UENDRET) or f.who is not None or f.area is not None


def wallet(f: Fact) -> Wallet:
    """Where a "For deg" fact goes; general facts are not shown there (is_general)."""
    if f.effect is Effect.UENDRET:
        return Wallet.FAST
    if f.kind in (Kind.BETALER, Kind.FAR):
        return MONEY[f.effect]
    return Wallet.REGEL


def by_wallet(sections: list[Section]) -> list[Group]:
    """The same facts grouped by what they do to the household's money, keeping the order within each group."""
    tagged = [Tagged(f, s.label) for s in sections for f in s.changed + s.unchanged]
    groups = [Group(w, tuple(t for t in tagged if wallet(t.fact) is w)) for w in WALLET_LABEL]
    return [g for g in groups if g.items]


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
            if f.id not in seen and f.personas and fits(f)
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


def general(facts: list[Fact]) -> list[Section]:
    """Every general fact: by who it is for, with those for everyone first, then by part of the budget."""
    every = Profile(personas=frozenset(PERSONAS))
    people = select([f for f in facts if is_general(f) and f.area is None], every)
    areas = []
    for key, label in AREAS.items():
        mine = sorted((f for f in facts if f.area == key), key=lambda f: ORDER[f.effect])
        if mine:
            areas.append(Section(
                label=label,
                changed=tuple(f for f in mine if f.effect is not Effect.UENDRET),
                unchanged=tuple(f for f in mine if f.effect is Effect.UENDRET),
            ))
    return sorted(people, key=lambda s: s.label != "Gjelder alle") + areas
