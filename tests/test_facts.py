"""Which facts a household sees (METHOD.md §6)."""

from adapters.datasets import JsonDatasets
from core.facts import ASKED, PERSONAS, WALLET_LABEL, Effect, Kind, Profile, Wallet, by_wallet, general, is_general, select, wallet
from core.tax import Adult, Business

FACTS = JsonDatasets().facts()


def titles(profile: Profile) -> set[str]:
    return {f.id for s in select(FACTS, profile) for f in s.changed + s.unchanged}


def test_everyone_sees_household_facts_without_choosing_anything() -> None:
    sections = select(FACTS, Profile(adults=(Adult(),)))
    assert [s.label for s in sections] == ["Gjelder alle"]


def test_incomes_and_children_tell_the_situation() -> None:
    told = Profile(
        kids={"1-5": 1},
        adults=(Adult(wage=400_000, pension=100_000), Adult(business=300_000, business_kind=Business.JORDBRUK)),
    ).situations
    assert told == {"barnefamilie", "arbeidstaker", "pensjonist", "naeringsdrivende", "bonde"}
    assert Profile(adults=(Adult(business=300_000, business_kind=Business.FISKE),)).situations == {"naeringsdrivende", "fisker"}
    # A kind with no amount says nothing
    assert Profile(adults=(Adult(business_kind=Business.JORDBRUK),)).situations == set()


def test_the_chosen_personas_are_kept() -> None:
    assert Profile(personas=frozenset({"bilist"}), adults=(Adult(),)).situations == {"bilist"}


def test_the_form_asks_only_what_the_incomes_cannot_tell() -> None:
    told = {"barnefamilie", "arbeidstaker", "pensjonist", "bonde", "fisker"}
    assert set(ASKED) | told == set(PERSONAS)
    assert not set(ASKED) & told


def test_each_fact_is_shown_once() -> None:
    profile = Profile(personas=frozenset({"barnefamilie", "student", "pensjonist", "syk_ufor", "bilist"}))
    ids = [f.id for s in select(FACTS, profile) for f in s.changed + s.unchanged]
    assert len(ids) == len(set(ids))


def test_child_age_facts_follow_the_children_entered() -> None:
    family = frozenset({"barnefamilie"})
    toddlers = titles(Profile(personas=family, kids={"1-5": 2}))
    baby = titles(Profile(personas=family, kids={"0-1": 1}))
    assert "barnehage-makspris" in toddlers and "barnehage-makspris" not in baby
    assert "engangsstonad-kuttes" in baby and "engangsstonad-kuttes" not in toddlers
    # Before any child is entered, every age band is shown
    everything = titles(Profile(personas=family))
    assert {"barnehage-makspris", "engangsstonad-kuttes"} <= everything


def test_unchanged_facts_are_kept_apart() -> None:
    for s in select(FACTS, Profile(personas=frozenset({"barnefamilie"}))):
        assert all(f.effect is not Effect.UENDRET for f in s.changed)
        assert all(f.effect is Effect.UENDRET for f in s.unchanged)


def test_children_over_18_bring_the_student_facts() -> None:
    profile = Profile(personas=frozenset({"barnefamilie"}), kids={"18+": 1})
    sections = {s.label: {f.id for f in s.changed + s.unchanged} for s in select(FACTS, profile)}
    assert "studielan-basislan-g" in sections["Barn over 18 år som studerer"]
    # Only an adult child: no barnehage or school facts
    assert "barnehage-makspris" not in titles(profile)
    # Choosing Student yourself keeps the usual label
    labels = [s.label for s in select(FACTS, Profile(personas=frozenset({"student"}), kids={"18+": 1}))]
    assert "Student" in labels and "Barn over 18 år som studerer" not in labels


def test_barnetrygd_needs_a_child_under_18() -> None:
    family = frozenset({"barnefamilie"})
    assert "barnetrygd-uendret" not in titles(Profile(personas=family, kids={"18+": 2}))
    assert "barnetrygd-uendret" in titles(Profile(personas=family, kids={"18+": 1, "16-18": 1}))
    assert "barnetrygd-uendret" in titles(Profile(personas=family))


