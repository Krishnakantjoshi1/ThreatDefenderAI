const p = new URLSearchParams(location.search);
const url = p.get("u") || "";
const $ = (s) => document.querySelector(s);
$("#score").textContent = p.get("s") || "?";
const v = p.get("v") || "DANGEROUS";
$("#verdict").textContent = v; $("#verdict").className = "badge v-" + v;
$("#title").textContent = p.get("c") || "Dangerous page";
$("#addr").textContent = url;
(p.get("r") || "").split("|").filter(Boolean).forEach((t) => { const li = document.createElement("li"); li.textContent = t; $("#reasons").appendChild(li); });
if (p.get("id")) $("#analyze").href = "http://127.0.0.1:8000/attack_story.html?id=" + encodeURIComponent(p.get("id"));
else $("#analyze").hidden = true;

$("#close").addEventListener("click", async () => { const t = await chrome.tabs.getCurrent(); if (t) chrome.tabs.remove(t.id); else window.close(); });
$("#proceed").addEventListener("click", () => {
  let host = ""; try { host = new URL(url).hostname; } catch (e) { return; }
  chrome.runtime.sendMessage({ type: "allow", host }, () => { location.href = url; });
});
