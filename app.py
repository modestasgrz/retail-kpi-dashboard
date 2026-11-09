from datetime import date, timedelta
from pathlib import Path

import streamlit as st
from pydantic import ValidationError

from kpi.core import countries, run_scenario
from kpi.models import ALL, FIRST_WEEK, LAST_WEEK, MAX_DATE, OUTSIDE_UK, UK, Filters

PRESETS = {
    "Full year": (FIRST_WEEK, LAST_WEEK, ALL),
    "Q4 2011": (date(2011, 10, 3), LAST_WEEK, ALL),
    "UK only": (FIRST_WEEK, LAST_WEEK, UK),
    "Outside UK": (FIRST_WEEK, LAST_WEEK, OUTSIDE_UK),
}
CUSTOM = "Custom"
SUNDAY = timedelta(days=6)
cached_scenario = st.cache_data(show_spinner=False)(run_scenario)


def apply_preset() -> None:
    if st.session_state.preset == CUSTOM:
        return
    start, end, country = PRESETS[st.session_state.preset]
    st.session_state.dates = (start, end + SUNDAY)
    st.session_state.country = country
    st.session_state.pop("week", None)


def mark_custom() -> None:
    st.session_state.preset = CUSTOM


def reset() -> None:
    st.session_state.preset = "Full year"
    apply_preset()


st.set_page_config(
    page_title="Retail KPI dashboard", page_icon=":material/monitoring:", layout="wide"
)
st.html(
    f"<style>{(Path(__file__).parent / 'assets' / 'style.css').read_text()}</style>"
)
if "preset" not in st.session_state:
    reset()

pages = st.navigation(
    [
        st.Page(
            "views/overview.py",
            title="Overview",
            icon=":material/dashboard:",
            default=True,
        ),
        st.Page(
            "views/trends.py",
            title="Trends",
            icon=":material/show_chart:",
            url_path="trends",
        ),
        st.Page(
            "views/flags.py",
            title="Flagged weeks",
            icon=":material/flag:",
            url_path="flags",
        ),
        st.Page(
            "views/table.py",
            title="Weekly table",
            icon=":material/table_view:",
            url_path="table",
        ),
        st.Page(
            "views/methodology.py",
            title="Methodology & data",
            icon=":material/info:",
            url_path="methodology",
        ),
    ]
)

with st.sidebar:
    st.markdown("### Retail KPI dashboard")
    st.caption("Weekly review of a UK online giftware retailer, Dec 2010 – Dec 2011.")
    st.selectbox("Preset", [*PRESETS, CUSTOM], key="preset", on_change=apply_preset)
    st.date_input(
        "Date range (snaps to whole weeks)",
        min_value=FIRST_WEEK,
        max_value=MAX_DATE,
        key="dates",
        on_change=mark_custom,
        format="YYYY-MM-DD",
    )
    st.selectbox("Country", countries(), key="country", on_change=mark_custom)
    dates = st.session_state.dates
    if len(dates) != 2:
        st.error("Pick both a start and an end date.")
        st.stop()
    try:
        probe = Filters(
            start=dates[0],
            end=dates[1],
            country=st.session_state.country,
            week=dates[1],
        )
        weeks = cached_scenario(probe).weeks
    except ValidationError as err:
        st.error(str(err.errors()[0]["msg"]).removeprefix("Value error, "))
        st.stop()
    except ValueError as err:
        st.error(str(err))
        st.stop()
    options = [w.week_start for w in weeks]
    full = [
        w.week_start for w in weeks if "partial_week" not in {f.rule for f in w.flags}
    ]
    if st.session_state.get("week") not in options:
        st.session_state.week = (full or options)[-1]
    flagged = {w.week_start for w in weeks if w.flags}
    st.selectbox(
        "Week",
        options,
        key="week",
        format_func=lambda d: f"{d} – {d + SUNDAY}{'  ⚑' if d in flagged else ''}",
    )
    st.button("Reset to Full year", key="reset", on_click=reset, width="stretch")
    st.divider()
    st.caption("Data: UCI Online Retail II (Chen 2012), CC BY 4.0")

st.session_state.scenario = cached_scenario(
    probe.model_copy(update={"week": st.session_state.week})
)
pages.run()
