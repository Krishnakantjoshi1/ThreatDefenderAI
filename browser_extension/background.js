// ThreatDefender AI - background service worker.
// It contains NO detection logic: every decision comes from the local engine at API.
const API = "http://127.0.0.1:8000";
const ALLOW_MINUTES = 10;
const COLORS = { SAFE: "#2f7d4f", SUSPICIOUS: "#a86a0c", DANGEROUS: "#c2410c", CRITICAL: "#b42318" };
const cache = new Map();            // url -> { t, result }
let health = { t: 0, ok: false, enabled: true };

async function post(path, body) {
  const r = await fetch(API + path, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) });
  if (!r.ok) throw new Error("API " + r.status);
  return r.json();
}

async function engineStatus() {
  if (Date.now() - health.t < 5000) return health;
  try {
    const r = await fetch(API + "/api/health");
    const j = await r.json();
    health = { t: Date.now(), ok: true, enabled: j.protection_enabled !== false };
  } catch (e) { health = { t: Date.now(), ok: false, enabled: true }; }
  return health;
}

async function isAllowed(host) {
  const { allow = {} } = await chrome.storage.session.get("allow");
  return (allow[host] || 0) > Date.now();
}
async function allowHost(host) {
  const { allow = {} } = await chrome.storage.session.get("allow");
  allow[host] = Date.now() + ALLOW_MINUTES * 60000;
  await chrome.storage.session.set({ allow });
}

function badge(tabId, result) {
  if (!result) { chrome.action.setBadgeText({ tabId, text: "?" }); chrome.action.setBadgeBackgroundColor({ tabId, color: "#5a6a66" }); return; }
  chrome.action.setBadgeText({ tabId, text: result.verdict === "SAFE" ? "" : String(result.score) });
  chrome.action.setBadgeBackgroundColor({ tabId, color: COLORS[result.verdict] || "#5a6a66" });
}

function warningUrl(url, r) {
  const q = new URLSearchParams({
    u: url, s: String(r.score), v: r.verdict, c: r.category || "", id: String(r.id || ""),
    r: (r.reasons || []).slice(0, 5).map((x) => x.label).join("|"),
  });
  return chrome.runtime.getURL("warning.html") + "?" + q.toString();
}

async function checkUrl(tabId, url) {
  const cached = cache.get(url);
  if (cached && Date.now() - cached.t < 5 * 60000) return cached.result;
  const result = await post("/api/scan", { content: url, kind: "url", online: false }); // fast local path
  cache.set(url, { t: Date.now(), result });
  if (cache.size > 300) cache.delete(cache.keys().next().value);
  return result;
}

chrome.webNavigation.onBeforeNavigate.addListener(async (d) => {
  if (d.frameId !== 0) return;
  try {
    const u = new URL(d.url);
    if (["127.0.0.1", "localhost"].includes(u.hostname)) return;     // never scan our own dashboard
    const st = await engineStatus();
    if (!st.ok) { badge(d.tabId, null); return; }                    // engine not running: do not block anything
    if (!st.enabled) { chrome.action.setBadgeText({ tabId: d.tabId, text: "off" }); return; }
    if (await isAllowed(u.hostname)) return;
    const result = await checkUrl(d.tabId, d.url);
    badge(d.tabId, result);
    if (result.action === "BLOCK") chrome.tabs.update(d.tabId, { url: warningUrl(d.url, result) });
  } catch (e) { badge(d.tabId, null); }
}, { url: [{ schemes: ["http", "https"] }] });

chrome.runtime.onMessage.addListener((msg, sender, sendResponse) => {
  (async () => {
    if (msg.type === "page") {
      const st = await engineStatus();
      if (!st.ok || !st.enabled) return sendResponse({ ok: false });
      const host = new URL(msg.payload.url).hostname;
      if (await isAllowed(host)) return sendResponse({ ok: false });
      const result = await post("/api/scan/page", { ...msg.payload, online: false });
      if (sender.tab) badge(sender.tab.id, result);
      if (result.action === "BLOCK" && sender.tab) chrome.tabs.update(sender.tab.id, { url: warningUrl(msg.payload.url, result) });
      return sendResponse({ ok: true, result });
    }
    if (msg.type === "allow") { await allowHost(msg.host); return sendResponse({ ok: true }); }
    sendResponse({ ok: false });
  })().catch(() => sendResponse({ ok: false }));
  return true; // async response
});
