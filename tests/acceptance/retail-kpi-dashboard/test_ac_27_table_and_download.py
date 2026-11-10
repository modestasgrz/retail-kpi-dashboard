"""AC-27 — Given the app on defaults, when Weekly table is opened, then it shows one dataframe with the last 8 weeks of the range (2011-10-17 .. 2011-12-05) and a download button with file name "weekly-kpis_2010-12-06_2011-12-05_all-countries.csv" whose CSV holds all 53 weeks; when the toggle `all_weeks` is switched on, the dataframe has 53 rows."""

import gc
from collections.abc import Iterator

import pytest
from fixture import app, download_file


@pytest.fixture
def no_gc() -> Iterator[None]:
    """The download is read from Streamlit's in-memory media storage, reachable only until a gc pass."""
    gc.disable()
    yield
    gc.enable()


def test_ac_27_table_and_download(no_gc: None) -> None:
    at = app()
    at.switch_page("views/table.py").run()
    assert not at.exception
    assert len(at.dataframe) == 1
    weeks = [str(w)[:10] for w in at.dataframe[0].value["Week"]]
    assert weeks == [
        "2011-10-17",
        "2011-10-24",
        "2011-10-31",
        "2011-11-07",
        "2011-11-14",
        "2011-11-21",
        "2011-11-28",
        "2011-12-05",
    ]
    buttons = at.get("download_button")
    assert len(buttons) == 1
    name, content = download_file(buttons[0])
    assert name == "weekly-kpis_2010-12-06_2011-12-05_all-countries.csv"
    text = content.decode("utf-8")
    assert text.startswith("week_start,revenue_gbp,")
    assert len(text.strip().splitlines()) == 54
    at.toggle(key="all_weeks").set_value(True).run()
    assert not at.exception
    assert len(at.dataframe[0].value) == 53
