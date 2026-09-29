"""PlanX connected investment dashboard entrypoint.

The main research screen follows the approved 1→2→3→4 vertical scroll layout.
The source-based verification panel is rendered after the four screenshot-style
sections so official facts and missing evidence remain clearly separated.
"""

from dashboard_scroll_v4 import render_research as render_dashboard
from verification_panel import render_verification_panel


def render_research(store, state, sample_mode):
    render_dashboard(store, state, sample_mode)
    render_verification_panel(store, state, sample_mode)


__all__ = ["render_research"]
