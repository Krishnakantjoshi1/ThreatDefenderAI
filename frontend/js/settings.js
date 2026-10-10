(function () {
  const { api, esc, $ } = TD;
  const say = (t) => { const m = $("#msg"); m.textContent = t; m.hidden = !t; if (t) setTimeout(() => (m.hidden = true), 3500); };
  const radio = (name) => document.querySelector(`input[name=${name}]:checked`);

  function paint(data) {
    const s = data.settings, m = data.mode;
    document.querySelector(`input[name=pref][value=${s.mode_preference}]`).checked = true;
    document.querySelector(`input[name=mm][value=${s.manual_mode}]`).checked = true;
    $("#manualSet").disabled = s.mode_preference !== "manual";
    $("#forceOffline").checked = s.force_offline === "true";
    $("#storePreview").checked = s.store_preview === "true";
    ["hybrid", "online"].forEach((k) => {
      const ok = m.available_modes.includes(k);
      $("#o-" + k).classList.toggle("off", !ok);
      $("#o-" + k).querySelector("input").disabled = !ok || s.mode_preference !== "manual";
    });
    $("#availNote").textContent = m.network === "connected" ? m.note : "Hybrid and Online are unavailable because there is no internet. " + m.note;
  }

  async function save(patch) {
    try { paint(await api("/api/settings", { method: "POST", body: patch })); say("Saved."); } catch (e) { say(e.message); }
  }

  async function load() {
    paint(await api("/api/settings"));
    const ai = await api("/api/ai/status");
    $("#aiLine").innerHTML = ai.model_ready ? `<b>Phi-3 is ready</b> (${esc(ai.model)}) and runs only on this computer.` : esc(ai.detail);
    const info = await api("/api/intel/status");
    $("#feedLine").textContent = info.feed.present ? info.feed.entries + " entries stored" : "Not downloaded yet";
  }

  document.querySelectorAll("input[name=pref]").forEach((r) => r.addEventListener("change", () => save({ mode_preference: radio("pref").value })));
  document.querySelectorAll("input[name=mm]").forEach((r) => r.addEventListener("change", () => save({ manual_mode: radio("mm").value })));
  $("#forceOffline").addEventListener("change", (e) => save({ force_offline: e.target.checked }));
  $("#storePreview").addEventListener("change", (e) => save({ store_preview: e.target.checked }));
  $("#feedBtn").addEventListener("click", async () => {
    $("#feedBtn").disabled = true; $("#feedLine").textContent = "Downloading…";
    try { const r = await api("/api/intel/update", { method: "POST" }); $("#feedLine").textContent = r.detail; } catch (e) { $("#feedLine").textContent = e.message; }
    $("#feedBtn").disabled = false;
  });
  window.addEventListener("td:mode", () => api("/api/settings").then(paint).catch((e) => say(e.message)));
  load().catch((e) => say(e.message));
})();
