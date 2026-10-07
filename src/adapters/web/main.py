"""FastAPI + Jinja + HTMX. Every fragment is also reachable as a full page via the same query string."""

import json
from collections.abc import Awaitable, Callable
from pathlib import Path
from typing import Annotated
from urllib.parse import urlencode

from fastapi import FastAPI, Query, Request
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import HTMLResponse, PlainTextResponse, RedirectResponse, Response
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from adapters.datasets import DATASETS, JsonDatasets
from adapters.web import fmt
from app.queries import Queries
from core.budget import FundYear, Kommune, Node, Side
from core.facts import EFFECT_LABEL, KID_BANDS, PERSONAS, Profile
from core.tax import Adult

HERE = Path(__file__).parent
MAX_INCOME = 100_000_000

data = JsonDatasets()
queries = Queries(data)
app = FastAPI(title="Statsbudsjettet 2027", docs_url=None, redoc_url=None, openapi_url=None)
app.add_middleware(GZipMiddleware, minimum_size=1000)


@app.middleware("http")
async def headers(request: Request, call_next: Callable[[Request], Awaitable[Response]]) -> Response:
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    response.headers["Content-Security-Policy"] = (
        "default-src 'self'; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline'; img-src 'self' data:"
    )
    path = request.url.path
    if path.startswith(("/static/", "/data/")):
        response.headers["Cache-Control"] = "public, max-age=3600"
    elif "hx-request" not in request.headers:
        response.headers["Cache-Control"] = "public, max-age=300"
    return response


app.mount("/static", StaticFiles(directory=HERE / "static"), name="static")
app.mount("/data", StaticFiles(directory=DATASETS), name="data")


def template_context(request: Request) -> dict[str, object]:
    """Names every template can use."""
    return {
        "PERSONAS": PERSONAS, "KID_BANDS": KID_BANDS, "EFFECT_LABEL": EFFECT_LABEL, "Side": Side,
        "group_slot": group_slot, "per_person": queries.budget.per_person,
    }


templates = Jinja2Templates(directory=HERE / "templates", context_processors=[template_context])
templates.env.filters |= {name: getattr(fmt, name) for name in fmt.__all__}


def group_slot(group: str) -> int:
    """Colour slot: 0 for income, 1..8 for the spending groups in display order (CSS --g-N)."""
    groups = queries.budget.groups
    return groups.index(group) + 1 if group in groups else 0


def tojson_nodes(nodes: tuple[Node, ...], side: Side, base: str) -> str:
    """Treemap island data. Layout needs non-negative sizes; labels use the exact sum (METHOD.md §4)."""
    return json.dumps([
        {
            "name": n.name, "size": max(0.0, n.v2027), "v": n.v2027, "slot": group_slot(n.group),
            "href": f"/utforsk?{urlencode({'side': side, 'sti': f'{base}/{n.key}'.strip('/')})}" if n.has_children else None,
            "pp": queries.budget.per_person(n.v2027),
        }
        for n in nodes
    ], ensure_ascii=False)


def tojson_kommuner(kommuner: tuple[Kommune, ...]) -> str:
    return json.dumps([{"nr": k.nr, "n": k.name, "f": k.fylke, "pop": k.population, "pp": round(k.per_person)} for k in kommuner], ensure_ascii=False)


def tojson_fund(fund: tuple[FundYear, ...]) -> str:
    return json.dumps([{"year": f.year, "value": f.share, "forecast": f.forecast} for f in fund])


templates.env.filters |= {"tojson_nodes": tojson_nodes, "tojson_kommuner": tojson_kommuner, "tojson_fund": tojson_fund}


def _numbers(text: str, limit: int) -> list[int]:
    out = []
    for part in text.split(",")[:limit]:
        digits = "".join(c for c in part if c.isdigit())
        out.append(min(int(digits), MAX_INCOME) if digits else 0)
    return out


def profile_from(meg: str, barn: str, lonn: str, pensjon: str) -> Profile:
    """Parse the shareable query string. Anything unknown or malformed is dropped, never an error."""
    personas = frozenset(p for p in meg.split(",") if p in PERSONAS)
    # Links from before a band was added carry fewer values; the missing bands count as 0
    counts = _numbers(barn, len(KID_BANDS)) + [0] * len(KID_BANDS)
    kids = dict(zip(KID_BANDS, (min(n, 10) for n in counts), strict=False))
    wages, pensions = _numbers(lonn, 2), _numbers(pensjon, 2)
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


