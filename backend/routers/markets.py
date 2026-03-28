import asyncio
from datetime import datetime, timedelta

import yfinance as yf
from cachetools import TTLCache
from fastapi import APIRouter

router = APIRouter(prefix="/markets", tags=["markets"])

_markets_cache = TTLCache(maxsize=5, ttl=900)

MARKET_TICKERS = {
    "SPY": {"name": "S&P 500 ETF", "type": "equity"},
    "QQQ": {"name": "Nasdaq 100 ETF", "type": "equity"},
    "DX-Y.NYB": {"name": "US Dollar Index", "type": "forex"},
    "GLD": {"name": "Gold ETF", "type": "commodity"},
    "USO": {"name": "Oil ETF", "type": "commodity"},
    "TLT": {"name": "20Y Treasury ETF", "type": "bond"},
}


def _fetch_ticker_data(symbol: str) -> dict | None:
    try:
        ticker = yf.Ticker(symbol)
        hist = ticker.history(period="7d")
        if hist.empty:
            return None

        closes = hist["Close"].tolist()
        if not closes:
            return None

        current = closes[-1]
        prev_close = closes[-2] if len(closes) >= 2 else closes[0]
        pct_change = ((current - prev_close) / prev_close) * 100 if prev_close else 0

        # 5-day sparkline: last 5 daily closes
        sparkline = closes[-5:] if len(closes) >= 5 else closes

        info = ticker.fast_info
        display_name = MARKET_TICKERS.get(symbol, {}).get("name", symbol)
        if symbol == "DX-Y.NYB":
            display_symbol = "DXY"
        else:
            display_symbol = symbol

        return {
            "symbol": display_symbol,
            "original_symbol": symbol,
            "name": display_name,
            "type": MARKET_TICKERS.get(symbol, {}).get("type", "equity"),
            "price": round(current, 2),
            "prev_close": round(prev_close, 2),
            "change_pct": round(pct_change, 2),
            "change_abs": round(current - prev_close, 2),
            "sparkline": [round(v, 2) for v in sparkline],
            "currency": "USD",
        }
    except Exception as e:
        return {"symbol": symbol, "error": str(e)}


@router.get("/")
async def get_markets():
    if "markets" in _markets_cache:
        return _markets_cache["markets"]

    loop = asyncio.get_event_loop()

    tasks = [
        loop.run_in_executor(None, _fetch_ticker_data, symbol)
        for symbol in MARKET_TICKERS.keys()
    ]
    results = await asyncio.gather(*tasks)

    markets = {}
    for symbol, data in zip(MARKET_TICKERS.keys(), results):
        display_symbol = "DXY" if symbol == "DX-Y.NYB" else symbol
        if data:
            markets[display_symbol] = data

    result = {"markets": markets, "timestamp": datetime.utcnow().isoformat()}
    _markets_cache["markets"] = result
    return result
