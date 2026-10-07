"""Query-string validation shared by the pages and the JSON API, with pydantic v2.

Validation never fails: unknown personas are dropped, numbers keep their digits only and are capped,
so an old or hand-edited link still shows a page.
"""

from typing import Annotated
from urllib.parse import urlencode

from pydantic import BaseModel, BeforeValidator, ConfigDict, Field, TypeAdapter

from core.facts import KID_BANDS, PERSONAS, Profile
from core.tax import Adult

MAX_INCOME = 100_000_000
MAX_KIDS = 10


def _parts(value: object) -> list[str]:
    """A comma-separated string, or repeated query values, as a list of parts."""
    items = value if isinstance(value, (list, tuple)) else [value]
    return [part for item in items for part in str(item).split(",")] if value not in ("", None) else []


def _kroner(value: object) -> int:
    digits = "".join(c for c in str(value) if c.isdigit())
    return min(int(digits), MAX_INCOME) if digits else 0


type Kroner = Annotated[int, BeforeValidator(_kroner)]
KRONER = TypeAdapter(Kroner)


def _personas(value: object) -> tuple[str, ...]:
    chosen = set(_parts(value))
    return tuple(p for p in PERSONAS if p in chosen)


def _kids(value: object) -> tuple[int, ...]:
    # Links from before a band was added carry fewer values; the missing bands count as 0
    counts = [min(_kroner(p), MAX_KIDS) for p in _parts(value)[: len(KID_BANDS)]]
    return tuple(counts + [0] * (len(KID_BANDS) - len(counts)))


def _two_amounts(value: object) -> tuple[int, ...]:
    return tuple(_kroner(p) for p in _parts(value)[:2])


class ProfileQuery(BaseModel):
    """The four query parameters behind "For deg": ?meg=…&barn=…&lonn=…&pensjon=…"""

    model_config = ConfigDict(frozen=True)

    meg: Annotated[tuple[str, ...], BeforeValidator(_personas)] = Field(default=(), description=f"Any of {', '.join(PERSONAS)}")
    barn: Annotated[tuple[int, ...], BeforeValidator(_kids)] = Field(default=(0,) * len(KID_BANDS), description=f"Children per age band: {', '.join(KID_BANDS)}")
    lonn: Annotated[tuple[int, ...], BeforeValidator(_two_amounts)] = Field(default=(), description="Yearly wage in kroner, up to two adults")
    pensjon: Annotated[tuple[int, ...], BeforeValidator(_two_amounts)] = Field(default=(), description="Yearly pension in kroner, up to two adults")

    def profile(self) -> Profile:
        if not self.lonn and not self.pensjon:
            adults: tuple[Adult, ...] = (Adult(wage=500_000),)
        else:
            pairs = [(self._at(self.lonn, i), self._at(self.pensjon, i)) for i in range(2)]
            # The second adult counts only when they have an income
            adults = tuple(Adult(w, p) for i, (w, p) in enumerate(pairs) if i == 0 or w or p)
        return Profile(personas=frozenset(self.meg), kids=dict(zip(KID_BANDS, self.barn, strict=True)), adults=adults)

    @staticmethod
    def _at(values: tuple[int, ...], i: int) -> int:
        return values[i] if i < len(values) else 0


def kroner(text: str) -> int:
    return KRONER.validate_python(text)


def profile_from(meg: str, barn: str, lonn: str, pensjon: str) -> Profile:
    return ProfileQuery.model_validate({"meg": meg, "barn": barn, "lonn": lonn, "pensjon": pensjon}).profile()


def profile_query(p: Profile) -> str:
    return urlencode({
        "meg": ",".join(k for k in PERSONAS if k in p.personas),
        "barn": ",".join(str(p.kids.get(b, 0)) for b in KID_BANDS),
        "lonn": ",".join(str(round(a.wage)) for a in p.adults),
        "pensjon": ",".join(str(round(a.pension)) for a in p.adults),
    })
