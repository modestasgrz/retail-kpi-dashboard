from datetime import date, datetime
from pathlib import Path
from string import capwords

import pandas as pd
import pytest

from kpi import core
from kpi.build import build
from kpi.core import run_scenario
from kpi.data import COLUMNS
from kpi.models import FIRST_WEEK, LAST_WEEK, UK, Filters

W = date(2011, 9, 19)


def top_reason(tmp_path: Path, desc: str) -> str:
    rows = [("1", "20001", desc, 1, datetime(2011, 9, 20, 10), 10.0, 1.0, UK)]
    out = tmp_path / "d"
    build(pd.DataFrame(rows, columns=COLUMNS), out)
    s = run_scenario(Filters(start=W, end=W, country=UK, week=W), out)
    return next(f.reason for f in s.selected.flags if f.rule == "top_line")


@pytest.mark.parametrize(
    ("desc", "expected"),
    [
        ("white hanging heart", "White Hanging Heart"),
        ("WHITE HANGING HEART", "White Hanging Heart"),
        ("wHiTe HaNgInG hEaRt", "White Hanging Heart"),
        ("Already Title Case", "Already Title Case"),
        ("MEN'S WATCH", "Men's Watch"),
        ("CHILDREN'S APRON", "Children's Apron"),
        ("3 PIECE SET 12CM", "3 Piece Set 12cm"),
        ("RETROSPOT 2011", "Retrospot 2011"),
        ("CAFÉ ÉCLAIR ÑANDÚ", "Café Éclair Ñandú"),
        ("ΑΘΗΝΑ MUG", "Αθηνα Mug"),
    ],
)
def test_top_line_reason_title_cases_description(
    tmp_path: Path, desc: str, expected: str
) -> None:
    assert expected == capwords(desc)
    assert (
        top_reason(tmp_path, desc)
        == f"One line is 100.0% of revenue: {expected}, £10 (invoice 1)"
    )


def test_top_line_reason_title_cases_with_hyphen_and_slash(tmp_path: Path) -> None:
    assert (
        top_reason(tmp_path, "BLUE-GREEN MUG/CUP")
        == "One line is 100.0% of revenue: Blue-green Mug/cup, £10 (invoice 1)"
    )


def test_top_line_reason_real_data_contains_capwords_description() -> None:
    weekly = pd.read_parquet(core.DATA_DIR / "weekly.parquet")
    checked = 0
    for country in sorted(weekly["filter"].unique()):
        s = run_scenario(
            Filters(start=FIRST_WEEK, end=LAST_WEEK, country=country, week=LAST_WEEK),
            core.DATA_DIR,
        )
        by_week = {f.week_start: f.reason for f in s.flags if f.rule == "top_line"}
        rows = weekly[weekly["filter"] == country]
        for r in rows.to_dict("records"):
            reason = by_week.get(pd.Timestamp(r["week_start"]).date())
            if reason is None:
                continue
            assert capwords(r["top_line_description"]) in reason, (country, reason)
            checked += 1
    assert checked > 0
