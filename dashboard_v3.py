import hashlib
import html
from datetime import date, datetime, timezone

import pandas as pd
import streamlit as st

from automatic import brief
from bi_view import detail, overview, peers_chart, theme
from chat_research import growth, parse_bundle, published, request_text, trends
from market_data import (
    SECTOR_REFERENCE,
    market_snapshots,
    safe_market_history,
    safe_reference_history,
    sector_snapshots,
)


MARKET_LABELS = ("KOSPI", "KOSDAQ", "USD/KRW", "WTI", "GOLD")


def _styles():
    st.markdown(
        """
<style>
.px-dashboard-title { display:flex; align-items:flex-end; justify-content:space-between; gap:18px; margin:2px 0 12px; }
.px-dashboard-title .brand { font:700 30px/1 Georgia,serif; color:#8d6427; letter-spacing:-.04em; }
.px-dashboard-title .brand span { font:700 9px/1.2 ui-monospace,SFMono-Regular,Menlo,monospace; letter-spacing:.25em; color:#364152; margin-left:10px; }
.px-dashboard-title .meta { color:#748091; font-size:11px; text-align:right; }
.px-flow { display:flex; justify-content:flex-end; align-items:center; gap:7px; margin:10px 0 14px; flex-wrap:wrap; }
.px-flow span { background:#f7f4ee; border:1px solid #eee7dc; border-radius:7px; padding:7px 24px; color:#685e52; font-size:11px; }
.px-flow b { color:#b08436; font-size:12px; }
.px-flow .active { background:#b88938; color:white; border-color:#b88938; font-weight:800; }
.px-judgement { min-height:160px; background:#fff; border:1px solid #e7ddcf; border-radius:11px; padding:15px 15px 13px; overflow:hidden; }
.px-judgement-label { font-size:12px; font-weight:800; color:#5f554b; margin-bottom:12px; }
.px-judgement strong { display:block; color:#352d25; font-size:18px; line-height:1.25; letter-spacing:-.025em; }
.px-judgement p { color:#7a8593; font-size:11px; line-height:1.55; margin:13px 0 0; }
.px-gold { border-top:3px solid #b88938; } .px-slate { border-top:3px solid #98a5b4; }
.px-green { border-top:3px solid #23885e; } .px-blue { border-top:3px solid #3e7fd4; }
.px-focus { border:1px solid #e3d8ca; border-radius:11px; background:#fff; padding:15px 18px; margin:8px 0 12px; }
.px-focus-head { display:flex; justify-content:space-between; align-items:flex-start; gap:16px; margin-bottom:4px; }
.px-focus-name { font-size:20px; font-weight:850; color:#352d25; }
.px-focus-code { color:#8190a2; font-size:10px; margin-left:5px; }
.px-focus-price { font:700 25px/1.2 Georgia,serif; color:#352d25; margin-top:8px; }
.px-up { color:#cf4545; font:700 12px sans-serif; } .px-down { color:#2d6fd0; font:700 12px sans-serif; }
.px-sector-grid { display:grid; grid-template-columns:repeat(4,minmax(0,1fr)); border-radius:9px; overflow:hidden; border:1px solid #e4ddd3; }
.px-sector-cell { min-height:82px; padding:13px 10px; display:flex; flex-direction:column; justify-content:center; text-align:center; border-right:1px solid rgba(255,255,255,.5); border-bottom:1px solid rgba(255,255,255,.5); }
.px-sector-cell b { font-size:11px; color:#20313a; } .px-sector-cell strong { margin-top:3px; font-size:14px; color:#14232b; }
.px-sector-cell small { color:#42505b; font-size:9px; margin-top:2px; }
.px-watch-row { display:grid; grid-template-columns:minmax(0,1fr) auto auto; gap:10px; padding:9px 0; border-bottom:1px solid #eee7de; align-items:center; }
.px-watch-row:last-child { border-bottom:none; } .px-watch-name { font-weight:720; color:#3c332b; font-size:12px; }
.px-watch-price { font:700 12px/1 Georgia,serif; color:#3c332b; } .px-watch-delta { font-size:10px; font-weight:750; }
.px-source-note { color:#8c98a8; font-size:10px; line-height:1.5; }
@media(max-width:900px) { .px-sector-grid{grid-template-columns:repeat(2,minmax(0,1fr));} .px-dashboard-title{align-items:flex-start;flex-direction:column;} .px-dashboard-title .meta{text-align:left;} }
</style>
""",
        unsafe_allow_html=True,
    )


