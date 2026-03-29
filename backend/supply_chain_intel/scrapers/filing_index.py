from __future__ import annotations

from supply_chain_intel.models import FilingMetadata
from supply_chain_intel.scrapers.sec_client import SECClient


TICKERS_URL = "https://www.sec.gov/files/company_tickers.json"


class FilingIndex:
    def __init__(self, client: SECClient | None = None) -> None:
        self.client = client or SECClient()

    def resolve_company(self, ticker: str) -> dict:
        ticker_lookup = ticker.upper().strip()
        payload = self.client.fetch_json(TICKERS_URL)
        for item in payload.values():
            if item["ticker"].upper() == ticker_lookup:
                cik = str(item["cik_str"]).zfill(10)
                return {
                    "ticker": item["ticker"],
                    "company_name": item["title"],
                    "cik": cik,
                }
        raise ValueError(f"Ticker '{ticker}' was not found in the SEC company directory.")

    def latest_10k(self, ticker: str) -> FilingMetadata:
        company = self.resolve_company(ticker)
        submissions_url = f"https://data.sec.gov/submissions/CIK{company['cik']}.json"
        submissions = self.client.fetch_json(submissions_url)
        recent = submissions.get("filings", {}).get("recent", {})
        forms = recent.get("form", [])
        accession_numbers = recent.get("accessionNumber", [])
        filing_dates = recent.get("filingDate", [])
        primary_documents = recent.get("primaryDocument", [])

        for idx, form in enumerate(forms):
            if form != "10-K":
                continue
            accession = accession_numbers[idx]
            accession_compact = accession.replace("-", "")
            primary_document = primary_documents[idx]
            filing_url = (
                f"https://www.sec.gov/Archives/edgar/data/"
                f"{int(company['cik'])}/{accession_compact}/{primary_document}"
            )
            return FilingMetadata(
                ticker=company["ticker"],
                company_name=company["company_name"],
                cik=company["cik"],
                accession_number=accession,
                filing_date=filing_dates[idx],
                primary_document=primary_document,
                filing_url=filing_url,
            )
        raise ValueError(f"No recent 10-K filing found for {ticker.upper()}.")
