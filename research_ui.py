"""PlanX connected investment dashboard entrypoint.

The implementation lives in dashboard_v3.py so the main app can keep a stable
import path while the dashboard layout evolves independently.
"""

from dashboard_v3 import render_research

__all__ = ["render_research"]
