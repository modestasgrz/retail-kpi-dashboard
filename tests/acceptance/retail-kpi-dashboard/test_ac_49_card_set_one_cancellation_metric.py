"""AC-49 — Given the app on defaults, then the Overview has exactly 9 metrics labelled, in order, "Net revenue", "Orders", "Avg order (net)", "Gross revenue", "Units", "Customers", "New customers", "Returning customers", "Cancelled" (no "Cancellation rate" or "Revenue after cancellations" card); "Gross revenue" shows "£309 378"; "Cancelled" shows `money()` of the core's cancelled value with inverse delta colour and help ending with `sources["cancelled_value"]`."""

from datetime import date

from fixture import REPO, app, metric

S = "\u202f"
LABELS = [
    "Net revenue",
    "Orders",
    "Avg order (net)",
    "Gross revenue",
    "Units",
    "Customers",
    "New customers",
    "Returning customers",
    "Cancelled",
]


def test_ac_49_card_set_one_cancellation_metric() -> None:
    from streamlit.proto.Metric_pb2 import Metric

    from kpi.core import run_scenario
    from kpi.fmt import money
    from kpi.models import FIRST_WEEK, LAST_WEEK, Filters

    s = run_scenario(
        Filters(start=FIRST_WEEK, end=LAST_WEEK, week=date(2011, 11, 28)),
        REPO / "data" / "derived",
    )
    at = app()
    assert not at.exception
    assert [m.label for m in at.metric] == LABELS
    assert metric(at, "Gross revenue").value == f"£309{S}378"
    cancelled = metric(at, "Cancelled")
    assert cancelled.value == money(s.selected.cancelled_value)
    assert cancelled.proto.help.endswith(s.sources["cancelled_value"])
    # cancelled value fell vs 2011-11-21, so inverse colouring shows it as good
    assert s.selected.cancelled_value_wow is not None
    assert s.selected.cancelled_value_wow < 0
    assert cancelled.proto.color == Metric.MetricColor.Value("GREEN")
