from collections.abc import Callable
from datetime import timedelta
from string import capwords
from typing import Literal, cast

import pandas as pd
import streamlit as st

from kpi.fmt import change, count, money, money2, pct, points
from kpi.models import ALL, FLAG_LABELS
from views.ui import header

LABEL = "Weekly summary written by AI in an earlier run; every figure was checked against the computed numbers. This app makes no AI calls."

s = header("Overview")
w = s.selected
if s.filters.country == ALL and s.summary is not None:
    st.markdown(s.summary.headline.replace('"', ""))
    st.caption(LABEL)

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
            "\n".join(f"- **{FLAG_LABELS[f.rule]}** · {f.reason}" for f in w.flags)
        )

recent = [x for x in s.weeks if x.week_start <= w.week_start][-12:]
cards: list[tuple[str, str, str, str, Literal["normal", "inverse"]]] = [
    ("Revenue", money(w.revenue), change(w.revenue_wow), "revenue", "normal"),
    ("Orders", count(w.orders), change(w.orders_wow), "orders", "normal"),
    ("Average order value", money2(w.aov), change(w.aov_wow), "aov", "normal"),
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
        "Cancellation rate",
        pct(w.cancellation_rate),
        points(w.cancellation_rate_change_pp),
        "cancellation_rate",
        "inverse",
    ),
    (
        "Cancelled value",
        money(w.cancelled_value),
        change(w.cancelled_value_wow),
        "cancelled_value",
        "inverse",
    ),
    (
        "Revenue after cancellations",
        money(w.net_revenue),
        change(w.net_revenue_wow),
        "net_revenue",
        "normal",
    ),
]
for key, row in (("big", cards[:3]), ("small", cards[3:])):
    with st.container(key=key):
        for col, (label, value, delta, k, color) in zip(
            st.columns(len(row), gap="small"), row, strict=True
        ):
            none = delta == "n/a"
            col.metric(
                label,
                value,
                delta,
                delta_color="off" if none else color,
                delta_arrow="off" if none else "auto",
                help=s.sources[k],
                chart_data=[v for x in recent if (v := getattr(x, k)) is not None]
                if key == "big"
                else None,
                chart_type="line",
            )
st.caption(
    f"Changes are vs the previous week; the lines show the last {len(recent)} week{'s' if len(recent) > 1 else ''} in range. Hover the ? on a card for its formula and inputs. A change shows n/a when the previous week had no base to compare with."
)

left, right = st.columns(2)
for col, title, rows, name in (
    (left, "Top 5 products", s.top_products, capwords),
    (right, "Top 5 countries", s.top_countries, str),
):
    with col:
        st.subheader(title)
        if rows:
            st.dataframe(
                pd.DataFrame(
                    {
                        "Name": [name(r.label) for r in rows],
                        "Revenue": [r.revenue for r in rows],
                        "Share of week": [100 * r.revenue / w.revenue for r in rows],
                    }
                ).style.format({"Revenue": cast(Callable[[object], str], money)}),
                hide_index=True,
                width="stretch",
                column_config={
                    "Name": st.column_config.TextColumn(width=205),
                    "Revenue": st.column_config.Column(width=80),
                    "Share of week": st.column_config.ProgressColumn(
                        format="%.1f%%", min_value=0, max_value=100, width=112
                    ),
                },
            )
        else:
            st.caption("No sales this week.")

if s.filters.country != ALL:
    st.info(
        "The saved weekly summary covers all countries, so it is hidden while a country filter is on."
    )
elif s.summary is None:
    st.caption("No saved summary for this week (no sales).")
else:
    with st.expander("Full weekly summary"):
        st.caption(LABEL)
        st.markdown(f"**{s.summary.headline.replace('"', '')}**")
        st.markdown(s.summary.text.replace('"', ""))
