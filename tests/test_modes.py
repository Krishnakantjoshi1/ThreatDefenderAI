import os
import unittest

from app.database import repository as repo
from app.modes import mode_state
from app.modes.controller import resolve_mode


class ModeTests(unittest.TestCase):
    """The test suite runs with TD_FORCE_OFFLINE=1, i.e. the internet is 'down'."""

    def tearDown(self):
        mode_state.set_preference("auto", "hybrid")

    def test_auto_without_internet_is_offline(self):
        mode_state.set_preference("auto")
        m = resolve_mode()
        self.assertEqual((m["effective"], m["network"]), ("offline", "disconnected"))
        self.assertEqual(m["available_modes"], ["offline"])

    def test_manual_online_falls_back_honestly(self):
        mode_state.set_preference("manual", "online")
        m = resolve_mode()
        self.assertEqual(m["effective"], "offline")
        self.assertTrue(m["fallback"])
        self.assertIn("FALLBACK", m["note"])

    def test_manual_offline_is_not_a_fallback(self):
        mode_state.set_preference("manual", "offline")
        self.assertFalse(resolve_mode()["fallback"])

    def test_invalid_values_rejected(self):
        with self.assertRaises(ValueError):
            mode_state.set_preference("sometimes")
        with self.assertRaises(ValueError):
            mode_state.set_preference("manual", "cloud")

    def test_no_online_calls_when_offline(self):
        from app.tools.tool_registry import run_online_tools
        rep = run_online_tools([{"host": "x.top", "registered_domain": "x.top", "score": 50, "url": "http://x.top"}], "offline")
        self.assertFalse(rep["used"])
        self.assertEqual(rep["sent"], [])


if __name__ == "__main__":
    unittest.main()
