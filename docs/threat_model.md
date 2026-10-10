# Threat model and honest limits

**Covers:** phishing links, scam messages (English/Hinglish/Hindi), credential-harvesting pages
(via the Chrome extension), suspicious files (static checks), look-alike and brand-impersonating domains.

**Does not cover:** all malware on the operating system, real-time interception of every SMS/email
app, other browsers (Chromium only for now), zero-day exploits, deep malware analysis.

**Known limitations**
* Rule-based detection can miss new wording and can mis-flag unusual legitimate messages.
  Tune patterns in `app/detectors/text_detector.py`; add tests in `tests/`.
* The extension decides on navigation, so the first request may start before the block page appears.
  Chrome's declarativeNetRequest would give stricter blocking (future work).
* The built-in known-bad list is a small seed. Use Settings -> "Download latest phishing list" once while online.
* Phi-3 is a small model: it may phrase explanations imperfectly. The verdict never depends on it.
* Prompt injection: scanned text is passed to Phi-3 inside an "untrusted" block, and the AI cannot change the verdict.