def _market_header():
    today = datetime.now().astimezone().strftime("%Y년 %m월 %d일")
    st.markdown(
        '<div class="px-dashboard-title"><div><span class="brand">PlanX <span>STOCK INTELLIGENCE</span></span></div>'
        f'<div class="meta">{html.escape(today)} · 실제 연결 데이터는 기준시각과 출처를 함께 표시합니다.</div></div>',
        unsafe_allow_html=True,
    )
    snapshots = market_snapshots()
    cols = st.columns(5, gap="small")
    for col, label in zip(cols, MARKET_LABELS):
        snapshot = snapshots.get(label, {"value": "연결 확인", "note": "응답 확인 필요", "change_pct": None, "checked": "응답 확인 필요", "rows": []})
        with col:
            with st.container(border=True):
                st.caption(label)
                st.markdown(f"### {snapshot['value']}")
                change = snapshot.get("change_pct")
                if change is None:
                    st.caption(snapshot["note"])
                else:
                    arrow = "▲" if change > 0 else "▼" if change < 0 else "■"
                    st.caption(f"{arrow} {change:+.2f}% · {snapshot.get('checked','')}")
                rows = snapshot.get("rows") or []
                if len(rows) >= 2:
                    spark = pd.DataFrame(rows[-12:])[["date", "close"]].set_index("date")
                    st.line_chart(spark, height=55, use_container_width=True)
                st.caption("Yahoo Finance · 지연 가능")
    return snapshots


def _pct(current, previous):
    try:
        current, previous = float(current), float(previous)
        if previous > 0:
            return (current / previous - 1.0) * 100.0
    except (TypeError, ValueError, ZeroDivisionError):
        pass
    return None


def _official_result(stock):
    report = stock.get("report") or {}
    if not report or not report.get("years"):
        return None
    try:
        return brief(report)
    except (KeyError, TypeError, ValueError, IndexError, ZeroDivisionError):
        return None


def _focus_metrics(stock, research, market, sectors):
    auto = _official_result(stock)
    score = None if not auto else auto.get("total")
    if score is None:
        total_value, total_note = "평가 보류", "공식 결산·가치 자료가 모두 모이면 자동 점수를 계산합니다."
    else:
        total_value, total_note = f"{score:.0f}/100", "성장 30 · 수익성 30 · 가치 40의 규칙 기반 참고 점수입니다."

    kospi = market.get("KOSPI", {}).get("change_pct")
    fx = market.get("USD/KRW", {}).get("change_pct")
    if kospi is None or fx is None:
        macro_value, macro_note = "시장 확인", "KOSPI와 원/달러 응답을 기다리고 있습니다."
    else:
        k_arrow = "↑" if kospi > 0 else "↓" if kospi < 0 else "→"
        f_arrow = "↑" if fx > 0 else "↓" if fx < 0 else "→"
        macro_value = f"KOSPI {k_arrow} · 원/달러 {f_arrow}"
        macro_note = f"KOSPI {kospi:+.2f}% · USD/KRW {fx:+.2f}%"

    valid_sectors = [(name, row.get("change_pct")) for name, row in sectors.items() if row.get("change_pct") is not None]
    if valid_sectors:
        leader, chg = max(valid_sectors, key=lambda x: x[1])
        sector_value, sector_note = f"{leader} {chg:+.1f}%", "대표 ETF의 1일 등락 기준이며 국내 업종지수는 아닙니다."
    else:
        sector_value, sector_note = "섹터 확인", "대표 섹터 데이터 응답을 기다리고 있습니다."

    report = stock.get("report") or {}
    notices = report.get("disclosures") or []
    order_words = ("수주", "공급계약", "계약체결", "수출")
    order_hits = [x for x in notices if any(word in str(x.get("title", "")) for word in order_words)]
    if order_hits:
        order_value, order_note = f"관련 공시 {len(order_hits)}건", "현재 수집된 DART 공시 제목에서 수주·공급계약·수출 키워드를 확인했습니다."
    else:
        order_value, order_note = "근거 대기", "현재 수집 공시에서 수출·수주 근거를 확인하지 못했습니다."

    f = (research or {}).get("financial") or {}
    profit_growth = _pct(f.get("operating_profit"), f.get("prior_operating_profit")) if f else None
    if profit_growth is None and auto:
        profit_growth = auto.get("profit_growth")
    if profit_growth is None:
        growth_value, growth_note = "실적 확인", "전년 같은 기간 또는 최근 결산 영업이익 비교가 필요합니다."
    else:
        growth_value = f"영업이익 {profit_growth:+.1f}%"
        growth_note = "동일 기준의 전년 비교가 가능한 공식 실적을 사용합니다."

    flow = (research or {}).get("flow") or {}
    if flow:
        total_flow = float(flow.get("foreign", 0)) + float(flow.get("institution", 0))
        flow_value = f"합산 {total_flow:+,.0f}{flow.get('unit','')}"
        flow_note = f"외국인 {float(flow.get('foreign',0)):+,.0f} · 기관 {float(flow.get('institution',0)):+,.0f} · {flow.get('start','')}~{flow.get('end','')}"
    else:
        flow_value, flow_note = "수급 확인", "출처가 있는 외국인·기관 순매수 자료가 필요합니다."

    return [
        ("종합 분석점수", total_value, total_note, "gold"),
        ("매크로", macro_value, macro_note, "slate"),
        ("성장산업", sector_value, sector_note, "green"),
        ("수출·수주", order_value, order_note, "green"),
        ("실적 성장", growth_value, growth_note, "green"),
        ("수급 강도", flow_value, flow_note, "blue"),
    ]


