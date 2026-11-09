"""Shared helpers for the retail-kpi-dashboard acceptance tests (DEC-01): fixture F (DEC-17) and AppTest access."""

import gc
from datetime import date, datetime
from pathlib import Path
from typing import Any

import pandas as pd

REPO = Path(__file__).resolve().parents[3]
APP = str(REPO / "app.py")
COLUMNS = [
    "Invoice",
    "StockCode",
    "Description",
    "Quantity",
    "InvoiceDate",
    "Price",
    "Customer ID",
    "Country",
]
NONE = float("nan")
UK = "United Kingdom"
W0, W1, W2 = date(2011, 9, 5), date(2011, 9, 12), date(2011, 9, 19)

LINES: list[tuple[Any, ...]] = [
    ("400001", "20001", "MUG RED", 1, datetime(2010, 1, 10, 9), 2.00, 90003, "France"),
    ("500001", "20001", "MUG RED", 10, datetime(2011, 9, 13, 10), 2.00, 90001, UK),
    ("500001", "20002", "MUG BLUE", 5, datetime(2011, 9, 13, 10), 4.00, 90001, UK),
    (
        "500002",
        "20001",
        "MUG RED",
        20,
        datetime(2011, 9, 14, 11),
        2.00,
        90003,
        "France",
    ),
    ("500003", "20001", "MUG RED", 30, datetime(2011, 9, 20, 9), 2.00, 90002, UK),
    ("500003", "20003", "LAMP", 2, datetime(2011, 9, 20, 9), 25.00, 90002, UK),
    ("500004", "20002", "MUG BLUE", 10, datetime(2011, 9, 21, 12), 4.00, 90004, UK),
    ("500004", "20002", "MUG BLUE", 10, datetime(2011, 9, 21, 12), 4.00, 90004, UK),
    ("500005", "20003", "LAMP", 1, datetime(2011, 9, 22, 12), 25.00, 90004, "France"),
    ("500006", "20002", "MUG BLUE", 5, datetime(2011, 9, 23, 15), 4.00, NONE, UK),
    ("C500007", "20003", "LAMP", -1, datetime(2011, 9, 24, 10), 25.00, 90002, UK),
    ("A500008", "B", "Adjust bad debt", 1, datetime(2011, 9, 24, 11), 100.00, NONE, UK),
    ("500009", "POST", "POSTAGE", 1, datetime(2011, 9, 24, 12), 15.00, 90004, "France"),
    ("500010", "20001", "MUG RED", 3, datetime(2011, 9, 25, 10), 0.00, 90001, UK),
    ("500011", "20002", "MUG BLUE", 2, datetime(2011, 9, 25, 11), 4.00, 90001, UK),
]


def raw(extra: list[tuple[Any, ...]] | None = None) -> pd.DataFrame:
    df = pd.DataFrame(LINES + (extra or []), columns=COLUMNS)
    df["Invoice"] = df["Invoice"].astype(str)
    df["StockCode"] = df["StockCode"].astype(str)
    return df


def built(tmp_path: Path, extra: list[tuple[Any, ...]] | None = None) -> Path:
    from kpi.build import build

    out = tmp_path / "derived"
    build(raw(extra), out)
    return out


def scenario(
    data_dir: Path,
    week: date = W2,
    country: str = "All countries",
    start: date = W0,
    end: date = W2,
) -> Any:
    from kpi.core import run_scenario
    from kpi.models import Filters

    return run_scenario(
        Filters(start=start, end=end, country=country, week=week), data_dir
    )


def week_row(data_dir: Path, week: date, country: str = "All countries") -> Any:
    s = scenario(data_dir, week=week, country=country)
    return s.selected


def rules(row: Any) -> list[str]:
    return [f.rule for f in row.flags]


def reasons(row: Any) -> dict[str, str]:
    return {f.rule: f.reason for f in row.flags}


def app() -> Any:
    from streamlit.testing.v1 import AppTest

    at = AppTest.from_file(APP, default_timeout=60)
    return at.run()


def metric(at: Any, label: str) -> Any:
    found = [m for m in at.metric if m.label == label]
    assert found, f"no metric labelled {label!r}; have {[m.label for m in at.metric]}"
    return found[0]


def texts(at: Any) -> str:
    """Every visible text element of the page and sidebar, joined."""
    parts: list[str] = []
    for kind in (
        "title",
        "header",
        "subheader",
        "markdown",
        "caption",
        "text",
        "info",
        "warning",
        "error",
        "success",
    ):
        parts.extend(str(e.value) for e in getattr(at, kind))
    return "\n".join(parts)


def download_file(button: Any) -> tuple[str, bytes]:
    """(file name, content) of an AppTest download button, read from the in-memory media storage."""
    from streamlit.runtime.media_file_manager import MediaFileManager
    from streamlit.runtime.media_file_storage import MediaFileStorageError

    file_id = button.proto.url.split("/")[-1].split(".")[0]
    for obj in gc.get_objects():
        if isinstance(obj, MediaFileManager):
            try:
                storage: Any = obj._storage
                f = storage.get_file(file_id)
            except MediaFileStorageError:
                continue
            return f.filename or "", f.content
    raise AssertionError("download not found in media storage")
