import unittest

from app.security.risk_engine import compute_risk, verdict_for


class RiskEngineTests(unittest.TestCase):
    def test_thresholds(self):
        self.assertEqual([verdict_for(x) for x in (0, 29, 30, 59, 60, 79, 80, 100)],
                         ["SAFE", "SAFE", "SUSPICIOUS", "SUSPICIOUS", "DANGEROUS", "DANGEROUS", "CRITICAL", "CRITICAL"])

    def test_no_evidence_is_safe(self):
        r = compute_risk({"url": 0, "text": 0})
        self.assertEqual((r["score"], r["verdict"], r["action"]), (0, "SAFE", "ALLOW"))

    def test_signals_reinforce_each_other(self):
        one = compute_risk({"text": 60})["score"]
        two = compute_risk({"text": 60, "url": 60})["score"]
        self.assertGreater(two, one)

    def test_never_exceeds_100(self):
        self.assertLessEqual(compute_risk({"url": 100, "text": 100, "intel": 100, "file": 100})["score"], 100)

    def test_known_bad_is_critical(self):
        self.assertEqual(compute_risk({"intel": 97})["verdict"], "CRITICAL")

    def test_actions(self):
        self.assertEqual(compute_risk({"text": 40})["action"], "WARN")
        self.assertEqual(compute_risk({"text": 100, "url": 100})["action"], "BLOCK")


if __name__ == "__main__":
    unittest.main()
