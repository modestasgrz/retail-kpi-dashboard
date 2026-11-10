"""AC-36 — Given the app on defaults, when Trends is opened, then the segmented control `measure` shows "Net" and in each of the 4 charts the first trace's y value for week 2010-12-27 is null (a gap, not 0); the revenue chart's first trace is net revenue and has null at 2011-12-05; it has a trace named "Partial week" with `showlegend` false whose last x is 2011-12-05, marker symbol "circle-open" and marker colour `MUTED`; and an annotation with text "Partial · 35.7% cancelled"; when `measure` is "Gross", the first trace is gross revenue and the y-axis range ends below the partial week's £483 725."""

import json
from typing import Any

from fixture import REPO, app

S = "\u202f"


def at_week(trace: dict[str, Any], week: str) -> Any:
    xs = [str(x)[:10] for x in trace["x"]]
    return trace["y"][xs.index(week)]


def charts(at: Any) -> list[dict[str, Any]]:
    return [json.loads(c.proto.spec) for c in at.get("plotly_chart")]


def revenue_chart(at: Any) -> dict[str, Any]:
    return next(
        c for c in charts(at) if any(t.get("name") == "Partial week" for t in c["data"])
    )


def test_ac_36_trend_gaps_and_partial_week() -> None:
    from kpi.core import run_scenario
    from kpi.models import FIRST_WEEK, LAST_WEEK, Filters
    from kpi.theme import MUTED

    weeks = {
        str(w.week_start): w
        for w in run_scenario(
            Filters(start=FIRST_WEEK, end=LAST_WEEK, week=LAST_WEEK),
            REPO / "data" / "derived",
        ).weeks
    }
    at = app()
    at.switch_page("views/trends.py").run()
    assert not at.exception
    assert at.segmented_control(key="measure").value == "Net"
    found = charts(at)
    assert len(found) == 4
    for chart in found:
        assert at_week(chart["data"][0], "2010-12-27") is None
    revenue = revenue_chart(at)
    main = revenue["data"][0]
    assert at_week(main, "2011-12-05") is None
    assert at_week(main, "2011-11-28") == weeks["2011-11-28"].net_revenue
    partial = next(t for t in revenue["data"] if t.get("name") == "Partial week")
    assert partial.get("showlegend") is False
    assert str(partial["x"][-1])[:10] == "2011-12-05"
    assert partial["marker"]["symbol"] == "circle-open"
    assert partial["marker"]["color"] == MUTED
    texts = [a["text"] for a in revenue["layout"].get("annotations", [])]
    assert "Partial · 35.7% cancelled" in texts
    at.segmented_control(key="measure").set_value("Gross").run()
    assert not at.exception
    gross = revenue_chart(at)
    assert at_week(gross["data"][0], "2011-11-28") == weeks["2011-11-28"].revenue
    assert gross["layout"]["yaxis"]["range"][1] < weeks["2011-12-05"].revenue
