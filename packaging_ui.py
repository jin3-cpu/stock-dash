"""Legacy semiconductor back-end/HBM screen.

The dedicated sidebar entry has been retired. Existing sessions that still point
at this page are redirected to the main PlanX investment dashboard.
"""
import pandas as pd
import streamlit as st

PACKAGING_STOCKS = [
    {"code": "042700", "name": "한미반도체", "chain": "HBM TC 본더", "focus": "HBM4·Wide TC·하이브리드 본딩"},
    {"code": "039030", "name": "이오테크닉스", "chain": "레이저/패키징", "focus": "레이저 가공·첨단 패키징 투자"},
    {"code": "089030", "name": "테크윙", "chain": "HBM 테스트", "focus": "HBM 검사장비 수주·매출 전환"},
    {"code": "095340", "name": "ISC", "chain": "테스트 소켓", "focus": "AI·고성능 반도체 테스트 수요"},
    {"code": "058470", "name": "리노공업", "chain": "테스트핀/소켓", "focus": "고부가 테스트 부품·마진"},
    {"code": "067310", "name": "하나마이크론", "chain": "OSAT", "focus": "패키징·테스트 가동률·CAPEX"},
]
BY_CODE = {item["code"]: item for item in PACKAGING_STOCKS}


def _money(value):
    return f"{value:,.0f}원" if value is not None else "—"


def render_packaging(state):
    # The dedicated HBM page is no longer part of primary navigation.
    # Redirect stale browser sessions safely to the main investment dashboard.
    st.session_state.nav_choice = "오늘의 투자판단"
    st.rerun()
