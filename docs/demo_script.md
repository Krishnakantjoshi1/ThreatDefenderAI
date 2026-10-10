# Live demo (about 3 minutes)

Before: `start.bat`, load the extension, `ollama pull phi3` once, Settings -> Auto mode.

1. **Dashboard** - Protection is on, empty honeycomb.
2. **Scanner -> "Bank KYC scam" -> Scan now** - CRITICAL, honeycomb fills, reasons, attack story, Phi-3 explanation (try Hinglish).
3. **Scanner -> "Genuine OTP"** - SAFE. Shows it is not a keyword blocker.
4. **Chrome** - open `http://secure-login.amazon.account-verify.top/` -> block page.
5. **Offline** - turn Wi-Fi off (or Settings -> "Simulate offline"). Dashboard shows OFFLINE / disconnected. Scan the same scam: same verdict.
6. **Reconnect** - chip returns to HYBRID. Scan result says exactly what (if anything) was sent online.
7. **Quarantine** page - the critical items, with Restore / Delete.

Fallback if something fails: the Scanner example buttons and `python scripts/smoke_test.py` always work.