def _judgement_cards(stock, research, market, sectors):
    st.markdown(
        '<div class="px-flow"><span>시장</span><b>›</b><span>산업</span><b>›</b><span>기업</span><b>›</b><span class="active">투자판단</span></div>',
        unsafe_allow_html=True,
    )
    signals = _focus_metrics(stock or {}, research or {}, market, sectors)
    cols = st.columns(6, gap="small")
    for col, (title, value, note, tone) in zip(cols, signals):
        with col:
            st.markdown(
                '<div class="px-judgement px-' + tone + '"><div class="px-judgement-label">'
                + html.escape(title) + '</div><strong>' + html.escape(value)
                + '</strong><p>' + html.escape(note) + '</p></div>',
                unsafe_allow_html=True,
            )


def _price_snapshot(stock, research, frame):
    price = None
    delta = None
    price_date = None
    if frame is not None and not frame.empty:
        closes = frame["close"].astype(float)
        price = float(closes.iloc[-1])
        price_date = str(frame["date"].iloc[-1])
        if len(closes) >= 2 and closes.iloc[-2] != 0:
            delta = (closes.iloc[-1] / closes.iloc[-2] - 1.0) * 100.0
    valuation = (research or {}).get("valuation") or {}
    if price is None and valuation:
        price = float(valuation.get("current_price"))
        price_date = valuation.get("price_date")
    report = stock.get("report") or {}
    if price is None and report.get("price") is not None:
        price = float(report["price"])
        price_date = report.get("price_date")
    snap = stock.get("price_snapshot") or {}
    if price is None and snap.get("price") is not None:
        price = float(snap["price"])
        price_date = snap.get("date")
    return price, delta, price_date


def _normalized_chart(frame, stock):
    series = []
    if frame is not None and not frame.empty:
        own = frame[["date", "close"]].copy()
        own["date"] = pd.to_datetime(own["date"])
        own = own.drop_duplicates("date").set_index("date")["close"].astype(float)
        if not own.empty:
            own = own / own.iloc[0] * 100.0
            own.name = stock.get("name", "선택종목")
            series.append(own)
    kospi_rows = safe_market_history("KOSPI", "1y")
    if kospi_rows:
        ks = pd.DataFrame(kospi_rows)
        ks["date"] = pd.to_datetime(ks["date"])
        ks = ks.drop_duplicates("date").set_index("date")["close"].astype(float)
        if not ks.empty:
            ks = ks / ks.iloc[0] * 100.0
            ks.name = "KOSPI"
            series.append(ks)

    auto = _official_result(stock)
    sector_name = None
    symbol = None
    if auto and auto.get("sectors"):
        label = auto["sectors"][0].get("sector")
        if label in SECTOR_REFERENCE:
            sector_name, symbol = SECTOR_REFERENCE[label]
    if symbol:
        rows = safe_reference_history(symbol, "1y")
        if rows:
            ref = pd.DataFrame(rows)
            ref["date"] = pd.to_datetime(ref["date"])
            ref = ref.drop_duplicates("date").set_index("date")["close"].astype(float)
            if not ref.empty:
                ref = ref / ref.iloc[0] * 100.0
                ref.name = f"{sector_name} ETF"
                series.append(ref)
    if not series:
        return None
    chart = pd.concat(series, axis=1).sort_index().ffill().dropna(how="all")
    return chart.tail(260)


