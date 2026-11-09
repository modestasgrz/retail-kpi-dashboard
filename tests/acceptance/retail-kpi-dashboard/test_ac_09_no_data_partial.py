"""AC-09 — Given fixture F built, week 2011-09-05 has exactly one flag, no_data "No sales lines this week"; given fixture F plus one product line on 2011-12-07 12:00 (last line of the data), week 2011-12-05 has partial_week "Data ends 2011-12-07; the week is missing days", and week 2011-09-19 has no partial_week flag."""

from datetime import date, datetime
from pathlib import Path

from fixture import W0, W2, built, reasons, rules, scenario, week_row


def test_ac_09_no_data_partial(tmp_path: Path) -> None:
    out = built(tmp_path / "a")
    w0 = scenario(out, week=W0).selected
    assert rules(w0) == ["no_data"]
    assert reasons(w0)["no_data"] == "No sales lines this week"
    extra = [
        (
            "590001",
            "20001",
            "MUG RED",
            1,
            datetime(2011, 12, 7, 12),
            2.00,
            90001,
            "United Kingdom",
        )
    ]
    out2 = built(tmp_path / "b", extra)
    last = scenario(
        out2, week=date(2011, 12, 5), start=date(2011, 12, 5), end=date(2011, 12, 5)
    ).selected
    assert (
        reasons(last)["partial_week"]
        == "Data ends 2011-12-07; the week is missing days"
    )
    assert "partial_week" not in rules(week_row(out2, W2))
