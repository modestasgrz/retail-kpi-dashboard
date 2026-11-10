from collections.abc import Callable, Hashable
from datetime import timedelta
from typing import cast

import pandas as pd
import streamlit as st

from kpi.core import weekly_csv
from kpi.fmt import change, count, money, rounded
from kpi.theme import BAD, GOOD
from views.ui import header, strip

SHORT = {
    "no_data": "No sales",
    "partial_week": "Partial",
    "revenue_swing": "Revenue",
    "orders_swing": "Orders",
    "large_cancellations": "Cancels",
    "top_line": "Big line",
    "placed_cancelled": "Placed+cancelled",
}

WIDTH = {
    "Net revenue": 84,
    "Gross": 72,
    "Orders": 54,
    "Avg order (net)": 100,
    "Units": 66,
    "Customers": 74,
    "New": 48,
    "Returning": 74,
    "Cancelled": 78,
}

s = header("Weekly table")
every = st.session_state.get("all_weeks", False) or len(s.weeks) <= 8
listed = s.weeks if every else s.weeks[-8:]
strip(
    "What are the exact weekly numbers?",
    f"Showing {'all' if every else 'the last 8'} of {len(s.weeks)} weeks, {listed[0].week_start} – {listed[-1].week_start + timedelta(days=6)}.",
    "Switch on Show changes for week and year comparisons; Download CSV has every week.",
)
f = s.filters
controls = st.columns([1, 1, 2], vertical_alignment="center")
all_weeks = controls[0].toggle("All weeks", key="all_weeks")
changes = controls[1].toggle("Show changes", key="changes")
controls[2].download_button(
    "Download CSV",
    weekly_csv(s),
    file_name=f"weekly-kpis_{f.start}_{f.end}_{f.country.lower().replace(' ', '-')}.csv",
    mime="text/csv",
    icon=":material/download:",
    help="Download every week in the range for a spreadsheet. Raw numbers (2 decimals, no thousands separators) for spreadsheets.",
)
weeks = s.weeks if all_weeks else s.weeks[-8:]
columns: dict[str, tuple[str, Callable[..., str]]] = {
    "Net revenue": ("net_revenue", money),
    "Net vs last week": ("net_revenue_wow", change),
    "Net vs last year": ("net_revenue_yoy", change),
    "Gross": ("revenue", money),
    "Orders": ("orders", count),
    "Orders vs last week": ("orders_wow", change),
    "Avg order (net)": ("net_aov", money),
    "Units": ("units", count),
    "Customers": ("customers", count),
    "New": ("new_customers", count),
    "Returning": ("returning_customers", count),
    "Cancelled": ("cancelled_value", money),
}
deltas: list[Hashable] = ["Net vs last week", "Net vs last year", "Orders vs last week"]
shown = {name: spec for name, spec in columns.items() if changes or name not in deltas}
table = pd.DataFrame(
    {
        "Week": [str(w.week_start) for w in weeks],
        "Flags": [", ".join(SHORT[fl.rule] for fl in w.flags) for w in weeks],
        **{name: [getattr(w, key) for w in weeks] for name, (key, _) in shown.items()},
    }
)


def tone(value: object) -> str:
    """Good/bad colour for a change, as shown after rounding to 0.1."""
    if not isinstance(value, float) or pd.isna(value):
        return ""
    shown = rounded(value, "0.1")
    return f"color: {GOOD if shown > 0 else BAD}" if shown else ""


styled = table.style.format(
    {name: cast(Callable[[object], str], fmt) for name, (_, fmt) in shown.items()},
    na_rep="n/a",
)
st.dataframe(
    styled.map(tone, subset=deltas) if changes else styled,
    placeholder="n/a",
    hide_index=True,
    width="stretch",
    height=min(560, 38 + 35 * len(table)),
    column_config={
        **{name: st.column_config.Column(width=WIDTH.get(name, 92)) for name in shown},
        "Week": st.column_config.TextColumn(pinned=True, width=80),
        "Flags": st.column_config.TextColumn(
            width=166,
            help="What was flagged that week, in short; full reasons are on Flagged weeks. Revenue / Orders = swing vs the 4-week average, Cancels = large cancellations, Big line = one big order, Placed+cancelled = an order cancelled the same week, Partial = partial week.",
        ),
    },
)
