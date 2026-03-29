"""
Phase 1: SEC Scraper
Fetches 10-K filings from SEC EDGAR using only free public endpoints.

SEC Fair Access compliance:
  - User-Agent must identify the bot and include a contact email.
  - Max 10 requests/second (we target ~6-7 to stay safely under).
  - Reference: https://www.sec.gov/os/accessing-edgar-data
"""

import json
import os
import time
import logging
import requests

from config import (
    EDGAR_SUBMISSIONS_URL,
    EDGAR_ARCHIVE_URL,
    SEC_USER_AGENT,
    SEC_RATE_LIMIT_DELAY,
    SEC_MAX_RETRIES,
    SEC_RETRY_BACKOFF,
    DATA_RAW_DIR,
)

logger = logging.getLogger(__name__)


def _session() -> requests.Session:
    """Return a requests Session pre-configured with the required SEC User-Agent."""
    s = requests.Session()
    s.headers.update({
        "User-Agent": SEC_USER_AGENT,
        "Accept-Encoding": "gzip, deflate",
        "Host": "data.sec.gov",
    })
    return s


def _get(url: str, session: requests.Session, stream: bool = False) -> requests.Response:
    """
    GET a URL with retry logic and rate-limit delay.
    Raises requests.HTTPError on non-2xx after all retries are exhausted.
    """
    delay = SEC_RETRY_BACKOFF
    for attempt in range(1, SEC_MAX_RETRIES + 1):
        try:
            time.sleep(SEC_RATE_LIMIT_DELAY)
            resp = session.get(url, timeout=30, stream=stream)
            resp.raise_for_status()
            return resp
        except requests.RequestException as exc:
            logger.warning("Attempt %d/%d failed for %s: %s", attempt, SEC_MAX_RETRIES, url, exc)
            if attempt == SEC_MAX_RETRIES:
                raise
            time.sleep(delay)
            delay *= 2
    # Should never reach here
    raise RuntimeError("Unreachable")  # pragma: no cover


def get_cik(ticker: str) -> str:
    """
    Look up a company's zero-padded 10-digit CIK from its ticker symbol.

    Uses the EDGAR company_tickers.json endpoint (no auth required).

    Args:
        ticker: Stock ticker symbol, e.g. "AAPL".

    Returns:
        Zero-padded 10-digit CIK string, e.g. "0000320193".

    Raises:
        ValueError: If the ticker is not found in EDGAR.
    """
    url = "https://www.sec.gov/files/company_tickers.json"
    session = _session()
    session.headers.update({"Host": "www.sec.gov"})

    logger.info("Fetching EDGAR company tickers list...")
    resp = _get(url, session)
    tickers_data = resp.json()

    ticker_upper = ticker.upper()
    for entry in tickers_data.values():
        if entry.get("ticker", "").upper() == ticker_upper:
            cik_raw = str(entry["cik_str"])
            cik_padded = cik_raw.zfill(10)
            logger.info("Resolved %s -> CIK %s", ticker, cik_padded)
            return cik_padded

    raise ValueError(f"Ticker '{ticker}' not found in SEC EDGAR company list.")


def get_latest_10k_url(cik: str) -> tuple[str, str]:
    """
    Find the URL and accession number of the most recent 10-K filing for a CIK.

    Args:
        cik: Zero-padded 10-digit CIK string.

    Returns:
        Tuple of (filing_index_url, accession_number).

    Raises:
        ValueError: If no 10-K filing is found for this CIK.
    """
    url = EDGAR_SUBMISSIONS_URL.format(cik=cik)
    session = _session()

    logger.info("Fetching submissions for CIK %s...", cik)
    resp = _get(url, session)
    data = resp.json()

    filings = data.get("filings", {}).get("recent", {})
    forms = filings.get("form", [])
    accessions = filings.get("accessionNumber", [])
    dates = filings.get("filingDate", [])

    # Find the most recent 10-K (not 10-K/A amendment)
    for form, accession, date in zip(forms, accessions, dates):
        if form == "10-K":
            # Accession number format: 0000320193-23-000064
            acc_clean = accession.replace("-", "")
            index_url = f"{EDGAR_ARCHIVE_URL}/{cik.lstrip('0')}/{acc_clean}/{accession}-index.htm"
            logger.info("Found 10-K filed %s, accession %s", date, accession)
            return index_url, accession

    raise ValueError(f"No 10-K filing found for CIK {cik}.")


def _find_primary_doc_url(index_url: str, cik: str, accession: str) -> str:
    """
    Parse the EDGAR filing index page to find the primary 10-K document URL.

    Args:
        index_url: URL of the filing index .htm page.
        cik: Numeric CIK (without leading zeros).
        accession: Accession number with dashes.

    Returns:
        Full URL of the primary 10-K document.
    """
    from bs4 import BeautifulSoup

    session = _session()
    session.headers.update({"Host": "www.sec.gov"})

    logger.info("Fetching filing index: %s", index_url)
    resp = _get(index_url, session)
    soup = BeautifulSoup(resp.text, "lxml")

    acc_clean = accession.replace("-", "")
    base = f"{EDGAR_ARCHIVE_URL}/{cik}/{acc_clean}"

    # The filing index table lists documents; find the 10-K htm document
    for row in soup.find_all("tr"):
        cells = row.find_all("td")
        if len(cells) >= 4:
            doc_type = cells[3].get_text(strip=True)
            if doc_type in ("10-K", "10-K "):
                link_tag = cells[2].find("a")
                if link_tag and link_tag.get("href"):
                    href = link_tag["href"]
                    # href may be relative or absolute
                    if href.startswith("/"):
                        return f"https://www.sec.gov{href}"
                    return f"{base}/{href}"

    # Fallback: return the .htm index itself (some older filings have inline docs)
    logger.warning("Could not identify primary 10-K doc; falling back to index URL.")
    return index_url


def download_10k(ticker: str, force: bool = False) -> str:
    """
    Full pipeline: resolve ticker -> CIK -> find 10-K -> download to local cache.

    Args:
        ticker: Stock ticker symbol.
        force: If True, re-download even if a cached file exists.

    Returns:
        Local file path of the downloaded 10-K HTML.
    """
    ticker = ticker.upper()
    cache_dir = os.path.join(DATA_RAW_DIR, ticker)
    os.makedirs(cache_dir, exist_ok=True)
    cache_path = os.path.join(cache_dir, "10k_latest.html")

    if not force and os.path.exists(cache_path):
        logger.info("Cache hit: %s already exists. Skipping download.", cache_path)
        return cache_path

    # Step 1: resolve ticker to CIK
    cik = get_cik(ticker)

    # Step 2: find the most recent 10-K filing index
    index_url, accession = get_latest_10k_url(cik)

    # Step 3: find the primary document within the filing
    cik_numeric = cik.lstrip("0") or "0"
    primary_url = _find_primary_doc_url(index_url, cik_numeric, accession)

    # Step 4: download the document
    logger.info("Downloading 10-K from %s ...", primary_url)
    session = _session()
    session.headers.update({"Host": "www.sec.gov"})
    resp = _get(primary_url, session)

    with open(cache_path, "w", encoding="utf-8", errors="replace") as f:
        f.write(resp.text)

    logger.info("Saved 10-K to %s (%d bytes)", cache_path, os.path.getsize(cache_path))
    return cache_path
