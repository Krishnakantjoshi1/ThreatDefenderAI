import unittest
from pathlib import Path

from app import config
from app.security import quarantine
from app.services import scan_service
from app.utils.file_utils import safe_filename


class QuarantineTests(unittest.TestCase):
    def test_critical_file_is_isolated_and_inert(self):
        r = scan_service.scan_file("invoice.pdf.exe", b"MZ\x90\x00payload")
        self.assertEqual(r["verdict"], "CRITICAL")
        self.assertTrue(r["quarantine"])
        files = list(config.quarantine_dir().glob("*.quarantined"))
        self.assertTrue(files)
        self.assertFalse(any(f.suffix == ".exe" for f in config.quarantine_dir().iterdir()))

    def test_duplicate_is_not_requarantined(self):
        a = scan_service.scan_file("dup.pdf.exe", b"MZ\x90dup")
        b = scan_service.scan_file("dup.pdf.exe", b"MZ\x90dup")
        self.assertEqual(a["quarantine"]["id"], b["quarantine"]["id"])
        self.assertFalse(b["quarantine"]["new"])

    def test_restore_and_delete(self):
        r = scan_service.scan_file("restore_me.doc.exe", b"MZ\x90restore")
        qid = r["quarantine"]["id"]
        out = quarantine.restore_item(qid)
        self.assertTrue(Path(out["path"]).exists())
        with self.assertRaises(KeyError):
            quarantine.restore_item(qid)  # already restored
        r2 = scan_service.scan_file("delete_me.doc.exe", b"MZ\x90delete")
        self.assertEqual(quarantine.delete_item(r2["quarantine"]["id"])["status"], "deleted")

    def test_path_traversal_blocked(self):
        self.assertEqual(safe_filename("../../etc/passwd"), "passwd")
        self.assertEqual(safe_filename("..\\..\\win.ini"), "win.ini")


if __name__ == "__main__":
    unittest.main()
