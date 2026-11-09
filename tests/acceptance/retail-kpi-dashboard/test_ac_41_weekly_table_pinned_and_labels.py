"""AC-41 — Given the app on defaults, when Weekly table is opened, then its dataframe's "Week" column is pinned, it has a "Flags" column holding the `FLAG_LABELS` labels joined by ", " (week 2011-12-05: "Partial week, Revenue swing, Large cancellations, One big order"), and it still has 53 rows."""

import json

from fixture import app


def test_ac_41_weekly_table_pinned_and_labels() -> None:
    at = app()
    at.switch_page("views/table.py").run()
    assert not at.exception
    assert len(at.dataframe) == 1
    table = at.dataframe[0]
    assert json.loads(table.proto.columns)["Week"]["pinned"] is True
    df = table.value
    assert len(df) == 53
    row = df[df["Week"].astype(str) == "2011-12-05"]
    assert row["Flags"].tolist() == [
        "Partial week, Revenue swing, Large cancellations, One big order"
    ]
