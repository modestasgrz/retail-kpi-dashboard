from pathlib import Path

import pandas as pd

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
PRODUCT_CODE = r"^\d{5}[A-Za-z]*$"
BUCKETS = ["duplicate", "cancellation", "adjustment", "non_product", "non_positive"]


def read(path: Path) -> pd.DataFrame:
    """All sheets of the UCI workbook, concatenated."""
    sheets = pd.read_excel(
        path, sheet_name=None, dtype={"Invoice": str, "StockCode": str}
    )
    return pd.concat([sheet[COLUMNS] for sheet in sheets.values()], ignore_index=True)


def clean(raw: pd.DataFrame) -> pd.DataFrame:
    """One row per raw line with `bucket` (DEC-04, first match wins) and `revenue`."""
    df = raw[COLUMNS].copy()
    df["Invoice"] = df["Invoice"].astype(str)
    df["StockCode"] = df["StockCode"].astype(str)
    df["Description"] = df["Description"].fillna("").astype(str).str.strip()
    df["Country"] = df["Country"].fillna("").astype(str).str.strip()
    df["InvoiceDate"] = pd.to_datetime(df["InvoiceDate"])
    rules = [
        df.duplicated(subset=COLUMNS),
        df["Invoice"].str.startswith("C"),
        df["Invoice"].str.startswith("A"),
        ~df["StockCode"].str.match(PRODUCT_CODE),
        (df["Price"] <= 0) | (df["Quantity"] <= 0),
    ]
    df["bucket"] = "product"
    for name, mask in reversed(list(zip(BUCKETS, rules, strict=True))):
        df.loc[mask, "bucket"] = name
    df["revenue"] = df["Quantity"] * df["Price"]
    return df
