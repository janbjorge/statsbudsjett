"""The web adapter: full pages, HTMX fragments and the shareable "For deg" link."""

from fastapi.testclient import TestClient

from adapters.web.main import app, profile_from, profile_query

client = TestClient(app)
HX = {"HX-Request": "true"}
FAMILY = "meg=barnefamilie,arbeidstaker,bilist&barn=0,2,0,0&lonn=650000,650000&pensjon=0,0"


def test_front_page_renders_every_section() -> None:
    html = client.get("/").text
    for anchor in ("oversikt", "meg", "skatt", "inntekter", "utforsk", "endringer", "kommune", "olje", "feil", "ordliste"):
        assert f'id="{anchor}"' in html


def test_shared_family_link_shows_the_tax_effect() -> None:
    html = client.get(f"/?{FAMILY}").text
    assert "3 076 kr lavere skatt" in html


def test_fragment_sets_a_shareable_url() -> None:
    r = client.get(f"/meg?del=resultat&{FAMILY}", headers=HX)
    assert r.status_code == 200
    assert r.headers["HX-Replace-Url"].startswith("/?meg=barnefamilie")


def test_fragments_redirect_to_the_full_page_without_htmx() -> None:
    for url in (f"/meg?{FAMILY}", "/kvittering?skatt=1000", "/utforsk?sti=g:Forsvar", "/kommune?k=Bergen"):
        r = client.get(url, follow_redirects=False)
        assert r.status_code == 307 and r.headers["location"].startswith("/?"), url


def test_bad_input_never_errors() -> None:
    for url in ("/?meg=hacker,<script>&barn=x,y&lonn=-5,abc&pensjon=9999999999999", "/utforsk?sti=g:Finnes ikke&kap=999999", "/sok?q=%3Cscript%3E", "/kommune?k=Atlantis"):
        assert client.get(url, headers=HX).status_code == 200, url


def test_profile_round_trip() -> None:
    p = profile_from("pensjonist,student", "1,0,2,0", "100000,0", "250000,300000")
    assert profile_from(**dict(pair.split("=") for pair in profile_query(p).replace("%2C", ",").split("&"))) == p


def test_flows_page_and_downloads() -> None:
    page = client.get("/flyt").text
    assert 'id="sankey"' in page and 'id="flyt-data"' in page
    assert 'aria-current="page"' in page  # the shared site nav marks where we are
    assert client.get("/data/poster-2027.csv").text.startswith("side,gruppe")
    assert client.get("/helse").text == "ok"
