from collections import Counter

import pandas as pd
import streamlit as st

from views.ui import header

s = header("Flagged weeks")
if not s.flags:
    st.success(
        "No flagged weeks in the selected range.", icon=":material/check_circle:"
    )
else:
    counts = Counter(f.rule for f in s.flags)
    st.caption(
        " · ".join(f"{rule.replace('_', ' ')}: {n}" for rule, n in counts.items())
    )
    st.dataframe(
        pd.DataFrame(
            {
                "Week": [str(f.week_start) for f in s.flags],
                "Flag": [f.rule for f in s.flags],
                "Reason": [f.reason for f in s.flags],
            }
        ),
        hide_index=True,
        width="stretch",
        height=min(35 * len(s.flags) + 38, 640),
        column_config={"Reason": st.column_config.TextColumn(width="large")},
    )
st.caption(
    "Rules: see Methodology & data. A flag asks for a look; it is not an error in the data."
)
