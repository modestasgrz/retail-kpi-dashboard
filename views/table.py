from collections.abc import Callable, Hashable
from typing import cast

import pandas as pd
import streamlit as st

from kpi.core import weekly_csv
from kpi.fmt import change, count, money, money2, pct, rounded
from kpi.models import FLAG_LABELS
from kpi.theme import GREEN, RED
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
    "The CSV holds raw numbers (2 decimals, no thousands separators) for spreadsheets; the screen uses £ and percentages. Changes are vs the previous week."
)
columns = {
    "Revenue": ("revenue", money),
    "Rev. change": ("revenue_wow", change),
    "Orders": ("orders", count),
    "Orders change": ("orders_wow", change),
    "Avg order": ("aov", money2),
    "Units": ("units", count),
    "Customers": ("customers", count),
    "New": ("new_customers", count),
    "Returning": ("returning_customers", count),
    "Cancel rate": ("cancellation_rate", pct),
    "Cancelled": ("cancelled_value", money),
    "After cancel.": ("net_revenue", money),
}
changes: list[Hashable] = ["Rev. change", "Orders change"]
table = pd.DataFrame(
    {
        "Week": [str(w.week_start) for w in s.weeks],
        "Flags": [", ".join(FLAG_LABELS[fl.rule] for fl in w.flags) for w in s.weeks],
        **{
            name: [getattr(w, key) for w in s.weeks]
            for name, (key, _) in columns.items()
        },
    }
)


def tone(value: object) -> str:
    """Green for a rise, red for a fall, as shown after rounding to 0.1."""
    if not isinstance(value, float) or pd.isna(value):
        return ""
    shown = rounded(value, "0.1")
    return f"color: {GREEN if shown > 0 else RED}" if shown else ""


st.dataframe(
    table.style.format(
        {
            name: cast(Callable[[object], str], fmt)
            for name, (_, fmt) in columns.items()
        },
        na_rep="n/a",
    ).map(tone, subset=changes),
    placeholder="n/a",
    hide_index=True,
    width="stretch",
    height=560,
    column_config={
        "Week": st.column_config.TextColumn(pinned=True),
        "Flags": st.column_config.TextColumn(width="large"),
    },
)
