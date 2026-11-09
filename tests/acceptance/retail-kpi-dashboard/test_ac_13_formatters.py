"""AC-13 — money(483725.4) "£483 725", money(0.5) "£1", money2(950.336) "£950.34", count(17225) "17 225", pct(16.66667) "16.7%", change(153.75) "+153.8%", change(-23.15) "-23.2%", change(0.0) "+0.0%", change(None) "n/a", points(-1.25) "-1.3 pp"; thousands separator U+202F."""

S = "\u202f"


def test_ac_13_formatters() -> None:
    from kpi.fmt import change, count, money, money2, pct, points

    assert money(483725.4) == f"£483{S}725"
    assert money(0.5) == "£1"
    assert money2(950.336) == "£950.34"
    assert count(17225) == f"17{S}225"
    assert pct(16.66667) == "16.7%"
    assert change(153.75) == "+153.8%"
    assert change(-23.15) == "-23.2%"
    assert change(0.0) == "+0.0%"
    assert change(None) == "n/a"
    assert points(-1.25) == "-1.3 pp"
