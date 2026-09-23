from __future__ import annotations

import html
import streamlit as st


NAV_ITEMS = [
    ("홈", "⌂"),
    ("시장 현황", "▥"),
    ("종목 분석", "◫"),
    ("공시 분석", "▤"),
    ("테마 & 섹터", "◇"),
    ("포트폴리오", "▣"),
    ("관심 종목", "☆"),
    ("AI 인사이트", "✦"),
    ("데이터 연결 관리", "⚙"),
]


def apply_theme():
    st.markdown(
        """
<style>
:root {
  --bg:#fffdfa; --surface:#ffffff; --sidebar:#fcf8f0;
  --line:#e8ddce; --text:#352d25; --muted:#788394;
  --gold:#ae843c; --gold-soft:#f4ead7; --green:#177a53; --red:#c34b4b;
}
html,body,[class*="css"] { font-family:Pretendard,"Noto Sans KR","Apple SD Gothic Neo",sans-serif; }
.stApp { background:var(--bg); color:var(--text); }
.block-container { max-width:1640px; padding:1.65rem 2rem 4rem; }
header[data-testid="stHeader"] { background:rgba(255,253,250,.95); }
section[data-testid="stSidebar"] { background:var(--sidebar); border-right:1px solid var(--line); }
section[data-testid="stSidebar"] > div { padding-top:1.3rem; }
[data-testid="stSidebar"] .stRadio > label { display:none; }
[data-testid="stSidebar"] .stRadio div[role="radiogroup"] { gap:.3rem; }
[data-testid="stSidebar"] .stRadio div[role="radiogroup"] label { border-radius:8px; padding:.68rem .6rem; }
[data-testid="stSidebar"] .stRadio div[role="radiogroup"] label:hover { background:#f7efe1; }
[data-testid="stSidebar"] .stRadio div[role="radiogroup"] label:has(input:checked) {
  background:var(--gold-soft); box-shadow:inset 3px 0 var(--gold); font-weight:700;
}
h1,h2,h3,h4 { color:var(--text); letter-spacing:-.035em; }
h1 { font-weight:800; } p,li { line-height:1.6; }
[data-testid="stCaptionContainer"] { color:var(--muted); }
[data-testid="stMetric"],[data-testid="stVerticalBlockBorderWrapper"] {
  background:var(--surface); border:1px solid var(--line) !important;
  border-radius:11px !important; box-shadow:none !important;
}
[data-testid="stMetric"] { padding:13px 16px; }
[data-testid="stMetricValue"] { color:var(--text); font-variant-numeric:tabular-nums; }
.stButton > button,.stFormSubmitButton > button { border-radius:8px; min-height:2.6rem; font-weight:650; }
.stButton > button[kind="primary"],.stFormSubmitButton > button[kind="primary"] {
  background:var(--gold); border-color:var(--gold); color:#fff;
}
.stTextInput input,.stTextArea textarea,.stSelectbox div[data-baseweb="select"] > div {
  border-radius:8px !important;
}
.stTabs [data-baseweb="tab-list"] { gap:8px; overflow-x:auto; }
.stTabs [data-baseweb="tab"] { white-space:nowrap; }
.stDataFrame { border:1px solid var(--line); border-radius:9px; overflow:hidden; }
.planx-brand { margin:8px 0 30px; padding-bottom:18px; border-bottom:1px solid var(--line); }
.planx-brand-title { color:#89642d; font:700 32px/1 Georgia,serif; letter-spacing:-.06em; }
.planx-brand-sub { margin-top:5px; color:#695946; font:700 9px Georgia,serif; letter-spacing:.22em; }
.planx-hero { padding:15px 0 22px; margin-bottom:6px; }
.planx-eyebrow { color:#9b753b; font-size:11px; font-weight:800; letter-spacing:.14em; margin-bottom:10px; }
.planx-hero h1 { margin:0; font-size:32px; line-height:1.25; }
.planx-hero p { color:#795f48; font-size:14px; margin:10px 0 0; }
.planx-card { background:var(--surface); border:1px solid var(--line); border-radius:10px;
  min-height:105px; padding:16px 18px; }
.planx-card-title { font-size:12px; font-weight:700; color:#736657; margin-bottom:8px; }
.planx-card-value { font-size:22px; font-weight:750; color:var(--text); font-variant-numeric:tabular-nums; }
.planx-card-note { margin-top:6px; font-size:11px; color:var(--muted); }
.planx-empty { background:#fff; border:1px dashed #d9cbb8; border-radius:10px; padding:20px; color:#786b5c; }
.planx-source { display:inline-flex; padding:4px 9px; border-radius:999px;
  font-size:11px; background:#f8f4ed; border:1px solid var(--line); color:#786b5c; }
.planx-status-ok { color:#176a4d; background:#eaf5ee; border-color:#c8e4d0; }
.planx-status-wait { color:#866328; background:#fbf4e5; border-color:#ead9b5; }
.planx-status-bad { color:#aa4242; background:#fff0ef; border-color:#efcdca; }
hr { border-color:var(--line) !important; }
@media(max-width:900px) { .block-container { padding:1rem 1rem 3rem; } .planx-hero h1 { font-size:27px; } }

/* Dashboard layout inspired by the approved cream and gold mockup. */
.block-container { max-width:1800px; padding:1.1rem 1.5rem 4rem; }
section[data-testid="stSidebar"] { min-width:235px; }
[data-testid="stSidebar"] .planx-brand { margin:10px 0 24px; padding-bottom:22px; }
.planx-brand-title { font-size:39px; font-weight:700; }
.planx-brand-sub { letter-spacing:.26em; }
.px-topline { display:flex; justify-content:space-between; align-items:center;
  gap:16px; border-bottom:1px solid var(--line); padding:5px 0 16px; margin-bottom:16px;
  color:#866b41; font-size:11px; font-weight:700; letter-spacing:.08em; }
.px-topline span:last-child { color:var(--muted); font-weight:500; letter-spacing:0; }
.planx-hero { padding:21px 0 17px; }
.planx-hero h1 { font-size:31px; font-weight:800; }
.planx-card { min-height:94px; padding:14px 16px; }
.planx-card-value { font-family:Georgia,Pretendard,"Noto Sans KR",serif; font-size:20px; }
[data-testid="stMetric"] { min-height:112px; padding:16px 18px; }
[data-testid="stVerticalBlockBorderWrapper"] { padding:3px; }
[data-testid="stSidebar"] .stRadio div[role="radiogroup"] label { margin-bottom:7px; }
[data-testid="stSidebar"] .stRadio div[role="radiogroup"] label:has(input:checked) { color:#7c5a20; }
@media(max-width:900px) {
  .block-container { padding:1rem 1rem 3rem; }
  .px-topline { flex-direction:column; align-items:flex-start; }
}
</style>
""",
        unsafe_allow_html=True,
    )