def test_amounts_that_stay_the_same_in_kroner_count_as_better_or_worse() -> None:
    effect = {f.id: f.effect for f in FACTS}
    assert effect["barnetrygd-uendret"] is Effect.MINUS
    assert effect["kontantstotte-uendret"] is Effect.MINUS
    assert effect["barnehage-makspris"] is Effect.PLUSS


def test_elbil_vat_only_for_those_buying_a_car() -> None:
    assert "elbil-moms-grense-150000" not in titles(Profile(personas=frozenset({"bilist"})))
    assert "elbil-moms-grense-150000" in titles(Profile(personas=frozenset({"bilkjoper"})))


def test_households_of_more_than_one_are_dere() -> None:
    assert (Profile().you, Profile().subject) == ("deg", "du")
    assert (Profile(kids={"1-5": 1}).you, Profile(kids={"1-5": 1}).subject) == ("dere", "dere")


def test_only_household_money_is_better_or_worse() -> None:
    by_id = {f.id: f for f in FACTS}
    assert by_id["horeapparatgaranti"].label("du") == "● Mer til tilbudet"
    assert by_id["horeapparatgaranti"].tone == "pluss"
    assert by_id["elavgift-7-32"].label("dere") == "▲ Dere betaler mer"
    assert by_id["elavgift-7-32"].label("du") == "▲ Du betaler mer"
    assert by_id["barnetrygd-uendret"].label("du") == "▼ Reelt mindre verdt"


def test_wallet_groups_hold_every_fact_once_in_page_order() -> None:
    profile = Profile(personas=frozenset({"bilist", "distrikt_nord"}), kids={"1-5": 2})
    sections = select(FACTS, profile)
    groups = by_wallet(sections)
    assert sorted(t.fact.id for g in groups for t in g.items) == sorted(titles(profile))
    order = list(WALLET_LABEL)
    assert [g.wallet for g in groups] == sorted((g.wallet for g in groups), key=order.index)
    # Within a group the facts keep the situation order, so "Gjelder alle" comes last
    for g in groups:
        seen = [t.situation for t in g.items]
        assert seen == sorted(seen, key=[s.label for s in sections].index)


def test_only_money_counts_as_more_or_less() -> None:
    for f in FACTS:
        w = wallet(f)
        if w in (Wallet.UT, Wallet.INN, Wallet.BEGGE):
            assert f.kind in (Kind.BETALER, Kind.FAR) and f.effect is not Effect.UENDRET
        if w is Wallet.FAST:
            assert f.effect is Effect.UENDRET
    assert Wallet.UT in {wallet(f) for f in FACTS if f.id == "barnetrygd-uendret"}


def test_general_changes_leave_for_deg_for_their_own_page() -> None:
    """More to barnevernet or less to fiskeflåten changes no household's money or rules, so it sits on /tilbud (METHOD.md §6)."""
    shown = general(FACTS)
    ids = [f.id for s in shown for f in s.changed + s.unchanged]
    assert sorted(ids) == sorted(f.id for f in FACTS if is_general(f)) and len(ids) == len(set(ids))
    assert shown[0].label == "Gjelder alle"
    by_id = {f.id: f for f in FACTS}
    assert is_general(by_id["barnevern-flere-plasser"])
    # A sector's money is named in the badge, coloured by which way it goes for them
    assert by_id["co2-kompensasjon-fiskeflaten"].label("du") == "▼ Fiskeflåten får mindre"
    assert by_id["co2-kompensasjon-fiskeflaten"].tone == "minus"
    assert not is_general(by_id["elavgift-7-32"])
    regel = next(f for f in FACTS if f.kind is Kind.REGEL and f.effect is not Effect.UENDRET and not is_general(f))
    assert wallet(regel) is Wallet.REGEL
