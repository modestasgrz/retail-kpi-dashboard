"""AC-36 — Given the app on defaults, when Trends is opened, then in each of the 4 charts the first trace's y value for week 2010-12-27 is null (a gap, not 0), the revenue chart's first trace has null at 2011-12-05, the revenue chart has a trace named "Partial week" whose last x is 2011-12-05 and whose marker symbol is "circle-open", and the revenue chart has an annotation with text "Partial week, £172 782 cancelled (35.7%)"."""

import json
from typing import Any

from fixture import app

S = "\u202f"


def at_week(trace: dict[str, Any], week: str) -> Any:
    xs = [str(x)[:10] for x in trace["x"]]
    return trace["y"][xs.index(week)]


def test_ac_36_trend_gaps_and_partial_week() -> None:
    at = app()
    at.switch_page("views/trends.py").run()
    assert not at.exception
    charts = [json.loads(c.proto.spec) for c in at.get("plotly_chart")]
    assert len(charts) == 4
    for chart in charts:
        assert at_week(chart["data"][0], "2010-12-27") is None
    revenue = next(
        c for c in charts if any(t.get("name") == "Partial week" for t in c["data"])
    )
    assert at_week(revenue["data"][0], "2011-12-05") is None
    partial = next(t for t in revenue["data"] if t.get("name") == "Partial week")
    assert str(partial["x"][-1])[:10] == "2011-12-05"
    assert partial["marker"]["symbol"] == "circle-open"
    texts = [a["text"] for a in revenue["layout"].get("annotations", [])]
    assert f"Partial week, £172{S}782 cancelled (35.7%)" in texts
