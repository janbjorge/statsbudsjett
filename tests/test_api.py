"""The JSON API under /api and /llms.txt, for agents."""

from fastapi.testclient import TestClient

from adapters.web.main import app, queries

client = TestClient(app)


def test_openapi_lists_every_endpoint() -> None:
    paths = client.get("/api/openapi.json").json()["paths"]
    for path in ("/oversikt", "/meg", "/fakta", "/utforsk", "/sok", "/endringer", "/inntekter", "/kommune", "/kommuner", "/kvittering", "/visste-du", "/oljefond"):
        assert path in paths, path


def test_overview_matches_the_page() -> None:
    o = client.get("/api/oversikt").json()
    assert o["utgifter_mrd_kr_2027"] == queries.overview().total
    assert len(o["grupper"]) == 8


def test_meg_gives_the_same_tax_change_as_the_page() -> None:
    r = client.get("/api/meg?meg=barnefamilie,arbeidstaker,bilist&barn=0,2,0,0&lonn=650000,650000&pensjon=0,0").json()
    assert round(r["skatt"]["endring_kr"]) == -3076  # the page says "3 076 kr lavere skatt" (tests/test_web.py)
    assert r["lenke"].startswith("/?meg=barnefamilie")
    fact = r["seksjoner"][0]["endret"][0]
    assert fact["kilde"]["url"].startswith("https://www.regjeringen.no/")


def test_tree_paths_lead_one_level_down() -> None:
    top = client.get("/api/utforsk").json()
    child = top["under"][0]
    below = client.get("/api/utforsk", params={"sti": child["sti"]}).json()
    assert below["her"]["navn"] == child["navn"]
    assert abs(sum(n["mrd_kr_2027"] for n in below["under"]) - child["mrd_kr_2027"]) < 1e-6


def test_kommune_by_name_and_unknown() -> None:
    k = client.get("/api/kommune?k=Bergen").json()
    assert k["nr"] == "4601" and k["frie_inntekter_per_innbygger_kr_2027"] > 10_000  # kroner, not thousands
    assert client.get("/api/kommune?k=Atlantis").status_code == 404


def test_bad_input_never_errors() -> None:
    for url in ("/api/meg?meg=<script>&barn=x&lonn=-5", "/api/kvittering?skatt=abc", "/api/sok?q=%3C", "/api/utforsk?sti=g:Finnes ikke"):
        assert client.get(url).status_code == 200, url
    assert client.get("/api/utforsk?side=tull").status_code == 422


def test_api_is_open_to_other_origins() -> None:
    r = client.get("/api/oversikt", headers={"Origin": "https://example.org"})
    assert r.headers["access-control-allow-origin"] == "*"


def test_llms_txt_links_resolve() -> None:
    r = client.get("/llms.txt")
    assert r.headers["content-type"].startswith("text/markdown")
    text = r.text
    assert text.startswith("# Statsbudsjettet 2027")
    base = "http://testserver/"
    links = [part.split(")")[0] for part in text.split("](")[1:]]
    for url in (u for u in links if u.startswith(base)):
        assert client.get(url.removeprefix(base.rstrip("/"))).status_code == 200, url