def _sector_heatmap(sectors):
    def sort_key(label):
        change = sectors[label].get("change_pct")
        return (change is None, -(change if change is not None else -999.0))

    cells = []
    for label in sorted(sectors, key=sort_key):
        row = sectors[label]
        change = row.get("change_pct")
        if change is None:
            bg = "#eef0f2"
            value = "확인 필요"
        elif change >= 0:
            alpha = min(0.75, 0.18 + abs(change) / 7)
            bg = f"rgba(39,139,91,{alpha:.2f})"
            value = f"{change:+.1f}%"
        else:
            alpha = min(0.7, 0.16 + abs(change) / 7)
            bg = f"rgba(206,86,86,{alpha:.2f})"
            value = f"{change:+.1f}%"
        cells.append(
            f'<div class="px-sector-cell" style="background:{bg}"><b>{html.escape(label)}</b><strong>{html.escape(value)}</strong><small>{html.escape(row.get("symbol", ""))}</small></div>'
        )
    st.markdown('<div class="px-sector-grid">' + "".join(cells) + "</div>", unsafe_allow_html=True)
    st.caption("대표 미국 상장 ETF의 1일 등락률 프록시 · 국내 업종지수와 동일하지 않습니다 · Yahoo Finance")


def _watchlist(details):
    if not details:
        st.info("관심종목을 추가하면 가격·조사 상태가 여기에 표시됩니다.")
        return
    markup = []
    for _, (stock, research, _, frame) in list(details.items())[:7]:
        price, delta, _ = _price_snapshot(stock, research, frame)
        value = f"{price:,.0f}" if price is not None else "조회 필요"
        if delta is None:
            delta_text, cls = "", ""
        else:
            delta_text = f"{delta:+.2f}%"
            cls = "px-up" if delta >= 0 else "px-down"
        markup.append(
            '<div class="px-watch-row"><div class="px-watch-name">★ '
            + html.escape(stock.get("name", "종목")) + '</div><div class="px-watch-price">' + html.escape(value)
            + '</div><div class="px-watch-delta ' + cls + '">' + html.escape(delta_text) + '</div></div>'
        )
    st.markdown("".join(markup), unsafe_allow_html=True)


def _stock_controls(store, state, stocks, sample_mode):
    if sample_mode:
        st.info("둘러보기 중입니다. APP_PASSWORD와 공식 API 키를 설정하면 개인 종목 저장과 공식 분석이 활성화됩니다.")
        return
    with st.expander("＋ 종목 추가", expanded=not state.get("stocks")):
        with st.form("research_manual"):
            name = st.text_input("종목명", placeholder="예: 삼성전자")
            with st.expander("종목코드를 알고 있다면 · 선택"):
                code = st.text_input("종목코드", max_chars=6)
            if st.form_submit_button("내 목록에 추가", type="primary"):
                import re
                if not name.strip() or (code and not re.fullmatch(r"[0-9]{6}", code)):
                    st.error("종목명과 숫자 6자리 코드를 확인하세요. 코드는 생략할 수 있습니다.")
                else:
                    known = next((s for s in state.get("stocks", []) if s["name"].strip().casefold() == name.strip().casefold()), {})
                    identity = known.get("code") or code or "pending-" + hashlib.sha256(name.strip().casefold().encode()).hexdigest()[:16]
                    try:
                        store.save_stock({"code": identity, "name": name.strip(), "kind": known.get("kind", "관심")})
                        st.rerun()
                    except Exception:
                        st.error("목록 저장에 실패했습니다. 저장 공간 설정을 확인하세요.")
    if stocks:
        with st.expander("조사 요청 · 최신 내용으로 업데이트"):
            st.write("아래 요청문을 이 대화창에 보내면 출처가 있는 조사 결과를 저장소 형식에 맞춰 갱신할 수 있습니다.")
            st.code(request_text(list(stocks.values())), language=None)
            if st.button("반영된 조사 결과 다시 읽기"):
                st.rerun()
            with st.expander("조사 파일 가져오기 · 고급"):
                upload = st.file_uploader("별도로 받은 조사 JSON 가져오기 · 선택", type=["json"])
                if upload and st.button("조사 파일 검증·저장"):
                    try:
                        reports = parse_bundle(upload.getvalue())

                        def save(data):
                            merged = {r["code"]: r for r in data.get("chat_research", [])}
                            for r in reports:
                                if r["code"] not in merged or r["as_of"] >= merged[r["code"]]["as_of"]:
                                    merged[r["code"]] = r
                            data["chat_research"] = list(merged.values())

                        store.change(save)
                        st.rerun()
                    except (ValueError, KeyError, TypeError):
                        st.error("조사 파일의 형식·출처·기간을 확인하세요. 기존 결과는 유지했습니다.")
                    except Exception:
                        st.error("저장에 실패했습니다. 기존 결과는 유지했습니다.")


