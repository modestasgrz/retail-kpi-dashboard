"""AC-01 — Given fixture F, when `build(raw, out_dir)` runs, then out_dir holds weekly.parquet, products.parquet and meta.json, no file has a column named `Customer ID`, and none of the fixture customer ids (90001-90004) appears as a value in any file."""

import json
from pathlib import Path

import pandas as pd
from fixture import built


def test_ac_01_build_outputs(tmp_path: Path) -> None:
    out = built(tmp_path)
    names = {p.name for p in out.iterdir()}
    assert {"weekly.parquet", "products.parquet", "meta.json"} <= names
    ids = {"90001", "90002", "90003", "90004"}
    for name in ("weekly.parquet", "products.parquet"):
        df = pd.read_parquet(out / name)
        assert "Customer ID" not in df.columns
        values = {
            str(v).removesuffix(".0") for col in df.columns for v in df[col].tolist()
        }
        assert not ids & values, name
    meta = (out / "meta.json").read_text()
    json.loads(meta)
    assert not any(i in meta for i in ids)
