"""The web adapter: full pages, HTMX fragments and the shareable "For deg" link."""

import re

from fastapi.testclient import TestClient

from adapters.web.main import app, profile_from, profile_query, queries

client = TestClient(app)
HX = {"HX-Request": "true"}
FAMILY = "meg=barnefamilie,arbeidstaker,bilist&barn=0,2,0,0&lonn=650000,650000&pensjon=0,0"
FAMILY_ARGS = ("barnefamilie,arbeidstaker,bilist", "0,2,0,0", "650000,650000", "0,0")


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
        # the redirect is cacheable, so a cache must not hand it to the HTMX request for the same URL
        assert "HX-Request" in r.headers["vary"], url


def test_bad_input_never_errors() -> None:
    for url in ("/?meg=hacker,<script>&barn=x,y&lonn=-5,abc&pensjon=9999999999999&naering=x&naering_type=<b>", "/utforsk?sti=g:Finnes ikke&kap=999999", "/sok?q=%3Cscript%3E", "/kommune?k=Atlantis"):
        assert client.get(url, headers=HX).status_code == 200, url


def test_profile_round_trip() -> None:
    p = profile_from("pensjonist,student", "1,0,2,0", "100000,0", "250000,300000")
    assert profile_from(**dict(pair.split("=") for pair in profile_query(p).replace("%2C", ",").split("&"))) == p


FARMER = "meg=bonde&barn=0,0,0,0&lonn=0&pensjon=0&naering=550000&naering_type=jordbruk"


def test_farmer_link_shows_the_farm_tax() -> None:
    # 117 290,70 kr worked by hand from Prop. 1 LS tabell 1.5 and skatteloven § 8-1 (tests/test_tax.py)
    html = client.get(f"/?{FARMER}").text
    assert re.search(r"om lag <b>117\W291\Wkr</b>", html)
    assert '<option value="jordbruk" selected>' in html


LOVDATA = "https://lovdata.no/dokument/NL/lov/1999-03-26-14/%C2%A7"


def test_farmer_breakdown_cites_the_law() -> None:
    # Each line of "Slik er skatten regnet" names its source: Prop. 1 LS page, or the skatteloven section
    html = client.get(f"/?{FARMER}").text
    calc = html[html.index('<details class="calc">'):html.index("</details>", html.index('<details class="calc">'))]
    assert re.search(r"Jordbruksfradrag</td><td class=\"num\">208\W900\Wkr", calc)
    assert f'{LOVDATA}8-1"' in calc and f'{LOVDATA}12-11"' in calc
    assert f'{LOVDATA}6-60"' not in calc
    for page in (26, 27, 28, 79, 82):  # tabell 1.5, no minstefradrag for business (79), nominal deductions (82)
        assert f"Prop. 1 LS s. {page}<" in calc, page
    assert re.search(r"Skatt i 2027</b></td><td class=\"num\"><b>117\W291\Wkr", calc)


def test_fisher_breakdown_cites_the_fiskerfradrag() -> None:
    html = client.get("/?meg=fisker&naering=400000&naering_type=fiske").text
    assert f'{LOVDATA}6-60"' in html and f'{LOVDATA}8-1"' not in html


def test_wage_breakdown_has_no_business_notes() -> None:
    meg, barn, lonn, pensjon = FAMILY_ARGS
    html = client.get(f"/?meg={meg}&barn={barn}&lonn={lonn}&pensjon={pensjon}").text
    assert html.count("<caption>Voksen") == 2 and "Minstefradrag" in html
    assert LOVDATA not in html and "Prop. 1 LS s. 79" not in html


def test_bonde_preset_is_a_farmer_not_a_wage_earner() -> None:
    html = client.get("/").text
    assert "naering=550000&amp;naering_type=jordbruk" in html


def test_business_profile_round_trip() -> None:
    p = profile_from("bonde", "0,0,0,0", "0,300000", "0,0", "550000,0", "jordbruk,annen")
    query = profile_query(p)
    assert "naering_type=jordbruk%2Cannen" in query
    assert profile_from(**dict(pair.split("=") for pair in query.replace("%2C", ",").split("&"))) == p


def test_links_without_business_income_stay_as_before() -> None:
    assert "naering" not in profile_query(profile_from(*FAMILY_ARGS))


def test_unknown_business_kind_is_annen_naering() -> None:
    (adult,) = profile_from(None, None, None, None, "400000", "hacker").adults
    assert (adult.business, adult.business_kind) == (400_000, "annen")


def test_flows_page_and_downloads() -> None:
    page = client.get("/flyt").text
    assert 'id="sankey"' in page and 'id="flyt-data"' in page
    assert 'aria-current="page"' in page  # the shared site nav marks where we are
    assert "Største økning" in page  # the tiles come with the page, not from JavaScript, so nothing jumps when it runs
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


def test_static_files_are_versioned_and_cached_for_good() -> None:
    html = client.get("/").text
    url = re.search(r'href="(/static/app\.css\?v=\w+)"', html)
    assert url, "pages link static files with a content hash"
    assert "immutable" in client.get(url[1]).headers["cache-control"]
    assert "immutable" not in client.get("/static/app.css").headers["cache-control"]  # an unversioned URL may change


def test_head_answers_like_get_without_a_body() -> None:
    for path in ("/", "/flyt", "/static/app.css", "/data/kommuner-2027.csv", "/api/openapi.json"):
        get, head = client.get(path), client.head(path)
        assert (head.status_code, head.headers["content-type"]) == (get.status_code, get.headers["content-type"]), path
        assert head.content == b"", path
    assert client.head("/finnes-ikke").status_code == 404
