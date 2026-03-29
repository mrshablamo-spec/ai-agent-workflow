from __future__ import annotations

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from supply_chain_intel.pipelines.workflow import run_supply_chain_workflow

router = APIRouter(prefix="/supply-chain", tags=["supply-chain"])


class AnalysisRequest(BaseModel):
    ticker: str = Field(..., description="Public ticker symbol, e.g. NVDA")
    include_news: bool = True


@router.get("/health")
def supply_chain_health() -> dict:
    return {
        "status": "ok",
        "engine": "mini-palantir-supply-chain",
        "requires_api_keys": False,
    }


@router.post("/analyze")
def analyze_supply_chain(request: AnalysisRequest) -> dict:
    try:
        return run_supply_chain_workflow(request.ticker, include_news=request.include_news)
    except Exception as exc:  # pragma: no cover - keeps the API ergonomic during live scraping
        raise HTTPException(status_code=400, detail=str(exc)) from exc
