"""Reads the JSON files in datasets/ (written by pipeline/datasets.py) into core types."""

from pathlib import Path

import orjson

from core.budget import Budget, Chapter, Flow, FundParts, FundYear, Kommune, Post, Side
from core.facts import Amount, Effect, Fact, Kind
from core.tax import Growth, TaxPages, TaxTable

DATASETS = Path(__file__).parents[2] / "datasets"


class JsonDatasets:
    """Implements core.ports.Datasets. Everything is read once at startup; the files only change on deploy."""

    def __init__(self, root: Path = DATASETS) -> None:
        self._raw = {name: orjson.loads((root / name).read_bytes()) for name in ("budget.json", "meg.json")}
        self._budget = self._read_budget()
        self._facts = self._read_facts()
        self._tax = self._read_tax()

    def budget(self) -> Budget:
        return self._budget

    def facts(self) -> list[Fact]:
        return self._facts

    def tax_table(self) -> TaxTable:
        return self._tax

    def raw(self, name: str) -> dict:
        """The JSON as-is, for chart islands that draw it in the browser."""
        return self._raw[name]

    def _read_budget(self) -> Budget:
        d = self._raw["budget.json"]
        return Budget(
            groups=tuple(d["groups"]),
            income=tuple(d["income"]),
            population=d["population"],
            flows={int(y): tuple(Flow(f["level"], f["source"], f["target"], f["beløp"]) for f in fs) for y, fs in d["flows"].items()},
            posts=tuple(
                Post(Side(p["s"]), p["g"], p["l"], p["k"], p["kn"], p["p"], p["pn"], p["v"], p["v26"]) for p in d["posts"]
            ),
            chapters=tuple(Chapter(c["k"], c["kn"], Side(c["s"]), c["v"], c["v26"]) for c in d["chapters"]),
            kommuner=tuple(
                Kommune(k["nr"], k["navn"], k["fylke"], k["pop"], k["frie26"], k["frie27"], k["vekst"], k["skatteindeks"])
                for k in d["kommuner"]
            ),
            fund=tuple(FundYear(f["year"], f["value"], f["forecast"], f["spend"], f["expected"], f["size"]) for f in d["fund"]),
            fund_parts=tuple(
                FundParts(p["year"], p["oil"], p["withdraw"], p["returns"], p["krone"], p["size"]) for p in d["fund_parts"]
            ),
        )

    def _read_facts(self) -> list[Fact]:
        return [
            Fact(
                id=f["id"],
                personas=tuple(f["personas"]),
                detail=f.get("detail"),
                title=f["title_nb"],
                summary=f["summary_nb"],
                effect=Effect(f["effect"]),
                amounts=tuple(Amount(a["label_nb"], a.get("y2026"), a.get("y2027"), a.get("unit") or "") for a in f["amounts"] or []),
                source_title=f["source_title"],
                source_url=f["source_url"],
                page=f.get("page"),
                caveat=f.get("caveat_nb"),
                under_18=bool(f.get("under_18")),
                kind=Kind(f["kind"]) if f.get("kind") else None,
                same_kroner=bool(f.get("same_kroner")),
                who=f.get("who"),
                area=f.get("area"),
            )
            for f in self._raw["meg.json"]["items"]
        ]

    def _read_tax(self) -> TaxTable:
        t = self._raw["meg.json"]["tax"]
        return TaxTable(
            params={k: {"y2026": v["y2026"], "y2027": v["y2027"]} for k, v in t["params"].items()},
            trinnskatt=t["trinnskatt"],
            growth=Growth(
                wage=t["growth"]["wage"]["pct"], pension=t["growth"]["pension"]["pct"],
                wage_page=t["growth"]["wage"].get("page"), pension_page=t["growth"]["pension"].get("page"),
            ),
            pages=TaxPages(
                alminnelig=t["params"]["skatt_alminnelig_inntekt"]["page"],
                personfradrag=t["params"]["personfradrag"]["page"],
                minstefradrag=t["params"]["minstefradrag_lonn_sats"]["page"],
                trygdeavgift=t["params"]["trygdeavgift_lonn"]["page"],
                trinnskatt=t["trinnskatt_page"],
                pensjonsfradrag=t["params"]["pensjonsskattefradrag_maks"]["page"],
                jordbruksfradrag=t["params"]["jordbruksfradrag_maks"]["page"],
                fiskerfradrag=t["params"]["fiskerfradrag_ovre"]["page"],
                restskatt=t["params"]["restskatt_nedre_grense"]["page"],
            ),
            source_url=t["source_url"],
        )
