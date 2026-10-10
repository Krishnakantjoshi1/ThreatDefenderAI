# Privacy design

* All detection runs on this computer.
* The Ollama address must be loopback (127.0.0.1 / localhost). Anything else is refused,
  so message text can never be sent to a remote AI by accident.
* OFFLINE mode makes no network calls at all.
* HYBRID sends only a registered domain name (e.g. `example.top`) to DNS and rdap.org.
  ONLINE may additionally send a full URL to Google Safe Browsing, only if you set a key.
* Every scan result lists exactly what was sent (`online.sent`) and shows it in the UI.
* History keeps a masked 80-character preview and a one-way fingerprint, not the message.
  Turning off "keep preview" removes even the preview and the matched snippets.
* Threat Memory stores fingerprint, category, risk score, timestamps. Not the message.
* The API only accepts browser calls from this computer's pages and the extension.
* Files are inspected as bytes, never executed. Quarantined files are stored with a
  random name and a `.quarantined` extension.
* The extension sends page text (to localhost only) only when a page has a password field.
