"""PlanX connected investment dashboard entrypoint.

The main dashboard lives in dashboard_v3.py. The source-based verification
panel is rendered immediately after it so the selected company can be reviewed
with official results and disclosures without inventing missing facts.
"""

from dashboard_v3 import render_research as render_dashboard
from verification_panel import render_verification_panel


def render_research(store, state, sample_mode):
    render_dashboard(store, state, sample_mode)
    render_verification_panel(store, state, sample_mode)


__all__ = ["render_research"]