def _official_detail(stock):
    report = stock.get("report") or {}
    if not report:
        st.info("이 종목의 공식 결산 분석이 아직 없습니다. 설정 → 종목 분석에서 최신 데이터를 조회할 수 있습니다.")
        return
    result = _official_result(stock)
    st.subheader(stock.get("name", "기업"))
    years = report.get("years") or []
    latest_year = years[-1].get("year", "") if years else ""
    st.caption(
        f"시세 기준일 {report.get('price_date','확인 필요')} · 결산 {latest_year} · "
        f"{report.get('basis','')} · 실시간 시세가 아닙니다."
    )
    if result:
        with st.container(border=True):
            st.markdown("**핵심 요약**")
            st.write(result.get("summary", ""))
    a, b, c = st.columns([1.2, 1, 1], gap="large")
    with a, st.container(border=True):
        st.subheader("주력사업과 기업 특징")
        excerpt = report.get("business_excerpt", "")
        st.write(excerpt[:650] + ("…" if len(excerpt) > 650 else "") if excerpt else "사업보고서 설명을 수집하지 못했습니다.")
    with b, st.container(border=True):
        st.subheader("영업이익 변화")
        if years:
            chart = pd.DataFrame(years)[["year", "profit"]].rename(columns={"year": "연도", "profit": "영업이익"})
            chart["연도"] = chart["연도"].astype(str)
            st.bar_chart(chart.set_index("연도"), height=220)
        else:
            st.info("결산 자료가 필요합니다.")
    with c, st.container(border=True):
        st.subheader("가격과 가치의 거리")
        fair = result.get("fair") if result else None
        if fair:
            st.metric("기본 참고가", f"{fair['base']:,.0f}원")
            st.caption(f"낮은 {fair['low']:,.0f}원 · 높은 {fair['high']:,.0f}원 · 현재 대비 {fair['gap']:+.1f}%")
            st.write(result.get("fair_reason", ""))
        else:
            st.write("평가 근거를 기다리고 있습니다.")
            if result:
                st.caption(result.get("fair_reason", ""))


