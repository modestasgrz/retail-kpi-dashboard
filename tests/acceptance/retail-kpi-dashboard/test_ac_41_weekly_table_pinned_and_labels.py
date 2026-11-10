"""AC-41 — Given the app on defaults, when Weekly table is opened, then its dataframe's "Week" column is pinned, its columns are exactly ["Week", "Flags", "Net revenue", "Gross", "Orders", "Avg order (net)", "Units", "Customers", "New", "Returning", "Cancelled"], the "Flags" column holds the `FLAG_LABELS` labels joined by ", " (week 2011-12-05: "Partial week, Placed and cancelled"); when the toggle `changes` is switched on, the columns "Net vs last week", "Net vs last year" and "Orders vs last week" are added."""

import json

from fixture import app

COLUMNS = [
    "Week",
    "Flags",
    "Net revenue",
    "Gross",
    "Orders",
    "Avg order (net)",
    "Units",
    "Customers",
    "New",
    "Returning",
    "Cancelled",
]
CHANGES = ["Net vs last week", "Net vs last year", "Orders vs last week"]


def test_ac_41_weekly_table_pinned_and_labels() -> None:
    at = app()
    at.switch_page("views/table.py").run()
    assert not at.exception
    assert len(at.dataframe) == 1
    table = at.dataframe[0]
    assert json.loads(table.proto.columns)["Week"]["pinned"] is True
    df = table.value
    assert list(df.columns) == COLUMNS
    row = df[df["Week"].astype(str) == "2011-12-05"]
    assert row["Flags"].tolist() == ["Partial week, Placed and cancelled"]
    at.toggle(key="changes").set_value(True).run()
    assert not at.exception
    assert all(c in at.dataframe[0].value.columns for c in CHANGES)
