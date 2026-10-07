"""Which facts a household sees (METHOD.md §6)."""

from adapters.datasets import JsonDatasets
from core.facts import Effect, Profile, select

FACTS = JsonDatasets().facts()


def titles(profile: Profile) -> set[str]:
    return {f.id for s in select(FACTS, profile) for f in s.changed + s.unchanged}


def test_everyone_sees_household_facts_without_choosing_anything() -> None:
    sections = select(FACTS, Profile())
    assert [s.label for s in sections] == ["Gjelder alle"]


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
