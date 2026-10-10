import unittest

from app.detectors.url_detector import analyze_url


class UrlDetectorTests(unittest.TestCase):
    def codes(self, url):
        return {i["code"] for i in analyze_url(url)["indicators"]}

    def test_trusted_sites_score_zero(self):
        for u in ["https://www.google.com/search?q=cats", "https://www.sbi.co.in/web/personal-banking", "https://github.com/a/b"]:
            self.assertEqual(analyze_url(u)["score"], 0, u)

    def test_brand_impersonation(self):
        r = analyze_url("http://secure-login.amazon.account-verify.top/a")
        self.assertIn("brand_impersonation", {i["code"] for i in r["indicators"]})
        self.assertGreaterEqual(r["score"], 80)

    def test_typosquat(self):
        self.assertIn("lookalike", self.codes("https://paypa1.com/signin"))

    def test_ip_host_and_http(self):
        c = self.codes("http://192.168.1.5/verify")
        self.assertTrue({"ip_host", "no_https"} <= c)

    def test_known_bad_domain(self):
        r = analyze_url("http://sbi-kyc-update.xyz/login")
        self.assertTrue(r["known_bad"])
        self.assertGreaterEqual(r["score"], 95)

    def test_shortener_is_suspicious_not_critical(self):
        s = analyze_url("bit.ly/abc")["score"]
        self.assertTrue(30 <= s < 60, s)

    def test_at_symbol_trick(self):
        self.assertIn("at_symbol", self.codes("http://www.sbi.co.in@evil.example.top/login"))

    def test_garbage_does_not_crash(self):
        for u in ["", "http://", "::::", "http://[bad", "a" * 5000]:
            analyze_url(u)


if __name__ == "__main__":
    unittest.main()
