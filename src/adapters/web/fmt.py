"""Norwegian number formatting for templates: 2 286,8 mrd. kr, 1 200 kr, +5,7 %."""

__all__ = ["amount", "kr", "nb", "nb1", "num", "pct", "signed1", "signed_amount"]

NBSP = "\u00a0"


def _group(n: int) -> str:
    return f"{n:,}".replace(",", NBSP)


def nb(v: float) -> str:
    """Whole number with thin grouping: 405 677. No sign when the rounded value is 0."""
    r = round(abs(v))
    return ("−" if v < 0 and r else "") + _group(r)


def nb1(v: float) -> str:
    """One decimal with comma: 2 286,8. No sign when the rounded value is 0,0."""
    whole, frac = f"{abs(v):.1f}".split(".")
    minus = v < 0 and (int(whole) or int(frac))
    return ("−" if minus else "") + _group(int(whole)) + "," + frac


def num(v: float | None) -> str:
    """A number exactly as the source writes it: 6,52 stays 6,52; 1200 is 1 200."""
    if v is None:
        return ""
    if float(v).is_integer():
        return nb(v)
    whole, _, frac = f"{abs(v):.4f}".rstrip("0").partition(".")
    return ("−" if v < 0 else "") + _group(int(whole)) + ("," + frac if frac else "")


def kr(v: float) -> str:
    return nb(v) + NBSP + "kr"


def amount(bn: float) -> str:
    """Billions as mrd. kr, small amounts as mill. kr."""
    a = abs(bn)
    if a >= 1:
        return nb1(bn) + NBSP + "mrd." + NBSP + "kr"
    if a >= 0.001:
        return nb(bn * 1000) + NBSP + "mill." + NBSP + "kr"
    return kr(bn * 1e9)


def _sign(v: float) -> str:
    return "+" if v > 0 else "−" if v < 0 else "±"


def signed_amount(bn: float) -> str:
    return _sign(bn) + amount(abs(bn))


def signed1(v: float) -> str:
    """Sign follows the shown decimal, so 0,04 is ±0,0 and not +0,0."""
    return _sign(round(v, 1)) + nb1(abs(v))


def pct(v: float | None) -> str:
    return "" if v is None else _sign(round(v, 1)) + nb1(abs(v)) + NBSP + "%"
