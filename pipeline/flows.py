"""Build chart data for the 2026 vs 2027 budget flows from Gul bok datagrunnlag.

View: the non-oil budget, as Finansdepartementet presents it. Petroleum flows
(SDØE, petroleum taxes, Equinor dividend, transfer to the fund) and loan
transactions (post 90-99) are removed; the transfer from the fund then closes
the gap, so income equals spending exactly.
"""

from pathlib import Path

import polars as pl

ROOT = Path(__file__).parent.parent
FILES = {
    2026: ROOT / "data/excel/2026/2026_gulbok_datagrunnlag.xlsx",
    2027: ROOT / "data/excel/2027_gulbok_datagrunnlag.xlsx",
}

PETROLEUM = [2440, 2800, 5440, 5507, 5508, 5509, 5685]  # see METHOD.md §1

# Expense groups in display order; the first seven get a categorical slot, the last is gray
GROUPS = [
    "Folketrygden",
    "Kommunesektoren",
    "Helse og omsorg",
    "Forsvar",
    "Arbeid, familie og integrering",
    "Utdanning og forskning",
    "Samferdsel",
    "Øvrige formål",
]
INCOME = [
    "Skatt på inntekt og formue",
    "Trygde- og arbeidsgiveravgift",
    "Merverdiavgift",
    "Andre skatter og avgifter",
    "Renter, utbytte og andre inntekter",
    "Overføring fra oljefondet",
]

kap, omr, kat = pl.col("kap_nr"), pl.col("omr_nr"), pl.col("kat_nr")

income_source = (
    pl.when(kap == 5800).then(pl.lit("Overføring fra oljefondet"))
    .when(kap == 5501).then(pl.lit("Skatt på inntekt og formue"))
    .when(kap == 5700).then(pl.lit("Trygde- og arbeidsgiveravgift"))
    .when(kap == 5521).then(pl.lit("Merverdiavgift"))
    .when(kap.is_between(5500, 5599)).then(pl.lit("Andre skatter og avgifter"))
    .otherwise(pl.lit("Renter, utbytte og andre inntekter"))
)

expense_group = (
    pl.when(omr.is_in([28, 29, 30, 33])).then(pl.lit("Folketrygden"))
    .when((omr == 13) & (kat == 70)).then(pl.lit("Kommunesektoren"))
    .when(omr == 10).then(pl.lit("Helse og omsorg"))
    .when(omr == 4).then(pl.lit("Forsvar"))
    .when(omr.is_in([9, 11])).then(pl.lit("Arbeid, familie og integrering"))
    .when(omr == 7).then(pl.lit("Utdanning og forskning"))
    .when(omr.is_in([21, 22])).then(pl.lit("Samferdsel"))
    .otherwise(pl.lit("Øvrige formål"))
)