def _research_detail(selected, stock, r, trend, frame, store, sample_mode):
    if not r:
        _official_detail(stock)
        return
    st.subheader(stock["name"])
    st.caption("조사일 " + r["as_of"] + " · 각 표의 자료 기간은 아래에 별도 표시합니다. 실시간 분석이 아닙니다.")
    detail(r)
    summary = r.get("summary")
    if summary:
        with st.container(border=True):
            st.markdown("**핵심 요약**")
            st.write(summary["text"])
    tabs = st.tabs(["어떤 기업인가요?", "실적은 어떤가요?", "주가 흐름", "가격과 확인 사항"])
    with tabs[0]:
        st.subheader("주력사업과 기업 특징")
        entry = r.get("business")
        if entry:
            st.write(entry["text"])
            st.link_button("설명의 원문 근거", entry["source"], key="research_business")
        else:
            st.info("조사 필요")
    with tabs[1]:
        f = r.get("financial")
        if f:
            st.caption(f"누적 {f['period']} / 전년 {f['prior_period']} · {f['basis']} · {f['currency']} {f['unit']}")
            st.dataframe(
                [
                    {"항목": "매출", "이번 누적": f["revenue"], "전년 누적": f["prior_revenue"], "변화": growth(f["revenue"], f["prior_revenue"])},
                    {"항목": "영업이익", "이번 누적": f["operating_profit"], "전년 누적": f["prior_operating_profit"], "변화": growth(f["operating_profit"], f["prior_operating_profit"])},
                ],
                hide_index=True,
                use_container_width=True,
            )
            st.link_button("실적 근거", f["source"])
        else:
            st.info("전년 같은 기간 누적 실적 조사 필요")
        peers = r.get("peers")
        st.subheader("경쟁사 영업이익 순위")
        if peers and peers["rows"]:
            st.write(peers["selection_reason"])
            st.caption(f"비교 표본 내 순위 · {peers['period']} · {peers['basis']} · {peers['currency']} {peers['unit']}")
            peers_chart(peers)
            df = pd.DataFrame(peers["rows"])
            df["순위"] = df["operating_profit"].rank(method="min", ascending=False).astype(int)
            st.dataframe(
                df.sort_values("순위")[["순위", "name", "operating_profit", "source"]].rename(
                    columns={"name": "기업", "operating_profit": "영업이익", "source": "출처"}
                ),
                hide_index=True,
                use_container_width=True,
            )
        else:
            st.info("같은 기간·회계기준의 경쟁사 실적 조사 필요")
    with tabs[2]:
        flow = r.get("flow")
        if flow:
            st.caption(flow["start"] + " ~ " + flow["end"] + " · 순매수 " + flow["unit"])
            a, b = st.columns(2)
            a.metric("외국인 순매수", f"{flow['foreign']:+,.0f}")
            b.metric("기관 순매수", f"{flow['institution']:+,.0f}")
            st.link_button("수급 근거", flow["source"])
        else:
            st.info("외국인·기관 수급 조사 필요")
        a, b = st.columns(2)
        a.metric("일봉 추세", trend["daily"])
        b.metric("완료 주봉 추세", trend["weekly"])
        st.caption("수정종가 기준: 일봉 20·60일, 주봉 10·20주 평균과 장기 평균 기울기를 함께 확인합니다. 진행 중인 주는 제외합니다.")
        if frame is not None and not frame.empty:
            st.caption("가격 자료 마지막 거래일 " + str(frame["date"].iloc[-1]))
            st.line_chart(frame.set_index("date")["close"])
            st.link_button("가격 자료 근거", r["prices"]["source"])
    with tabs[3]:
        v = r.get("valuation")
        if v:
            a, b, c = st.columns(3)
            for col, key, label in [(a, "low", "낮은 참고가"), (b, "base", "기본 참고가"), (c, "high", "높은 참고가")]:
                col.metric(label, f"{v[key]:,.0f}원")
            st.write(v["method"])
            st.caption(f"비교 가격 {v['current_price']:,.0f}원 · {v['price_date']} · 기본 참고가 대비 차이 {(v['base']/v['current_price']-1)*100:+.1f}%")
            st.link_button("평가 근거", v["source"])
        else:
            st.info("평가 가정과 가격 근거 조사 필요")
        for gap in r.get("data_gaps", []):
            st.write("확인 필요 · " + str(gap))
    if not sample_mode:
        with st.expander("투자일지 남기기"):
            with st.form("research_note"):
                note = st.text_area("투자일지 · 다음 확인할 조건")
                if st.form_submit_button("기록 저장") and note.strip():
                    try:
                        store.log("journal", {"code": selected, "at": datetime.now(timezone.utc).isoformat(), "kind": "note", "note": note.strip()})
                        st.success("일지를 저장했습니다.")
                    except Exception:
                        st.error("저장 실패. 입력 내용을 보관하세요.")


