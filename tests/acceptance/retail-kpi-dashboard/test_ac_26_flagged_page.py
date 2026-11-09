"""AC-26 — Given the app on defaults, Flagged weeks has a table row for 2011-12-05 whose reasons include "Data ends 2011-12-09; the week is missing days" and "£172 782 cancelled against £483 725 revenue (35.7%)"."""

from fixture import app

S = "\u202f"


def test_ac_26_flagged_page() -> None:
    at = app()
    at.switch_page("views/flags.py").run()
    assert not at.exception
    rows = [
        r
        for df in at.dataframe
        for r in df.value.astype(str).agg(" | ".join, axis=1).tolist()
        if "2011-12-05" in r
    ]
    assert rows, "no row for 2011-12-05"
    joined = " ".join(rows)
    assert "Data ends 2011-12-09; the week is missing days" in joined
    assert f"£172{S}782 cancelled against £483{S}725 revenue (35.7%)" in joined