# None means the group has no breakdown and ends in the middle column
expense_leaf = (
    pl.when(omr == 28).then(pl.lit("Foreldrepenger"))
    .when((omr == 29) & (kat == 70)).then(pl.lit("Alderspensjon"))
    .when((omr == 29) & (kat == 50)).then(pl.lit("Sykepenger, AAP og uføretrygd"))
    .when(omr == 30).then(pl.lit("Legehjelp og legemidler"))
    .when(omr == 33).then(pl.lit("Dagpenger mv."))
    .when(omr == 29).then(pl.lit("Andre trygdeytelser"))
    .when(kap == 571).then(pl.lit("Rammetilskudd kommuner"))
    .when(kap == 572).then(pl.lit("Rammetilskudd fylkeskommuner"))
    .when((omr == 13) & (kat == 70)).then(pl.lit("Øvrig til kommunesektoren"))
    .when((omr == 10) & (kat == 30)).then(pl.lit("Sykehusene"))
    .when(omr == 10).then(pl.lit("Øvrig helse og omsorg"))
    .when(omr == 4).then(pl.lit(None))
    .when((omr == 9) & (kat == 10)).then(pl.lit("Drift av Nav"))
    .when((omr == 9) & (kat == 30)).then(pl.lit("Arbeidsmarkedstiltak"))
    .when((omr == 9) & (kat == 70)).then(pl.lit("Integrering"))
    .when((omr == 11) & (kat == 10)).then(pl.lit("Familie og oppvekst"))
    .when((omr == 11) & (kat == 20)).then(pl.lit("Barnevern"))
    .when(omr.is_in([9, 11])).then(pl.lit("Øvrig arbeid og familie"))
    .when((omr == 7) & (kat == 60)).then(pl.lit("Høyere utdanning og forskning"))
    .when((omr == 7) & (kat == 80)).then(pl.lit("Lånekassen"))
    .when((omr == 7) & (kat == 20)).then(pl.lit("Grunnopplæring"))
    .when(omr == 7).then(pl.lit("Øvrig utdanning"))
    .when((omr == 21) & (kat == 30)).then(pl.lit("Vei"))
    .when((omr == 21) & (kat == 50)).then(pl.lit("Jernbane"))
    .when(omr.is_in([21, 22])).then(pl.lit("Øvrig samferdsel"))
    .when(omr == 6).then(pl.lit("Justis og beredskap"))
    .when(omr.is_in([2, 3])).then(pl.lit("Utenriks og bistand"))
    .when(kap.is_in([1632, 1633])).then(pl.lit("Momskompensasjon"))
    .when(omr == 24).then(pl.lit("Renter på statsgjeld"))
    .when(omr == 15).then(pl.lit("Landbruk og mat"))
    .when(omr.is_in([12, 18])).then(pl.lit("Klima, miljø og energi"))
    .when(omr == 17).then(pl.lit("Næring og fiskeri"))
    .when(omr == 8).then(pl.lit("Kultur og medier"))
    .otherwise(pl.lit("Statsforvaltning og annet"))
)


def load(year: int) -> pl.DataFrame:
    return (
        pl.read_excel(FILES[year], sheet_name="Data")
        .filter((pl.col("post_nr") < 90) & ~kap.is_in(PETROLEUM))
        .with_columns(pl.col("beløp").cast(pl.Float64) / 1e9)
    )


def flows(year: int) -> pl.DataFrame:
    """One row per flow: source -> target, amount in billion NOK."""
    d = load(year)
    total = f"Statsbudsjettet {year}"
    income = (
        d.filter(kap >= 3000)
        .group_by(source=income_source)
        .agg(pl.col("beløp").sum())
        .with_columns(target=pl.lit(total), level=pl.lit(0))
    )
    spend = d.filter(kap < 3000).with_columns(group=expense_group, leaf=expense_leaf)
    groups = (
        spend.group_by(target="group")
        .agg(pl.col("beløp").sum())
        .with_columns(source=pl.lit(total), level=pl.lit(1))
    )
    leaves = (
        spend.drop_nulls("leaf")
        .group_by(source="group", target="leaf")
        .agg(pl.col("beløp").sum())
        .with_columns(level=pl.lit(2))
    )
    cols = ["level", "source", "target", "beløp"]
    out = pl.concat([income.select(cols), groups.select(cols), leaves.select(cols)])
    balance = float(income["beløp"].sum()) - float(groups["beløp"].sum())
    assert abs(balance) < 1e-6, f"{year}: income and spending differ by {balance} bn"
    # Round to whole kroner: parallel group_by sums differ in the last float bits between runs
    return out.with_columns(pl.col("beløp").round(9), year=pl.lit(year)).sort("level", "source", "target")


def diff() -> pl.DataFrame:
    """Change per income source, group and sub-group from 2026 to 2027."""
    both = pl.concat([flows(y) for y in FILES])
    # Diff on stable keys: income sources, groups and leaves (total node renamed per year)
    keyed = both.with_columns(
        key=pl.when(pl.col("level") == 0).then("source").otherwise("target"),
        parent=pl.when(pl.col("level") == 2).then("source").otherwise(pl.lit(None)),
    )
    return (
        keyed.pivot(on="year", index=["level", "key", "parent"], values="beløp")
        .rename({"2026": "y2026", "2027": "y2027"})
        .with_columns(pl.col("y2026", "y2027").fill_null(0.0))
        .with_columns(change=(pl.col("y2027") - pl.col("y2026")).round(9))
        .with_columns(pct=pl.when(pl.col("y2026") > 0).then(pl.col("change") / pl.col("y2026") * 100))
        .sort("level", "change", descending=[False, True])
    )
