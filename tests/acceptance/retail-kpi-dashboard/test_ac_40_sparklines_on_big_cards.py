"""AC-40 — Given the app on defaults, then the metrics "Net revenue", "Orders" and "Avg order (net)" have `chart_data` equal to the core's `net_revenue`, `orders` and `net_aov` for the 12 weeks ending at the selected week (2011-09-12 .. 2011-11-28; weeks with no value skipped), and the other 6 card metrics have no chart data; on preset "Q4 2011" the sparkline holds the 9 weeks 2011-10-03 .. 2011-11-28."""

from datetime import date

import pytest
from fixture import REPO, app, metric

BIG = {"Net revenue": "net_revenue", "Orders": "orders", "Avg order (net)": "net_aov"}
SMALL = [
    "Gross revenue",
    "Units",
    "Customers",
    "New customers",
    "Returning customers",
    "Cancelled",
]


def test_ac_40_sparklines_on_big_cards() -> None:
    from kpi.core import run_scenario
    from kpi.models import LAST_WEEK, Filters

    at = app()
    for preset, start, n in [
        ("Full year", date(2011, 9, 12), 12),
        ("Q4 2011", date(2011, 10, 3), 9),
    ]:
        at.selectbox(key="preset").select(preset).run()
        s = run_scenario(
            Filters(start=start, end=LAST_WEEK, week=date(2011, 11, 28)),
            REPO / "data" / "derived",
        )
        shown = [w for w in s.weeks if w.week_start <= date(2011, 11, 28)]
        assert len(shown) == n
        for label, key in BIG.items():
            expected = [getattr(w, key) for w in shown if getattr(w, key) is not None]
            assert list(metric(at, label).proto.chart_data) == pytest.approx(
                expected
            ), (preset, label)
        for label in SMALL:
            assert list(metric(at, label).proto.chart_data) == [], label
