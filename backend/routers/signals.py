import os
import time

from cachetools import TTLCache
from fastapi import APIRouter
from groq import Groq

router = APIRouter(prefix="/signals", tags=["signals"])

_signal_cache = TTLCache(maxsize=5, ttl=900)


def _build_prompt(headlines: list[str], indicators: dict) -> str:
    headlines_str = "\n".join(f"- {h}" for h in headlines[:15])
    ind_lines = []
    for key, data in indicators.items():
        if isinstance(data, dict):
            ind_lines.append(f"  {data.get('name', key)}: {data.get('current', 'N/A')}{data.get('unit', '')} (prev: {data.get('previous', 'N/A')}{data.get('unit', '')}, {data.get('direction', '')})")
    indicators_str = "\n".join(ind_lines)

    return f"""You are a senior macro analyst at a top hedge fund. Analyze the following headlines and economic indicators and produce a structured intelligence report.

TODAY'S TOP HEADLINES:
{headlines_str}

CURRENT ECONOMIC INDICATORS:
{indicators_str}

Respond in this EXACT JSON format (no markdown, pure JSON):
{{
  "sentiment": "Bullish" | "Bearish" | "Neutral",
  "sentiment_score": <number from -100 to 100>,
  "risks": [
    {{"title": "<risk title>", "detail": "<1 sentence detail>"}},
    {{"title": "<risk title>", "detail": "<1 sentence detail>"}},
    {{"title": "<risk title>", "detail": "<1 sentence detail>"}}
  ],
  "opportunities": [
    {{"title": "<opportunity title>", "detail": "<1 sentence detail>"}},
    {{"title": "<opportunity title>", "detail": "<1 sentence detail>"}},
    {{"title": "<opportunity title>", "detail": "<1 sentence detail>"}}
  ],
  "geopolitical_brief": "<1 paragraph geopolitical situation summary, 3-4 sentences>",
  "key_theme": "<single most important macro theme in 5-8 words>"
}}"""


@router.post("/analyze")
async def analyze_macro(payload: dict):
    cache_key = "signal"
    if cache_key in _signal_cache:
        return _signal_cache[cache_key]

    groq_api_key = os.getenv("GROQ_API_KEY", "")
    if not groq_api_key:
        return _mock_signal()

    headlines = payload.get("headlines", [])
    indicators = payload.get("indicators", {})

    try:
        client = Groq(api_key=groq_api_key)
        prompt = _build_prompt(headlines, indicators)

        response = client.chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=[
                {"role": "system", "content": "You are a senior macro intelligence analyst. Always respond with valid JSON only, no markdown code blocks."},
                {"role": "user", "content": prompt},
            ],
            max_tokens=800,
            temperature=0.4,
        )

        content = response.choices[0].message.content.strip()
        # Strip markdown code blocks if present
        if content.startswith("```"):
            content = content.split("```")[1]
            if content.startswith("json"):
                content = content[4:]

        import json
        signal_data = json.loads(content)
        result = {"signal": signal_data, "source": "groq/llama-3.1-8b-instant"}
        _signal_cache[cache_key] = result
        return result

    except Exception as e:
        fallback = _mock_signal()
        fallback["error"] = str(e)[:100]
        return fallback


def _mock_signal():
    return {
        "signal": {
            "sentiment": "Neutral",
            "sentiment_score": 5,
            "risks": [
                {"title": "Elevated Interest Rates", "detail": "Persistent high rates continue to pressure growth stocks and real estate valuations."},
                {"title": "Geopolitical Instability", "detail": "Ongoing conflicts in multiple regions threaten global supply chains and energy markets."},
                {"title": "Dollar Strength", "detail": "A strong DXY creates headwinds for emerging markets and multinational earnings."},
            ],
            "opportunities": [
                {"title": "AI Infrastructure Buildout", "detail": "Accelerating AI adoption continues to drive demand for semiconductors and data center equipment."},
                {"title": "Energy Transition", "detail": "Clean energy investments remain robust with substantial policy tailwinds in the US and EU."},
                {"title": "Defense Spending", "detail": "NATO members accelerating defense budgets creates sustained demand for defense contractors."},
            ],
            "geopolitical_brief": "Global markets are navigating a complex environment of persistent inflation, elevated interest rates, and heightened geopolitical tensions. The Federal Reserve's data-dependent stance keeps markets on edge ahead of key economic releases. Energy markets remain sensitive to Middle East developments while the AI-driven tech sector provides a counterbalancing growth narrative.",
            "key_theme": "Fed pivot timing vs. sticky inflation",
        },
        "source": "mock",
    }
