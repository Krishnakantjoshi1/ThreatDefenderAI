import unittest

from app.detectors.text_detector import analyze_text


class TextDetectorTests(unittest.TestCase):
    def test_bank_scam_is_high(self):
        r = analyze_text("URGENT! Your SBI account will be blocked today. Enter your OTP now.")
        self.assertGreaterEqual(r["score"], 80)
        self.assertGreaterEqual(r["dimension_scores"]["credential"], 60)
        self.assertGreaterEqual(r["dimension_scores"]["urgency"], 40)

    def test_hinglish(self):
        self.assertGreaterEqual(analyze_text("Aapka SBI account aaj band ho jayega. Turant OTP bataiye.")["score"], 80)

    def test_genuine_otp_notice_is_safe(self):
        r = analyze_text("Your OTP is 482913. Do not share it with anyone. - HDFC Bank")
        self.assertLess(r["score"], 15)
        self.assertTrue(r["legit_notice"])

    def test_ordinary_messages_are_safe(self):
        for t in ["Hey, are we still meeting for lunch tomorrow at 1pm?",
                  "Congratulations on your promotion! Proud of you.",
                  "Your Amazon order #4021 has been shipped and will arrive tomorrow."]:
            self.assertLess(analyze_text(t)["score"], 20, t)

    def test_zero_width_evasion(self):
        r = analyze_text("Ur\u200bgent! Enter your O\u200bTP immediately")
        self.assertGreaterEqual(r["score"], 60)

    def test_empty(self):
        self.assertEqual(analyze_text("")["score"], 0)


if __name__ == "__main__":
    unittest.main()
