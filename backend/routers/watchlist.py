import asyncio

import yfinance as yf
from cachetools import TTLCache
from fastapi import APIRouter

router = APIRouter(prefix="/watchlist", tags=["watchlist"])

_watchlist_cache = TTLCache(maxsize=5, ttl=900)

WATCHLIST = ["NVDA", "PLTR", "ANET", "MU", "COHR", "CEG", "SPY", "XLE"]


def _fmt_market_cap(val: float | None) -> str:
    if val is None:
        return "N/A"
    if val >= 1e12:
        return f"${val/1e12:.2f}T"
    if val >= 1e9:
        return f"${val/1e9:.2f}B"
    if val >= 1e6:
        return f"${val/1e6:.2f}M"
    return f"${val:,.0f}"


def _fetch_watchlist_item(symbol: str) -> dict:
    try:
        ticker = yf.Ticker(symbol)
        hist = ticker.history(period="2d")
        info = ticker.fast_info

        if hist.empty:
            return {"symbol": symbol, "error": "No data"}

        closes = hist["Close"].tolist()
        current = closes[-1]
        prev_close = closes[-2] if len(closes) >= 2 else closes[0]
        pct_change = ((current - prev_close) / prev_close) * 100 if prev_close else 0

        market_cap = None
        try:
            market_cap = info.market_cap
        except Exception:
            pass

        return {
            "symbol": symbol,
            "price": round(current, 2),
            "prev_close": round(prev_close, 2),
            "change_pct": round(pct_change, 2),
            "change_abs": round(current - prev_close, 2),
            "market_cap": _fmt_market_cap(market_cap),
            "market_cap_raw": market_cap,
        }
    except Exception as e:
        return {"symbol": symbol, "error": str(e)[:60]}


@router.get("/")
async def get_watchlist():
    if "watchlist" in _watchlist_cache:
        return _watchlist_cache["watchlist"]

    loop = asyncio.get_event_loop()
    tasks = [loop.run_in_executor(None, _fetch_watchlist_item, s) for s in WATCHLIST]
    results = await asyncio.gather(*tasks)

    result = {"tickers": list(results)}
    _watchlist_cache["watchlist"] = result
    return result
