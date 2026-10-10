"""Run AFTER starting the server (python run.py):   python scripts/smoke_test.py
Checks the real HTTP server end to end and prints PASS/FAIL for each step."""
import base64
import json
import sys
import urllib.error
import urllib.request

BASE = sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:8000"
failures = 0


def call(method, path, body=None):
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(BASE + path, data=data, method=method, headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            raw = r.read()
            return r.status, (json.loads(raw) if raw[:1] in (b"{", b"[") else raw.decode("utf-8", "ignore"))
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode("utf-8", "ignore")
    except OSError as e:
        return 0, str(e)


def check(name, ok, info=""):
    global failures
    failures += 0 if ok else 1
    print(("PASS  " if ok else "FAIL  ") + name + (f"  [{info}]" if info else ""))


s, r = call("GET", "/api/health")
if s != 200:
    print(f"FAIL  server not reachable at {BASE} ({r}). Start it with: python run.py")
    sys.exit(1)
check("health", r.get("status") == "ok", f"mode={r['mode']['effective']} network={r['mode']['network']}")

scam = "URGENT! Your SBI account will be blocked today. Verify your account immediately and claim your Rs 5000 cashback. Enter your OTP here: http://sbi-kyc-update.xyz/login"
s, r = call("POST", "/api/scan", {"content": scam})
check("scam message -> CRITICAL", s == 200 and r["verdict"] == "CRITICAL", f"score={r.get('score')} {r.get('latency_ms')}ms")
sid = r.get("id")
s, r = call("POST", "/api/scan", {"content": "Your OTP is 482913. Do not share it with anyone. - HDFC Bank"})
check("genuine OTP notice -> SAFE", s == 200 and r["verdict"] == "SAFE", f"score={r.get('score')}")
s, r = call("POST", "/api/scan", {"content": "http://secure-login.amazon.account-verify.top/signin", "online": False})
check("phishing URL -> BLOCK", s == 200 and r["action"] == "BLOCK", f"score={r.get('score')}")
s, r = call("POST", "/api/scan/page", {"url": "http://hdfc-secure-login.top/x", "text": "Enter password and OTP urgently", "has_password_field": True, "forms": [{"action": "http://evil.xyz/c"}]})
check("page scan -> BLOCK", s == 200 and r["action"] == "BLOCK", f"score={r.get('score')}")
s, r = call("POST", "/api/scan/file", {"filename": "invoice.pdf.exe", "content_b64": base64.b64encode(b"MZ\x90\x00").decode()})
check("file scan -> quarantined", s == 200 and bool(r.get("quarantine")), f"score={r.get('score')}")
s, r = call("POST", "/api/explain", {"scan_id": sid, "content": scam, "lang": "en"})
check("explain", s == 200 and bool(r.get("why")), f"source={r.get('source')}")
s, r = call("GET", "/api/history")
check("history", s == 200 and len(r["items"]) >= 3)
s, r = call("GET", "/api/quarantine")
check("quarantine list", s == 200 and len(r["items"]) >= 1)
s, r = call("GET", "/api/stats")
check("stats", s == 200 and r["total_scans"] >= 4)
s, r = call("GET", "/api/ai/status")
check("local AI status (informational)", s == 200, r.get("detail", ""))
for page in ("/", "/scanner.html", "/history.html", "/quarantine.html", "/settings.html", "/attack_story.html", "/js/app.js", "/css/style.css"):
    s, _ = call("GET", page)
    check("serves " + page, s == 200)
print("\nALL PASSED" if failures == 0 else f"\n{failures} CHECK(S) FAILED")
sys.exit(1 if failures else 0)
