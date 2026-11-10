"""AC-16 — Given fixture F built and week 2011-09-19, All countries, then `scenario.sources["revenue"]` = "sum(Quantity × Price) over 6 product lines, 2011-09-19..2011-09-25", and `scenario.sources` has a non-empty entry for each of the 9 card KPIs of DEC-11 (round 3), and `sources["cancelled_value"]` contains "12.3% of gross revenue" and "cancellation rate 16.7%"."""

from pathlib import Path

from fixture import built, scenario

KEYS = [
    "revenue",
    "orders",
    "units",
    "customers",
    "new_customers",
    "returning_customers",
    "cancelled_value",
    "net_revenue",
    "net_aov",
]


def test_ac_16_sources(tmp_path: Path) -> None:
    s = scenario(built(tmp_path))
    assert (
        s.sources["revenue"]
        == "sum(Quantity × Price) over 6 product lines, 2011-09-19..2011-09-25"
    )
    for key in KEYS:
        assert s.sources.get(key, "").strip(), key
    assert len(KEYS) == 9
    assert "12.3% of gross revenue" in s.sources["cancelled_value"]
    assert "cancellation rate 16.7%" in s.sources["cancelled_value"]
