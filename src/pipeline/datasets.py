"""Build datasets/ for the web app from the downloaded sources. Run: uv run python -m pipeline.datasets"""

import json
from pathlib import Path

import polars as pl

from core.facts import AREAS
from pipeline import verify
from pipeline.flows import (
    FILES,
    GROUPS,
    INCOME,
    ROOT,
    diff,
    expense_group,
    expense_leaf,
    flows,
    income_source,
    kap,
    load,
)

OUT = ROOT / "datasets"
GH = ROOT / "data/gront_hefte/kommunene-tabeller"
NB3 = ROOT / "data/excel/kap_3_nb_2027.xlsx"
COUNTIES = ROOT / "data/frie_inntekter/countycollection.json"


def posts() -> list[dict]:
    """Every non-oil post in 2027 with its 2026 amount, both in billion NOK."""
    keys = ["kap_nr", "post_nr"]
    d27 = load(2027).with_columns(
        side=pl.when(kap < 3000).then(pl.lit("utgift")).otherwise(pl.lit("inntekt")),
        group=pl.when(kap < 3000).then(expense_group).otherwise(income_source),
        leaf=pl.when(kap < 3000).then(expense_leaf),
    )
    d26 = load(2026).group_by(keys).agg(v26=pl.col("beløp").sum())
    return (
        d27.join(d26, on=keys, how="left")
        .select(
            s=pl.col("side"),
            g=pl.col("group"),
            l=pl.col("leaf").fill_null(pl.col("group")),
            k=pl.col("kap_nr"),
            kn=pl.col("kap_navn"),
            p=pl.col("post_nr"),
            pn=pl.col("post_navn"),
            v=pl.col("beløp").round(4),
            v26=pl.col("v26").round(4),
        )
        .sort("k", "p")
        .to_dicts()
    )


def chapters() -> list[dict]:
    """Chapter totals for both years, matched on chapter number."""
    def by_kap(year: int, col: str) -> pl.DataFrame:
        return load(year).group_by("kap_nr").agg(pl.col("kap_navn").first(), pl.col("beløp").sum().alias(col))

    c27, c26 = by_kap(2027, "v"), by_kap(2026, "v26")
    return (
        c27.join(c26, on="kap_nr", how="full", coalesce=True, suffix="_26")
        .with_columns(
            kn=pl.coalesce("kap_navn", "kap_navn_26"),
            s=pl.when(kap < 3000).then(pl.lit("utgift")).otherwise(pl.lit("inntekt")),
        )
        .select(k="kap_nr", kn="kn", s="s", v=pl.col("v").round(4), v26=pl.col("v26").round(4))
        .sort("k")
        .to_dicts()
    )


def sheet_rows(path: Path, sheet: str | None = None) -> pl.DataFrame:
    return pl.read_excel(path, sheet_name=sheet, has_header=False) if sheet else pl.read_excel(path, has_header=False)


def kommuner() -> list[dict]:
    """Frie inntekter, population and tax level per kommune from Grønt hefte 2027."""
    is_kommune = pl.col("column_0").str.contains(r"^\d{4} ")
    num = lambda c: pl.col(c).cast(pl.Float64)
    crit = sheet_rows(GH / "tabell-f-k-kriteriedata.ods").filter(is_kommune).select(
        navn="column_0", pop=num("column_2"), skatteindeks=num("column_37")
    )
    frie = sheet_rows(GH / "tabell-3-k-anslag-pa-frie-inntekter-i-2027.ods").filter(is_kommune).select(
        navn="column_0", frie26=num("column_1") * 1000, frie27=num("column_3") * 1000, vekst=num("column_5")
    )
    fylker = {c["fylkeskommune"]["id"]: c["fylkeskommune"]["name"].removesuffix(" fylkeskommune") for c in json.loads(COUNTIES.read_text())["data"]}
    split = [pl.col("navn").str.slice(0, 4).alias("nr"), pl.col("navn").str.slice(5).str.strip_chars()]
    return (
        crit.with_columns(split)
        .join(frie.with_columns(split).drop("navn"), on="nr")
        .with_columns(fylke=pl.col("nr").str.slice(0, 2).replace_strict(fylker, default=None))
        .select("nr", "navn", "fylke", pl.col("pop").cast(pl.Int64), "frie26", "frie27", "vekst", "skatteindeks")
        .sort("navn")
        .to_dicts()
    )


