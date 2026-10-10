import unittest

from app.ai.explanation import explain, parse_sections, quick_explanation
from app.services import scan_service


class AiTests(unittest.TestCase):
    def setUp(self):
        self.r = scan_service.scan_input("URGENT! Your SBI account will be blocked. Enter your OTP at http://sbi-kyc-update.xyz/login", online=False)

    def test_parser(self):
        p = parse_sections("WHY: a. GOAL: b. STORY: c -> d\nACTION: e")
        self.assertEqual((p["why"], p["goal"], p["story"], p["action"]), ("a.", "b.", "c -> d", "e"))

    def test_fallback_when_ollama_missing(self):
        ex = explain(self.r, "text", use_ai=True)   # Ollama is not running in tests
        self.assertEqual(ex["source"], "rule-based")
        self.assertTrue(ex["why"] and ex["action"])

    def test_hinglish_quick_explanation(self):
        ex = quick_explanation(self.r, "hinglish")
        self.assertIn("1930", ex["action"])

    def test_remote_ollama_is_refused(self):
        from app import config
        from app.ai import ollama_client
        old = config.OLLAMA_URL
        config.OLLAMA_URL = "http://evil.example.com:11434"
        try:
            self.assertIsNone(ollama_client.generate("secret message"))
            self.assertFalse(ollama_client.status()["running"])
        finally:
            config.OLLAMA_URL = old


if __name__ == "__main__":
    unittest.main()
