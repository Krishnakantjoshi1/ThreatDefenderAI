# Architecture

One security engine, three interfaces (web dashboard, Chrome extension, desktop launcher).

```
Input (message / URL / page / file)
  -> detectors: url, text, sender, content, file      (deterministic, offline)
  -> Honeycomb: 7 dimensions (money, offer, conversation, identity, urgency, credential, link)
  -> behavior combos + Threat Memory + local threat list
  -> Risk Engine  (noisy-OR evidence fusion -> 0-100 -> SAFE / SUSPICIOUS / DANGEROUS / CRITICAL)
  -> action: ALLOW / WARN / BLOCK   (+ Quarantine on CRITICAL)
  -> Local AI (Phi-3 via Ollama) explains the verdict. It never decides it.
```

| Folder | Role |
|---|---|
| `app/detectors` | URL, text (EN/Hinglish/Hindi), sender, page content, file analysis |
| `app/honeycomb` | 7-dimension aggregation and category naming |
| `app/security` | risk engine, evidence fusion, attack chain, quarantine, protection switch |
| `app/intelligence` | local threat DB, Threat Memory, Scam DNA |
| `app/ai` | Ollama client (loopback only), prompts, explanations |
| `app/modes` | network monitor, AUTO/MANUAL, OFFLINE/HYBRID/ONLINE |
| `app/tools` | online tools (RDAP domain age, optional Safe Browsing, feed download) |
| `app/services` | orchestration used by the API |
| `app/api` | FastAPI routes |
| `frontend/` | dashboard, scanner, history, quarantine, attack story, settings |
| `browser_extension/` | Manifest V3 extension calling the local API |

## Why it is fast
Detection is pure Python rules (about 10 ms per scan). Phi-3 is called afterwards and
separately, so the verdict appears instantly and the AI explanation follows.
The browser extension uses the fast local-only path.

## Risk engine
`final = 100 * (1 - PRODUCT(1 - weight_i * score_i / 100))` over evidence components:
url, text, content, file, sender, behavior, honeycomb breadth, memory, intel, online.
Several independent signals reinforce each other; one weak signal alone stays low.
Thresholds: 0-29 SAFE, 30-59 SUSPICIOUS, 60-79 DANGEROUS, 80-100 CRITICAL (`app/config.py`).