def _not_htmx(request: Request) -> bool:
    return "hx-request" not in request.headers


type Q = Annotated[str, Query()]


def _side(side: str) -> Side:
    return Side.INNTEKT if side == Side.INNTEKT else Side.UTGIFT


@app.get("/", response_class=HTMLResponse)
def index(
    request: Request,
    meg: Q = "",
    barn: Q = "",
    lonn: Q = "",
    pensjon: Q = "",
    skatt: Q = "150000",
    side: Q = "utgift",
    sti: Q = "",
    k: Q = "",
) -> HTMLResponse:
    tax_kroner = (_numbers(skatt, 1) or [150_000])[0]
    return templates.TemplateResponse(request, "index.html", {
        "o": queries.overview(),
        "m": queries.meg(profile_from(meg, barn, lonn, pensjon)),
        "tax_kroner": tax_kroner,
        "receipt": queries.receipt(tax_kroner),
        "income": queries.income(),
        "t": queries.tree(_side(side), sti),
        "changes": queries.changes(),
        "kv": queries.kommune(k),
        "kommuner": queries.budget.kommuner,
        "fund": queries.budget.fund,
    })


@app.get("/meg", response_class=HTMLResponse)
def meg_fragment(request: Request, meg: Q = "", barn: Q = "", lonn: Q = "", pensjon: Q = "", del_: Annotated[str, Query(alias="del")] = "") -> Response:
    """The "For deg" section. del=resultat returns only the result, so typing in the form keeps focus."""
    profile = profile_from(meg, barn, lonn, pensjon)
    share = f"/?{profile_query(profile)}#meg"
    if _not_htmx(request):
        return RedirectResponse(share)
    page = "_meg_result.html" if del_ == "resultat" else "_meg.html"
    response = templates.TemplateResponse(request, page, {"m": queries.meg(profile)})
    response.headers["HX-Replace-Url"] = share
    return response


@app.get("/kvittering", response_class=HTMLResponse)
def receipt_fragment(request: Request, skatt: Q = "150000") -> Response:
    if _not_htmx(request):
        return RedirectResponse(f"/?{urlencode({'skatt': skatt})}#skatt")
    tax_kroner = (_numbers(skatt, 1) or [0])[0]
    return templates.TemplateResponse(request, "_receipt.html", {"receipt": queries.receipt(tax_kroner), "tax_kroner": tax_kroner})


@app.get("/utforsk", response_class=HTMLResponse)
def tree_fragment(request: Request, side: Q = "utgift", sti: Q = "", kap: Q = "") -> Response:
    s = _side(side)
    if kap.isdigit() and any(p.kap == int(kap) for p in queries.budget.posts):
        s, sti = queries.chapter_path(int(kap))
    if _not_htmx(request):
        return RedirectResponse(f"/?{urlencode({'side': s, 'sti': sti})}#utforsk")
    return templates.TemplateResponse(request, "_tree.html", {"t": queries.tree(s, sti)})


@app.get("/sok", response_class=HTMLResponse)
def search_fragment(request: Request, q: Q = "") -> HTMLResponse:
    return templates.TemplateResponse(request, "_search.html", {"hits": queries.search(q), "q": q})


@app.get("/kommune", response_class=HTMLResponse)
def kommune_fragment(request: Request, k: Q = "") -> Response:
    if _not_htmx(request):
        return RedirectResponse(f"/?{urlencode({'k': k})}#kommune")
    return templates.TemplateResponse(request, "_kommune.html", {"kv": queries.kommune(k), "kommuner": queries.budget.kommuner})


@app.get("/flyt", response_class=HTMLResponse)
def flows_page(request: Request) -> HTMLResponse:
    d = data.raw("budget.json")
    payload = {"groups": d["groups"], "income": d["income"], "flows": d["flows"], "diff": d["diff"]}
    return templates.TemplateResponse(request, "flyt.html", {"payload": json.dumps(payload, ensure_ascii=False).replace("</", "<\\/")})


@app.get("/helse", response_class=PlainTextResponse)
def health() -> str:
    return "ok"
