from collections.abc import Callable
from typing import cast

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
columns = {
    "Revenue": ("revenue", money),
    "Revenue vs prev.": ("revenue_wow", change),
    "Orders": ("orders", count),
    "Orders vs prev.": ("orders_wow", change),
    "Avg order": ("aov", money2),
    "Units": ("units", count),
    "Customers": ("customers", count),
    "New": ("new_customers", count),
    "Returning": ("returning_customers", count),
    "Cancellation rate": ("cancellation_rate", pct),
    "Cancelled": ("cancelled_value", money),
    "After cancellations": ("net_revenue", money),
}
table = pd.DataFrame(
    {
        "Week": [str(w.week_start) for w in s.weeks],
        **{
            name: [getattr(w, key) for w in s.weeks]
            for name, (key, _) in columns.items()
        },
        "Flags": [", ".join(fl.rule for fl in w.flags) for w in s.weeks],
    }
)
st.dataframe(
    table.style.format(
        {
            name: cast(Callable[[object], str], fmt)
            for name, (_, fmt) in columns.items()
        },
        na_rep="n/a",
    ),
    placeholder="n/a",
    hide_index=True,
    width="stretch",
    height=560,
)
