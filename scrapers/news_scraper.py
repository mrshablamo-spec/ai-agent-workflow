"""
Phase 5 support: News Scraper
Fetches recent news headlines for a given entity using Google News RSS.
No API key required — uses public RSS feeds via BeautifulSoup.
"""

import logging
import time
import urllib.parse
import requests
from bs4 import BeautifulSoup

from config import (
    NEWS_RSS_TEMPLATE,
    NEWS_MAX_HEADLINES,
    NEWS_REQUEST_DELAY,
    SEC_USER_AGENT,
)

logger = logging.getLogger(__name__)


def _fetch_rss(url: str) -> str:
    """Fetch raw RSS XML from a URL."""
    headers = {
        "User-Agent": SEC_USER_AGENT,
        "Accept": "application/rss+xml, application/xml, text/xml, */*",
    }
    resp = requests.get(url, headers=headers, timeout=15)
    resp.raise_for_status()
    return resp.text


def get_headlines(entity: str, max_results: int = NEWS_MAX_HEADLINES) -> list[dict]:
    """
    Fetch recent news headlines for an entity from Google News RSS.

    Args:
        entity: Company name, country, or search term.
        max_results: Maximum number of headlines to return.

    Returns:
        List of dicts with keys: title, source, link, published.
    """
    query = urllib.parse.quote_plus(f"{entity} supply chain")
    url = NEWS_RSS_TEMPLATE.format(query=query)

    logger.info("Fetching news for '%s'...", entity)
    time.sleep(NEWS_REQUEST_DELAY)

    try:
        xml = _fetch_rss(url)
    except requests.RequestException as exc:
        logger.warning("News fetch failed for '%s': %s", entity, exc)
        return []

    soup = BeautifulSoup(xml, "lxml-xml")
    items = soup.find_all("item")

    headlines = []
    for item in items[:max_results]:
        title_tag = item.find("title")
        source_tag = item.find("source")
        link_tag = item.find("link")
        pub_tag = item.find("pubDate")

        headlines.append({
            "entity": entity,
            "title": title_tag.get_text(strip=True) if title_tag else "",
            "source": source_tag.get_text(strip=True) if source_tag else "",
            "link": link_tag.get_text(strip=True) if link_tag else "",
            "published": pub_tag.get_text(strip=True) if pub_tag else "",
        })

    logger.info("Found %d headlines for '%s'", len(headlines), entity)
    return headlines


def get_headlines_batch(entities: list[str], max_per_entity: int = NEWS_MAX_HEADLINES) -> dict[str, list[dict]]:
    """
    Fetch headlines for multiple entities, respecting rate limits.

    Args:
        entities: List of entity names.
        max_per_entity: Max headlines per entity.

    Returns:
        Dict mapping entity name -> list of headline dicts.
    """
    results = {}
    for entity in entities:
        results[entity] = get_headlines(entity, max_results=max_per_entity)
    return results
