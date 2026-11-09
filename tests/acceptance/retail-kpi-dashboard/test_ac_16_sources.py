"""AC-16 — Given fixture F built and week 2011-09-19, All countries, then scenario.sources["revenue"] = "sum(Quantity × Price) over 6 product lines, 2011-09-19..2011-09-25", and sources has a non-empty entry for each of the 10 card KPIs of DEC-11."""

from pathlib import Path

from fixture import built, scenario

KEYS = [
    "revenue",
    "orders",
    "aov",
    "units",
    "customers",
    "new_customers",
    "returning_customers",
    "cancellation_rate",
    "cancelled_value",
    "net_revenue",
]


def test_ac_16_sources(tmp_path: Path) -> None:
    s = scenario(built(tmp_path))
    assert (
        s.sources["revenue"]
        == "sum(Quantity × Price) over 6 product lines, 2011-09-19..2011-09-25"
    )
    for key in KEYS:
        assert s.sources.get(key, "").strip(), key
