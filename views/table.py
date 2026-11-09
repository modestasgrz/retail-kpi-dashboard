import pandas as pd
import streamlit as st

from kpi.core import weekly_csv
from kpi.fmt import change, count, money, money2, pct
from views.ui import header

s = header("Weekly table")
f = s.filters
st.download_button(
    "Download CSV",
    weekly_csv(s),
    file_name=f"weekly-kpis_{f.start}_{f.end}_{f.country.lower().replace(' ', '-')}.csv",
    mime="text/csv",
    icon=":material/download:",
)
st.caption(
    "The CSV holds raw numbers (2 decimals, no thousands separators) for spreadsheets; the screen uses £ and percentages."
)
st.dataframe(
    pd.DataFrame(
        {
            "Week": [str(w.week_start) for w in s.weeks],
            "Revenue": [money(w.revenue) for w in s.weeks],
            "Revenue vs prev.": [change(w.revenue_wow) for w in s.weeks],
            "Orders": [count(w.orders) for w in s.weeks],
            "Orders vs prev.": [change(w.orders_wow) for w in s.weeks],
            "Avg order": [money2(w.aov) for w in s.weeks],
            "Units": [count(w.units) for w in s.weeks],
            "Customers": [count(w.customers) for w in s.weeks],
            "New": [count(w.new_customers) for w in s.weeks],
            "Returning": [count(w.returning_customers) for w in s.weeks],
            "Cancellation rate": [pct(w.cancellation_rate) for w in s.weeks],
            "Cancelled": [money(w.cancelled_value) for w in s.weeks],
            "After cancellations": [money(w.net_revenue) for w in s.weeks],
            "Flags": [", ".join(fl.rule for fl in w.flags) for w in s.weeks],
        }
    ),
    hide_index=True,
    width="stretch",
    height=560,
)
