"""AC-10 — Given fixture F built, week 2011-09-19 has top_line "One line is 29.6% of revenue: MUG RED, £60 (invoice 500003)"; a week whose largest line is exactly 25.0% of revenue has no top_line flag."""

from datetime import date, datetime
from pathlib import Path

from fixture import built, reasons, scenario, week_row


def test_ac_10_top_line_flag(tmp_path: Path) -> None:
    assert (
        reasons(scenario(built(tmp_path / "a")).selected)["top_line"]
        == "One line is 29.6% of revenue: MUG RED, £60 (invoice 500003)"
    )
    quarter = [
        (
            f"60010{i}",
            f"3000{i}",
            f"ITEM {i}",
            1,
            datetime(2011, 10, 4, 10 + i),
            10.00,
            91001,
            "United Kingdom",
        )
        for i in range(4)
    ]
    row = week_row(built(tmp_path / "b", quarter), date(2011, 10, 3))
    assert "top_line" not in reasons(row)
