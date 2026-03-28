import os

import httpx
from cachetools import TTLCache
from fastapi import APIRouter

router = APIRouter(prefix="/economics", tags=["economics"])

_econ_cache = TTLCache(maxsize=5, ttl=900)

FRED_SERIES = {
    "fed_funds_rate": {
        "id": "FEDFUNDS",
        "name": "Fed Funds Rate",
        "unit": "%",
        "description": "Federal Funds Effective Rate",
    },
    "cpi_yoy": {
        "id": "CPIAUCSL",
        "name": "CPI YoY",
        "unit": "%",
        "description": "Consumer Price Index (YoY)",
        "yoy": True,
    },
    "gdp_growth": {
        "id": "A191RL1Q225SBEA",
        "name": "GDP Growth",
        "unit": "%",
        "description": "Real GDP Growth Rate (QoQ Annualized)",
    },
    "unemployment": {
        "id": "UNRATE",
        "name": "Unemployment Rate",
        "unit": "%",
        "description": "US Unemployment Rate",
    },
    "treasury_10y": {
        "id": "DGS10",
        "name": "10Y Treasury",
        "unit": "%",
        "description": "10-Year Treasury Constant Maturity Rate",
    },
    "wti_oil": {
        "id": "DCOILWTICO",
        "name": "WTI Oil",
        "unit": "$/bbl",
        "description": "WTI Crude Oil Price",
    },
}


async def _fetch_fred_series(series_id: str, api_key: str, limit: int = 3) -> list[dict]:
    async with httpx.AsyncClient(timeout=10) as client:
        resp = await client.get(
            "https://api.stlouisfed.org/fred/series/observations",
            params={
                "series_id": series_id,
                "api_key": api_key,
                "file_type": "json",
                "sort_order": "desc",
                "limit": limit,
            },
        )
        if resp.status_code == 200:
            data = resp.json()
            return [o for o in data.get("observations", []) if o.get("value") != "."]
        return []


def _calc_yoy(observations: list[dict]) -> tuple[float, float]:
    """For monthly data, compute YoY % change using 12-month lag."""
    # observations are desc sorted, we need at least 13
    if len(observations) < 2:
        return 0.0, 0.0
    try:
        current = float(observations[0]["value"])
        previous = float(observations[1]["value"])
        return current, previous
    except (ValueError, IndexError):
        return 0.0, 0.0


def _direction(current: float, previous: float) -> str:
    if current > previous:
        return "up"
    elif current < previous:
        return "down"
    return "flat"


@router.get("/")
async def get_economic_indicators():
    if "indicators" in _econ_cache:
        return _econ_cache["indicators"]

    api_key = os.getenv("FRED_API_KEY", "")
    if not api_key:
        # Return mock data when no API key
        return _mock_indicators()

    import asyncio

    async def fetch_indicator(key: str, meta: dict):
        limit = 14 if meta.get("yoy") else 3
        obs = await _fetch_fred_series(meta["id"], api_key, limit=limit)
        if not obs:
            return key, None

        current_val, prev_val = _calc_yoy(obs)

        if meta.get("yoy") and len(obs) >= 13:
            try:
                curr_raw = float(obs[0]["value"])
                prev_year = float(obs[12]["value"])
                current_val = round(((curr_raw - prev_year) / prev_year) * 100, 2)
                prev_raw2 = float(obs[1]["value"])
                prev_year2 = float(obs[13]["value"]) if len(obs) > 13 else prev_year
                prev_val = round(((prev_raw2 - prev_year2) / prev_year2) * 100, 2)
            except (ValueError, IndexError, ZeroDivisionError):
                pass

        return key, {
            "key": key,
            "name": meta["name"],
            "unit": meta["unit"],
            "description": meta["description"],
            "current": round(current_val, 3),
            "previous": round(prev_val, 3),
            "direction": _direction(current_val, prev_val),
            "date": obs[0].get("date", ""),
        }

    tasks = [fetch_indicator(k, v) for k, v in FRED_SERIES.items()]
    results = await asyncio.gather(*tasks)

    indicators = {}
    for key, data in results:
        if data:
            indicators[key] = data

    result = {"indicators": indicators}
    _econ_cache["indicators"] = result
    return result


def _mock_indicators():
    return {
        "indicators": {
            "fed_funds_rate": {"key": "fed_funds_rate", "name": "Fed Funds Rate", "unit": "%", "description": "Federal Funds Effective Rate", "current": 5.33, "previous": 5.33, "direction": "flat", "date": "2024-01-01"},
            "cpi_yoy": {"key": "cpi_yoy", "name": "CPI YoY", "unit": "%", "description": "Consumer Price Index (YoY)", "current": 3.1, "previous": 3.4, "direction": "down", "date": "2024-01-01"},
            "gdp_growth": {"key": "gdp_growth", "name": "GDP Growth", "unit": "%", "description": "Real GDP Growth Rate (QoQ Annualized)", "current": 3.3, "previous": 4.9, "direction": "down", "date": "2024-01-01"},
            "unemployment": {"key": "unemployment", "name": "Unemployment Rate", "unit": "%", "description": "US Unemployment Rate", "current": 3.7, "previous": 3.7, "direction": "flat", "date": "2024-01-01"},
            "treasury_10y": {"key": "treasury_10y", "name": "10Y Treasury", "unit": "%", "description": "10-Year Treasury Constant Maturity Rate", "current": 4.15, "previous": 3.88, "direction": "up", "date": "2024-01-01"},
            "wti_oil": {"key": "wti_oil", "name": "WTI Oil", "unit": "$/bbl", "description": "WTI Crude Oil Price", "current": 72.4, "previous": 70.1, "direction": "up", "date": "2024-01-01"},
        }
    }
