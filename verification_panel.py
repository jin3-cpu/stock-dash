"""Source-based company verification panel for the PlanX dashboard.

This module only summarizes facts already present in the stored official report
or validated chat-research bundle. Missing evidence is shown as '추가 확인'.
"""
from __future__ import annotations

import re
from datetime import datetime, timezone

import streamlit as st

from chat_research import published


def _pct(current, previous):
    try:
        current, previous = float(current), float(previous)
        if previous > 0:
            return (current / previous - 1.0) * 100.0
    except (TypeError, ValueError, ZeroDivisionError):
        pass
    return None


def _sentences(text: str) -> list[str]:
    clean = re.sub(r"\s+", " ", str(text or "")).strip()
    if not clean:
        return []
    parts = re.split(r"(?<=[.!?다])\s+|\s*[·•]\s*", clean)
    result = []
    for part in parts:
        part = part.strip(" -·•")
        if len(part) < 12:
            continue
        if part not in result:
            result.append(part)
    return result


def _merged_research(state):
    research = published()
    for row in state.get("chat_research", []):
        code = row.get("code")
        if not code:
            continue
        old = research.get(code)
        if old is None or row.get("as_of", "") >= old.get("as_of", ""):
            research[code] = row
    return research


def _selected(state):
    selected = st.session_state.get("research_selected")
    if not selected:
        return None, None, None
    stocks = {s.get("code"): s for s in state.get("stocks", []) if s.get("code")}
    for position in st.session_state.get("account_snapshot", {}).get("positions", []):
        code = position.get("code")
        if code and code not in stocks:
            stocks[code] = {"code": code, "name": position.get("name", code)}
    stock = stocks.get(selected)
    if not stock:
        return selected, None, None
    research = _merged_research(state)
    row = research.get(selected)
    if not row and str(selected).startswith("pending-"):
        name = str(stock.get("name", "")).strip().casefold()
        matches = [r for r in research.values() if str(r.get("name", "")).strip().casefold() == name]
        if len(matches) == 1:
            row = matches[0]
    return selected, stock, row or {}


def _business_lines(stock, research):
    entry = (research or {}).get("business") or {}
    text = entry.get("text") or (stock.get("report") or {}).get("business_excerpt", "")
    sentences = _sentences(text)
    revenue_words = ("매출", "판매", "수익", "제품", "서비스", "공급", "고객")
    money = next((s for s in sentences if any(word in s for word in revenue_words)), None)
    first = sentences[0] if sentences else None
    third = next((s for s in sentences if s not in {first, money}), None)
    return [
        first or "주요 사업 설명은 추가 확인이 필요합니다.",
        money or "돈을 버는 구조를 직접 설명하는 근거는 추가 확인이 필요합니다.",
        third or "사업 구조를 보완할 공식 근거는 추가 확인이 필요합니다.",
    ], entry.get("source")


def _financial(stock, research):
    f = (research or {}).get("financial") or {}
    if f:
        return {
            "period": f.get("period", ""),
            "prior_period": f.get("prior_period", ""),
            "revenue": f.get("revenue"),
            "prior_revenue": f.get("prior_revenue"),
            "profit": f.get("operating_profit"),
            "prior_profit": f.get("prior_operating_profit"),
            "unit": f.get("unit", ""),
            "basis": f.get("basis", ""),
            "source": f.get("source"),
            "date": (research or {}).get("as_of", f.get("period", "")),
        }
    years = (stock.get("report") or {}).get("years") or []
    if len(years) >= 2:
        prev, cur = years[-2], years[-1]
        return {
            "period": str(cur.get("year", "")),
            "prior_period": str(prev.get("year", "")),
            "revenue": cur.get("revenue"),
            "prior_revenue": prev.get("revenue"),
            "profit": cur.get("profit"),
            "prior_profit": prev.get("profit"),
            "unit": "억원",
            "basis": (stock.get("report") or {}).get("basis", "확정 결산"),
            "source": None,
            "date": (stock.get("report") or {}).get("fetched") or (stock.get("report") or {}).get("price_date", ""),
        }
    return None


def _disclosures(stock):
    rows = (stock.get("report") or {}).get("disclosures") or []
    return sorted(rows, key=lambda x: str(x.get("date", "")), reverse=True)


def _evidence(title, detail, date="", source=None, state="확인"):
    return {"title": title, "detail": detail, "date": str(date or "기준일 확인 필요"), "source": source, "state": state}


