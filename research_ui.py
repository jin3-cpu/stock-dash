"""PlanX connected investment dashboard entrypoint.

The main research screen follows the approved 1→2→3→4 vertical scroll layout.
The source-based verification panel is rendered after the four screenshot-style
sections so official facts and missing evidence remain clearly separated.
"""

import streamlit as st

from dashboard_scroll_v4 import render_research as render_dashboard
from verification_panel import render_verification_panel


# app.py still contains a legacy HBM navigation entry. Filter that legacy item at
# the shared Streamlit radio boundary so it cannot appear or be selected while
# the rest of the app is migrated without disrupting the current deployment.
if st.session_state.get("nav_choice") == "후공정 · HBM":
    st.session_state["nav_choice"] = "오늘의 투자판단"

if not getattr(st.radio, "_planx_sidebar_filtered", False):
    _streamlit_radio = st.radio

    def _planx_radio(label, options, *args, **kwargs):
        if label == "메뉴":
            options = [item for item in options if item != "후공정 · HBM"]
        return _streamlit_radio(label, options, *args, **kwargs)

    _planx_radio._planx_sidebar_filtered = True
    st.radio = _planx_radio


def render_research(store, state, sample_mode):
    render_dashboard(store, state, sample_mode)
    render_verification_panel(store, state, sample_mode)


__all__ = ["render_research"]
