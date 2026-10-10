# Frontend UI system

## Current implementation

The web UI is plain HTML, CSS, and browser JavaScript served as static files by
FastAPI. There is no React, Tailwind, package manifest, or frontend build step.
The existing files are reused rather than migrating frameworks or replacing the
working detection and extension flows.

| Existing path | Current role |
|---|---|
| `frontend/index.html` | Dashboard entry point, protection overview, live metrics, recent scans |
| `frontend/scanner.html` | Single message/link and file scans; bounded batch workflow UI |
| `frontend/history.html` | Existing history filter/details flow with report download actions |
| `frontend/settings.html` | Existing protection, privacy, and local-intelligence settings |
| `frontend/css/style.css` | Shared responsive dark/light visual tokens, components, focus, and reduced-motion styles |
| `frontend/js/theme.js` | Applies the persisted user-selected theme before shared CSS renders; follows system preference until a choice is saved |
| `frontend/js/app.js` | Shared `TD.api` JSON client, report download transport, navigation, theme toggle, and scan-result rendering |
| `frontend/js/scanner.js` | Existing `/api/scan`, `/api/scan/file`, and `/api/explain` single-scan flows |
| `frontend/js/batch-scan.js` | Batch input validation, one job submission, progress polling, cancellation, and paginated results |
| `frontend/js/history.js` | Existing history list/filter/delete behavior and per-scan PDF actions |
| `frontend/js/report-export.js` | Same-origin, no-store report download actions and visible errors |
| `frontend/js/dashboard.js` | Existing live dashboard metrics and recent scans |
| `frontend/js/settings.js` | Existing settings, local AI, and threat-feed controls |
| `browser_extension/` | Existing Manifest V3 extension; still uses `/api/health`, `/api/scan`, `/api/scan/page`, and `/api/protection` |
| `desktop/launcher.py` | Detects an existing healthy local service or starts one on loopback before opening the dashboard |

## Visual and interaction rules

- Dark is the default palette unless the operating system prefers light. The
  navigation toggle switches between explicit light and dark palettes, saves
  the user's choice locally, and keeps it across app pages and reloads.
- The dashboard Threat signal shows the latest saved threat's actual score and
  recorded attack-dimension scores. It shows an empty state when there is no
  detected threat; the visualization does not invent or simulate metrics.
- Use the shared spacing, panel, border, and risk-color tokens in `style.css`.
  Reserve gradients for subtle backgrounds; do not add decorative fake charts
  or metrics.
- Keep dynamic scan content escaped when constructing markup. Batch results are
  inserted with `textContent`, and batch previews do not echo pasted payloads.
- Keep actions keyboard-operable, use labels and headings, retain visible focus,
  and announce progress/errors using status or alert regions.
- Respect reduced-motion preferences. Keep tables horizontally scrollable on
  narrow screens and constrain batch result rendering to one 25-row page.
- Use the existing `TD.api` helper for JSON requests. It sends same-origin
  credentials, serializes JSON request bodies, applies a timeout, and reports
  HTTP and connection failures. Use `TD.download` for uncached PDF responses;
  it uses same-origin credentials and does not persist report data.

## Existing API usage and pending backend work

The current UI uses these implemented backend paths:

- `POST /api/scan` with `{content, kind, sender, online}`
- `POST /api/scan/file` with `{filename, content_b64}`
- `POST /api/scan/page` for extension page metadata
- `POST /api/explain`
- `GET /api/history?limit=...&min_score=...`, `GET /api/history/{scan_id}`,
  and `DELETE /api/history` or `/api/history/{scan_id}`
- `GET /api/stats`, `GET /api/protection`, `POST /api/protection`,
  `GET/POST /api/settings`, `GET /api/mode`, and local-intelligence status/update
- `GET /api/health`

The batch and report controls target the shared baseline routes:

- `POST /api/scans/batch`
- `GET /api/scans/jobs/{job_id}`
- `GET /api/scans/jobs/{job_id}/results?limit=...&offset=...`
- `POST /api/scans/jobs/{job_id}/cancel`
- `GET /api/reports/scans/{scan_id}.pdf`
- `GET /api/reports/history.pdf`

These batch and PDF endpoints are **not present in the inspected backend**. The
UI handles missing endpoints visibly instead of simulating successful results.
The frontend currently caps a batch at 500 unique items, 20,000 characters per
item, 2 MiB of serialized item data, and 25 displayed results per page. URL
items must use HTTP(S); duplicates are skipped with feedback, and invalid lines
are identified by line number without echoing their contents. Failed results on
the visible page can be explicitly retried as a new batch; successful items are
not resubmitted by that action.

The inspected API also has no login/session routes or authenticated user
identity. The frontend does not create a client-side profile ID or claim that
history, settings, jobs, quarantine, or reports are user-isolated. Those
guarantees require backend authentication and owner-filtered persistence before
they can be represented as available UI functionality. The current history API
does not support offset pagination or search, so the UI does not pretend to
offer those features.

See `docs/api-contract.md` once the backend publishes its implemented contract;
this frontend note records the inspected routes and baseline-dependent controls,
not a substitute backend contract.
