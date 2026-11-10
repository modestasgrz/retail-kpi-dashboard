from datetime import timedelta

import streamlit as st

from kpi.fmt import count, money
from kpi.models import Scenario


def header(title: str) -> Scenario:
    """Page title and the range line shared by every data page (DEC-18)."""
    s: Scenario = st.session_state.scenario
    f, t = s.filters, s.totals
    st.title(title)
    left, right = st.columns([4, 1], vertical_alignment="center")
    left.caption(
        f"Range {f.start} – {f.end + timedelta(days=6)} · revenue {money(t.revenue)} · orders {count(t.orders)} · flagged weeks {count(t.flagged_weeks)}"
    )
    with right.container(key="asof"):
        st.caption(f":green[●] Data as of {s.data_end}")
    return s
