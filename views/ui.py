from datetime import timedelta

import streamlit as st

from kpi.fmt import count, money
from kpi.models import Scenario


def header(title: str) -> Scenario:
    """Page title, the filter line and the range strip shared by every data page (AC-21)."""
    s: Scenario = st.session_state.scenario
    f = s.filters
    st.title(title)
    st.caption(
        f"{f.country} · weeks {f.start} – {f.end + timedelta(days=6)} ({s.totals.weeks} weeks) · selected week {f.week} – {f.week + timedelta(days=6)}"
    )
    with st.container(key="strip"):
        a, b, c = st.columns(3)
        a.metric(
            "Range revenue",
            money(s.totals.revenue),
            help="Sum of weekly product revenue over the selected weeks",
        )
        b.metric(
            "Range orders",
            count(s.totals.orders),
            help="Sum of weekly orders over the selected weeks",
        )
        c.metric(
            "Flagged weeks",
            count(s.totals.flagged_weeks),
            help="Weeks in range with at least one flag (see Flagged weeks)",
        )
    return s
