from typing import Literal

import pandas as pd
import streamlit as st

from kpi.fmt import change, count, money, money2, pct, points
from kpi.models import ALL
from views.ui import header

s = header("Overview")
w = s.selected

if w.flags:
    for flag in w.flags:
        st.warning(
            f"**{flag.rule.replace('_', ' ').capitalize()}** · {flag.reason}",
            icon=":material/flag:",
        )
else:
    st.success("No flags this week.", icon=":material/check_circle:")

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
st.subheader("Selected week vs previous week")
for row in (cards[:5], cards[5:]):
    for col, (label, value, delta, key, color) in zip(st.columns(5), row, strict=True):
        col.metric(
            label,
            value,
            None if delta == "n/a" else delta,
            delta_color=color,
            help=s.sources[key],
        )
st.caption(
    "Hover the ⓘ on a card for its formula and inputs. A change shows n/a when the previous week had no base to compare with."
)

left, right = st.columns(2)
for col, title, rows in (
    (left, "Top 5 products", s.top_products),
    (right, "Top 5 countries", s.top_countries),
):
    with col:
        st.subheader(title)
        if rows:
            st.dataframe(
                pd.DataFrame(
                    {
                        "Name": [r.label for r in rows],
                        "Revenue": [money(r.revenue) for r in rows],
                    }
                ),
                hide_index=True,
                width="stretch",
            )
        else:
            st.caption("No sales this week.")

st.subheader("Weekly summary")
if s.filters.country != ALL:
    st.info(
        "The saved weekly summary covers all countries, so it is hidden while a country filter is on."
    )
elif s.summary is None:
    st.caption("No saved summary for this week (no sales).")
else:
    st.caption(
        "Weekly summary written by AI in an earlier run; every figure was checked against the computed numbers. This app makes no AI calls."
    )
    with st.container(border=True):
        st.markdown(f"**{s.summary.headline}**")
        st.markdown(s.summary.text)