def _opportunities_and_risks(stock, research, financial, disclosures):
    opportunities = []
    risks = []
    as_of = (research or {}).get("as_of") or (stock.get("report") or {}).get("fetched") or "기준일 확인 필요"

    if financial:
        rg = _pct(financial.get("revenue"), financial.get("prior_revenue"))
        pg = _pct(financial.get("profit"), financial.get("prior_profit"))
        if pg is not None and pg > 0:
            opportunities.append(_evidence(
                "영업이익 성장 지속 가능성",
                f"동일 기준 영업이익이 전년 비교기간보다 {pg:+.1f}% 변했습니다. 다음 실적에서도 이 흐름이 이어지는지 확인합니다.",
                financial.get("date"), financial.get("source"),
            ))
        elif pg is not None and pg < 0:
            risks.append(_evidence(
                "영업이익 둔화 위험",
                f"동일 기준 영업이익이 전년 비교기간보다 {pg:+.1f}% 변했습니다. 일회성인지 추세인지 다음 실적에서 확인합니다.",
                financial.get("date"), financial.get("source"),
            ))
        if rg is not None and rg > 0:
            opportunities.append(_evidence(
                "매출 성장의 이익 전환 가능성",
                f"동일 기준 매출이 전년 비교기간보다 {rg:+.1f}% 변했습니다. 매출 증가가 영업이익과 현금흐름으로 이어지는지 확인합니다.",
                financial.get("date"), financial.get("source"),
            ))
        elif rg is not None and rg < 0:
            risks.append(_evidence(
                "매출 둔화 위험",
                f"동일 기준 매출이 전년 비교기간보다 {rg:+.1f}% 변했습니다. 수요·가격·물량 중 어떤 요인인지 추가 확인이 필요합니다.",
                financial.get("date"), financial.get("source"),
            ))

    order_words = ("수주", "공급계약", "계약체결", "수출")
    risk_words = ("유상증자", "전환사채", "채무", "소송", "감사의견", "불성실", "투자주의", "회생")
    for item in disclosures:
        title = str(item.get("title", ""))
        if len(opportunities) < 2 and any(word in title for word in order_words):
            opportunities.append(_evidence(
                "수주·공급계약의 매출 전환 가능성",
                f"공시 제목에서 '{title}' 사실이 확인됩니다. 계약이 실제 매출·이익으로 인식되는 시점과 조건을 다음 공시에서 확인합니다.",
                item.get("date"), item.get("url"),
            ))
        if len(risks) < 2 and any(word in title for word in risk_words):
            risks.append(_evidence(
                "재무·법률 관련 공시 확인",
                f"공시 제목에서 '{title}' 사실이 확인됩니다. 영향 규모와 후속 조치를 원문에서 확인합니다.",
                item.get("date"), item.get("url"),
            ))

    for gap in (research or {}).get("data_gaps", []):
        if len(risks) >= 2:
            break
        risks.append(_evidence(
            "핵심 근거 미확인",
            "확인되지 않은 항목: " + str(gap),
            as_of,
            None,
            "추가 확인",
        ))

    while len(opportunities) < 2:
        opportunities.append(_evidence(
            "추가 확인",
            "현재 자료만으로 두 번째 성장 기회를 사실로 확정할 근거가 충분하지 않습니다.",
            as_of,
            None,
            "추가 확인",
        ))
    while len(risks) < 2:
        risks.append(_evidence(
            "추가 확인",
            "현재 자료만으로 두 번째 위험을 사실로 확정할 근거가 충분하지 않습니다.",
            as_of,
            None,
            "추가 확인",
        ))
    return opportunities[:2], risks[:2]


def _edge(research):
    for key in ("competitive_edge", "edge"):
        entry = (research or {}).get(key)
        if isinstance(entry, dict) and entry.get("text") and entry.get("source"):
            return entry.get("text"), entry.get("source"), (research or {}).get("as_of", "")
    return "추가 확인", None, (research or {}).get("as_of", "기준일 확인 필요")


def _next_indicator(financial, disclosures):
    if financial:
        return "다음 공식 실적에서 누적 영업이익의 전년 동기 대비 변화", "현재 실적 변화가 일회성인지 지속되는지 가장 직접적으로 다시 확인할 수 있습니다."
    if any(any(word in str(x.get("title", "")) for word in ("수주", "공급계약", "계약체결")) for x in disclosures):
        return "수주·공급계약의 실제 매출 인식 여부", "계약 체결 사실과 실제 실적 기여를 구분하기 위해 확인합니다."
    return "다음 공식 실적 공시", "현재 자료에는 실적 추세를 이어서 판단할 충분한 비교 근거가 없습니다."


def _journal(stock, research, financial, opportunities, risks, indicator, edge_text):
    name = stock.get("name", "선택 기업")
    as_of = (research or {}).get("as_of") or (stock.get("report") or {}).get("fetched") or "기준일 확인 필요"
    facts = []
    if financial:
        pg = _pct(financial.get("profit"), financial.get("prior_profit"))
        rg = _pct(financial.get("revenue"), financial.get("prior_revenue"))
        if rg is not None:
            facts.append(f"매출 전년 비교 {rg:+.1f}%")
        if pg is not None:
            facts.append(f"영업이익 전년 비교 {pg:+.1f}%")
    if not facts:
        facts.append("실적 비교 근거 추가 확인")
    edge_label = edge_text if edge_text != "추가 확인" else "추가 확인(별도 근거가 있는 경우에만 확정)"
    return (
        f"[{name} 투자일지 초안]\n"
        f"기준일: {as_of}\n"
        f"현재 확인: {' · '.join(facts)}\n"
        f"성장 기회: {opportunities[0]['title']} / {opportunities[1]['title']}\n"
        f"확인할 위험: {risks[0]['title']} / {risks[1]['title']}\n"
        f"경쟁력·엣지: {edge_label}\n"
        f"다음 확인 지표: {indicator[0]}\n"
        "판단: 다음 확인 지표가 업데이트되기 전까지 기존 사실과 가정을 구분해 기록한다."
    )


