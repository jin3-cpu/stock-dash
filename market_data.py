from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor, as_completed
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

SECTOR_PROXIES = {
    "반도체": "SOXX",
    "IT": "XLK",
    "산업재": "XLI",
    "자동차·소비": "XLY",
    "금융": "XLF",
    "에너지": "XLE",
    "헬스케어": "XLV",
    "통신": "XLC",
    "소재": "XLB",
    "유틸리티": "XLU",
    "부동산": "XLRE",
    "바이오": "IBB",
}

SECTOR_REFERENCE = {
    "반도체": ("반도체", "SOXX"),
    "전력기기": ("산업재", "XLI"),
    "배터리": ("배터리", "LIT"),
    "로봇": ("로봇", "BOTZ"),
    "방산": ("방산", "ITA"),
    "바이오·제약": ("바이오", "IBB"),
    "소프트웨어": ("소프트웨어", "IGV"),
}

_YAHOO_CHART = "https://query1.finance.yahoo.com/v8/finance/chart/{symbol}"
_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 Chrome/142 Safari/537.36"
    )
}


def _format_value(value: float, kind: str) -> str:
    if kind == "fx":
        return f"{value:,.1f}원"
    if kind == "usd":
        return f"${value:,.2f}"
    return f"{value:,.2f}"


def _fetch_chart(symbol: str, range_: str = "1mo", interval: str = "1d") -> dict:
    response = requests.get(
        _YAHOO_CHART.format(symbol=symbol),
        params={"range": range_, "interval": interval, "includePrePost": "false"},
        headers=_HEADERS,
        timeout=(4, 7),
    )
    response.raise_for_status()
    payload = response.json().get("chart", {})
    if payload.get("error"):
        raise ValueError(str(payload["error"]))
    results = payload.get("result") or []
    if not results:
        raise ValueError("market result missing")
    result = results[0]
    meta = result.get("meta") or {}
    timestamps = result.get("timestamp") or []
    quotes = ((result.get("indicators") or {}).get("quote") or [{}])[0]
    raw_closes = quotes.get("close") or []
    rows = []
    for stamp, close in zip(timestamps, raw_closes):
        if close is None:
            continue
        rows.append(
            {
                "date": datetime.fromtimestamp(int(stamp), tz=timezone.utc).date().isoformat(),
                "close": float(close),
            }
        )
    current = meta.get("regularMarketPrice")
    if current is None and rows:
        current = rows[-1]["close"]
    if current is None:
        raise ValueError("market price missing")
    previous = None
    if len(rows) >= 2:
        previous = rows[-2]["close"]
    if previous is None:
        previous = meta.get("chartPreviousClose") or meta.get("previousClose") or current
    current = float(current)
    previous = float(previous)
    change_pct = ((current - previous) / previous * 100.0) if previous else 0.0
    regular_time = meta.get("regularMarketTime")
    checked = None
    if regular_time:
        checked = (
            datetime.fromtimestamp(int(regular_time), tz=timezone.utc)
            .astimezone(ZoneInfo("Asia/Seoul"))
            .strftime("%m-%d %H:%M")
        )
    return {
        "current": current,
        "previous": previous,
        "change_pct": change_pct,
        "checked": checked or "기준시각 확인 필요",
        "rows": rows,
    }


def _market_one(item: tuple[str, dict]) -> tuple[str, dict]:
    label, spec = item
    data = _fetch_chart(spec["symbol"], "1mo", "1d")
    return label, {
        **data,
        "value": _format_value(data["current"], spec["kind"]),
        "note": f"{data['change_pct']:+.2f}% · {data['checked']}",
        "status": "Yahoo Finance · 지연 시세 가능",
    }


@st.cache_data(ttl=300, show_spinner=False)
def market_snapshots() -> dict[str, dict]:
    result: dict[str, dict] = {}
    with ThreadPoolExecutor(max_workers=5) as pool:
        futures = {pool.submit(_market_one, item): item[0] for item in MARKETS.items()}
        for future in as_completed(futures):
            label = futures[future]
            try:
                key, data = future.result()
                result[key] = data
            except (requests.RequestException, ValueError, KeyError, TypeError, IndexError):
                result[label] = {
                    "value": "연결 확인",
                    "note": "시장 데이터 응답을 확인하세요",
                    "status": "Yahoo Finance",
                    "current": None,
                    "previous": None,
                    "change_pct": None,
                    "checked": "응답 확인 필요",
                    "rows": [],
                }
    return result


@st.cache_data(ttl=300, show_spinner=False)
def market_snapshot(label: str) -> dict:
    spec = MARKETS[label]
    data = _fetch_chart(spec["symbol"], "1mo", "1d")
    return {
        **data,
        "value": _format_value(data["current"], spec["kind"]),
        "note": f"{data['change_pct']:+.2f}% · {data['checked']}",
        "status": "Yahoo Finance · 지연 시세 가능",
    }


@st.cache_data(ttl=600, show_spinner=False)
def market_history(label: str, range_: str = "1y") -> list[dict]:
    spec = MARKETS[label]
    return _fetch_chart(spec["symbol"], range_, "1d")["rows"]


@st.cache_data(ttl=600, show_spinner=False)
def reference_history(symbol: str, range_: str = "1y") -> list[dict]:
    return _fetch_chart(symbol, range_, "1d")["rows"]


def _sector_one(item: tuple[str, str]) -> tuple[str, dict]:
    label, symbol = item
    data = _fetch_chart(symbol, "5d", "1d")
    return label, {
        "symbol": symbol,
        "change_pct": data["change_pct"],
        "current": data["current"],
        "checked": data["checked"],
    }


@st.cache_data(ttl=600, show_spinner=False)
def sector_snapshots() -> dict[str, dict]:
    result: dict[str, dict] = {}
    with ThreadPoolExecutor(max_workers=6) as pool:
        futures = {pool.submit(_sector_one, item): item[0] for item in SECTOR_PROXIES.items()}
        for future in as_completed(futures):
            label = futures[future]
            try:
                key, data = future.result()
                result[key] = data
            except (requests.RequestException, ValueError, KeyError, TypeError, IndexError):
                result[label] = {
                    "symbol": SECTOR_PROXIES[label],
                    "change_pct": None,
                    "current": None,
                    "checked": "응답 확인 필요",
                }
    return result


def safe_market_snapshot(label: str) -> dict:
    try:
        return market_snapshot(label)
    except (requests.RequestException, ValueError, KeyError, TypeError, IndexError):
        return {
            "value": "연결 확인",
            "note": "시장 데이터 응답을 확인하세요",
            "status": "Yahoo Finance",
            "current": None,
            "previous": None,
            "change_pct": None,
            "checked": "응답 확인 필요",
            "rows": [],
        }


def safe_market_history(label: str, range_: str = "1y") -> list[dict]:
    try:
        return market_history(label, range_)
    except (requests.RequestException, ValueError, KeyError, TypeError, IndexError):
        return []


def safe_reference_history(symbol: str, range_: str = "1y") -> list[dict]:
    try:
        return reference_history(symbol, range_)
    except (requests.RequestException, ValueError, KeyError, TypeError, IndexError):
        return []
