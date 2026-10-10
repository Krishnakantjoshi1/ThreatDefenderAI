const API = "http://127.0.0.1:8000";
const $ = (selector) => document.querySelector(selector);
const categories = [
  { key: "identity", name: "Identity", icon: "ID", order: 1, explanation: ["Sender name may not match the domain", "Check the source before trusting the message"], action: "Verify the sender through another channel" },
  { key: "urgency", name: "Urgency", icon: "!", order: 2, explanation: ["Look for pressure to act immediately", "Scams often use deadlines to prevent careful review"], action: "Pause and verify before taking action" },
  { key: "conversation", name: "Conversation", icon: "↔", order: 3, explanation: ["Review the context and tone of the conversation", "Unexpected requests may be part of social engineering"], action: "Confirm the request with someone you trust" },
  { key: "credential", name: "Credential", icon: "⌑", order: 4, explanation: ["The content may try to collect sign-in details", "Never share passwords, PINs, or one-time codes"], action: "Do not enter or share your credentials" },
  { key: "link", name: "Link", icon: "↗", order: 5, explanation: ["The URL may use a lookalike domain", "Check the full address before opening or signing in"], action: "Don't click the link; visit the known site directly" },
  { key: "offer", name: "Offer", icon: "✧", order: 6, explanation: ["Unexpected rewards can be used to lure a response", "Be cautious if an offer asks for personal details or payment"], action: "Verify the offer using the organisation's official channel" },
  { key: "money", name: "Money", icon: "¤", order: 7, explanation: ["The request may involve a payment or transfer", "Upfront fees and unusual payment methods are warning signs"], action: "Do not pay until the request is independently verified" },
];
const reduceMotion = window.matchMedia("(prefers-reduced-motion: reduce)");
const scores = Object.fromEntries(categories.map(({ key }) => [key, 0]));
let enabled = true;
let activeTab = null;
let selectedKey = null;
let detailFrame = 0;

async function getJson(path, opts = {}) {
  const response = await fetch(API + path, opts);
  let data = null;
  try { data = await response.json(); } catch (error) { /* The error response may not be JSON. */ }
  if (!response.ok) throw new Error((data && data.detail) || "ThreatDefender API " + response.status);
  return data;
}

function severity(score) {
  if (score >= 80) return "high";
  if (score > 0) return "medium";
  return "none";
}

function severityLabel(score) {
  const value = severity(score);
  return value === "high" ? "High risk" : value === "medium" ? "Medium risk" : "No signal";
}

function tileColor(score) {
  return score >= 80 ? "#c44d24" : score > 0 ? "#e09a40" : "#e3ebe8";
}

function animateNumber(element, from, to, duration = 950) {
  const start = performance.now();
  const initial = Number(from) || 0;
  const valueNode = element.firstChild;
  const setValue = (value) => { valueNode.textContent = String(value); };
  if (reduceMotion.matches || initial === to) {
    setValue(to);
    return;
  }
  const tick = (now) => {
    const progress = Math.min((now - start) / duration, 1);
    const eased = 1 - Math.pow(1 - progress, 4);
    setValue(Math.round(initial + (to - initial) * eased));
    if (progress < 1) requestAnimationFrame(tick);
  };
  requestAnimationFrame(tick);
}

function renderHoneycomb() {
  const host = $("#honeycomb");
  host.replaceChildren();
  categories.forEach((category, index) => {
    const tile = document.createElement("button");
    tile.type = "button";
    tile.className = "hex-tile";
    tile.dataset.key = category.key;
    tile.dataset.order = String(category.order);
    tile.style.setProperty("--tile-order", String(index));
    tile.style.setProperty("--float-phase", `${-(index * 0.43)}s`);
    tile.innerHTML = `<span class="tile-category">${category.name}</span><b class="tile-score">0<span>%</span></b>`;
    tile.addEventListener("click", () => selectCategory(category.key));
    tile.addEventListener("pointerdown", () => tile.classList.add("pressed"));
    tile.addEventListener("pointerup", () => tile.classList.remove("pressed"));
    tile.addEventListener("pointerleave", () => tile.classList.remove("pressed"));
    host.appendChild(tile);
  });
  host.hidden = false;
  updateScores(scores);
}

function updateScores(newScores = {}) {
  let changed = false;
  categories.forEach((category) => {
    const next = Number(newScores[category.key]);
    if (!Number.isFinite(next)) return;
    const score = Math.max(0, Math.min(100, Math.round(next)));
    const old = scores[category.key];
    scores[category.key] = score;
    changed ||= old !== score;
    const tile = $(`.hex-tile[data-key="${category.key}"]`);
    if (!tile) return;
    const value = tile.querySelector(".tile-score");
    const from = Number.parseInt(value.firstChild.textContent, 10) || 0;
    tile.dataset.severity = severity(score);
    tile.style.setProperty("--tile-color", tileColor(score));
    tile.setAttribute("aria-label", `${category.name}, ${score} percent, ${severityLabel(score).toLowerCase()}`);
    tile.title = `${category.name}: ${score}% – click for details`;
    animateNumber(value, from, score);
  });
  if (selectedKey) renderDetails(selectedKey);
  return changed;
}

