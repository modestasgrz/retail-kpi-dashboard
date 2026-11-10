"""AC-50 — Given the app on defaults (week 2011-11-28, All countries), then the net revenue of the selected week is the same on every page: `money()` of the core value is the "Net revenue" metric value; the Trends revenue chart's first trace at 2011-11-28 equals the core float; and the Weekly table's "Net revenue" cell for 2011-11-28 equals the core float."""

import json
from datetime import date

import pytest
from fixture import REPO, app, metric


def test_ac_50_same_net_revenue_every_page() -> None:
    from kpi.core import run_scenario
    from kpi.fmt import money
    from kpi.models import FIRST_WEEK, LAST_WEEK, Filters

    s = run_scenario(
        Filters(start=FIRST_WEEK, end=LAST_WEEK, week=date(2011, 11, 28)),
        REPO / "data" / "derived",
    )
    net = s.selected.net_revenue
    at = app()
    assert metric(at, "Net revenue").value == money(net)
    at.switch_page("views/trends.py").run()
    chart = json.loads(at.get("plotly_chart")[0].proto.spec)
    main = chart["data"][0]
    xs = [str(x)[:10] for x in main["x"]]
    assert main["y"][xs.index("2011-11-28")] == pytest.approx(net)
    at.switch_page("views/table.py").run()
    df = at.dataframe[0].value
    row = df[df["Week"].astype(str).str[:10] == "2011-11-28"]
    assert row["Net revenue"].tolist() == pytest.approx([net])
