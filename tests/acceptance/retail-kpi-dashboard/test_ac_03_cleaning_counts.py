"""AC-03 — Given fixture F built, when week 2011-09-19 is read, then the data-quality counts are duplicate 1, cancellation 1, adjustment 1, non-product 1, non-positive 1, and none of those lines adds to revenue, orders or units."""

from pathlib import Path

import pandas as pd
from fixture import W2, built, raw


def test_ac_03_cleaning_counts(tmp_path: Path) -> None:
    from kpi.data import clean

    out = built(tmp_path)
    lines = clean(raw())
    week = lines[
        (lines["InvoiceDate"] >= pd.Timestamp(W2))
        & (lines["InvoiceDate"] < pd.Timestamp(W2) + pd.Timedelta(days=7))
    ]
    counts = week["bucket"].value_counts().to_dict()
    assert counts == {
        "product": 6,
        "duplicate": 1,
        "cancellation": 1,
        "adjustment": 1,
        "non_product": 1,
        "non_positive": 1,
    }
    weekly = pd.read_parquet(out / "weekly.parquet")
    row = weekly[
        (pd.to_datetime(weekly["week_start"]) == pd.Timestamp(W2))
        & (weekly["filter"] == "All countries")
    ]
    assert len(row) == 1
    assert float(row["revenue"].iloc[0]) == 203.0
    assert int(row["orders"].iloc[0]) == 5
    assert int(row["units"].iloc[0]) == 50
