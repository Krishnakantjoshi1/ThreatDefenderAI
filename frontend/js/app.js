/* Shared helpers for every page. Everything dynamic is escaped with esc() - scanned text is attacker-controlled. */
(function () {
  const NAV = [["/", "Dashboard"], ["/scanner.html", "Scanner"], ["/history.html", "History"],
               ["/quarantine.html", "Quarantine"], ["/settings.html", "Settings"]];

  const esc = (s) => String(s ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
  const $ = (sel, root = document) => root.querySelector(sel);

  async function request(path, opts = {}) {
    const { timeoutMs = 120000, signal, ...fetchOptions } = opts;
    const controller = new AbortController();
    let timedOut = false;
    const timer = setTimeout(() => { timedOut = true; controller.abort(); }, timeoutMs);
    const onAbort = () => controller.abort();
    if (signal) {
      if (signal.aborted) controller.abort();
      else signal.addEventListener("abort", onAbort, { once: true });
    }
    const headers = { "Content-Type": "application/json", ...(fetchOptions.headers || {}) };
    const o = { credentials: "same-origin", ...fetchOptions, headers, signal: controller.signal };
    if (o.body && typeof o.body !== "string") o.body = JSON.stringify(o.body);
    let res;
    try {
      res = await fetch(path, o);
    } catch (e) {
      if (timedOut) throw new Error("The request timed out. Check the local service and try again.");
      if (signal && signal.aborted) throw new Error("The request was cancelled.");
      throw new Error("Cannot reach the local ThreatDefender server. Is run.py running?");
    } finally {
      clearTimeout(timer);
      if (signal) signal.removeEventListener("abort", onAbort);
    }
    return res;
  }

  async function api(path, opts = {}) {
    const res = await request(path, opts);
    let data = null;
    try { data = await res.json(); } catch (e) { /* non-JSON */ }
    if (!res.ok) {
      const error = new Error((data && data.detail) || `Request failed (${res.status})`);
      error.status = res.status;
      throw error;
    }
    return data;
  }

  async function download(path, fallbackFilename) {
    const res = await request(path, { timeoutMs: 30000, cache: "no-store" });
    if (!res.ok) {
      let data = null;
      try { data = await res.json(); } catch (e) { /* non-JSON */ }
      const error = new Error((data && data.detail) || `Download failed (${res.status})`);
      error.status = res.status;
      throw error;
    }
    const disposition = res.headers.get("Content-Disposition") || "";
    const match = disposition.match(/filename="?([^";\r\n]+)"?/i);
    const filename = (match && match[1].split(/[\\/]/).pop().replace(/[\u0000-\u001f]/g, "")) || fallbackFilename;
    const blob = await res.blob();
    const objectUrl = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = objectUrl;
    link.download = filename;
    link.hidden = true;
    document.body.appendChild(link);
    link.click();
    link.remove();
    setTimeout(() => URL.revokeObjectURL(objectUrl), 1000);
  }

  const badge = (v) => `<span class="badge v-${esc(v)}">${esc(v)}</span>`;
  const when = (iso) => { try { return new Date(iso).toLocaleString(); } catch (e) { return iso; } };

  /* ---------- honeycomb: 7 hexagons, one per attack dimension ---------- */
  const STOPS = [[0, [70, 198, 192]], [45, [232, 181, 72]], [100, [180, 35, 24]]];
  function heat(v) {
    v = Math.max(0, Math.min(100, v));
    for (let i = 1; i < STOPS.length; i++) {
      if (v <= STOPS[i][0]) {
        const [a, ca] = STOPS[i - 1], [b, cb] = STOPS[i], t = (v - a) / (b - a);
        return "rgb(" + ca.map((c, k) => Math.round(c + (cb[k] - c) * t)).join(",") + ")";
      }
    }
    return "rgb(180,35,24)";
  }
  const HEX_ORDER = [["credential", 0, 0], ["identity", -120], ["urgency", -60], ["link", 0], ["money", 60], ["offer", 120], ["conversation", 180]];
  const LABELS = { money: "Money", offer: "Offer", conversation: "Conversation", identity: "Identity", urgency: "Urgency", credential: "Credential", link: "Link" };

  function honeycomb(scores) {
    scores = scores || {};
    const R = 50, cx = 170, cy = 150, d = Math.sqrt(3) * R * 1.07;
    let out = `<svg class="honeycomb" viewBox="0 0 340 300" role="img" aria-label="Honeycomb threat analysis: ` +
      esc(Object.entries(scores).map(([k, v]) => `${LABELS[k] || k} ${v} percent`).join(", ")) + `">`;
    for (const [dim, ang] of HEX_ORDER) {
      const x = dim === "credential" ? cx : cx + d * Math.cos((ang * Math.PI) / 180);
      const y = dim === "credential" ? cy : cy + d * Math.sin((ang * Math.PI) / 180);
      const v = scores[dim] || 0;
      const pts = [0, 1, 2, 3, 4, 5].map((k) => { const a = ((60 * k - 90) * Math.PI) / 180; return (x + R * Math.cos(a)).toFixed(1) + "," + (y + R * Math.sin(a)).toFixed(1); }).join(" ");
      const fg = v >= 60 ? "#fff" : getComputedStyle(document.documentElement).getPropertyValue("--ink").trim();
      out += `<g><title>${esc(LABELS[dim])}: ${v}%</title><polygon points="${pts}" fill="${heat(v)}"/>` +
        `<text class="hc-name" x="${x.toFixed(1)}" y="${(y - 4).toFixed(1)}" text-anchor="middle" fill="${fg}">${esc(LABELS[dim])}</text>` +
        `<text class="hc-val" x="${x.toFixed(1)}" y="${(y + 16).toFixed(1)}" text-anchor="middle" fill="${fg}">${v}%</text></g>`;
    }
    return out + "</svg>";
  }

  /* ---------- top bar + live mode chip ---------- */
  function mountTopbar() {
    const host = $("#topbar"); if (!host) return;
    const here = location.pathname === "/index.html" ? "/" : location.pathname;
    host.className = "topbar";
    host.innerHTML = `<div class="topbar-in">
      <a class="brand" href="/"><svg viewBox="0 0 32 32" aria-hidden="true"><path d="M16 2l11 6.2v12.4L16 30 5 20.6V8.2z" fill="var(--accent)"/><path d="M16 9l5.5 3.1v6.2L16 24l-5.5-5.7v-6.2z" fill="none" stroke="var(--panel)" stroke-width="2"/></svg><span>ThreatDefender <span class="brand-ai">AI</span></span></a>
      <nav class="nav" aria-label="Main">${NAV.map(([h, t]) => `<a href="${h}" ${h === here ? 'aria-current="page"' : ""}>${t}</a>`).join("")}</nav>
      <div class="topbar-tools">
        <button class="theme-toggle" id="themeToggle" type="button" aria-label="Switch to light theme" title="Switch to light theme" aria-pressed="false">
          <svg class="theme-icon theme-icon-sun" viewBox="0 0 24 24" aria-hidden="true"><circle cx="12" cy="12" r="4"/><path d="M12 2v2m0 16v2M4.93 4.93l1.42 1.42m11.3 11.3 1.42 1.42M2 12h2m16 0h2M4.93 19.07l1.42-1.42m11.3-11.3 1.42-1.42"/></svg>
          <svg class="theme-icon theme-icon-moon" viewBox="0 0 24 24" aria-hidden="true"><path d="M20.5 15.4A8.5 8.5 0 0 1 8.6 3.5 8.5 8.5 0 1 0 20.5 15.4Z"/></svg>
          <span class="theme-toggle-label">Light</span>
        </button>
        <span class="chip" id="modeChip" role="status"><span class="dot"></span><span>Checking…</span></span>
      </div></div>`;
    const themeButton = $("#themeToggle");
    const updateThemeButton = (theme) => {
      const nextLabel = theme === "dark" ? "light" : "dark";
      themeButton.setAttribute("aria-label", `Switch to ${nextLabel} theme`);
      themeButton.title = `Switch to ${nextLabel} theme`;
      themeButton.setAttribute("aria-pressed", String(theme === "light"));
      $(".theme-toggle-label", themeButton).textContent = nextLabel === "light" ? "Light" : "Dark";
    };
    updateThemeButton(window.TDTheme.getTheme());
    themeButton.addEventListener("click", () => updateThemeButton(window.TDTheme.toggle()));
    window.addEventListener("td:theme", (event) => updateThemeButton(event.detail.theme));
    refreshChip(); setInterval(refreshChip, 4000);
  }
  async function refreshChip() {
    const chip = $("#modeChip"); if (!chip) return;
    try {
      const m = await api("/api/mode");
      const eff = m.effective.toUpperCase();
      const cls = m.fallback ? "amber" : m.effective === "offline" ? "" : "green";
      chip.innerHTML = `<span class="dot ${cls}"></span><span>${esc(eff)}${m.fallback ? " (fallback)" : ""} · network ${esc(m.network)}</span>`;
      chip.title = m.note;
      window.dispatchEvent(new CustomEvent("td:mode", { detail: m }));
    } catch (e) {
      chip.innerHTML = `<span class="dot red"></span><span>Server not reachable</span>`;
    }
  }

  /* ---------- full scan result renderer ---------- */
  function meter(label, v, hot) {
    return `<div class="meter"><span>${esc(label)}</span><div class="bar ${hot ? "hot" : ""}"><i style="width:${Math.max(0, Math.min(100, v))}%"></i></div><span class="num">${v}</span></div>`;
  }

  function renderThreatSignal(record, scores) {
    const host = $("#heroHex");
    const caption = $("#heroCap");
    host.replaceChildren();
    if (!record) {
      host.innerHTML = `<div class="signal-empty"><span class="signal-empty-icon" aria-hidden="true">✓</span><b>No saved threat signal</b><p class="small muted">Threat analysis will appear here when a threat is detected.</p><a class="text-link" href="/scanner.html">Run a scan <span aria-hidden="true">→</span></a></div>`;
      caption.textContent = "Threat activity updates from your local scan history.";
      return;
    }

    const score = Math.max(0, Math.min(100, Number(record.score) || 0));
    const level = score >= 80 ? "critical" : score >= 60 ? "dangerous" : score >= 30 ? "suspicious" : "safe";
    const verdict = String(record.verdict || level).toUpperCase();
    const dimensions = ["credential", "identity", "urgency", "link", "money", "offer", "conversation"]
      .map((key) => [key, Math.max(0, Math.min(100, Number(scores && scores[key]) || 0))])
      .sort((a, b) => b[1] - a[1]);
    const strongest = dimensions.filter(([, value]) => value > 0).slice(0, 5);

    host.innerHTML = `<div class="signal-overview">
      <div class="signal-ring signal-${level}" style="--signal-value:${score}%" role="img" aria-label="Latest threat risk ${score} out of 100">
        <div class="signal-ring-center"><b>${score}</b><span>/ 100</span></div>
      </div>
      <div class="signal-summary">
        <span class="signal-kicker">Latest detected threat</span>
        <span class="badge v-${esc(verdict)}">${esc(verdict)}</span>
        <b class="signal-category">${esc(record.category || "Threat detected")}</b>
        <span class="small muted">${esc(when(record.created_at))}</span>
      </div>
    </div>
    <div class="signal-breakdown">
      <div class="signal-breakdown-heading"><b>Signal breakdown</b><span class="small muted">By attack dimension</span></div>
      ${strongest.length ? strongest.map(([key, value]) => `<div class="signal-meter"><span>${esc(LABELS[key])}</span><div class="signal-track"><i style="width:${value}%"></i></div><b>${value}%</b></div>`).join("") : `<p class="small muted">No dimension scores were recorded for this threat.</p>`}
    </div>`;
    caption.innerHTML = `<a class="text-link" href="/attack_story.html?id=${encodeURIComponent(record.id)}">Review threat analysis <span aria-hidden="true">→</span></a>`;
  }

  function explanationHtml(ex, loading) {
    if (!ex) return "";
    const tag = loading ? `<span class="spinner"></span>Phi-3 is writing a deeper explanation…`
      : ex.source === "phi3" ? `Explained by ${esc(ex.model)} running on this device (${ex.latency_ms} ms)` : `Built-in explainer${ex.note ? " · " + esc(ex.note) : ""}`;
    return `<dl class="explain"><dt>Why it is risky</dt><dd>${esc(ex.why)}</dd>` +
      (ex.goal ? `<dt>What the attacker wants</dt><dd>${esc(ex.goal)}</dd>` : "") +
      (ex.story ? `<dt>Attack story</dt><dd>${esc(ex.story)}</dd>` : "") +
      `<dt>What you should do</dt><dd>${esc(ex.action)}</dd></dl><p class="source-tag">${tag}</p>`;
  }

  function renderResult(el, r, opts = {}) {
    const hc = r.honeycomb || { scores: {} };
    const reasons = (r.reasons || []).map((x) => `<li><b>${esc(x.label)}</b><div class="ev">${esc(LABELS[x.dimension] || x.dimension)}${x.evidence ? " · " + esc(x.evidence) : ""}</div></li>`).join("");
    const chain = (r.attack_chain || []).map((c) => `<li class="${c.dimension === "impact" ? "impact" : ""}"><b>${esc(c.stage)}</b><span class="muted">${esc(c.explanation)}</span><div class="ev">${esc(c.evidence)}</div></li>`).join("");
    const comps = (r.components || []).map((c) => meter(c.name, c.score, c.score >= 60)).join("");
    const dna = r.scam_dna || {};
    const urls = (r.urls || []).map((u) => `<tr><td class="ev">${esc(u.url)}</td><td class="num">${u.score}</td><td>${u.trusted ? "Trusted site" : esc((u.indicators || []).join("; ") || "No issues")}</td></tr>`).join("");
    const on = r.online || {};
    const mem = r.memory || {};
    const mode = r.mode || {};
    el.innerHTML = `
      <section class="panel verdict-panel p-${esc(r.verdict)}" aria-live="polite">
        <div class="verdict">
          <div class="score c-${esc(r.verdict)}">${r.score}<small>/100</small></div>
          <div><div class="row">${badge(r.verdict)} <b>${esc(r.action)}</b> <span class="muted">· ${esc(r.category)}</span></div>
          <p style="margin:.4rem 0 0">${esc(r.summary)}</p></div>
        </div>
        <p class="small muted" style="margin:.8rem 0 0">Scanned on this device in ${r.latency_ms} ms · mode ${esc((mode.effective || "").toUpperCase())}${mode.fallback ? " (offline fallback)" : ""} · network ${esc(mode.network)}</p>
        ${r.quarantine ? `<p class="small" style="margin:.5rem 0 0"><b>Isolated in Quarantine.</b> <a href="/quarantine.html">View</a></p>` : ""}
        ${Number.isSafeInteger(Number(r.id)) && Number(r.id) > 0 ? `<p class="small" style="margin:.5rem 0 0"><button class="report-action" type="button" data-report-url="/api/reports/scans/${Number(r.id)}.pdf" data-report-name="threatdefender-scan-${Number(r.id)}.pdf">Download scan report (PDF)</button></p>` : ""}
      </section>
      <div class="grid2">
        <section class="panel"><h2>Honeycomb analysis</h2>${honeycomb(hc.scores)}
          <p class="small muted">Each cell is one way the message tries to manipulate you. Darker means stronger.</p></section>
        <section class="panel"><h2>Why it was flagged</h2>${reasons ? `<ul class="clean">${reasons}</ul>` : `<p class="muted">No warning signs found.</p>`}</section>
      </div>
      <section class="panel"><h2>Explanation</h2><div id="explainBox">${explanationHtml(r.quick_explanation, !!opts.aiLoading)}</div></section>
      ${chain ? `<section class="panel"><h2>Attack story</h2><ol class="chain">${chain}</ol>${r.id ? `<a class="small" href="/attack_story.html?id=${r.id}">Open full attack story</a>` : ""}</section>` : ""}
      <div class="grid2">
        <section class="panel"><h2>Scam DNA</h2>${Object.entries(dna.fingerprint || {}).map(([k, v]) => meter(LABELS[k] || k, v, v >= 60)).join("")}
          <p class="small">${dna.match ? `Behaves like a known pattern: <b>${esc(dna.match)}</b> (${dna.similarity}% match)` : `No strong match with known scam patterns.`}</p></section>
        <section class="panel"><h2>Risk engine evidence</h2>${comps || `<p class="muted">No evidence contributed to the score.</p>`}
          <p class="small muted">The security engine combines these signals. The AI only explains the result.</p></section>
      </div>
      ${urls ? `<section class="panel"><h2>Links found</h2><div class="table-wrap"><table><thead><tr><th>Link</th><th>Risk</th><th>Findings</th></tr></thead><tbody>${urls}</tbody></table></div></section>` : ""}
      <section class="panel"><h2>Privacy and intelligence</h2>
        <p>${esc(on.note || "")}</p>
        ${(on.sent || []).length ? `<p class="small">Sent to the internet: ${on.sent.map((s) => esc(s.what) + " <b>" + esc(s.value) + "</b> to " + esc(s.to)).join("; ")}. Your message text was never sent.</p>` : `<p class="small">Nothing left this device.</p>`}
        ${mem.seen_before ? `<p class="small">Threat Memory: this pattern was seen ${mem.times_seen} time(s) before${mem.prior_category ? " as " + esc(mem.prior_category) : ""}.</p>` : ""}
      </section>`;
  }

  window.TD = { api, download, esc, $, badge, when, honeycomb, renderResult, renderThreatSignal, explanationHtml, meter, LABELS };
  document.addEventListener("DOMContentLoaded", mountTopbar);
})();
