"""AC-35 — Given the committed data, then `run_scenario(...).data_end` is 2011-12-09, and `kpi.models.FLAG_LABELS` is exactly {no_data: "No sales", partial_week: "Partial week", revenue_swing: "Revenue swing", orders_swing: "Orders swing", large_cancellations: "Large cancellations", top_line: "One big order"}."""

from datetime import date
from typing import Any

from fixture import REPO


def test_ac_35_data_end_and_flag_labels() -> None:
    import kpi.models
    from kpi.core import run_scenario
    from kpi.models import FIRST_WEEK, LAST_WEEK, Filters

    labels: dict[str, str] = vars(kpi.models)["FLAG_LABELS"]

    s: Any = run_scenario(
        Filters(start=FIRST_WEEK, end=LAST_WEEK, week=date(2011, 11, 28)),
        REPO / "data" / "derived",
    )
    assert s.data_end == date(2011, 12, 9)
    assert labels == {
        "no_data": "No sales",
        "partial_week": "Partial week",
        "revenue_swing": "Revenue swing",
        "orders_swing": "Orders swing",
        "large_cancellations": "Large cancellations",
        "top_line": "One big order",
    }
