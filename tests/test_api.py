"""The JSON API under /api and /llms.txt, for agents."""

from fastapi.testclient import TestClient

from adapters.web.main import app, queries
from adapters.web.params import MAX_INCOME, ProfileQuery

client = TestClient(app)


def test_openapi_lists_every_endpoint() -> None:
    paths = client.get("/api/openapi.json").json()["paths"]
    for path in ("/oversikt", "/meg", "/fakta", "/utforsk", "/sok", "/endringer", "/inntekter", "/kommune", "/kommuner", "/kvittering", "/visste-du", "/oljefond", "/oljefond/bidrag", "/flyt", "/tilbud"):
        assert path in paths, path


def test_fund_parts_match_figure_3_6() -> None:
    rows = client.get("/api/oljefond/bidrag").json()
    last = rows[-1]
    assert last["aar"] == 2025
    assert last["avkastning_mrd_kr"] == 13371.9
    assert last["olje_inn_mrd_kr"] == 9561.9
    assert last["uttak_mrd_kr"] == -4057.3
    assert last["kronekurs_mrd_kr"] == 2391.4
    assert last["fondsverdi_mrd_kr"] == 21267.9
    assert rows[0]["aar"] == 1996


def test_overview_matches_the_page() -> None:
    o = client.get("/api/oversikt").json()
    assert o["utgifter_mrd_kr_2027"] == queries.overview().total
    assert len(o["grupper"]) == 8


def test_meg_gives_the_same_tax_change_as_the_page() -> None:
    r = client.get("/api/meg?meg=barnefamilie,arbeidstaker,bilist&barn=0,2,0,0&lonn=650000,650000&pensjon=0,0").json()
    assert round(r["skatt"]["endring_kr"]) == -3076  # the page says "3 076 kr lavere skatt" (tests/test_web.py)
    assert r["lenke"].startswith("/?meg=barnefamilie")
    assert r["skatt"]["kilde"]["url"] == "https://www.regjeringen.no/no/dokumenter/prop.-1-ls-20262027/id3176120/"
    assert r["skatt"]["lonnsvekst_kilde_side"] == 80  # "anslått lønnsvekst på 4,0 pst." (data/persona/tax.json)
    fact = r["seksjoner"][0]["endret"][0]
    assert fact["kilde"]["url"].startswith("https://www.regjeringen.no/")


def test_meg_takes_business_income() -> None:
    # 117 290,70 kr worked by hand from Prop. 1 LS tabell 1.5 and skatteloven § 8-1 (tests/test_tax.py)
    r = client.get("/api/meg?meg=bonde&naering=550000&naering_type=jordbruk").json()
    assert r["profil"]["voksne"] == [{"lonn_kr": 0, "pensjon_kr": 0, "naering_kr": 550_000, "naering_type": "jordbruk"}]
    assert round(r["skatt"]["skatt_2027_kr"], 2) == 117_290.70
    assert r["lenke"].endswith("naering=550000&naering_type=jordbruk#meg")
    assert r["profil"]["situasjoner"] == ["bonde", "naeringsdrivende"]


def test_tree_paths_lead_one_level_down() -> None:
    top = client.get("/api/utforsk").json()
    child = top["under"][0]
    below = client.get("/api/utforsk", params={"sti": child["sti"]}).json()
    assert below["her"]["navn"] == child["navn"]
    assert abs(sum(n["mrd_kr_2027"] for n in below["under"]) - child["mrd_kr_2027"]) < 1e-6


def test_flow_chapters_lead_into_the_tree() -> None:
    flow = client.get("/api/flyt", params={"vis": "Folketrygden"}).json()
    chapter = flow["kapitler"][0]["kapittel"]
    assert client.get("/api/utforsk", params={"sti": chapter["sti"]}).json()["her"]["navn"] == chapter["navn"]
    assert client.get("/api/flyt", params={"vis": "tull"}).status_code == 404


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


def test_pages_point_agents_to_llms_txt() -> None:
    r = client.get("/")
    assert '</llms.txt>; rel="alternate"' in r.headers["link"]
    assert '</api/openapi.json>; rel="service-desc"' in r.headers["link"]
    assert '<link rel="alternate" type="text/markdown" href="/llms.txt"' in r.text
    assert '<link rel="service-desc" type="application/json" href="/api/openapi.json">' in r.text
    assert "link" not in client.get("/llms.txt").headers


def test_robots_txt_sends_crawlers_to_the_api() -> None:
    text = client.get("/robots.txt").text
    assert "http://testserver/llms.txt" in text and "http://testserver/api/openapi.json" in text
    assert "Allow: /api/\n" in text
    rules = [line.split(": ", 1)[1] for line in text.splitlines() if line.startswith("Disallow")]
    assert "/?*sti=" in rules and "/utforsk" in rules
    assert not any(r.startswith(("/api", "/*")) for r in rules)  # no rule reaches /api/utforsk?sti=
    assert "/" not in rules  # the pages themselves stay crawlable
    assert "Sitemap: http://testserver/sitemap.xml\n" in text


def test_sitemap_lists_the_pages_and_each_answers() -> None:
    r = client.get("/sitemap.xml")
    assert r.status_code == 200 and r.headers["content-type"].startswith("application/xml")
    urls = [u.split("</loc>")[0] for u in r.text.split("<loc>")[1:]]
    assert urls == [
        "http://testserver/", "http://testserver/flyt", "http://testserver/tilbud",
        "http://testserver/visste-du", "http://testserver/oljefondet", "http://testserver/ki",
    ]
    for url in urls:
        assert client.get(url).status_code == 200, url


def test_openapi_has_an_absolute_server_and_typed_responses() -> None:
    schema = client.get("/api/openapi.json").json()
    assert schema["servers"] == [{"url": "http://testserver/api"}]
    assert {"Meg", "FactOut", "Tree", "KommuneDetail"} <= set(schema["components"]["schemas"])


def test_meg_accepts_comma_lists_and_repeats() -> None:
    a = client.get("/api/meg?meg=student,pensjonist&lonn=100000").json()["profil"]
    b = client.get("/api/meg?meg=student&meg=pensjonist&lonn=100000").json()["profil"]
    assert a == b and a["meg"] == ["student", "pensjonist"]


def test_profile_query_drops_bad_input() -> None:
    p = ProfileQuery.model_validate({"meg": "hacker,student", "barn": "x,2", "lonn": "-5,abc", "pensjon": "9999999999999"}).profile()
    assert p.personas == {"student"}
    assert list(p.kids.values()) == [0, 2, 0, 0, 0]
    assert [(a.wage, a.pension) for a in p.adults] == [(5, MAX_INCOME)]


def test_agents_page_is_linked_and_shows_the_prompt() -> None:
    html = client.get("/ki").text
    assert "Spør en KI om budsjettet" in html and "http://testserver/llms.txt" in html
    assert 'href="/ki" aria-current="page"' in html
    assert 'href="/ki"' in client.get("/").text
