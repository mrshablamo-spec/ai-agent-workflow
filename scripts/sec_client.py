"""
scripts/sec_client.py — The Mouth (Ingestion Layer)

Pulls 10-K filings from SEC EDGAR using only free public endpoints.
Also fetches news headlines via Google News RSS (no API key required).

SEC Fair Access compliance:
  - User-Agent must identify the tool and include a contact email.
  - Max 10 requests/second. This client targets ~6-7 to stay safely under.
  - Reference: https://www.sec.gov/os/accessing-edgar-data

Owner: Codex implements. Claude reviews for Fair Access compliance.
"""

import json
import os
import time
import logging
import urllib.parse
import requests
from bs4 import BeautifulSoup

# ── Config ────────────────────────────────────────────────────────────────────
# Mandatory SEC-compliant headers to avoid rate-limiting.
# IMPORTANT: Replace with your real email before running at scale.
HEADERS = {"User-Agent": "MiniPalantirProject your_email@example.com"}

EDGAR_TICKERS_URL = "https://www.sec.gov/files/company_tickers.json"
EDGAR_SUBMISSIONS_URL = "https://data.sec.gov/submissions/CIK{cik}.json"
EDGAR_ARCHIVE_URL = "https://www.sec.gov/Archives/edgar/data"
NEWS_RSS_TEMPLATE = "https://news.google.com/rss/search?q={query}&hl=en-US&gl=US&ceid=US:en"

RATE_LIMIT_DELAY = 0.15      # seconds between requests (~6-7/sec)
MAX_RETRIES = 3
RETRY_BACKOFF = 2.0          # doubles each retry: 2s, 4s, 8s

# Resolved at runtime from config if available, else fall back to local defaults
try:
    from config import DATA_RAW_DIR
except ImportError:
    DATA_RAW_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "raw")

logger = logging.getLogger(__name__)


# ── HTTP helpers ──────────────────────────────────────────────────────────────

def _session(host: str = "data.sec.gov") -> requests.Session:
    """Return a Session with SEC-compliant headers."""
    s = requests.Session()
    s.headers.update({**HEADERS, "Host": host, "Accept-Encoding": "gzip, deflate"})
    return s


def _get(url: str, session: requests.Session) -> requests.Response:
    """GET with rate limiting and exponential-backoff retry."""
    delay = RETRY_BACKOFF
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            time.sleep(RATE_LIMIT_DELAY)
            resp = session.get(url, timeout=30)
            resp.raise_for_status()
            return resp
        except requests.RequestException as exc:
            logger.warning("Attempt %d/%d failed for %s: %s", attempt, MAX_RETRIES, url, exc)
            if attempt == MAX_RETRIES:
                raise
            time.sleep(delay)
            delay *= 2
    raise RuntimeError("Unreachable")  # pragma: no cover


# ── Public API ────────────────────────────────────────────────────────────────

def get_filing(ticker: str) -> str:
    """
    Top-level convenience function.
    Resolves ticker → CIK → latest 10-K URL → downloads and caches locally.

    Args:
        ticker: Stock ticker symbol, e.g. "AAPL".

    Returns:
        Local file path of the downloaded 10-K HTML.
    """
    return download_10k(ticker, force=False)


def get_cik(ticker: str) -> str:
    """
    Look up a company's zero-padded 10-digit CIK from its ticker symbol.

    Uses SEC's public company_tickers.json endpoint (no auth required).

    Args:
        ticker: Stock ticker symbol, e.g. "AAPL".

    Returns:
        Zero-padded 10-digit CIK string, e.g. "0000320193".

    Raises:
        ValueError: If the ticker is not found in EDGAR.
    """
    session = _session(host="www.sec.gov")
    logger.info("Fetching EDGAR ticker list to resolve %s...", ticker)
    resp = _get(EDGAR_TICKERS_URL, session)
    data = resp.json()

    ticker_upper = ticker.upper()
    for entry in data.values():
        if entry.get("ticker", "").upper() == ticker_upper:
            cik_padded = str(entry["cik_str"]).zfill(10)
            logger.info("Resolved %s -> CIK %s", ticker, cik_padded)
            return cik_padded

    raise ValueError(
        f"Ticker '{ticker}' not found in SEC EDGAR. "
        "Verify the ticker is a valid US public company."
    )


def get_latest_10k_url(cik: str) -> tuple[str, str]:
    """
    Find the filing index URL and accession number of the most recent 10-K.

    Args:
        cik: Zero-padded 10-digit CIK string.

    Returns:
        (filing_index_url, accession_number)

    Raises:
        ValueError: If no 10-K filing exists for this CIK.
    """
    url = EDGAR_SUBMISSIONS_URL.format(cik=cik)
    session = _session(host="data.sec.gov")

    logger.info("Fetching submissions for CIK %s...", cik)
    resp = _get(url, session)
    data = resp.json()

    filings = data.get("filings", {}).get("recent", {})
    forms = filings.get("form", [])
    accessions = filings.get("accessionNumber", [])
    dates = filings.get("filingDate", [])

    for form, accession, date in zip(forms, accessions, dates):
        if form == "10-K":
            acc_clean = accession.replace("-", "")
            cik_numeric = cik.lstrip("0") or "0"
            index_url = (
                f"{EDGAR_ARCHIVE_URL}/{cik_numeric}/{acc_clean}/{accession}-index.htm"
            )
            logger.info("Found 10-K filed %s, accession %s", date, accession)
            return index_url, accession

    raise ValueError(f"No 10-K filing found for CIK {cik}.")


