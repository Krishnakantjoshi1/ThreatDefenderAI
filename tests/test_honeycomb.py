import unittest

from app.detectors.text_detector import analyze_text
from app.honeycomb.analyzer import build_honeycomb
from app.honeycomb.dimensions import DIMENSIONS
from app.intelligence.scam_dna import scam_dna
from app.security.attack_chain import build_attack_chain


class HoneycombTests(unittest.TestCase):
    def setUp(self):
        t = analyze_text("URGENT! Your SBI account will be blocked. Verify your account and enter your OTP to claim your cashback.")
        self.inds = t["indicators"]
        self.hc = build_honeycomb(self.inds, [])

    def test_has_seven_dimensions_in_range(self):
        self.assertEqual(set(self.hc["scores"]), set(DIMENSIONS))
        self.assertTrue(all(0 <= v <= 100 for v in self.hc["scores"].values()))

    def test_dominant_and_category(self):
        self.assertIn("credential", self.hc["dominant"])
        self.assertNotEqual(self.hc["category"], "None detected")

    def test_scam_dna_matches_known_pattern(self):
        d = scam_dna(self.hc["scores"])
        self.assertTrue(d["top_matches"])

    def test_attack_chain_ends_with_impact(self):
        chain = build_attack_chain(self.hc["scores"], self.inds, 90)
        self.assertTrue(chain)
        self.assertEqual(chain[-1]["dimension"], "impact")

    def test_empty_gives_no_chain(self):
        hc = build_honeycomb([], [])
        self.assertEqual(build_attack_chain(hc["scores"], [], 0), [])
        self.assertEqual(hc["category"], "None detected")


if __name__ == "__main__":
    unittest.main()
