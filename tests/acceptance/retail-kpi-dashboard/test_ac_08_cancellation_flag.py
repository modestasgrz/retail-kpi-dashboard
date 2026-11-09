"""AC-08 — Given a week with revenue 100.00 and cancelled value 25.00, then it has large_cancellations "£25 cancelled against £100 revenue (25.0%)"; with cancelled value 24.99 it has no such flag."""

from datetime import date, datetime
from pathlib import Path

from fixture import built, reasons, week_row

WEEK = date(2011, 10, 3)


def lines(cancel_price: float) -> list[tuple[object, ...]]:
    return [
        (
            "600001",
            "30001",
            "VASE",
            4,
            datetime(2011, 10, 4, 10),
            25.00,
            91001,
            "United Kingdom",
        ),
        (
            "C600002",
            "30001",
            "VASE",
            -1,
            datetime(2011, 10, 5, 10),
            cancel_price,
            91001,
            "United Kingdom",
        ),
    ]


def test_ac_08_cancellation_flag(tmp_path: Path) -> None:
    hit = week_row(built(tmp_path / "a", lines(25.00)), WEEK)
    assert (
        reasons(hit)["large_cancellations"]
        == "£25 cancelled against £100 revenue (25.0%)"
    )
    miss = week_row(built(tmp_path / "b", lines(24.99)), WEEK)
    assert "large_cancellations" not in reasons(miss)
