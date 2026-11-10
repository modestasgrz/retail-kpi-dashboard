from collections import Counter
from datetime import timedelta

import streamlit as st

from kpi.models import FLAG_LABELS
from views.ui import flag_line, header

GRAY = {"no_data", "partial_week"}

s = header("Flagged weeks")
if not s.flags:
    st.success(
        "No flagged weeks in the selected range.", icon=":material/check_circle:"
    )
else:
    counts = Counter(f.rule for f in s.flags)
    st.caption(
        " · ".join(f"{FLAG_LABELS[rule]}: {n}" for rule, n in counts.items()),
        help="Rules and thresholds: see Methodology & data. A flag asks for a look; it is not an error in the data.",
    )
    with st.container(key="flags"):
        for w in s.weeks:
            if not w.flags:
                continue
            with st.container(border=True):
                st.markdown(
                    f"**{w.week_start} – {w.week_start + timedelta(days=6)}** "
                    + " ".join(
                        f":{'gray' if f.rule in GRAY else 'orange'}-badge[{FLAG_LABELS[f.rule]}]"
                        for f in w.flags
                    )
                )
                st.markdown(
                    "\n".join(flag_line(f, "- **{label}:** {reason}") for f in w.flags)
                )
