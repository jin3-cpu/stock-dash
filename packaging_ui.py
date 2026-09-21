"""Semiconductor back-end packaging/HBM watchlist linked to the KIS account snapshot."""
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
    st.header("반도체 후공정 · HBM")
    st.caption("KIS 계좌 보유현황과 관심종목을 연결한 밸류체인 화면 · 매수/매도 신호가 아닙니다.")

    snapshot = st.session_state.get("account_snapshot") or {}
    positions = {p["code"]: p for p in snapshot.get("positions", [])}
    selected_positions = [p for code, p in positions.items() if code in BY_CODE]
    value = sum(p.get("value", 0) for p in selected_positions)
    pnl = sum(p.get("pnl", 0) for p in selected_positions)
    account_value = snapshot.get("value", 0)
    sector_weight = value / account_value * 100 if account_value else 0

    cols = st.columns(4)
    cols[0].metric("후공정 평가액", _money(value) if snapshot else "계좌 연결 필요")
    cols[1].metric("후공정 평가손익", f"{pnl:+,.0f}원" if snapshot else "계좌 연결 필요")
    cols[2].metric("계좌 내 후공정 비중", f"{sector_weight:.1f}%" if snapshot else "계좌 연결 필요")
    cols[3].metric("보유 / 추적", f"{len(selected_positions)} / {len(PACKAGING_STOCKS)}")

    if not snapshot:
        st.info("‘계좌 연결’에서 KIS 잔고를 불러오면 보유수량·평단·현재가·수익률이 자동으로 연결됩니다.")

    saved = {item.get("code"): item for item in state.get("stocks", [])}
    rows = []
    for meta in PACKAGING_STOCKS:
        p = positions.get(meta["code"])
        cached = saved.get(meta["code"], {})
        price_snapshot = cached.get("price_snapshot") or {}
        price = p.get("price") if p else price_snapshot.get("price")
        average = p.get("average_cost") if p else None
        return_pct = ((price / average) - 1) * 100 if price is not None and average else None
        rows.append({
            "보유": "보유" if p else "관심",
            "종목": meta["name"],
            "코드": meta["code"],
            "밸류체인": meta["chain"],
            "현재가": price,
            "평균매입가": average,
            "수량": p.get("quantity") if p else None,
            "평가액": p.get("value") if p else None,
            "평가손익": p.get("pnl") if p else None,
            "수익률 %": round(return_pct, 2) if return_pct is not None else None,
        })
    frame = pd.DataFrame(rows)
    st.dataframe(
        frame,
        hide_index=True,
        use_container_width=True,
        column_config={
            "현재가": st.column_config.NumberColumn(format="%,.0f원"),
            "평균매입가": st.column_config.NumberColumn(format="%,.0f원"),
            "평가액": st.column_config.NumberColumn(format="%,.0f원"),
            "평가손익": st.column_config.NumberColumn(format="%+,.0f원"),
            "수익률 %": st.column_config.NumberColumn(format="%+.2f%%"),
        },
    )

    st.subheader("밸류체인별 확인 포인트")
    for item in PACKAGING_STOCKS:
        with st.container(border=True):
            left, right = st.columns([2, 5])
            left.markdown(f"**{item['name']}**")
            left.caption(item["chain"])
            right.write(item["focus"])

    st.caption("현재가는 KIS 계좌 조회값 또는 저장된 공식 시세 스냅샷을 사용합니다. 값이 없으면 임의로 채우지 않습니다.")
