"""The type scale: every text size on the site is one of six tokens, at weight 400 or 650 (docs/plan-density.md)."""

import re
from pathlib import Path

import pytest

WEB = Path(__file__).parent.parent / "src" / "adapters" / "web"
CSS = (WEB / "static" / "app.css").read_text()
TOKENS = ("display", "title", "heading", "body", "small", "chart")
TOKEN_DEF = re.compile(r"--t-(\w+):")


def _rules() -> list[str]:
    """Declarations outside the :root blocks that define the tokens."""
    return [d.strip() for d in re.split(r"[;{}]", CSS) if ":" in d and not TOKEN_DEF.search(d)]


def test_the_scale_has_exactly_the_six_tokens() -> None:
    assert tuple(TOKEN_DEF.findall(CSS)) == TOKENS


def test_every_font_size_is_a_token() -> None:
    sizes = [d for d in _rules() if d.startswith("font-size")]
    assert sizes
    bad = [d for d in sizes if not re.fullmatch(rf"font-size:\s*var\(--t-({'|'.join(TOKENS)})\)", d)]
    assert bad == []


def test_font_shorthand_only_inherits_or_uses_a_token() -> None:
    bad = [d for d in _rules() if re.match(r"font:", d) and not re.match(r"font:\s*(inherit|var\(--t-\w+\))", d)]
    assert bad == []


def test_only_two_weights() -> None:
    weights = {d.split(":", 1)[1].strip() for d in _rules() if d.startswith("font-weight")}
    assert weights <= {"400", "650"}
    # Browsers draw b, strong and th at 700 unless told otherwise
    assert re.search(r"^b, strong, h4, h5, h6, th \{ font-weight: 650; \}$", CSS, re.MULTILINE)


def test_grey_text_is_always_small() -> None:
    assert ".muted { color: var(--text-muted); font-size: var(--t-small); }" in CSS


def test_running_text_has_a_width_cap() -> None:
    assert re.search(r"^p, li \{ max-width: \d+ch; \}$", CSS, re.MULTILINE)


@pytest.mark.parametrize("path", sorted([*(WEB / "static").glob("*.js"), *(WEB / "templates").glob("*.html")]), ids=lambda p: p.name)
def test_no_sizes_outside_the_stylesheet(path: Path) -> None:
    if path.name.endswith(".min.js"):
        pytest.skip("vendored")
    text = path.read_text()
    assert not re.search(r"font-(size|weight)|fontSize|fontWeight", text), "set text sizes with a class from app.css"
