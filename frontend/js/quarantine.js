(function () {
  const { api, esc, $, when } = TD;
  function say(t, isError = false) {
    const m = $("#msg");
    m.textContent = t;
    m.classList.toggle("ok", !isError);
    m.classList.toggle("quarantine-error", isError);
    m.hidden = !t;
  }
  async function load() {
    const r = await api("/api/quarantine");
    if (!r.items.length) {
      $("#list").innerHTML = `<div class="empty"><span class="quarantine-empty-icon" aria-hidden="true"><svg viewBox="0 0 24 24"><path d="m5 12 4 4L19 6"/></svg></span><b>Nothing in quarantine</b><span>Critical threats will appear here automatically when isolated.</span></div>`;
      return;
    }
    $("#list").innerHTML = `<table><caption class="small muted">Items currently held in local quarantine</caption><thead><tr><th>Item</th><th>Type</th><th>Reason</th><th>Risk</th><th>Isolated</th><th>Actions</th></tr></thead><tbody>` +
      r.items.map((i) => `<tr><td><b>${esc(i.name)}</b></td><td>${esc(i.kind)}</td><td>${esc(i.reason)}</td><td class="num">${i.score}</td><td>${esc(when(i.created_at))}</td>
      <td class="row"><a class="btn" href="/attack_story.html?id=${i.scan_id}">Inspect</a>
      <button data-act="restore" data-id="${i.id}" type="button">Restore</button>
      <button class="danger" data-act="delete" data-id="${i.id}" type="button">Delete</button></td></tr>`).join("") + `</tbody></table>`;
    document.querySelectorAll("#list button[data-act]").forEach((button) => {
      button.addEventListener("click", () => act(button, button.dataset.act, button.dataset.id));
    });
  }
  async function act(button, kind, id) {
    try {
      if (kind === "restore") {
        if (!confirm("Restore this item? It was judged dangerous. A restored file is copied to the 'restored' folder inside the data/quarantine folder.")) return;
        button.disabled = true;
        const r = await api(`/api/quarantine/${id}/restore`, { method: "POST" });
        say(r.path ? "Restored to: " + r.path : "Released from quarantine.");
      } else {
        if (!confirm("Permanently delete this quarantined item?")) return;
        button.disabled = true;
        await api(`/api/quarantine/${id}`, { method: "DELETE" }); say("Deleted.");
      }
      await load();
    } catch (e) {
      button.disabled = false;
      say(e.message, true);
    }
  }
  load().catch((e) => ($("#list").innerHTML = `<div class="empty quarantine-error" role="alert">${esc(e.message)}</div>`));
})();