def download_10k(ticker: str, force: bool = False) -> str:
    """
    Full ingestion pipeline: ticker → CIK → 10-K index → primary doc → local cache.

    Caching: If `data/raw/{TICKER}/10k_latest.html` already exists and
    `force=False`, the download is skipped (SEC Fair Access — avoid redundant fetches).

    Args:
        ticker: Stock ticker symbol.
        force: Re-download even if cached file exists.

    Returns:
        Local file path of the cached 10-K HTML.
    """
    ticker = ticker.upper()
    cache_dir = os.path.join(DATA_RAW_DIR, ticker)
    os.makedirs(cache_dir, exist_ok=True)
    cache_path = os.path.join(cache_dir, "10k_latest.html")

    if not force and os.path.exists(cache_path):
        logger.info("Cache hit for %s — skipping download.", ticker)
        return cache_path

    cik = get_cik(ticker)
    index_url, accession = get_latest_10k_url(cik)
    primary_url = _find_primary_doc_url(index_url, cik.lstrip("0") or "0", accession)

    logger.info("Downloading 10-K from %s ...", primary_url)
    session = _session(host="www.sec.gov")
    resp = _get(primary_url, session)

    with open(cache_path, "w", encoding="utf-8", errors="replace") as f:
        f.write(resp.text)

    logger.info("Saved 10-K -> %s (%d bytes)", cache_path, os.path.getsize(cache_path))
    return cache_path


def get_headlines(entity: str, max_results: int = 5) -> list[dict]:
    """
    Fetch recent news headlines for an entity from Google News RSS.
    No API key required.

    Args:
        entity: Company name, country, or any search term.
        max_results: Maximum number of headlines to return.

    Returns:
        List of dicts: {entity, title, source, link, published}
    """
    query = urllib.parse.quote_plus(f"{entity} supply chain")
    url = NEWS_RSS_TEMPLATE.format(query=query)

    logger.info("Fetching news for '%s'...", entity)
    time.sleep(1.0)  # news RSS is more lenient but we still rate-limit

    try:
        headers = {**HEADERS, "Accept": "application/rss+xml, text/xml, */*"}
        resp = requests.get(url, headers=headers, timeout=15)
        resp.raise_for_status()
    except requests.RequestException as exc:
        logger.warning("News fetch failed for '%s': %s", entity, exc)
        return []

    soup = BeautifulSoup(resp.text, "lxml-xml")
    headlines = []
    for item in soup.find_all("item")[:max_results]:
        headlines.append({
            "entity": entity,
            "title": _tag_text(item, "title"),
            "source": _tag_text(item, "source"),
            "link": _tag_text(item, "link"),
            "published": _tag_text(item, "pubDate"),
        })

    logger.info("Found %d headlines for '%s'", len(headlines), entity)
    return headlines


def get_headlines_batch(entities: list[str], max_per_entity: int = 5) -> dict[str, list[dict]]:
    """Fetch headlines for multiple entities with rate limiting."""
    return {entity: get_headlines(entity, max_results=max_per_entity) for entity in entities}


# ── Internal helpers ──────────────────────────────────────────────────────────

def _find_primary_doc_url(index_url: str, cik_numeric: str, accession: str) -> str:
    """
    Parse the EDGAR filing index page to locate the primary 10-K document URL.
    Falls back to the index URL itself if the primary document can't be identified.
    """
    session = _session(host="www.sec.gov")
    logger.info("Parsing filing index: %s", index_url)
    resp = _get(index_url, session)
    soup = BeautifulSoup(resp.text, "lxml")

    acc_clean = accession.replace("-", "")
    base = f"{EDGAR_ARCHIVE_URL}/{cik_numeric}/{acc_clean}"

    for row in soup.find_all("tr"):
        cells = row.find_all("td")
        if len(cells) >= 4:
            doc_type = cells[3].get_text(strip=True)
            if doc_type.strip() in ("10-K", "10-K "):
                link_tag = cells[2].find("a")
                if link_tag and link_tag.get("href"):
                    href = link_tag["href"]
                    if href.startswith("/"):
                        return f"https://www.sec.gov{href}"
                    if href.startswith("http"):
                        return href
                    return f"{base}/{href}"

    logger.warning("Could not identify primary 10-K doc — falling back to index URL.")
    return index_url


def _tag_text(tag, name: str) -> str:
    found = tag.find(name)
    return found.get_text(strip=True) if found else ""
