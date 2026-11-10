"""AC-28 — Given the app, when Methodology & data is opened, then it shows "Chen, D. (2012)", "CC BY 4.0", "https://doi.org/10.24432/C5CG6D", the label and formula of each of the 9 card KPIs of DEC-11, each flag rule of DEC-08, the sentences "All figures come from real public data; nothing in this app is synthetic." and "Net revenue is revenue minus cancelled value; it is the headline figure on every page.", the placed-and-cancelled matching rule (text contains "same week, same stock code, same customer and same price") and the driver formula (text contains "contribution"); and the sidebar of every page shows "Data: UCI Online Retail II (Chen 2012), CC BY 4.0"."""

from fixture import app, texts

PAGES = [
    "views/overview.py",
    "views/trends.py",
    "views/flags.py",
    "views/table.py",
    "views/methodology.py",
]
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
RULES = [
    "no_data",
    "partial_week",
    "revenue_swing",
    "orders_swing",
    "large_cancellations",
    "top_line",
    "placed_cancelled",
]


def test_ac_28_methodology_attribution() -> None:
    at = app()
    at.switch_page("views/methodology.py").run()
    assert not at.exception
    page = (
        texts(at)
        + "\n"
        + "\n".join(str(df.value.to_csv()) for df in at.dataframe)
        + "\n"
        + "\n".join(str(t.value) for t in at.table)
    )
    for needle in [
        "Chen, D. (2012)",
        "CC BY 4.0",
        "https://doi.org/10.24432/C5CG6D",
        "All figures come from real public data; nothing in this app is synthetic.",
        "Net revenue is revenue minus cancelled value; it is the headline figure on every page.",
        "same week, same stock code, same customer and same price",
        "contribution",
        "sum(Quantity × Price)",
    ]:
        assert needle in page, needle
    for label in LABELS + RULES:
        assert label in page, label
    for path in PAGES:
        at.switch_page(path).run()
        assert "Data: UCI Online Retail II (Chen 2012), CC BY 4.0" in texts(
            at.sidebar
        ), path
