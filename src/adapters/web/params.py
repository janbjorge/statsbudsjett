"""Query-string parsing shared by the pages and the JSON API. Parsing never fails: bad input is dropped."""

from urllib.parse import urlencode

from core.facts import KID_BANDS, PERSONAS, Profile
from core.tax import Adult

MAX_INCOME = 100_000_000


def numbers(text: str, limit: int) -> list[int]:
    out = []
    for part in text.split(",")[:limit]:
        digits = "".join(c for c in part if c.isdigit())
        out.append(min(int(digits), MAX_INCOME) if digits else 0)
    return out


def profile_from(meg: str, barn: str, lonn: str, pensjon: str) -> Profile:
    """Parse the shareable query string. Anything unknown or malformed is dropped, never an error."""
    personas = frozenset(p for p in meg.split(",") if p in PERSONAS)
    # Links from before a band was added carry fewer values; the missing bands count as 0
    counts = numbers(barn, len(KID_BANDS)) + [0] * len(KID_BANDS)
    kids = dict(zip(KID_BANDS, (min(n, 10) for n in counts), strict=False))
    wages, pensions = numbers(lonn, 2), numbers(pensjon, 2)
    pairs = [(wages[i] if i < len(wages) else 0, pensions[i] if i < len(pensions) else 0) for i in range(2)]
    # The second adult counts only when they have an income
    adults = tuple(Adult(w, p) for i, (w, p) in enumerate(pairs) if i == 0 or w or p)
    if not lonn and not pensjon:
        adults = (Adult(wage=500_000),)
    return Profile(personas=personas, kids=kids, adults=adults)


def profile_query(p: Profile) -> str:
    return urlencode({
        "meg": ",".join(k for k in PERSONAS if k in p.personas),
        "barn": ",".join(str(p.kids.get(b, 0)) for b in KID_BANDS),
        "lonn": ",".join(str(round(a.wage)) for a in p.adults),
        "pensjon": ",".join(str(round(a.pension)) for a in p.adults),
    })
