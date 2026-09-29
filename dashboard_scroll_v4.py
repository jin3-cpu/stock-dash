"""Four-section single-scroll PlanX dashboard based on the approved screenshots."""
from __future__ import annotations

from datetime import date

import pandas as pd
import streamlit as st

from bi_view import overview
from chat_research import growth, published, trends
from dashboard_v3 import (
    _judgement_cards,
    _market_header,
    _normalized_chart,
    _price_snapshot,
    _research_detail,
    _sector_heatmap,
    _stock_controls,
    _styles,
    _watchlist,
)
from market_data import sector_snapshots


def _scroll_styles():
    st.markdown(
        """
<style>
/* Approved 1→2→3→4 vertical scroll composition */
.block-container { max-width: 1780px; padding-top: .7rem; padding-bottom: 5rem; }
.px-scroll-section { margin: 0 0 46px; padding: 0 0 34px; border-bottom: 1px solid #e8ddcf; }
.px-scroll-section:last-child { border-bottom: 0; }
.px-section-kicker { color:#a27634; font-size:10px; font-weight:800; letter-spacing:.15em; margin:4px 0 8px; }
.px-section-title { color:#352d25; font-size:30px; font-weight:850; letter-spacing:-.045em; margin:0 0 8px; }
.px-section-sub { color:#7a6045; font-size:13px; margin:0 0 22px; }
.px-summary-grid { display:grid; grid-template-columns:repeat(3,minmax(0,1fr)); gap:14px; margin:14px 0 24px; }
.px-summary-card { background:#fff; border:1px solid #e7dccd; border-radius:11px; padding:18px 20px; min-height:112px; }
.px-summary-card span { color:#748091; font-size:12px; }
.px-summary-card strong { display:block; color:#8d6427; font:700 26px/1.1 Georgia,serif; margin-top:12px; }
.px-company-banner { margin:10px 0 12px; padding:15px 18px; border:1px solid #e6dacb; border-radius:11px; background:#fff; }
.px-company-banner .name { font-size:20px; font-weight:850; color:#352d25; }
.px-company-banner .meta { float:right; color:#8a95a4; font-size:10px; text-align:right; }
.px-detail-title { font-size:28px; font-weight:850; letter-spacing:-.04em; color:#352d25; margin:8px 0 6px; }
.px-detail-caption { color:#97a2b1; font-size:11px; margin-bottom:16px; }
@media(max-width:900px){
  .px-summary-grid{grid-template-columns:1fr;}
  .px-section-title{font-size:25px;}
  .px-company-banner .meta{float:none;display:block;margin-top:8px;text-align:left;}
}
</style>
""",
        unsafe_allow_html=True,
    )


def _section_open(kicker: str, title: str, subtitle: str):
    st.markdown(
        '<div class="px-scroll-section">'
        f'<div class="px-section-kicker">{kicker}</div>'
        f'<div class="px-section-title">{title}</div>'
        f'<div class="px-section-sub">{subtitle}</div>',
        unsafe_allow_html=True,
    )


def _section_close():
    st.markdown("</div>", unsafe_allow_html=True)


def _load_context(state):
    research = published()
    for row in state.get("chat_research", []):
        code = row.get("code")
        if not code:
            continue
        if code not in research or row.get("as_of", "") >= research[code].get("as_of", ""):
            research[code] = row

    stocks = {s["code"]: s for s in state.get("stocks", []) if s.get("code")}
    for position in st.session_state.get("account_snapshot", {}).get("positions", []):
        code = position.get("code")
        if code:
            stocks[code] = {**stocks.get(code, {}), "code": code, "name": position.get("name", code)}

    rows, details = [], {}
    for key, stock in stocks.items():
        report = research.get(key)
        if not report and str(key).startswith("pending-"):
            name = str(stock.get("name", "")).strip().casefold()
            matches = [v for v in research.values() if str(v.get("name", "")).strip().casefold() == name]
            if len(matches) == 1:
                report = matches[0]
        report = report or {}
        financial = report.get("financial") or {}
        valuation = report.get("valuation") or {}
        flow = report.get("flow") or {}
        trend, frame = trends(report.get("prices"), report.get("as_of", date.today().isoformat()))
        rows.append(
            {
                "종목": stock.get("name", ""),
                "코드": report.get("code", key if not str(key).startswith("pending-") else "확인 필요"),
                "누적 매출 성장": growth(financial["revenue"], financial["prior_revenue"]) if financial else "조사 필요",
                "누적 영업이익 성장": growth(financial["operating_profit"], financial["prior_operating_profit"]) if financial else "조사 필요",
                "외국인 / 기관": f"{flow['foreign']:+,.0f} / {flow['institution']:+,.0f} {flow['unit']}" if flow else "조사 필요",
                "적정주가 참고": f"{valuation['base']:,.0f}원" if valuation else "조사 필요",
                "일봉": trend["daily"],
                "주봉": trend["weekly"],
                "조사일": report.get("as_of", "미조사"),
            }
        )
        details[key] = (stock, report, trend, frame)
    return stocks, rows, details


