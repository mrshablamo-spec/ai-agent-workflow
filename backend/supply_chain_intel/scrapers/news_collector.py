from __future__ import annotations

from urllib.parse import quote_plus

import feedparser

from supply_chain_intel.config import settings
from supply_chain_intel.models import NewsSignal
from supply_chain_intel.utils.text_utils import normalize_whitespace


class NewsCollector:
    def collect(self, company_name: str, entities: list[str]) -> list[NewsSignal]:
        query_terms = [company_name, *entities[:4]]
        query = quote_plus(" OR ".join(query_terms))
        feed_url = f"https://news.google.com/rss/search?q={query}"
        feed = feedparser.parse(feed_url)
        results: list[NewsSignal] = []
        lower_entities = {entity.lower() for entity in entities}

        for entry in feed.entries[: settings.max_news_items]:
            summary = normalize_whitespace(getattr(entry, "summary", ""))
            haystack = f"{entry.title} {summary}".lower()
            matched = [entity for entity in entities if entity.lower() in haystack]
            if not matched and lower_entities:
                continue
            results.append(
                NewsSignal(
                    title=entry.title,
                    source=getattr(getattr(entry, "source", None), "title", "Google News"),
                    published=getattr(entry, "published", ""),
                    link=entry.link,
                    summary=summary,
                    matched_entities=matched,
                )
            )
        return results