function renderDetails(key) {
  const category = categories.find((item) => item.key === key);
  if (!category) return;
  const score = scores[key];
  const panel = $("#detailPanel");
  panel.dataset.severity = severity(score);
  $("#detailIcon").textContent = category.icon;
  $("#detailName").textContent = category.name;
  $("#detailScore").textContent = String(score);
  $("#detailTrack").setAttribute("aria-valuenow", String(score));
  $("#detailSeverity").textContent = severityLabel(score);
  const explanation = $("#detailExplanation");
  explanation.replaceChildren();

  if (!score) {
    const message = document.createElement("p");
    message.className = "no-signal-message";
    message.textContent = `No signs of ${category.name.toLowerCase()} threats detected.`;
    explanation.appendChild(message);
    const action = document.createElement("p");
    action.className = "recommended-action";
    action.textContent = "Recommended: Continue browsing with care.";
    explanation.appendChild(action);
  } else {
    const heading = document.createElement("b");
    heading.className = "explanation-heading";
    heading.textContent = "Why this was flagged";
    explanation.appendChild(heading);
    const list = document.createElement("ul");
    category.explanation.slice(0, 3).forEach((text) => {
      const item = document.createElement("li");
      item.textContent = text;
      list.appendChild(item);
    });
    explanation.appendChild(list);
    const action = document.createElement("p");
    action.className = "recommended-action";
    action.textContent = `Recommended: ${category.action}.`;
    explanation.appendChild(action);
  }

  cancelAnimationFrame(detailFrame);
  $("#detailProgress").style.width = reduceMotion.matches ? `${score}%` : "0%";
  panel.hidden = false;
  if (!reduceMotion.matches) {
    detailFrame = requestAnimationFrame(() => {
      detailFrame = requestAnimationFrame(() => { $("#detailProgress").style.width = `${score}%`; });
    });
  }
}

function selectCategory(key) {
  const next = selectedKey === key ? null : key;
  if (selectedKey) $(`.hex-tile[data-key="${selectedKey}"]`)?.classList.remove("selected");
  selectedKey = next;
  document.querySelectorAll(".hex-tile").forEach((tile) => {
    tile.classList.toggle("dimmed", Boolean(selectedKey) && tile.dataset.key !== selectedKey);
    tile.classList.toggle("selected", tile.dataset.key === selectedKey);
  });
  if (selectedKey) {
    const tile = $(`.hex-tile[data-key="${selectedKey}"]`);
    const host = $("#honeycomb");
    host.querySelector(".ripple-wave")?.remove();
    const ripple = document.createElement("span");
    ripple.className = "ripple-wave";
    ripple.setAttribute("aria-hidden", "true");
    ripple.style.left = `${tile.offsetLeft + tile.offsetWidth / 2}px`;
    ripple.style.top = `${tile.offsetTop + tile.offsetHeight / 2}px`;
    ripple.style.borderColor = tileColor(scores[selectedKey]);
    host.appendChild(ripple);
    window.setTimeout(() => ripple.remove(), 700);
    renderDetails(selectedKey);
  } else {
    $("#detailPanel").hidden = true;
  }
}

function closeDetails() {
  if (!selectedKey) return;
  const tile = $(`.hex-tile[data-key="${selectedKey}"]`);
  tile?.classList.remove("selected", "dimmed");
  selectedKey = null;
  document.querySelectorAll(".hex-tile").forEach((item) => item.classList.remove("dimmed"));
  $("#detailPanel").hidden = true;
}

function displayResult(result) {
  const numericScore = Math.max(0, Math.min(100, Number(result.score) || 0));
  $("#result").hidden = false;
  $("#score").textContent = String(numericScore);
  $("#riskScore").dataset.severity = severity(numericScore);
  $("#verdict").textContent = String(result.verdict || "UNKNOWN");
  $("#verdict").className = `badge v-${String(result.verdict || "UNKNOWN").toUpperCase()}`;
  $("#category").textContent = result.verdict === "SAFE" ? "No threat indicators found" : String(result.category || "Threat detected");
  const labels = (result.reasons || []).slice(0, 2).map((item) => item.label).filter(Boolean);
  $("#reasonSummary").textContent = labels.join(" · ") || "Based on local threat analysis";
  const host = (activeTab && activeTab.url && /^https?:/.test(activeTab.url)) ? new URL(activeTab.url).hostname : "";
  $("#siteTitle").textContent = host || "Protected page";
  const scoresIncluded = result.honeycomb && result.honeycomb.scores;
  if (scoresIncluded) {
    updateScores(scoresIncluded);
    $("#signalEmpty").hidden = true;
    $("#honeycomb").hidden = false;
  } else {
    $("#signalEmpty").hidden = false;
    $("#honeycomb").hidden = true;
  }
  if (result.verdict === "SAFE") {
    $("#latestThreat").hidden = true;
  } else {
    $("#latestThreat").textContent = `Latest threat: ${String(result.category || result.verdict)} · ${numericScore}/100 · select a signal for details`;
    $("#latestThreat").hidden = false;
  }
}

