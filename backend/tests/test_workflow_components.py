import unittest

from supply_chain_intel.analysts.geography_analyst import GeographyAnalyst
from supply_chain_intel.config import settings
from supply_chain_intel.analysts.risk_analyst import RiskAnalyst
from supply_chain_intel.parsers.entity_extractor import EntityExtractor
from supply_chain_intel.parsers.tenk_section_parser import TenKSectionParser


class WorkflowComponentTests(unittest.TestCase):
    def test_extracts_item_1_and_item_1a_sections(self):
        raw_html = """
        <html><body>
        <h1>Item 1. Business</h1>
        <p>We depend on ASML Holding N.V. for lithography systems.</p>
        <h1>Item 1A. Risk Factors</h1>
        <p>Supply chain disruptions in Taiwan and Japan may affect production.</p>
        <h1>Item 1B. Unresolved Staff Comments</h1>
        </body></html>
        """
        parser = TenKSectionParser()
        sections = parser.extract_sections(raw_html)

        self.assertIn("ASML", sections["item_1"])
        self.assertIn("Taiwan", sections["item_1a"])

    def test_parser_skips_short_table_of_contents_matches(self):
        raw_html = """
        <html><body>
        <div>Table of Contents Item 1. Business Item 1A. Risk Factors Item 1B. Unresolved Staff Comments</div>
        <ix:nonNumeric>Item 1. Business</ix:nonNumeric>
        <p>{business}</p>
        <ix:nonNumeric>Item 1A. Risk Factors</ix:nonNumeric>
        <p>{risks}</p>
        <ix:nonNumeric>Item 1B. Unresolved Staff Comments</ix:nonNumeric>
        </body></html>
        """.format(
            business=" ".join(["We rely on ASML Holding N.V. for critical systems."] * 30),
            risks=" ".join(["Manufacturing disruption in the Netherlands and Taiwan remains a key risk."] * 30),
        )
        sections = TenKSectionParser().extract_sections(raw_html)

        self.assertIn("ASML Holding", sections["item_1"])
        self.assertIn("Netherlands", sections["item_1a"])
        self.assertGreater(len(sections["item_1"]), 500)

    def test_entity_extractor_finds_dependency_signal(self):
        extractor = EntityExtractor()
        signals = extractor.extract_supplier_signals(
            "We rely on ASML Holding N.V. as a sole-source supplier for key systems.",
            "NVIDIA Corporation",
        )

        self.assertTrue(signals)
        self.assertIn("ASML", signals[0].supplier)
        self.assertGreaterEqual(signals[0].confidence, 0.75)

    def test_risk_and_geography_analysts_classify_text(self):
        geography = GeographyAnalyst().analyze(
            "Manufacturing relies on suppliers in Taiwan and the U.S.",
            "War, export control, and logistics issues in the Netherlands, Taiwan, and Japan could disrupt production.",
        )
        risks = RiskAnalyst().analyze(
            "War, export control, and logistics issues in Taiwan and Japan could disrupt production."
        )

        detected = {item.geography for item in geography}
        self.assertTrue({"Taiwan", "Japan", "Netherlands", "United States"}.issubset(detected))
        self.assertTrue(any(item.category in {"geopolitical", "logistics", "manufacturing"} for item in risks))

    def test_settings_warn_on_placeholder_sec_identity(self):
        self.assertIsNotNone(settings.sec_identity_warning)
        self.assertIn("placeholder", settings.sec_identity_warning.lower())


if __name__ == "__main__":
    unittest.main()