def render_research(store, state, sample_mode):
    theme()
    _styles()
    market = _market_header()
    try:
        sectors = sector_snapshots()
    except Exception:
        sectors = {}

    research = published()
    for r in state.get("chat_research", []):
        if r["code"] not in research or r["as_of"] >= research[r["code"]]["as_of"]:
            research[r["code"]] = r

    stocks = {s["code"]: s for s in state.get("stocks", [])}
    for p in st.session_state.get("account_snapshot", {}).get("positions", []):
        stocks[p["code"]] = {**stocks.get(p["code"], {}), "code": p["code"], "name": p["name"]}

    rows, details = [], {}
    for key, stock in stocks.items():
        r = research.get(key)
        if not r and key.startswith("pending-"):
            matches = [v for v in research.values() if v["name"].strip().casefold() == stock["name"].strip().casefold()]
            if len(matches) == 1:
                r = matches[0]
        r = r or {}
        f, v, flow = r.get("financial") or {}, r.get("valuation") or {}, r.get("flow") or {}
        trend, frame = trends(r.get("prices"), r.get("as_of", date.today().isoformat()))
        row = {
            "종목": stock["name"],
            "코드": r.get("code", key if not key.startswith("pending-") else "확인 필요"),
            "누적 매출 성장": growth(f["revenue"], f["prior_revenue"]) if f else "조사 필요",
            "누적 영업이익 성장": growth(f["operating_profit"], f["prior_operating_profit"]) if f else "조사 필요",
            "외국인 / 기관": f"{flow['foreign']:+,.0f} / {flow['institution']:+,.0f} {flow['unit']}" if flow else "조사 필요",
            "적정주가 참고": f"{v['base']:,.0f}원" if v else "조사 필요",
            "일봉": trend["daily"],
            "주봉": trend["weekly"],
            "조사일": r.get("as_of", "미조사"),
        }
        rows.append(row)
        details[key] = (stock, r, trend, frame)

    st.markdown("#### 오늘의 투자판단")
    if details:
        keys = list(details)
        previous = st.session_state.get("research_selected")
        index = keys.index(previous) if previous in keys else 0
        selected = st.selectbox(
            "판단할 종목",
            keys,
            index=index,
            format_func=lambda k: stocks[k]["name"],
            key="research_selected",
            label_visibility="collapsed",
        )
        stock, r, trend, frame = details[selected]
    else:
        selected, stock, r, trend, frame = None, {}, {}, {"daily": "조사 필요", "weekly": "조사 필요"}, None

    _judgement_cards(stock, r, market, sectors)

    if selected:
        price, delta, price_date = _price_snapshot(stock, r, frame)
        delta_text = "" if delta is None else f"{delta:+.2f}%"
        delta_cls = "px-up" if delta is not None and delta >= 0 else "px-down"
        code = r.get("code") or stock.get("code", "")
        code = "코드 확인 대기" if str(code).startswith("pending-") else str(code)
        st.markdown(
            '<div class="px-focus"><div class="px-focus-head"><div><span class="px-focus-name">'
            + html.escape(stock.get("name", "선택종목")) + '</span><span class="px-focus-code">' + html.escape(code)
            + '</span><div class="px-focus-price">' + (f"{price:,.0f}원" if price is not None else "가격 조회 필요")
            + (' <span class="' + delta_cls + '">' + html.escape(delta_text) + '</span>' if delta_text else "")
            + '</div></div><div class="px-source-note">가격 기준일 ' + html.escape(str(price_date or "확인 필요"))
            + '<br>공식 일별 종가/수정주가 · 실시간 체결가 아님</div></div></div>',
            unsafe_allow_html=True,
        )
        chart = _normalized_chart(frame, stock)
        left, right = st.columns([2.1, 1], gap="small")
        with left, st.container(border=True):
            st.subheader("선택종목 · 시장 상대 흐름")
            if chart is not None and not chart.empty:
                st.line_chart(chart, height=330, use_container_width=True)
                st.caption("각 시계열 시작점을 100으로 환산 · 선택종목은 저장된 수정주가, 시장/참고 ETF는 Yahoo Finance")
            else:
                st.info("가격 시계열이 수집되면 선택종목과 KOSPI 상대 흐름을 표시합니다.")
        with right:
            with st.container(border=True):
                st.subheader("섹터별 등락률")
                _sector_heatmap(sectors)
            with st.container(border=True):
                st.subheader("관심종목")
                _watchlist(details)
    else:
        st.info("관심종목을 하나 추가하면 기업 중심 차트와 판단 카드가 활성화됩니다.")

    _stock_controls(store, state, stocks, sample_mode)

    st.markdown("### 내 관심종목 데이터 분석")
    overview(details, st.session_state.get("account_snapshot"))

    if rows:
        with st.expander("전체 지표 비교"):
            st.dataframe(pd.DataFrame(rows), hide_index=True, use_container_width=True)

    st.markdown("### 기업 하나를 깊게 보기")
    if not selected:
        st.info("종목을 추가한 뒤 공식 분석 또는 출처 기반 조사를 실행하세요.")
        return
    _research_detail(selected, stock, r, trend, frame, store, sample_mode)