async function load() {
  try {
    const health = await getJson("/api/health");
    enabled = health.protection_enabled !== false;
    $("#toggle").textContent = enabled ? "Pause protection" : "Turn protection on";
    $("#protectionIndicator").classList.toggle("is-paused", !enabled);
    $("#protectionIndicator span").textContent = enabled ? "Protection on" : "Paused";
    $("#mode").textContent = `${health.mode.effective.toUpperCase()}${health.mode.fallback ? " · offline fallback" : ""}  /  Network ${health.mode.network}`;
  } catch (error) {
    $("#protectionIndicator").classList.add("is-offline");
    $("#protectionIndicator span").textContent = "Engine offline";
    $("#state").textContent = "ThreatDefender is not running. Start it with start.bat (Windows) or python run.py.";
    $("#siteTitle").textContent = "Local engine unavailable";
    $("#toggle").disabled = $("#rescan").disabled = true;
    $("#mode").textContent = error.message;
    return;
  }

  try {
    const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
    activeTab = tab || null;
    if (!tab || !/^https?:/.test(tab.url || "")) {
      $("#state").textContent = "This page type is not scanned.";
      $("#siteTitle").textContent = "Unsupported page";
      $("#rescan").disabled = true;
      return;
    }
    await scan();
  } catch (error) {
    $("#state").textContent = `Could not inspect this tab: ${error.message}`;
  }
}

async function scan() {
  if (!activeTab || !/^https?:/.test(activeTab.url || "")) {
    const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
    activeTab = tab || null;
  }
  if (!activeTab || !/^https?:/.test(activeTab.url || "")) {
    $("#state").textContent = "This page type is not scanned.";
    return;
  }
  const hostname = new URL(activeTab.url).hostname;
  $("#siteTitle").textContent = hostname;
  $("#state").textContent = "Analyzing this page…";
  $("#honeycomb").setAttribute("aria-busy", "true");
  $(".analysis-state").setAttribute("aria-busy", "true");
  $("#rescan").disabled = true;
  try {
    const result = await getJson("/api/scan", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ content: activeTab.url, kind: "url", online: true }),
    });
    displayResult(result);
    $("#state").textContent = "Analysis complete";
  } catch (error) {
    $("#state").textContent = `Scan failed: ${error.message}`;
  } finally {
    $("#honeycomb").removeAttribute("aria-busy");
    $(".analysis-state").removeAttribute("aria-busy");
    $("#rescan").disabled = false;
  }
}

async function loadTheme() {
  let theme = "dark";
  try {
    const saved = await chrome.storage.local.get("td-theme");
    theme = saved["td-theme"] === "light" || saved["td-theme"] === "dark"
      ? saved["td-theme"]
      : (window.matchMedia("(prefers-color-scheme: light)").matches ? "light" : "dark");
  } catch (error) {
    console.warn("Could not load the saved extension theme.", error);
    theme = window.matchMedia("(prefers-color-scheme: light)").matches ? "light" : "dark";
  }
  applyTheme(theme);
}

function applyTheme(theme) {
  const next = theme === "light" ? "light" : "dark";
  document.documentElement.dataset.theme = next;
  $("#themeToggle").setAttribute("aria-label", `Switch to ${next === "dark" ? "light" : "dark"} theme`);
  $("#themeToggle").title = `Switch to ${next === "dark" ? "light" : "dark"} theme`;
}

$("#rescan").addEventListener("click", scan);
$("#closeDetail").addEventListener("click", closeDetails);
$("#themeToggle").addEventListener("click", async () => {
  const next = document.documentElement.dataset.theme === "dark" ? "light" : "dark";
  applyTheme(next);
  try { await chrome.storage.local.set({ "td-theme": next }); }
  catch (error) { console.warn("Could not save the extension theme preference.", error); }
});
$("#toggle").addEventListener("click", async () => {
  const button = $("#toggle");
  button.disabled = true;
  try {
    await getJson("/api/protection", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ enabled: !enabled }),
    });
    await load();
  } catch (error) {
    $("#state").textContent = `Could not update protection: ${error.message}`;
  } finally {
    button.disabled = false;
  }
});
$("#quarantineAction").addEventListener("click", () => console.log("Quarantine action selected", selectedKey));
$("#safeAction").addEventListener("click", () => console.log("Mark-as-safe action selected", selectedKey));
document.addEventListener("keydown", (event) => {
  if (event.key === "Escape") closeDetails();
});
document.addEventListener("click", (event) => {
  if (!selectedKey || $("#detailPanel").hidden) return;
  if ($("#detailPanel").contains(event.target) || $("#honeycomb").contains(event.target)) return;
  closeDetails();
});
window.matchMedia("(prefers-color-scheme: light)").addEventListener("change", async (event) => {
  try {
    const saved = await chrome.storage.local.get("td-theme");
    if (!saved["td-theme"]) applyTheme(event.matches ? "light" : "dark");
  } catch (error) { console.warn("Could not check the saved extension theme.", error); }
});

document.documentElement.style.setProperty("--entrance-duration", reduceMotion.matches ? "0ms" : "650ms");
renderHoneycomb();
loadTheme();
load();
window.updateScores = updateScores;
