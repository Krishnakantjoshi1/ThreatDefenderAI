(function () {
  const { api, esc, $, badge, when, renderThreatSignal } = TD;
  let protectionOn = true;

  function renderRecent(items) {
    if (!items.length) { $("#recent").innerHTML = `<div class="empty">No scans yet. <a href="/scanner.html">Scan a message or link</a> to see ThreatDefender work.</div>`; return; }
    $("#recent").innerHTML = `<table><thead><tr><th>Time</th><th>Type</th><th>Content</th><th>Risk</th><th>Verdict</th></tr></thead><tbody>` +
      items.map((i) => `<tr class="click" data-id="${i.id}"><td>${esc(when(i.created_at))}</td><td>${esc(i.kind)}</td><td>${esc(i.preview)}</td><td class="num">${i.score}</td><td>${badge(i.verdict)}</td></tr>`).join("") + `</tbody></table>`;
    document.querySelectorAll("#recent tr.click").forEach((tr) => tr.addEventListener("click", () => (location.href = "/attack_story.html?id=" + tr.dataset.id)));
  }

  async function load() {
    try {
      const [stats, prot, hist, ai, intel] = await Promise.all([
        api("/api/stats"), api("/api/protection"), api("/api/history?limit=8"), api("/api/ai/status"), api("/api/intel/status")]);
      protectionOn = prot.enabled;
      $("#protTitle").textContent = protectionOn ? "Protection is on" : "Protection is paused";
      $("#protBtn").textContent = protectionOn ? "Pause protection" : "Turn protection on";
      const m = prot.mode;
      $("#sMode").textContent = m.effective.toUpperCase() + (m.fallback ? " (offline fallback)" : "") + " · " + (m.preference === "auto" ? "Auto" : "Manual");
      $("#sNet").textContent = m.network === "connected" ? "Connected" : "Disconnected" + (m.simulated_offline ? " (simulated)" : "");
      $("#modeNote").textContent = m.note;
      $("#sAi").textContent = ai.model_ready ? "Ready (" + ai.model + ")" : ai.running ? "Model missing, using built-in explainer" : "Not running, using built-in explainer";
      $("#sMem").textContent = stats.memory_entries + " remembered pattern" + (stats.memory_entries === 1 ? "" : "s");
      $("#sFeed").textContent = intel.feed.present ? intel.feed.entries + " extra entries downloaded" : "Built-in list only";
      $("#stats").innerHTML = [["Scans", stats.total_scans], ["Threats found", stats.threats_detected], ["Blocked", stats.blocked], ["Suspicious", stats.suspicious], ["Quarantined", stats.quarantined]]
        .map(([l, v]) => `<div><b>${v}</b><span class="muted">${l}</span></div>`).join("");
      renderRecent(hist.items);
      if (stats.last_threat) {
        const full = await api("/api/history/" + stats.last_threat.id);
        const scores = full.result && full.result.honeycomb && full.result.honeycomb.scores;
        renderThreatSignal(stats.last_threat, scores || {});
      } else {
        renderThreatSignal(null, {});
      }
    } catch (e) {
      $("#protTitle").textContent = "Server not reachable";
      $("#protSub").textContent = e.message;
    }
  }

  $("#protBtn").addEventListener("click", async () => {
    await api("/api/protection", { method: "POST", body: { enabled: !protectionOn } });
    load();
  });
  window.addEventListener("td:mode", load);
  load();
})();