def brand():
    st.markdown(
        """
<div class="planx-brand">
  <div class="planx-brand-title">PlanX</div>
  <div class="planx-brand-sub">STOCK INTELLIGENCE</div>
</div>
""",
        unsafe_allow_html=True,
    )


def hero(title: str, subtitle: str, eyebrow: str = "PLANX INVESTMENT OS"):
    st.markdown(
        f"""
<div class="planx-hero">
  <div class="planx-eyebrow">{html.escape(eyebrow)}</div>
  <h1>{html.escape(title)}</h1>
  <p>{html.escape(subtitle)}</p>
</div>
""",
        unsafe_allow_html=True,
    )


def card(title: str, value: str, note: str = "", status: str = ""):
    status_html = f'<div class="planx-card-note">{html.escape(status)}</div>' if status else ""
    st.markdown(
        f"""
<div class="planx-card">
  <div class="planx-card-title">{html.escape(title)}</div>
  <div class="planx-card-value">{html.escape(value)}</div>
  <div class="planx-card-note">{html.escape(note)}</div>
  {status_html}
</div>
""",
        unsafe_allow_html=True,
    )


def empty_state(title: str, message: str):
    st.markdown(
        f"""
<div class="planx-empty">
  <strong style="color:#334155">{html.escape(title)}</strong><br>
  <span>{html.escape(message)}</span>
</div>
""",
        unsafe_allow_html=True,
    )


def source_badge(label: str, state: str = "wait"):
    cls = {"ok": "planx-status-ok", "bad": "planx-status-bad"}.get(state, "planx-status-wait")
    st.markdown(
        f'<span class="planx-source {cls}">{html.escape(label)}</span>',
        unsafe_allow_html=True,
    )
