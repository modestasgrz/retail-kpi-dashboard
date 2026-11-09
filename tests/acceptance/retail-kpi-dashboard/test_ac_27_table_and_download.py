"""AC-27 — Given the app on defaults, Weekly table shows a dataframe with 53 rows and a download button with file name "weekly-kpis_2010-12-06_2011-12-05_all-countries.csv"."""

from fixture import app, download_file


def test_ac_27_table_and_download() -> None:
    at = app()
    at.switch_page("views/table.py").run()
    assert not at.exception
    assert [len(df.value) for df in at.dataframe] == [53]
    buttons = at.get("download_button")
    assert len(buttons) == 1
    name, content = download_file(buttons[0])
    assert name == "weekly-kpis_2010-12-06_2011-12-05_all-countries.csv"
    assert content.decode("utf-8").startswith("week_start,revenue_gbp,")