def _selected(details, stocks):
    if not details:
        return None, {}, {}, {"daily": "조사 필요", "weekly": "조사 필요"}, None
    keys = list(details)
    previous = st.session_state.get("research_selected")
    index = keys.index(previous) if previous in keys else 0
    selected = st.selectbox(
        "자세히 볼 종목",
        keys,
        index=index,
        format_func=lambda key: stocks[key].get("name", key),
        key="research_selected",
    )
    stock, report, trend, frame = details[selected]
    return selected, stock, report, trend, frame


def _summary_cards(details):
    researched = sum(1 for _, report, _, _ in details.values() if report)
    total = len(details)
    pending = max(total - researched, 0)
    st.markdown(
        '<div class="px-summary-grid">'
        f'<div class="px-summary-card"><span>내 관심종목</span><strong>{total}개</strong></div>'
        f'<div class="px-summary-card"><span>조사 자료 보유</span><strong>{researched}개</strong></div>'
        f'<div class="px-summary-card"><span>추가 조사 필요</span><strong>{pending}개</strong></div>'
        '</div>',
        unsafe_allow_html=True,
    )


def _focus_board(stock, report, frame, details, sectors):
    price, delta, price_date = _price_snapshot(stock, report, frame)
    code = report.get("code") or stock.get("code", "")
    code = "코드 확인 대기" if str(code).startswith("pending-") else str(code)
    delta_text = "" if delta is None else f"{delta:+.2f}%"
    st.markdown(
        '<div class="px-company-banner">'
        f'<span class="name">{stock.get("name", "선택종목")} <small>{code}</small></span>'
        f'<span class="meta">가격 기준일 {price_date or "확인 필요"}<br>실시간 체결가 아님</span>'
        f'<div style="font:700 27px Georgia,serif;margin-top:10px">{f"{price:,.0f}원" if price is not None else "가격 조회 필요"}'
        f' <span style="font:700 12px sans-serif">{delta_text}</span></div></div>',
        unsafe_allow_html=True,
    )

    chart = _normalized_chart(frame, stock)
    left, right = st.columns([2.1, 1], gap="small")
    with left, st.container(border=True):
        if chart is not None and not chart.empty:
            st.line_chart(chart, height=330, use_container_width=True)
            st.caption("시작점을 100으로 환산 · 선택종목 수정주가 / KOSPI·참고 ETF")
        else:
            st.info("가격 시계열이 수집되면 선택종목과 시장 상대 흐름을 표시합니다.")
    with right:
        with st.container(border=True):
            st.markdown("**섹터별 등락률**")
            _sector_heatmap(sectors)
        with st.container(border=True):
            st.markdown("**관심종목**")
            _watchlist(details)


def render_research(store, state, sample_mode):
    """Render screenshots 1→2→3→4 as one vertically scrolling page."""
    _styles()
    _scroll_styles()

    # 1. Market + judgement board
    market = _market_header()
    try:
        sectors = sector_snapshots()
    except Exception:
        sectors = {}
    stocks, rows, details = _load_context(state)

    _section_open("SECTION 01", "오늘의 투자판단", "시장 → 산업 → 기업 → 투자판단 흐름을 한 화면에서 확인합니다.")
    selected, stock, report, trend, frame = _selected(details, stocks) if details else (None, {}, {}, {"daily": "조사 필요", "weekly": "조사 필요"}, None)
    _judgement_cards(stock, report, market, sectors)
    if selected:
        _focus_board(stock, report, frame, details, sectors)
    else:
        st.info("관심종목을 하나 추가하면 기업 중심 판단 보드가 활성화됩니다.")
    _section_close()

    # 2. Watchlist management and counts
    _section_open("PLANX · STOCK RESEARCH", "내 투자의 현재를 한눈에", "관심 있는 기업을 담고, 판단에 필요한 변화만 확인하세요.")
    _stock_controls(store, state, stocks, sample_mode)
    _summary_cards(details)
    _section_close()

    # 3. Portfolio/peer overview + company cards
    _section_open("SECTION 03", "내 관심종목 데이터 분석", "계좌·관심종목·기업 실적을 같은 기준으로 비교합니다.")
    overview(details, st.session_state.get("account_snapshot"))
    if rows:
        with st.expander("전체 지표 비교"):
            st.dataframe(pd.DataFrame(rows), hide_index=True, use_container_width=True)
    if selected:
        st.markdown('<div class="px-detail-title">기업 하나를 깊게 보기</div>', unsafe_allow_html=True)
        st.markdown(
            f'<div class="px-detail-caption">{stock.get("name", "기업")} · 조사일 {report.get("as_of", "미조사")}</div>',
            unsafe_allow_html=True,
        )
        from bi_view import detail
        if report:
            detail(report)
        elif stock.get("report"):
            # The official-only fallback is rendered in section 4 to avoid duplicate long blocks.
            st.info("출처 기반 비교자료는 아직 없으며, 아래 상세 구간에서 공식 결산 자료를 확인할 수 있습니다.")
        else:
            st.info("기업 상세 자료를 추가 조사하면 사업·실적·가치 카드가 표시됩니다.")
    _section_close()

    # 4. Summary + tabs + journal
    _section_open("SECTION 04", "기업 상세 리서치", "핵심 요약 → 사업 → 실적 → 주가 흐름 → 가치·확인사항 → 투자일지 순서로 봅니다.")
    if not selected:
        st.info("종목을 추가한 뒤 상세 리서치를 확인하세요.")
    else:
        _research_detail(selected, stock, report, trend, frame, store, sample_mode)
    _section_close()
