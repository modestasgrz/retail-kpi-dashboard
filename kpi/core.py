import csv
import io
import json
from datetime import date, datetime, timedelta
from functools import lru_cache
from pathlib import Path
from typing import Any

import pandas as pd

from kpi.fmt import change, count, money, money2, pct, rounded
from kpi.models import (
    ALL,
    OUTSIDE_UK,
    UK,
    Filters,
    Flag,
    Ranked,
    Scenario,
    Summary,
    Totals,
    WeekRow,
)

DATA_DIR = Path(__file__).resolve().parents[1] / "data" / "derived"
SWING_PCT = 25.0
CANCEL_SHARE = 25.0
TOP_LINE_SHARE = 25.0
CSV_HEADER = [
    "week_start",
    "revenue_gbp",
    "orders",
    "aov_gbp",
    "units",
    "customers",
    "new_customers",
    "returning_customers",
    "cancellation_invoices",
    "cancellation_rate_pct",
    "cancelled_value_gbp",
    "net_revenue_gbp",
    "product_lines",
    "lines_without_customer_id",
    "revenue_wow_pct",
    "orders_wow_pct",
    "flags",
]
WOW = [
    "revenue",
    "orders",
    "aov",
    "units",
    "customers",
    "new_customers",
    "returning_customers",
    "cancelled_value",
    "net_revenue",
]


class Data:
    def __init__(self, data_dir: Path) -> None:
        self.weekly = pd.read_parquet(data_dir / "weekly.parquet")
        self.weekly["week_start"] = pd.to_datetime(self.weekly["week_start"]).dt.date
        self.products = pd.read_parquet(data_dir / "products.parquet")
        self.products["week_start"] = pd.to_datetime(
            self.products["week_start"]
        ).dt.date
        meta = json.loads((data_dir / "meta.json").read_text())
        self.data_end = datetime.fromisoformat(meta["data_end"])
        self.countries: list[str] = meta["countries"]
        summaries = data_dir / "summaries.json"
        self.summaries: dict[str, dict[str, str]] = (
            json.loads(summaries.read_text()) if summaries.exists() else {}
        )


@lru_cache(maxsize=8)
def load(data_dir: Path) -> Data:
    return Data(data_dir)


def countries(data_dir: Path = DATA_DIR) -> list[str]:
    return list(load(data_dir).countries)


def swing(value: float | None) -> bool:
    """|change rounded half-up to 0.1| ≥ 25.0 (DEC-08)."""
    return value is not None and abs(rounded(value, "0.1")) >= SWING_PCT


def wow(now: float | None, base: float | None) -> float | None:
    if now is None or not base:
        return None
    return (now - base) / base * 100


def derived(r: dict[str, Any]) -> dict[str, Any]:
    orders, cancels = int(r["orders"]), int(r["cancellation_invoices"])
    return {
        "revenue": float(r["revenue"]),
        "orders": orders,
        "aov": float(r["revenue"]) / orders if orders else None,
        "units": int(r["units"]),
        "customers": int(r["customers"]),
        "new_customers": int(r["new_customers"]),
        "returning_customers": int(r["customers"]) - int(r["new_customers"]),
        "cancellation_rate": 100 * cancels / (orders + cancels)
        if orders + cancels
        else None,
        "cancelled_value": float(r["cancelled_value"]),
        "net_revenue": float(r["revenue"]) - float(r["cancelled_value"]),
    }


def week_flags(
    week: date,
    r: dict[str, Any],
    kpis: dict[str, Any],
    prev: dict[str, Any],
    row: dict[str, Any],
    data_end: datetime,
) -> list[Flag]:
    """Flags of DEC-08, in rule order."""
    flags: list[tuple[str, str]] = []
    revenue = kpis["revenue"]
    if int(r["product_lines"]) == 0:
        flags.append(("no_data", "No sales lines this week"))
    if week <= data_end.date() < week + timedelta(days=6):
        flags.append(
            ("partial_week", f"Data ends {data_end.date()}; the week is missing days")
        )
    if swing(row["revenue_wow"]):
        flags.append(
            (
                "revenue_swing",
                f"Revenue {change(row['revenue_wow'])} vs previous week ({money(revenue)} vs {money(prev['revenue'])})",
            )
        )
    if swing(row["orders_wow"]):
        flags.append(
            (
                "orders_swing",
                f"Orders {change(row['orders_wow'])} vs previous week ({count(kpis['orders'])} vs {count(prev['orders'])})",
            )
        )
    if revenue > 0 and kpis["cancelled_value"] >= CANCEL_SHARE / 100 * revenue:
        share = 100 * kpis["cancelled_value"] / revenue
        flags.append(
            (
                "large_cancellations",
                f"{money(kpis['cancelled_value'])} cancelled against {money(revenue)} revenue ({pct(share)})",
            )
        )
    if revenue > 0 and 100 * float(r["top_line_revenue"]) / revenue > TOP_LINE_SHARE:
        share = 100 * float(r["top_line_revenue"]) / revenue
        flags.append(
            (
                "top_line",
                f"One line is {pct(share)} of revenue: {r['top_line_description']}, {money(float(r['top_line_revenue']))} (invoice {r['top_line_invoice']})",
            )
        )
    return [Flag(week_start=week, rule=rule, reason=reason) for rule, reason in flags]


