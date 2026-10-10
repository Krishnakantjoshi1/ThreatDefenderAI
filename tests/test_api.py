"""HTTP-level tests. Skipped automatically if fastapi/httpx are not installed."""
import unittest

try:
    from fastapi.testclient import TestClient
    from app.main import app
    HAVE = True
except Exception:  # pragma: no cover
    HAVE = False


@unittest.skipUnless(HAVE, "fastapi + httpx not installed (pip install -r requirements.txt httpx)")
class ApiTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.client = TestClient(app)
        cls.client.__enter__()

    @classmethod
    def tearDownClass(cls):
        cls.client.__exit__(None, None, None)

    def test_health(self):
        r = self.client.get("/api/health")
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.json()["status"], "ok")

    def test_scan_scam_and_safe(self):
        bad = self.client.post("/api/scan", json={"content": "URGENT! SBI account blocked. Enter OTP at http://sbi-kyc-update.xyz/login"}).json()
        self.assertEqual(bad["verdict"], "CRITICAL")
        good = self.client.post("/api/scan", json={"content": "See you at lunch"}).json()
        self.assertEqual(good["verdict"], "SAFE")

    def test_validation_errors(self):
        self.assertEqual(self.client.post("/api/scan", json={"content": "  "}).status_code, 400)
        self.assertEqual(self.client.post("/api/scan", json={}).status_code, 422)
        self.assertEqual(self.client.post("/api/scan/file", json={"filename": "a", "content_b64": "!!"}).status_code, 400)

    def test_dashboard_is_served(self):
        self.assertEqual(self.client.get("/").status_code, 200)
        self.assertEqual(self.client.get("/scanner.html").status_code, 200)

    def test_history_stats_quarantine(self):
        self.client.post("/api/scan", json={"content": "Congratulations you won a lottery! Pay processing fee to claim your prize now"})
        self.assertGreaterEqual(len(self.client.get("/api/history").json()["items"]), 1)
        self.assertIn("total_scans", self.client.get("/api/stats").json())
        self.assertIn("items", self.client.get("/api/quarantine").json())

    def test_history_and_scan_pdf_reports(self):
        scan = self.client.post("/api/scan", json={"content": "See you at lunch"}).json()
        scan_id = scan["id"]

        history_report = self.client.get("/api/reports/history.pdf")
        self.assertEqual(history_report.status_code, 200)
        self.assertEqual(history_report.headers["content-type"], "application/pdf")
        self.assertIn("attachment;", history_report.headers["content-disposition"])
        self.assertTrue(history_report.content.startswith(b"%PDF-1.4"))

        scan_report = self.client.get(f"/api/reports/scans/{scan_id}.pdf")
        self.assertEqual(scan_report.status_code, 200)
        self.assertTrue(scan_report.content.startswith(b"%PDF-1.4"))
        self.assertIn(f"threatdefender-scan-{scan_id}.pdf", scan_report.headers["content-disposition"])
        self.assertEqual(self.client.get("/api/reports/scans/999999.pdf").status_code, 404)

    def test_explain_falls_back(self):
        sid = self.client.post("/api/scan", json={"content": "Urgent! Enter your OTP now or account blocked"}).json()["id"]
        ex = self.client.post("/api/explain", json={"scan_id": sid}).json()
        self.assertIn(ex["source"], ("rule-based", "phi3"))
        self.assertEqual(self.client.post("/api/explain", json={"scan_id": 999999}).status_code, 404)

    def test_mode_endpoint_offline(self):
        m = self.client.get("/api/mode").json()
        self.assertEqual(m["effective"], "offline")


if __name__ == "__main__":
    unittest.main()
