from collections.abc import Callable
from datetime import timedelta
from string import capwords
from typing import Literal, cast

import pandas as pd
import streamlit as st

from kpi.fmt import change, count, money, money2
from kpi.models import ALL, FLAG_LABELS, OUTSIDE_UK
from views.ui import flag_line, header, strip

LABEL = "Weekly summary written by AI in an earlier run; every figure was checked against the computed numbers. This app makes no AI calls."
AI = "AI-written summary, saved; numbers above are computed"
YEAR = timedelta(days=364)
PLAIN = {
    "net_revenue": "What the week's sales brought in after cancellations.",
    "orders": "How many separate orders customers placed.",
    "net_aov": "What an order was worth on average, after cancellations.",
    "revenue": "Sales before cancellations are taken off.",
    "units": "How many items were sold.",
    "customers": "How many different customers bought (only lines with a customer id count).",
    "new_customers": "Customers buying from the shop for the first time.",
    "returning_customers": "Customers who had bought before.",
    "cancelled_value": "The value of items cancelled this week; lower is better.",
}

s = header("Overview")
w = s.selected
strip(
    "How did the selected week go, and does anything need a look?",
    s.headline,
    "No sales this week. Pick another week in the sidebar."
    if w.product_lines == 0
    else f"Open Flag details below: {', '.join(FLAG_LABELS[f.rule] for f in w.flags)}."
    if w.flags
    else "Nothing flagged. Scan the top products and countries, then switch weeks in the sidebar.",
)

week, pill = st.columns([4, 1], vertical_alignment="center")
week.markdown(
    f"#### Week {w.week_start} – {w.week_start + timedelta(days=6)} · {s.filters.country}"
)
n = len(w.flags)
with pill.container(key="pill"):
    st.markdown(
        f":orange-badge[▲ {n} flag{'s' if n > 1 else ''}]"
        if n
        else ":green-badge[● All clear]"
    )
if n:
    with st.expander("Flag details"):
        st.markdown(
            "\n".join(flag_line(f, "- **{label}** · {reason}") for f in w.flags)
        )

recent = [x for x in s.weeks if x.week_start <= w.week_start][-12:]
base_week = w.week_start - YEAR
partial = any(f.rule == "partial_week" for f in w.flags)
big: list[
    tuple[
        str,
        str,
        str,
        float | None,
        float | None,
        float | None,
        Callable[[float], str],
    ]
] = [
    (
        "Net revenue",
        "net_revenue",
        money(w.net_revenue),
        w.net_revenue,
        w.net_revenue_wow,
        w.net_revenue_yoy,
        money,
    ),
    (
        "Orders",
        "orders",
        count(w.orders),
        w.orders,
        w.orders_wow,
        w.orders_yoy,
        lambda v: count(round(v)),
    ),
    (
        "Avg order (net)",
        "net_aov",
        money2(w.net_aov),
        w.net_aov,
        w.net_aov_wow,
        w.net_aov_yoy,
        money2,
    ),
]
with st.container(key="big"):
    for col, (label, k, text, value, wow, yoy, fmt) in zip(
        st.columns(3, gap="small"), big, strict=True
    ):
        delta = change(wow)
        col.metric(
            label,
            text,
            delta,
            delta_color="off" if delta == "n/a" else "normal",
            delta_arrow="off" if delta == "n/a" else "auto",
            delta_description="vs last week",
            help=f"{PLAIN[k]}\n\n{s.sources[k]}",
            chart_data=[v for x in recent if (v := getattr(x, k)) is not None],
            chart_type="area",
        )
        when = f"{base_week} – {base_week + timedelta(days=6)}"
        if yoy is None or value is None:
            why = (
                "this week is partial, so there is no like-for-like base"
                if partial
                else "no sales this week"
                if w.product_lines == 0
                else f"{when} had no sales or a zero or negative value"
            )
            col.caption(
                "— vs same week last year",
                help=f"There is no fair comparison with last year for this week: {why}.",
            )
        else:
            col.caption(
                f"{change(yoy)} vs same week last year",
                help=f"How this week compares with the same week a year ago. Same week a year earlier: {when}"
                + (f", {fmt(value / (1 + yoy / 100))}." if yoy != -100 else "."),
            )

small: list[tuple[str, str, str, str, Literal["normal", "inverse"]]] = [
    ("Gross revenue", money(w.revenue), change(w.revenue_wow), "revenue", "normal"),
    ("Units", count(w.units), change(w.units_wow), "units", "normal"),
    ("Customers", count(w.customers), change(w.customers_wow), "customers", "normal"),
    (
        "New customers",
        count(w.new_customers),
        change(w.new_customers_wow),
        "new_customers",
        "normal",
    ),
    (
        "Returning customers",
        count(w.returning_customers),
        change(w.returning_customers_wow),
        "returning_customers",
        "normal",
    ),
    (
        "Cancelled",
        money(w.cancelled_value),
        change(w.cancelled_value_wow),
        "cancelled_value",
        "inverse",
    ),
]
with st.container(key="small"):
    for col, (label, value_text, delta, k, color) in zip(
        st.columns(len(small), gap="small"), small, strict=True
    ):
        none = delta == "n/a"
        col.metric(
            label,
            value_text,
            delta,
            delta_color="off" if none else color,
            delta_arrow="off" if none else "auto",
            help=f"{PLAIN[k]}\n\n{s.sources[k]}",
        )

lists = [("Top 5 products", s.top_products, capwords)] + (
    [("Top 5 countries", s.top_countries, str)]
    if s.filters.country in (ALL, OUTSIDE_UK)
    else []
)
for col, (title, rows, name) in zip(st.columns(2), lists, strict=False):
    with col:
        st.subheader(title)
        if rows:
            shares = [100 * r.revenue / w.revenue for r in rows]
            st.dataframe(
                pd.DataFrame(
                    {
                        "Name": [name(r.label) for r in rows],
                        "Revenue": [r.revenue for r in rows],
                        "Share of week": shares,
                    }
                ).style.format({"Revenue": cast(Callable[[object], str], money)}),
                hide_index=True,
                width="stretch",
                column_config={
                    "Name": st.column_config.TextColumn(width=215),
                    "Revenue": st.column_config.Column(width=78),
                    "Share of week": st.column_config.ProgressColumn(
                        format="%.1f%%",
                        min_value=0,
                        max_value=max(shares),
                        width=95,
                        help="How much of the week's sales each one brought in. Share of the week's gross revenue; the longest bar is the largest share.",
                    ),
                },
            )
        else:
            st.caption("No sales this week.")

if s.filters.country != ALL:
    st.caption(
        "The saved weekly summary covers all countries, so it is hidden while a country filter is on."
    )
elif s.summary is None:
    st.caption("No saved summary for this week (no sales).")
else:
    with st.expander(AI):
        st.caption(LABEL)
        st.markdown(f"**{s.summary.headline.replace('"', '')}**")
        st.markdown(s.summary.text.replace('"', ""))
