import asyncio
import hashlib
import os
import time
from typing import Optional

import feedparser
import httpx
from cachetools import TTLCache
from fastapi import APIRouter, Query
from groq import Groq

router = APIRouter(prefix="/news", tags=["news"])

# Cache: article_hash -> summary, TTL = 6 hours
_summary_cache: dict[str, str] = {}
# Cache full news response for 15 min
_news_cache = TTLCache(maxsize=10, ttl=900)

CATEGORIES = {
    "geopolitics": ["geopolitics", "war", "conflict", "NATO", "sanctions", "diplomacy", "military"],
    "energy": ["oil", "gas", "OPEC", "energy", "pipeline", "LNG", "petroleum", "crude"],
    "central_banks": ["Fed", "Federal Reserve", "ECB", "central bank", "interest rate", "inflation", "monetary policy", "Powell", "Lagarde"],
    "tech": ["AI", "artificial intelligence", "semiconductor", "tech", "chip", "quantum", "cyber"],
    "defense": ["defense", "Pentagon", "arms", "weapons", "missile", "drone", "military spending"],
}

RSS_FEEDS = [
    ("Reuters", "https://feeds.reuters.com/reuters/worldNews"),
    ("Reuters Business", "https://feeds.reuters.com/reuters/businessNews"),
    ("Al Jazeera", "https://www.aljazeera.com/xml/rss/all.xml"),
    ("FT", "https://www.ft.com/rss/home/uk"),
]

NEWSAPI_QUERIES = [
    ("geopolitics", "geopolitics OR war OR sanctions OR NATO OR diplomacy"),
    ("energy", "oil price OR OPEC OR energy market OR LNG"),
    ("central_banks", "Federal Reserve OR ECB OR interest rates OR inflation"),
    ("tech", "AI chip OR semiconductor OR artificial intelligence"),
    ("defense", "defense spending OR Pentagon OR military"),
]


def _article_hash(url: str) -> str:
    return hashlib.md5(url.encode()).hexdigest()


async def _get_groq_summary(text: str, client: Groq) -> str:
    try:
        response = client.chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=[
                {
                    "role": "system",
                    "content": "You are a geopolitical and financial analyst. Summarize the following news article in exactly 2 concise sentences, focusing on key facts and implications. Be direct and analytical.",
                },
                {"role": "user", "content": f"Summarize this article:\n\n{text[:1500]}"},
            ],
            max_tokens=120,
            temperature=0.3,
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        return f"Summary unavailable: {str(e)[:60]}"


async def _fetch_rss() -> list[dict]:
    articles = []
    loop = asyncio.get_event_loop()

    async def parse_feed(name: str, url: str):
        try:
            feed = await loop.run_in_executor(None, feedparser.parse, url)
            for entry in feed.entries[:8]:
                articles.append({
                    "title": entry.get("title", ""),
                    "url": entry.get("link", ""),
                    "source": name,
                    "published": entry.get("published", ""),
                    "description": entry.get("summary", entry.get("description", ""))[:500],
                })
        except Exception:
            pass

    await asyncio.gather(*[parse_feed(n, u) for n, u in RSS_FEEDS])
    return articles


async def _fetch_newsapi(api_key: str) -> list[dict]:
    articles = []
    async with httpx.AsyncClient(timeout=10) as client:
        for category, query in NEWSAPI_QUERIES:
            try:
                resp = await client.get(
                    "https://newsapi.org/v2/everything",
                    params={
                        "q": query,
                        "apiKey": api_key,
                        "language": "en",
                        "sortBy": "publishedAt",
                        "pageSize": 5,
                    },
                )
                if resp.status_code == 200:
                    data = resp.json()
                    for art in data.get("articles", []):
                        articles.append({
                            "title": art.get("title", ""),
                            "url": art.get("url", ""),
                            "source": art.get("source", {}).get("name", "NewsAPI"),
                            "published": art.get("publishedAt", ""),
                            "description": art.get("description", "") or "",
                            "category_hint": category,
                        })
            except Exception:
                pass
    return articles


def _categorize(article: dict) -> str:
    text = (article.get("title", "") + " " + article.get("description", "")).lower()
    for cat, keywords in CATEGORIES.items():
        if any(kw.lower() in text for kw in keywords):
            return cat
    return "geopolitics"


@router.get("/")
async def get_news(category: Optional[str] = Query(None)):
    cache_key = category or "all"
    if cache_key in _news_cache:
        return _news_cache[cache_key]

    news_api_key = os.getenv("NEWS_API_KEY", "")
    groq_api_key = os.getenv("GROQ_API_KEY", "")

    # Fetch from all sources concurrently
    rss_articles = await _fetch_rss()
    newsapi_articles = await _fetch_newsapi(news_api_key) if news_api_key else []

    all_articles = rss_articles + newsapi_articles

    # Deduplicate by URL
    seen = set()
    unique = []
    for art in all_articles:
        if art["url"] and art["url"] not in seen and art["title"]:
            seen.add(art["url"])
            unique.append(art)

    # Categorize
    for art in unique:
        art["category"] = art.get("category_hint") or _categorize(art)

    # Filter by category
    if category and category != "all":
        filtered = [a for a in unique if a["category"] == category]
    else:
        filtered = unique

    filtered = filtered[:40]

    # Add AI summaries (use cache to avoid re-calling Groq)
    if groq_api_key:
        groq_client = Groq(api_key=groq_api_key)
        for art in filtered:
            h = _article_hash(art["url"])
            if h in _summary_cache:
                art["summary"] = _summary_cache[h]
            else:
                text = art.get("title", "") + ". " + art.get("description", "")
                summary = await _get_groq_summary(text, groq_client)
                _summary_cache[h] = summary
                art["summary"] = summary
    else:
        for art in filtered:
            art["summary"] = art.get("description", "")[:200]

    result = {"articles": filtered, "total": len(filtered), "cached_summaries": len(_summary_cache)}
    _news_cache[cache_key] = result
    return result


@router.get("/categories")
async def get_categories():
    return {"categories": list(CATEGORIES.keys())}
