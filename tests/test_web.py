"""The web adapter: full pages, HTMX fragments and the shareable "For deg" link."""

from fastapi.testclient import TestClient

from adapters.web.main import app, profile_from, profile_query, queries

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


def test_everyday_page_adds_up() -> None:
    e = queries.everyday()
    assert abs(sum(r.kroner for r in e.spending) - e.per_person) < 1
    assert abs(sum(r.kroner for r in e.income) - e.per_person) < 1  # income equals spending in the non-oil view
    html = client.get("/visste-du").text
    assert "Visste du?" in html and 'aria-current="page"' in html


def test_family_is_addressed_as_dere() -> None:
    html = client.get(f"/meg?del=resultat&{FAMILY}", headers=HX).text
    assert "Dere betaler mer" in html and "Du betaler mer" not in html


def test_other_host_names_redirect_to_the_canonical_one(monkeypatch) -> None:
    from adapters.web import main

    monkeypatch.setattr(main, "CANONICAL_HOST", "budsjettlupa.no")
    r = client.get(f"/?{FAMILY}", headers={"Host": "statsbudsjett.fly.dev"}, follow_redirects=False)
    assert r.status_code == 301
    assert r.headers["location"] == f"https://budsjettlupa.no/?{FAMILY}"
    assert client.get("/helse", headers={"Host": "statsbudsjett.fly.dev"}).status_code == 200
    html = client.get("/flyt", headers={"Host": "budsjettlupa.no"}).text
    assert '<link rel="canonical" href="https://budsjettlupa.no/flyt">' in html


def test_without_a_canonical_host_every_host_name_is_served() -> None:
    assert client.get("/", headers={"Host": "statsbudsjett.fly.dev"}).status_code == 200
    assert 'rel="canonical"' not in client.get("/").text
