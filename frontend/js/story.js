(function () {
  const { api, esc, $, renderResult, explanationHtml, when } = TD;
  const id = new URLSearchParams(location.search).get("id");
  async function load() {
    if (!id || !/^\d+$/.test(id)) { $("#result").innerHTML = `<div class="empty">No scan selected. Open one from <a href="/history.html">History</a>.</div>`; return; }
    try {
      const item = await api("/api/history/" + id);
      $("#meta").textContent = `${when(item.created_at)} · ${item.kind} · ${item.preview}`;
      renderResult($("#result"), item.result);
      if (item.explanation) $("#explainBox").innerHTML = explanationHtml(item.explanation, false);
      if (item.verdict !== "SAFE") { $("#aiBtn").hidden = false; $("#lang").hidden = false; }
    } catch (e) { $("#result").innerHTML = `<div class="empty">${esc(e.message)}</div>`; }
  }
  $("#aiBtn").addEventListener("click", async () => {
    $("#explainBox").innerHTML = `<p class="source-tag"><span class="spinner"></span>Phi-3 is writing a deeper explanation…</p>`;
    try { $("#explainBox").innerHTML = explanationHtml(await api("/api/explain", { method: "POST", body: { scan_id: Number(id), lang: $("#lang").value } }), false); }
    catch (e) { $("#explainBox").textContent = e.message; }
  });
  load();
})();
