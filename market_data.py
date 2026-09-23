from __future__ import annotations

from datetime import datetime, timezone
from zoneinfo import ZoneInfo

import requests
import streamlit as st


MARKETS = {
    "KOSPI": {"symbol": "^KS11", "kind": "index"},
    "KOSDAQ": {"symbol": "^KQ11", "kind": "index"},
    "USD/KRW": {"symbol": "KRW=X", "kind": "fx"},
    "WTI": {"symbol": "CL=F", "kind": "usd"},
    "GOLD": {"symbol": "GC=F", "kind": "usd"},
}

_YAHOO_CHART = "https://query1.finance.yahoo.com/v8/finance/chart/{symbol}"


def _format_value(value: float, kind: str) -> str:
    if kind == "fx":
        return f"{value:,.1f}원"
    if kind == "usd":
        return f"${value:,.2f}"
    return f"{value:,.2f}"


@st.cache_data(ttl=300, show_spinner=False)
def market_snapshot(label: str) -> dict:
    spec = MARKETS[label]
    response = requests.get(
        _YAHOO_CHART.format(symbol=spec["symbol"]),
        params={"range": "5d", "interval": "1d", "includePrePost": "false"},
        headers={
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 Chrome/142 Safari/537.36"
            )
        },
        timeout=(4, 8),
    )
    response.raise_for_status()
    result = response.json()["chart"]["result"][0]
    meta = result.get("meta") or {}
    closes = [
        float(value)
        for value in ((result.get("indicators") or {}).get("quote") or [{}])[0].get("close", [])
        if value is not None
    ]
    if not closes and meta.get("regularMarketPrice") is None:
        raise ValueError("market price missing")

    current = float(meta.get("regularMarketPrice") or closes[-1])
    previous = closes[-2] if len(closes) >= 2 else float(meta.get("chartPreviousClose") or current)
    change_pct = ((current - previous) / previous * 100) if previous else 0.0

    regular_time = meta.get("regularMarketTime")
    if regular_time:
        checked = (
            datetime.fromtimestamp(int(regular_time), tz=timezone.utc)
            .astimezone(ZoneInfo("Asia/Seoul"))
            .strftime("%m-%d %H:%M")
        )
    else:
        checked = "기준시각 확인 필요"

    return {
        "value": _format_value(current, spec["kind"]),
        "note": f"{change_pct:+.2f}% · {checked}",
        "status": "Yahoo Finance · 지연 시세 가능",
    }


def safe_market_snapshot(label: str) -> dict:
    try:
        return market_snapshot(label)
    except (requests.RequestException, ValueError, KeyError, TypeError, IndexError):
        return {
            "value": "연결 확인",
            "note": "시장 데이터 응답을 확인하세요",
            "status": "Yahoo Finance",
        }
