"""Read-only JSON API for agents and scripts, mounted at /api. The OpenAPI schema is at /api/openapi.json.

Input and output are pydantic v2 models, so the schema documents every field.
Field names carry their unit: `_mrd_kr` is billions of kroner, `_kr` is kroner, `_prosent` is percent.
The core mixes units (the tree is in mrd. kr, per-person figures and kommune money in kr), so this adapter names them.
"""

from typing import Annotated

from fastapi import FastAPI, HTTPException, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, ConfigDict, Field

from adapters.web.params import Kroner, ProfileQuery, profile_query
from app.queries import Queries
from core import budget as b
from core.facts import Effect, Fact, Kind

DESCRIPTION = """\
Norway's 2027 state budget proposal (Prop. 1 S (2026–2027), presented 7 October 2026), as JSON.
Not an official source. Every "For deg" fact links to the government document it comes from.

Units are in the field names: `_mrd_kr` is billions of kroner, `_kr` is kroner, `_prosent` is percent.
Totals are the non-oil budget: petroleum income, the transfer to the oil fund and loan transactions (posts 90–99)
are left out, and the transfer from the oil fund counts as income. Amounts are the proposals for 2026 and 2027
(Gul bok), in nominal kroner. The spending group names are this site's own. Method: /llms.txt links to it.
"""


class Out(BaseModel):
    model_config = ConfigDict(frozen=True)


class Overview(Out):
    utgifter_mrd_kr_2027: float
    utgifter_mrd_kr_2026: float
    endring_mrd_kr: float
    endring_prosent: float
    fra_oljefondet_mrd_kr_2027: float
    oljefond_andel_av_utgiftene_prosent_2027: float
    storste_gruppe: str
    storste_gruppe_mrd_kr_2027: float
    innbyggere: int
    grupper: list[str]
    inntektskilder: list[str]


class Named(Out):
    navn: str
    mrd_kr_2027: float


class TreeNode(Out):
    navn: str
    gruppe: str
    kap: int | None
    post: int | None
    mrd_kr_2027: float
    mrd_kr_2026: float | None
    endring_mrd_kr: float | None
    sti: str | None = Field(description="Pass as `sti` to go one level down; null for a post")


class Crumb(Out):
    sti: str
    navn: str


class Tree(Out):
    side: b.Side
    sti: str
    brodsmuler: list[Crumb]
    her: TreeNode
    under: list[TreeNode]


class Hit(Out):
    tittel: str
    side: b.Side
    gruppe: str
    omrade: str
    kap: int
    post: int | None
    mrd_kr_2027: float


class Change(Out):
    kapittel: str
    gruppe: str
    mrd_kr_2026: float
    mrd_kr_2027: float
    endring_mrd_kr: float
    endring_prosent: float | None


class Changes(Out):
    opp: list[Change]
    ned: list[Change]
    kapitler_uten_sammenligning: int


class KommuneRow(Out):
    nr: str
    navn: str
    fylke: str | None
    innbyggere: int
    frie_inntekter_per_innbygger_kr_2027: float


class KommuneDetail(KommuneRow):
    frie_inntekter_kr_2026: float
    frie_inntekter_kr_2027: float
    vekst_prosent: float
    skatteinngang_indeks: float
    landssnitt_per_innbygger_kr_2027: float
    rangering: int
    antall_kommuner: int


class ReceiptLine(Out):
    navn: str
    kr: float


class ReceiptGroup(ReceiptLine):
    andel_prosent: float
    linjer: list[ReceiptLine]


class Receipt(Out):
    skatt_kr: int
    grupper: list[ReceiptGroup]


class Amount(Out):
    navn: str
    verdi_2026: float | None
    verdi_2027: float | None
    enhet: str


class Source(Out):
    tittel: str
    url: str
    side: int | None


class FactOut(Out):
    id: str
    personer: list[str]
    tittel: str
    oppsummering: str
    effekt: Effect
    type: Kind | None
    under_18: bool
    forbehold: str | None
    belop: list[Amount]
    kilde: Source


class Adult(Out):
    lonn_kr: float
    pensjon_kr: float


class ProfileOut(Out):
    meg: list[str]
    barn: dict[str, int]
    voksne: list[Adult]


class Tax(Out):
    skatt_2027_kr: float
    skatt_referanse_kr: float
    endring_kr: float
    inntekt_kr: float
    lonnsvekst_prosent: float
    pensjonsvekst_prosent: float


class Section(Out):
    navn: str
    endret: list[FactOut]
    uendret: list[FactOut]


