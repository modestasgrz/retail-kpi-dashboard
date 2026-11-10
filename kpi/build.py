import argparse
import json
from datetime import timedelta
from pathlib import Path

import pandas as pd
from loguru import logger

from kpi.data import BUCKETS, PRODUCT_CODE, clean, read
from kpi.download import FILE_NAME, download
from kpi.models import ALL, FIRST_WEEK, LAST_WEEK, OUTSIDE_UK, UK

WEEKS = pd.date_range(FIRST_WEEK - timedelta(days=28), LAST_WEEK, freq="7D")
DQ_COLUMNS = [f"{b}_lines" for b in BUCKETS]


def weekly(lines: pd.DataFrame) -> pd.DataFrame:
    """Per-week KPI inputs (DEC-06) for the lines of one filter value, one row per week of WEEKS."""
    products = lines[lines["bucket"] == "product"]
    by_week = products.groupby("week")
    with_id = products[products["Customer ID"].notna()]
    new = with_id[with_id["first_week"] == with_id["week"]]
    cancels = lines[lines["bucket"] == "cancellation"]
    product_cancels = cancels[cancels["StockCode"].str.match(PRODUCT_CODE)]
    top = (
        products.sort_values(
            ["revenue", "InvoiceDate"], ascending=[False, True], kind="stable"
        )
        .drop_duplicates("week")
        .set_index("week")
    )
    out = pd.DataFrame(
        {
            "revenue": by_week["revenue"].sum(),
            "orders": by_week["Invoice"].nunique(),
            "units": by_week["Quantity"].sum(),
            "customers": with_id.groupby("week")["Customer ID"].nunique(),
            "new_customers": new.groupby("week")["Customer ID"].nunique(),
            "product_lines": by_week.size(),
            "lines_without_customer_id": products["Customer ID"]
            .isna()
            .groupby(products["week"])
            .sum(),
            "cancellation_invoices": cancels.groupby("week")["Invoice"].nunique(),
            "cancelled_value": -product_cancels.groupby("week")["revenue"].sum(),
            "product_cancellation_lines": product_cancels.groupby("week").size(),
            **{
                f"{b}_lines": lines[lines["bucket"] == b].groupby("week").size()
                for b in BUCKETS
            },
        }
    ).reindex(WEEKS)
    counts = [c for c in out.columns if c not in ("revenue", "cancelled_value")]
    out = out.fillna(0)
    out[counts] = out[counts].astype("int64")
    top = top.reindex(WEEKS)
    out["top_line_revenue"] = top["revenue"]
    out["top_line_description"] = top["Description"].fillna("")
    out["top_line_invoice"] = top["Invoice"].fillna("")
    out.index.name = "week_start"
    return out.reset_index()


def products(lines: pd.DataFrame) -> pd.DataFrame:
    """Revenue and units per week and StockCode; description = most frequent one in that week (ties: alphabetical)."""
    p = lines[lines["bucket"] == "product"]
    sums = p.groupby(["week", "StockCode"]).agg(
        revenue=("revenue", "sum"), units=("Quantity", "sum")
    )
    labels = (
        p.groupby(["week", "StockCode", "Description"])
        .size()
        .reset_index(name="n")
        .sort_values(
            ["week", "StockCode", "n", "Description"],
            ascending=[True, True, False, True],
        )
        .drop_duplicates(["week", "StockCode"])
        .set_index(["week", "StockCode"])["Description"]
    )
    out = sums.join(labels.rename("description")).reset_index()
    return out.rename(columns={"week": "week_start", "StockCode": "stock_code"})


def build(raw: pd.DataFrame, out_dir: Path) -> None:
    """Write weekly.parquet, products.parquet and meta.json (DEC-06). Customer ids never leave this function."""
    df = clean(raw)
    data_end = df["InvoiceDate"].max()
    df["week"] = df["InvoiceDate"].dt.normalize() - pd.to_timedelta(
        df["InvoiceDate"].dt.day_of_week, unit="D"
    )
    first_seen = (
        df[(df["bucket"] == "product") & df["Customer ID"].notna()]
        .groupby("Customer ID")["week"]
        .min()
    )
    df["first_week"] = pd.to_datetime(df["Customer ID"].map(first_seen.to_dict()))
    df = df[df["week"].isin(WEEKS)]
    countries = sorted(
        set(
            df.loc[
                (df["bucket"] == "product") & (df["week"] >= pd.Timestamp(FIRST_WEEK)),
                "Country",
            ]
        )
        - {UK, ""},
        key=str.casefold,
    )
    masks = {
        ALL: pd.Series(True, index=df.index),
        UK: df["Country"] == UK,
        OUTSIDE_UK: df["Country"] != UK,
        **{c: df["Country"] == c for c in countries},
    }
    weekly_parts, product_parts = [], []
    for name, mask in masks.items():
        lines = df[mask]
        weekly_parts.append(weekly(lines).assign(filter=name))
        product_parts.append(products(lines).assign(filter=name))
    out_dir.mkdir(parents=True, exist_ok=True)
    pd.concat(weekly_parts, ignore_index=True).to_parquet(
        out_dir / "weekly.parquet", index=False
    )
    pd.concat(product_parts, ignore_index=True).to_parquet(
        out_dir / "products.parquet", index=False
    )
    meta = {"data_end": data_end.isoformat(), "countries": list(masks)}
    (out_dir / "meta.json").write_text(json.dumps(meta, indent=1) + "\n")
    logger.info(
        "built {} filter values x {} weeks into {}", len(masks), len(WEEKS), out_dir
    )


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(
        description="Build the derived tables from the raw UCI workbook."
    )
    parser.add_argument("--raw", type=Path, default=Path("data/raw") / FILE_NAME)
    parser.add_argument("--out", type=Path, default=Path("data/derived"))
    args = parser.parse_args(argv)
    if not args.raw.exists():
        download(args.raw.parent)
    build(read(args.raw), args.out)


if __name__ == "__main__":
    main()
