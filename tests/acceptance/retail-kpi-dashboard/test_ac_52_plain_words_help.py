"""AC-52 — Given the app on defaults, then the help of each of the 9 Overview metrics is its DEC-31 plain sentence, a blank line, then the core's `sources[key]`, and the plain sentence has no formula characters ("×", "−", "/", "sum(")."""

from datetime import date

from fixture import REPO, app, metric

PLAIN = {
    "Net revenue": (
        "net_revenue",
        "What the week's sales brought in after cancellations.",
    ),
    "Orders": ("orders", "How many separate orders customers placed."),
    "Avg order (net)": (
        "net_aov",
        "What an order was worth on average, after cancellations.",
    ),
    "Gross revenue": ("revenue", "Sales before cancellations are taken off."),
    "Units": ("units", "How many items were sold."),
    "Customers": (
        "customers",
        "How many different customers bought (only lines with a customer id count).",
    ),
    "New customers": (
        "new_customers",
        "Customers buying from the shop for the first time.",
    ),
    "Returning customers": ("returning_customers", "Customers who had bought before."),
    "Cancelled": (
        "cancelled_value",
        "The value of items cancelled this week; lower is better.",
    ),
}


def test_ac_52_plain_words_help() -> None:
    from kpi.core import run_scenario
    from kpi.models import FIRST_WEEK, LAST_WEEK, Filters

    s = run_scenario(
        Filters(start=FIRST_WEEK, end=LAST_WEEK, week=date(2011, 11, 28)),
        REPO / "data" / "derived",
    )
    at = app()
    for label, (key, plain) in PLAIN.items():
        assert metric(at, label).proto.help == f"{plain}\n\n{s.sources[key]}", label
        for mark in ("×", "−", "/", "sum("):
            assert mark not in plain, (label, mark)
