(function () {
  const { api, esc, $, badge, when } = TD;
  async function load() {
    $("#historyStatus").textContent = "Loading scan history…";
    const r = await api("/api/history?limit=200&min_score=" + ($("#threatsOnly").checked ? 30 : 0));
    if (!r.items.length) {
      $("#list").innerHTML = `<div class="empty">Nothing here yet. <a href="/scanner.html">Run a scan</a>.</div>`;
      $("#historyStatus").textContent = "No scans match this filter.";
      return;
    }
    $("#list").innerHTML = `<table><thead><tr><th>Time</th><th>Type</th><th>Content</th><th>Category</th><th>Risk</th><th>Verdict</th><th>Report</th></tr></thead><tbody>` +
      r.items.map((i) => `<tr class="click" data-id="${esc(i.id)}"><td>${esc(when(i.created_at))}</td><td>${esc(i.kind)}</td><td>${esc(i.preview)}</td><td>${esc(i.category)}</td><td class="num">${esc(i.score)}</td><td>${badge(i.verdict)}</td><td>${Number.isSafeInteger(Number(i.id)) && Number(i.id) > 0 ? `<button class="report-action" type="button" data-report-url="/api/reports/scans/${Number(i.id)}.pdf" data-report-name="threatdefender-scan-${Number(i.id)}.pdf">PDF</button>` : `<span class="muted">Unavailable</span>`}</td></tr>`).join("") + `</tbody></table>`;
    document.querySelectorAll("tr.click").forEach((tr) => tr.addEventListener("click", (event) => {
      if (event.target.closest("button")) return;
      location.href = "/attack_story.html?id=" + tr.dataset.id;
    }));
    $("#historyStatus").textContent = `${r.items.length} scan${r.items.length === 1 ? "" : "s"} shown.`;
  }
  $("#threatsOnly").addEventListener("change", () => load().catch((error) => {
    $("#historyStatus").textContent = `Could not load history: ${error.message}`;
  }));
  $("#clearBtn").addEventListener("click", async () => {
    if (!confirm("Delete all scan history? Quarantined items and Threat Memory are kept.")) return;
    $("#historyStatus").textContent = "Clearing history…";
    try {
      await api("/api/history", { method: "DELETE" });
      await load();
    } catch (error) {
      $("#historyStatus").textContent = `Could not clear history: ${error.message}`;
    }
  });
  load().catch((error) => {
    $("#list").innerHTML = `<div class="empty">${esc(error.message)}</div>`;
    $("#historyStatus").textContent = "History could not be loaded.";
  });
})();