class Meg(Out):
    profil: ProfileOut = Field(description="The household as understood; unknown values are dropped")
    skatt: Tax
    seksjoner: list[Section]
    lenke: str = Field(description="Path to the same result on the site")


class PerPerson(Out):
    navn: str
    kr: float


class Everyday(Out):
    innbyggere: int
    per_innbygger_kr: float
    per_innbygger_per_dag_kr: float
    per_dag_mrd_kr: float
    per_sekund_kr: float
    utgifter_per_innbygger: list[PerPerson]
    inntekter_per_innbygger: list[PerPerson]


class FundYear(Out):
    aar: int
    andel_prosent: float
    prognose: bool


def _fact(f: Fact) -> FactOut:
    return FactOut(
        id=f.id, personer=list(f.personas), tittel=f.title, oppsummering=f.summary,
        effekt=f.effect, type=f.kind, under_18=f.under_18, forbehold=f.caveat,
        belop=[Amount(navn=a.label, verdi_2026=a.y2026, verdi_2027=a.y2027, enhet=a.unit) for a in f.amounts],
        kilde=Source(tittel=f.source_title, url=f.source_url, side=f.page),
    )


def _node(n: b.Node, path: str) -> TreeNode:
    return TreeNode(
        navn=n.name, gruppe=n.group, kap=n.kap, post=n.post,
        mrd_kr_2027=n.v2027, mrd_kr_2026=n.v2026, endring_mrd_kr=n.change,
        sti=path if n.has_children else None,
    )


def _change(c: b.Change) -> Change:
    return Change(kapittel=c.name, gruppe=c.group, mrd_kr_2026=c.v2026, mrd_kr_2027=c.v2027, endring_mrd_kr=c.change, endring_prosent=c.pct)