def fund_share() -> list[dict]:
    """Share of budget spending covered by the oil fund, NB 2027 figure 3.4."""
    d = sheet_rows(NB3, "Fig3-4").filter(pl.col("column_0").str.contains(r"^\d{4}$"))
    return (
        d.select(
            year=pl.col("column_0").cast(pl.Int64),
            value=pl.coalesce(pl.col("column_1"), pl.col("column_2")).cast(pl.Float64),
            forecast=pl.col("column_1").is_null(),
        )
        .to_dicts()
    )


PERSONA = ROOT / "data/persona"
# Reference system for 2027: 2026 amounts adjusted by expected growth (Prop. 1 LS p. 79-80, METHOD.md §5)
GROWTH = {
    "wage": {"pct": 4.0, "page": 80, "quote": "Innslagspunktene i trinnskatten foreslås justert med anslått lønnsvekst på 4,0 pst."},
    "pension": {"pct": 3.35, "page": 79, "quote": "justeres med anslått lønns- og pensjonsvekst på henholdsvis 4,0 og 3,35 pst."},
}
TAX_SOURCE = "https://www.regjeringen.no/no/dokumenter/prop.-1-ls-20262027/id3176120/"


def meg() -> dict:
    """Verified persona facts and the tax rules the calculator needs."""
    if verify.main() != 0:
        raise SystemExit("persona facts failed verification, not building")
    for name, g in GROWTH.items():
        item = {"source_file": "data/text/prp202620270001ls0dddpdfs.txt", "amounts": [{"label_nb": name, "y2027": g["pct"]}], **g}
        if errs := verify.check_item(item, {}):
            raise SystemExit(f"growth assumption {name}: {errs}")
    items = []
    for f in sorted(PERSONA.glob("*.json")):
        if f.name != "tax.json":
            items += json.loads(f.read_text())
    # Curation on top of the extracted facts: duplicates between extraction runs, items the tax
    # calculator already covers, and spending growth that reads like a personal change
    drop = {"toll-klaer-tekstiler-5-prosent", "skatt-lavere-inntektsskatt", "personfradrag-okes", "dagpenger-utgifter"}
    add_personas = {"toll-klaer-5-prosent": ["naeringsdrivende"]}
    # Only for children under 18, with the words in the quote that say so (METHOD.md §6)
    under_18 = {"barnetrygd-uendret": "barn 0–18 år"}
    # Kroner amounts that stay the same while prices rise: a benefit is worth less, a price costs
    # less. The words in the quotes show the amount stays the same in kroner (METHOD.md §6)
    same_kroner = {
        "barnetrygd-uendret": ("minus", "no 2012 kroner per månad"),
        "kontantstotte-uendret": ("minus", "med uendra nivå"),
        "barnehage-makspris": ("pluss", "fryst på 1 200"),
        "innsatssonen-saerskilt-fradrag": ("minus", "45 000 kr 45 000 kr"),
        "jordbruksfradrag-uendret": ("minus", "99 600 kr 99 600 kr"),
        "hjelpemiddel-satser-nominelt": ("minus", "føre satsane vidare nominelt"),
        "bostotte-2027": ("minus", "nominelt vidareføre buutgiftstaka"),
    }
    # Money to or from a sector, an organisation or companies, not a household: off "For deg", onto /tilbud,
    # with the badge naming who it hits (METHOD.md §6)
    who = {
        "fot-flyruter": "Regionale flyruter",
        "momskompensasjon-frivillige": "Frivillige lag",
        "jordbruksavtalen-inntekt": "Jordbruket",
        "co2-kompensasjon-fiskeflaten": "Fiskeflåten",
        "avgift-oppdrettsfisk": "Oppdrettsselskapene",
        "grunnrenteskatt-havbruk-uendret": "Oppdrettsselskapene",
        "skattefunn-innstramming": "Bedrifter",
        "toll-klaer-5-prosent": "Butikkene",
        "arbeidsgiveravgift-uendret": "Arbeidsgivere",
        "stromstotte-jordbruk-2029": "Jordbruket",
        "co2-avgift-veksthus": "Veksthusene",
    }
    items = [it for it in items if it["id"] not in drop]
    if missing := who.keys() - {it["id"] for it in items}:
        raise SystemExit(f"general facts no longer extracted: {sorted(missing)}")
    for it in items:
        it["personas"] = it["personas"] + [p for p in add_personas.get(it["id"], []) if p not in it["personas"]]
        quotes = " ".join([it["quote"], *(e["quote"] for e in it.get("extra_quotes", []))])
        if (words := under_18.get(it["id"])) is not None:
            if words not in it["quote"]:
                raise SystemExit(f"{it['id']}: quote no longer says {words!r}")
            it["under_18"] = True
        if (rule := same_kroner.get(it["id"])) is not None:
            effect, words = rule
            if words not in quotes or it["effect"] not in ("uendret", effect):
                raise SystemExit(f"{it['id']}: quotes no longer say {words!r}, or the effect changed")
            it["effect"] = effect
            it["same_kroner"] = True
        it["who"] = who.get(it["id"], it.get("who"))
        # A part of the budget no profile covers: no personas, and a name for the badge when money goes to someone
        if (area := it.get("area")) is not None:
            if area not in AREAS or it["personas"]:
                raise SystemExit(f"{it['id']}: area {area!r} unknown, or the fact also has personas")
            if it.get("kind") in ("betaler", "far") and not it["who"]:
                raise SystemExit(f"{it['id']}: says who pays or gets, so it needs a who")
        if it["effect"] != "uendret" and it.get("kind") not in ("betaler", "far", "tilbud", "regel", "utgift"):
            raise SystemExit(f"{it['id']}: a change needs a kind (betaler, far, tilbud, regel or utgift)")
        if it.get("kind") == "utgift" and it.get("area") is None:
            raise SystemExit(f"{it['id']}: a spending total belongs to a part of the budget, so it needs an area")
    keep = ("id", "personas", "detail", "under_18", "kind", "same_kroner", "who", "area", "title_nb", "summary_nb", "effect", "amounts", "source_title", "source_url", "page", "caveat_nb")
    tax = json.loads((PERSONA / "tax.json").read_text())
    return {
        "items": [{k: it.get(k) for k in keep} for it in items],
        "tax": {
            "params": {p["key"]: {"y2026": p["y2026"], "y2027": p["y2027"], "page": p.get("page")} for p in tax["params"]},
            "trinnskatt": {y: tax["trinnskatt"][y] for y in ("y2026", "y2027")},
            "trinnskatt_page": tax["trinnskatt"]["page"],
            "growth": GROWTH,
            "source_url": TAX_SOURCE,
        },
    }


def main() -> None:
    kom = kommuner()
    payload = {
        "groups": GROUPS,
        "income": INCOME,
        "population": sum(k["pop"] for k in kom),
        "flows": {str(y): flows(y).drop("year").to_dicts() for y in FILES},
        "posts": posts(),
        "chapters": chapters(),
        "kommuner": kom,
        "fund": fund_share(),
    }
    payload["diff"] = diff().to_dicts()
    OUT.mkdir(exist_ok=True)
    (OUT / "budget.json").write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n")
    (OUT / "meg.json").write_text(json.dumps(meg(), ensure_ascii=False, indent=2) + "\n")
    # Downloads for anyone who wants the numbers themselves
    pl.DataFrame(payload["posts"]).rename(
        {"s": "side", "g": "gruppe", "l": "område", "k": "kapittel", "kn": "kapittelnavn", "p": "post", "pn": "postnavn", "v": "mrd_2027", "v26": "mrd_2026"}
    ).write_csv(OUT / "poster-2027.csv")
    pl.DataFrame(kom).write_csv(OUT / "kommuner-2027.csv")
    print(f"wrote {OUT}: {len(payload['posts'])} posts, {len(kom)} kommuner, population {payload['population']:,}")

if __name__ == "__main__":
    main()
