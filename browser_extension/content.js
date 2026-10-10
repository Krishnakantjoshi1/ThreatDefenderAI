// Collects page signals (password field, form targets, hidden iframes) and asks the LOCAL engine.
(function () {
  if (window.top !== window) return;
  if (!/^https?:$/.test(location.protocol) || ["127.0.0.1", "localhost"].includes(location.hostname)) return;

  function banner(result) {
    const host = document.createElement("div");
    const root = host.attachShadow({ mode: "closed" });
    const bar = document.createElement("div");
    bar.setAttribute("role", "alert");
    bar.style.cssText = "position:fixed;top:0;left:0;right:0;z-index:2147483647;background:#fbefd5;color:#14212b;border-bottom:3px solid #a86a0c;" +
      "font:15px/1.4 system-ui,sans-serif;padding:10px 16px;display:flex;gap:14px;align-items:center";
    const msg = document.createElement("span");
    const why = (result.reasons && result.reasons[0] && result.reasons[0].label) || result.category || "suspicious signals";
    msg.textContent = "ThreatDefender AI: this page looks " + result.verdict.toLowerCase() + " (" + result.score + "/100). " + why + ". Do not enter passwords or OTPs.";
    const btn = document.createElement("button");
    btn.textContent = "Dismiss";
    btn.style.cssText = "margin-left:auto;cursor:pointer;padding:4px 12px";
    btn.addEventListener("click", () => host.remove());
    bar.append(msg, btn);
    root.append(bar);
    document.documentElement.appendChild(host);
  }

  function run() {
    const hasPw = !!document.querySelector("input[type=password]");
    const forms = Array.from(document.forms).slice(0, 10).map((f) => ({ action: f.action || "" }));
    const hidden = Array.from(document.querySelectorAll("iframe")).filter((i) => {
      const r = i.getBoundingClientRect(), cs = getComputedStyle(i);
      return r.width < 3 || r.height < 3 || cs.display === "none" || cs.visibility === "hidden";
    }).length;
    // Page text is only sent (to localhost) when the page asks for a password.
    const text = hasPw && document.body ? document.body.innerText.slice(0, 4000) : "";
    chrome.runtime.sendMessage({ type: "page", payload: { url: location.href, title: document.title, text, has_password_field: hasPw, forms, hidden_iframes: hidden } },
      (res) => {
        if (chrome.runtime.lastError || !res || !res.ok) return;
        if (res.result.score >= 30 && res.result.action !== "BLOCK") banner(res.result);
      });
  }
  setTimeout(run, 800);
})();