def build(queries: Queries) -> FastAPI:
    api = FastAPI(title="Statsbudsjettet 2027 API", description=DESCRIPTION, version="1", docs_url=None, redoc_url=None, openapi_url=None)
    # Public, read-only data: any site or agent may call it
    api.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["GET"])

    @api.get("/openapi.json", include_in_schema=False)
    def openapi(request: Request) -> dict[str, object]:
        """The schema with an absolute server URL: ChatGPT actions refuse a relative one."""
        return {**api.openapi(), "servers": [{"url": str(request.url.replace(path=request.url.path.removesuffix("/openapi.json"), query=""))}]}

    @api.get("/oversikt", summary="Headline totals for 2027 and 2026")
    def overview() -> Overview:
        o, bud = queries.overview(), queries.budget
        return Overview(
            utgifter_mrd_kr_2027=o.total, utgifter_mrd_kr_2026=o.total_2026,
            endring_mrd_kr=o.change, endring_prosent=o.change_pct,
            fra_oljefondet_mrd_kr_2027=o.fund, oljefond_andel_av_utgiftene_prosent_2027=o.fund_share,
            storste_gruppe=o.top_group, storste_gruppe_mrd_kr_2027=o.top_amount,
            innbyggere=bud.population, grupper=list(bud.groups), inntektskilder=list(bud.income),
        )

    @api.get("/inntekter", summary="Income sources in 2027")
    def income() -> list[Named]:
        return [Named(navn=r.name, mrd_kr_2027=r.amount) for r in queries.income()]

    @api.get("/utforsk", summary="One level of the budget tree: group → area → chapter → post")
    def tree(
        side: Annotated[b.Side, Query(description="utgift (spending) or inntekt (income)")] = b.Side.UTGIFT,
        sti: Annotated[str, Query(description="Path from a previous answer's `sti`; empty for the top level")] = "",
    ) -> Tree:
        t = queries.tree(side, sti)
        base = t.crumbs[-1][0]
        return Tree(
            side=t.side, sti=base, brodsmuler=[Crumb(sti=p, navn=n) for p, n in t.crumbs],
            her=_node(t.node, base),
            under=[_node(n, f"{base}/{n.key}".strip("/")) for n in t.children],
        )

    @api.get("/sok", summary="Search chapter and post names (at least 2 characters)")
    def search(q: str = "") -> list[Hit]:
        return [
            Hit(tittel=h.title, side=h.side, gruppe=h.group, omrade=h.area, kap=h.kap, post=h.post, mrd_kr_2027=h.v2027)
            for h in queries.search(q)
        ]

    @api.get("/endringer", summary="Spending chapters that grow or shrink most from 2026 to 2027")
    def changes() -> Changes:
        c = queries.changes()
        return Changes(opp=[_change(x) for x in c.up], ned=[_change(x) for x in c.down], kapitler_uten_sammenligning=c.unmatched)

    @api.get("/kommuner", summary="Every kommune with frie inntekter (unrestricted income) per innbygger in 2027")
    def kommuner() -> list[KommuneRow]:
        return [
            KommuneRow(nr=k.nr, navn=k.name, fylke=k.fylke, innbyggere=k.population, frie_inntekter_per_innbygger_kr_2027=k.per_person)
            for k in queries.budget.kommuner
        ]

    @api.get("/kommune", summary="Frie inntekter for one kommune", responses={404: {"description": "No kommune matches"}})
    def kommune(k: Annotated[str, Query(description="Kommune number (4 digits) or name, e.g. 4601 or Bergen")]) -> KommuneDetail:
        found = b.find_kommune(queries.budget, k)
        if found is None:
            raise HTTPException(404, f"Fant ingen kommune som heter {k!r}. Se /api/kommuner.")
        v = b.kommune_view(queries.budget, found.nr)
        return KommuneDetail(
            nr=found.nr, navn=found.name, fylke=found.fylke, innbyggere=found.population,
            frie_inntekter_kr_2026=found.frie2026, frie_inntekter_kr_2027=found.frie2027, vekst_prosent=found.growth,
            skatteinngang_indeks=found.tax_index,
            frie_inntekter_per_innbygger_kr_2027=found.per_person, landssnitt_per_innbygger_kr_2027=v.average_per_person,
            rangering=v.rank, antall_kommuner=v.count,
        )

    @api.get("/kvittering", summary="Where a given amount of tax goes, split like 2027 spending")
    def receipt(skatt: Annotated[Kroner, Query(description="Tax paid in kroner")] = 150_000) -> Receipt:
        return Receipt(
            skatt_kr=skatt,
            grupper=[
                ReceiptGroup(navn=g.name, kr=g.kroner, andel_prosent=g.share, linjer=[ReceiptLine(navn=x.name, kr=x.kroner) for x in g.lines])
                for g in queries.receipt(skatt)
            ],
        )

    @api.get(
        "/meg",
        summary="What the budget changes for a household: tax and the facts that apply",
        description=(
            "Tax change is measured against 2026 rules adjusted for expected wage and pension growth, as the Ministry of Finance does. "
            "Each parameter takes comma-separated values (or repeats). With neither `lonn` nor `pensjon`, one adult earning 500 000 kr is assumed."
        ),
    )
    def meg(q: Annotated[ProfileQuery, Query()]) -> Meg:
        profile = q.profile()
        m = queries.meg(profile)
        return Meg(
            profil=ProfileOut(
                meg=list(q.meg), barn=profile.kids,
                voksne=[Adult(lonn_kr=a.wage, pensjon_kr=a.pension) for a in profile.adults],
            ),
            skatt=Tax(
                skatt_2027_kr=m.tax.tax_2027, skatt_referanse_kr=m.tax.tax_reference, endring_kr=m.tax.change,
                inntekt_kr=m.tax.income, lonnsvekst_prosent=m.growth_wage, pensjonsvekst_prosent=m.growth_pension,
            ),
            seksjoner=[Section(navn=s.label, endret=[_fact(f) for f in s.changed], uendret=[_fact(f) for f in s.unchanged]) for s in m.sections],
            lenke=f"/?{profile_query(profile)}#meg",
        )

    @api.get("/fakta", summary="Every verified \"For deg\" fact with its source document and page")
    def facts() -> list[FactOut]:
        return [_fact(f) for f in queries.facts()]

    @api.get("/visste-du", summary="2027 totals in everyday units: per innbygger, per day, per second")
    def everyday() -> Everyday:
        e = queries.everyday()
        return Everyday(
            innbyggere=e.population, per_innbygger_kr=e.per_person, per_innbygger_per_dag_kr=e.per_person_day,
            per_dag_mrd_kr=e.per_day, per_sekund_kr=e.per_second,
            utgifter_per_innbygger=[PerPerson(navn=r.name, kr=r.kroner) for r in e.spending],
            inntekter_per_innbygger=[PerPerson(navn=r.name, kr=r.kroner) for r in e.income],
        )

    @api.get("/oljefond", summary="Share of budget spending covered by the oil fund, per year (NB 2027 figure 3.4)")
    def fund() -> list[FundYear]:
        return [FundYear(aar=f.year, andel_prosent=f.share, prognose=f.forecast) for f in queries.budget.fund]

    return api
