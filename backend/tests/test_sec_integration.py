import unittest
from unittest.mock import MagicMock

from fastapi.testclient import TestClient

from main import app
from supply_chain_intel.models import FilingMetadata
from supply_chain_intel.scrapers.filing_index import FilingIndex


class FilingIndexTests(unittest.TestCase):
    def test_latest_10k_builds_expected_sec_archive_url(self):
        client = MagicMock()
        client.fetch_json.side_effect = [
            {
                "0": {
                    "ticker": "NVDA",
                    "title": "NVIDIA CORP",
                    "cik_str": 1045810,
                }
            },
            {
                "filings": {
                    "recent": {
                        "form": ["10-Q", "10-K"],
                        "accessionNumber": ["0000000000-00-000001", "0001045810-24-000123"],
                        "filingDate": ["2024-04-01", "2024-02-21"],
                        "primaryDocument": ["q1.htm", "nvda-20240128x10k.htm"],
                    }
                }
            },
        ]

        metadata = FilingIndex(client).latest_10k("NVDA")

        self.assertIsInstance(metadata, FilingMetadata)
        self.assertEqual(metadata.cik, "0001045810")
        self.assertEqual(metadata.filing_date, "2024-02-21")
        self.assertTrue(metadata.filing_url.endswith("/1045810/000104581024000123/nvda-20240128x10k.htm"))


class RouterHealthTests(unittest.TestCase):
    def test_supply_chain_health_exposes_sec_warning_shape(self):
        client = TestClient(app)
        response = client.get("/supply-chain/health")
        payload = response.json()

        self.assertEqual(response.status_code, 200)
        self.assertIn("sec_user_agent", payload)
        self.assertIn("warning", payload)


if __name__ == "__main__":
    unittest.main()