def _source_caption(date, source):
    st.caption("기준/날짜 · " + str(date or "확인 필요"))
    if source:
        st.markdown(f"[원문 근거]({source})")
    else:
        st.caption("원문 링크 · 추가 확인")


def render_verification_panel(store, state, sample_mode):
    selected, stock, research = _selected(state)
    if not selected or not stock:
        return

    st.markdown("---")
    st.markdown("### 공식 실적·공시 검증 리서치")
    st.caption("자료에 있는 사실만 정리합니다. 없는 수치·경쟁사 비교·목표주가는 만들지 않으며 근거가 부족하면 ‘추가 확인’으로 표시합니다.")

    business_lines, business_source = _business_lines(stock, research)
    financial = _financial(stock, research)
    disclosures = _disclosures(stock)
    opportunities, risks = _opportunities_and_risks(stock, research, financial, disclosures)
    edge_text, edge_source, edge_date = _edge(research)
    indicator = _next_indicator(financial, disclosures)
    journal = _journal(stock, research, financial, opportunities, risks, indicator, edge_text)

    left, right = st.columns([1, 1], gap="large")
    with left, st.container(border=True):
        st.subheader("1. 주요 사업과 돈을 버는 구조")
        for line in business_lines:
            st.write("• " + line)
        _source_caption((research or {}).get("as_of") or (stock.get("report") or {}).get("fetched"), business_source)

    with right, st.container(border=True):
        st.subheader("2. 실적 변화")
        if financial:
            unit = financial.get("unit", "")
            revenue_change = _pct(financial.get("revenue"), financial.get("prior_revenue"))
            profit_change = _pct(financial.get("profit"), financial.get("prior_profit"))
            rows = [
                {"항목": "매출", "현재": financial.get("revenue"), "비교": financial.get("prior_revenue"), "변화": None if revenue_change is None else f"{revenue_change:+.1f}%"},
                {"항목": "영업이익", "현재": financial.get("profit"), "비교": financial.get("prior_profit"), "변화": None if profit_change is None else f"{profit_change:+.1f}%"},
            ]
            st.dataframe(rows, hide_index=True, use_container_width=True)
            st.caption(f"{financial.get('period','')} / 비교 {financial.get('prior_period','')} · {financial.get('basis','')} · {unit}")
            _source_caption(financial.get("date"), financial.get("source"))
        else:
            st.info("비교 가능한 공식 실적은 추가 확인이 필요합니다.")

    with st.container(border=True):
        st.subheader("3. 최근 공시에서 확인된 사실")
        if disclosures:
            for index, item in enumerate(disclosures[:5], start=1):
                st.write(f"{index}. {item.get('date','')} · {item.get('title','제목 확인 필요')}")
                if item.get("url"):
                    st.markdown(f"[공시 원문]({item['url']})")
        else:
            st.info("현재 저장된 공식 공시가 없습니다. 공시가 없다는 확정 의미는 아닙니다.")

    c1, c2 = st.columns(2, gap="large")
    with c1, st.container(border=True):
        st.subheader("4. 성장 기회 2가지")
        for index, item in enumerate(opportunities, start=1):
            st.markdown(f"**{index}. {item['title']}**")
            st.write(item["detail"])
            _source_caption(item["date"], item["source"])

    with c2, st.container(border=True):
        st.subheader("5. 확인할 위험 2가지")
        for index, item in enumerate(risks, start=1):
            st.markdown(f"**{index}. {item['title']}**")
            st.write(item["detail"])
            _source_caption(item["date"], item["source"])

    c3, c4 = st.columns(2, gap="large")
    with c3, st.container(border=True):
        st.subheader("6. 경쟁력·엣지")
        if edge_text == "추가 확인":
            st.warning("추가 확인")
            st.write("현재 저장 자료에는 경쟁우위·점유율·기술 우위 등을 입증할 직접 근거가 없습니다.")
        else:
            st.write(edge_text)
        _source_caption(edge_date, edge_source)

    with c4, st.container(border=True):
        st.subheader("7. 다음에 확인할 지표")
        st.markdown("**" + indicator[0] + "**")
        st.write(indicator[1])

    with st.container(border=True):
        st.subheader("8. 투자일지 초안")
        st.text_area("초안", value=journal, height=210, key=f"verification_journal_{selected}")
        if not sample_mode:
            if st.button("이 초안을 투자일지에 저장", key=f"save_verification_journal_{selected}", type="primary"):
                try:
                    store.log(
                        "journal",
                        {
                            "code": selected,
                            "at": datetime.now(timezone.utc).isoformat(),
                            "kind": "verification-note",
                            "note": journal,
                        },
                    )
                    st.success("검증 리서치 초안을 투자일지에 저장했습니다.")
                except Exception:
                    st.error("투자일지 저장에 실패했습니다. 초안을 복사해 보관하세요.")
