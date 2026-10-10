(function () {
  const { api, esc, $, renderResult, explanationHtml } = TD;
  const SAMPLES = [
    ["Bank KYC scam", "🚨 URGENT! Your SBI account will be blocked today. Verify your account immediately and claim your ₹5,000 cashback. Enter your OTP here: http://sbi-kyc-update.xyz/login"],
    ["Lottery fee scam", "Congratulations! You won ₹50,000 in the lucky draw. Pay a ₹499 processing fee today to claim your prize."],
    ["Hinglish OTP scam", "Aapka SBI account aaj band ho jayega. Turant KYC update karein aur apna OTP bataiye: http://sbi-kyc-update.xyz/login"],
    ["Phishing link", "http://secure-login.amazon.account-verify.top/signin"],
    ["Family emergency", "Hi mom, this is my new number. I lost my phone. Please send money urgently and don't tell dad."],
    ["Genuine OTP", "Your OTP is 482913. Do not share it with anyone. - HDFC Bank"],
    ["Normal chat", "Hey, are we still meeting for lunch tomorrow at 1pm?"],
  ];
  let tab = "text", fileObj = null;

  const box = $(".examples");
  SAMPLES.forEach(([label, text]) => {
    const b = document.createElement("button"); b.type = "button"; b.textContent = label;
    b.addEventListener("click", () => { $("#content").value = text; $("#content").focus(); });
    box.appendChild(b);
  });

  document.querySelectorAll("[data-tab]").forEach((b) => b.addEventListener("click", () => {
    tab = b.dataset.tab;
    document.querySelectorAll("[data-tab]").forEach((x) => x.setAttribute("aria-selected", String(x === b)));
    $("#paneText").hidden = tab !== "text"; $("#paneFile").hidden = tab !== "file";
  }));

  const drop = $("#drop");
  ["dragenter", "dragover"].forEach((ev) => drop.addEventListener(ev, (e) => { e.preventDefault(); drop.classList.add("over"); }));
  ["dragleave", "drop"].forEach((ev) => drop.addEventListener(ev, (e) => { e.preventDefault(); drop.classList.remove("over"); }));
  drop.addEventListener("drop", (e) => { if (e.dataTransfer.files[0]) { fileObj = e.dataTransfer.files[0]; $("#status").textContent = "Selected: " + fileObj.name; } });
  $("#fileInput").addEventListener("change", (e) => { fileObj = e.target.files[0] || null; $("#status").textContent = fileObj ? "Selected: " + fileObj.name : ""; });

  const toB64 = (file) => new Promise((resolve, reject) => {
    const r = new FileReader();
    r.onload = () => resolve(String(r.result).split(",")[1] || "");
    r.onerror = () => reject(new Error("Could not read the file"));
    r.readAsDataURL(file);
  });

  function showError(msg) { const e = $("#err"); e.textContent = msg; e.hidden = !msg; }

  $("#scanBtn").addEventListener("click", async () => {
    showError(""); const btn = $("#scanBtn"); btn.disabled = true; $("#status").textContent = "Scanning…";
    const content = $("#content").value;
    try {
      let r;
      if (tab === "text") {
        if (!content.trim()) throw new Error("Paste a message or link first, or pick an example.");
        r = await api("/api/scan", { method: "POST", body: { content, sender: $("#sender").value.trim() || null } });
      } else {
        if (!fileObj) throw new Error("Choose a file first.");
        if (fileObj.size > 10 * 1024 * 1024) throw new Error("File is larger than 10 MB.");
        r = await api("/api/scan/file", { method: "POST", body: { filename: fileObj.name, content_b64: await toB64(fileObj) } });
      }
      window.dispatchEvent(new CustomEvent("td:scan-result", { detail: r }));
      const wantsAi = r.verdict !== "SAFE";
      renderResult($("#result"), r, { aiLoading: wantsAi });
      $("#status").textContent = "";
      $("#result").scrollIntoView({ behavior: "smooth", block: "start" });
      if (wantsAi) {
        try {
          const ex = await api("/api/explain", { method: "POST", body: { scan_id: r.id, content: tab === "text" ? content : null, lang: $("#lang").value } });
          $("#explainBox").innerHTML = explanationHtml(ex, false);
        } catch (e) {
          $("#explainBox").innerHTML = explanationHtml(r.quick_explanation, false) +
            `<p class="notice" role="status">The additional explanation was unavailable: ${esc(e.message)}</p>`;
        }
      }
    } catch (e) { showError(e.message); $("#status").textContent = ""; }
    btn.disabled = false;
  });
})();