def sources(row: WeekRow, r: dict[str, Any]) -> dict[str, str]:
    """Formula and inputs of each card KPI of the selected week (DEC-11)."""
    rng = f"{row.week_start}..{row.week_start + timedelta(days=6)}"
    lines = f"{count(row.product_lines)} product lines, {rng}"
    with_id = row.product_lines - row.lines_without_customer_id
    return {
        "revenue": f"sum(Quantity × Price) over {lines}",
        "orders": f"count of distinct invoices over {lines}",
        "aov": f"revenue {money2(row.revenue)} / orders {count(row.orders)}, {rng}",
        "units": f"sum(Quantity) over {lines}",
        "customers": f"count of distinct customer ids over the {count(with_id)} product lines that have one ({count(row.lines_without_customer_id)} have none), {rng}",
        "new_customers": f"customers whose first product line in the whole dataset falls in {rng}",
        "returning_customers": f"customers {count(row.customers)} − new customers {count(row.new_customers)}, {rng}",
        "cancellation_rate": f"cancellation invoices {count(row.cancellation_invoices)} / (orders {count(row.orders)} + cancellation invoices {count(row.cancellation_invoices)}) × 100, {rng}",
        "cancelled_value": f"−sum(Quantity × Price) over {count(int(r['cancellation_lines']))} cancellation lines with a product code, {rng}",
        "net_revenue": f"revenue {money(row.revenue)} − cancelled value {money(row.cancelled_value)}, {rng}",
    }


def ranked(rows: pd.DataFrame, label: str) -> list[Ranked]:
    rows = rows[rows["revenue"] > 0].sort_values(
        ["revenue", label], ascending=[False, True], kind="stable"
    )
    return [
        Ranked(label=str(r[label]), revenue=float(r["revenue"]))
        for _, r in rows.head(5).iterrows()
    ]


def run_scenario(filters: Filters, data_dir: Path = DATA_DIR) -> Scenario:
    """Every number the dashboard shows for these filters, computed once."""
    data = load(data_dir)
    if filters.country not in data.countries:
        raise ValueError(f"Unknown country: {filters.country}.")
    records = data.weekly[data.weekly["filter"] == filters.country].to_dict("records")
    table = {rec["week_start"]: {str(k): v for k, v in rec.items()} for rec in records}
    weeks: list[WeekRow] = []
    raw: dict[date, dict[str, Any]] = {}
    week = filters.start
    while week <= filters.end:
        r = table[week]
        prev = derived(table[week - timedelta(days=7)])
        kpis = derived(r)
        row: dict[str, Any] = {**kpis, "week_start": week}
        row.update({f"{k}_wow": wow(kpis[k], prev[k]) for k in WOW})
        rate, base = kpis["cancellation_rate"], prev["cancellation_rate"]
        row["cancellation_rate_change_pp"] = (
            rate - base if rate is not None and base is not None else None
        )
        row.update(
            {
                k: int(r[k])
                for k in (
                    "cancellation_invoices",
                    "product_lines",
                    "lines_without_customer_id",
                )
            }
        )
        row["flags"] = week_flags(week, r, kpis, prev, row, data.data_end)
        weeks.append(WeekRow(**row))
        raw[week] = r
        week += timedelta(days=7)
    selected = next(w for w in weeks if w.week_start == filters.week)
    flags = [f for w in weeks for f in w.flags]
    totals = Totals(
        revenue=sum(w.revenue for w in weeks),
        orders=sum(w.orders for w in weeks),
        units=sum(w.units for w in weeks),
        cancelled_value=sum(w.cancelled_value for w in weeks),
        net_revenue=sum(w.net_revenue for w in weeks),
        weeks=len(weeks),
        flagged_weeks=sum(1 for w in weeks if w.flags),
    )
    products = data.products[
        (data.products["filter"] == filters.country)
        & (data.products["week_start"] == filters.week)
    ]
    single = [c for c in data.countries if c not in (ALL, OUTSIDE_UK)]
    shown = {ALL: single, OUTSIDE_UK: [c for c in single if c != UK]}.get(
        filters.country, [filters.country]
    )
    by_country = data.weekly[
        (data.weekly["week_start"] == filters.week) & data.weekly["filter"].isin(shown)
    ]
    saved = data.summaries.get(str(filters.week)) if filters.country == ALL else None
    return Scenario(
        filters=filters,
        weeks=weeks,
        selected=selected,
        totals=totals,
        top_products=ranked(products, "description"),
        top_countries=ranked(by_country, "filter"),
        flags=flags,
        sources=sources(selected, raw[filters.week]),
        summary=Summary(**saved) if saved else None,
    )


def weekly_csv(scenario: Scenario) -> bytes:
    """The weekly KPI table of the range as UTF-8 CSV (DEC-12): raw numbers, 2 decimals, empty cell for n/a."""

    def num(value: float | None) -> str:
        return "" if value is None else f"{value:.2f}"

    out = io.StringIO()
    writer = csv.writer(out, lineterminator="\n")
    writer.writerow(CSV_HEADER)
    for w in scenario.weeks:
        writer.writerow(
            [
                w.week_start,
                num(w.revenue),
                w.orders,
                num(w.aov),
                w.units,
                w.customers,
                w.new_customers,
                w.returning_customers,
                w.cancellation_invoices,
                num(w.cancellation_rate),
                num(w.cancelled_value),
                num(w.net_revenue),
                w.product_lines,
                w.lines_without_customer_id,
                num(w.revenue_wow),
                num(w.orders_wow),
                "; ".join(f.rule for f in w.flags),
            ]
        )
    return out.getvalue().encode("utf-8")
