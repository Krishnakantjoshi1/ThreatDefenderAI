(function () {
  const { api, $ } = TD;
  const status = $("#reportStatus");
  const encoder = new TextEncoder();
  const historyButton = $("#historyReport");
  let historyRecords = null;
  let historyLoadError = null;
  const newestScans = new Map();

  async function refreshHistory() {
    if (historyButton) historyButton.disabled = true;
    try {
      const history = await api("/api/history?limit=500");
      if (!history || !Array.isArray(history.items)) throw new Error("The local history service returned invalid scan data.");
      historyRecords = history.items;
      historyLoadError = null;
      for (const scan of newestScans.values()) addScan(scan);
    } catch (error) {
      historyLoadError = error;
    } finally {
      if (historyButton) historyButton.disabled = false;
    }
  }

  function addScan(scan) {
    const id = Number(scan && scan.id);
    if (!Number.isSafeInteger(id) || id <= 0) return;
    newestScans.set(id, scan);
    if (historyRecords) {
      historyRecords = [scan, ...historyRecords.filter((record) => Number(record.id) !== id)]
        .sort((left, right) => Number(right.id) - Number(left.id));
    }
  }

  function printable(value) {
    return String(value ?? "")
      .normalize("NFKD")
      .replace(/[\u0300-\u036f]/g, "")
      .replace(/[^\x20-\x7e]/g, "?");
  }

  function escapePdf(value) {
    return printable(value).replace(/[\\()]/g, "\\$&");
  }

  function wrap(value, width = 86) {
    const words = printable(value).split(/\s+/);
    const lines = [];
    let line = "";
    for (const word of words) {
      if (word.length > width) {
        if (line) lines.push(line);
        line = "";
        for (let offset = 0; offset < word.length; offset += width) {
          lines.push(word.slice(offset, offset + width));
        }
      } else if (!line) {
        line = word;
      } else if (line.length + word.length + 1 <= width) {
        line += ` ${word}`;
      } else {
        lines.push(line);
        line = word;
      }
    }
    if (line) lines.push(line);
    return lines.length ? lines : [""];
  }

  function recordLines(record) {
    return [
      `Scan ${record.id ?? ""} | ${record.created_at || "Unknown time"}`,
      `Type: ${record.kind || "Unknown"} | Category: ${record.category || "Uncategorized"}`,
      `Risk: ${record.score ?? 0}/100 | Verdict: ${record.verdict || "Unknown"} | Action: ${record.action || "None"}`,
      ...wrap(`Preview: ${record.preview || "No preview available"}`),
      "",
    ];
  }

  function buildPdf(records, title) {
    const pages = [[
      title,
      `Generated: ${new Date().toISOString()}`,
      `Scans included: ${records.length}`,
      "",
    ]];
    for (const record of records) {
      for (const line of recordLines(record)) {
        if (pages[pages.length - 1].length >= 48) pages.push([`${title} (continued)`, ""]);
        pages[pages.length - 1].push(line);
      }
    }

    const objects = [
      "<< /Type /Catalog /Pages 2 0 R >>",
      "",
      "<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica /Encoding /WinAnsiEncoding >>",
    ];
    const pageIds = [];
    pages.forEach((lines, index) => {
      const pageId = objects.length + 1;
      const streamId = pageId + 1;
      pageIds.push(pageId);
      let y = 752;
      const commands = [];
      lines.forEach((line, lineIndex) => {
        const fontSize = lineIndex === 0 ? 16 : 9;
        commands.push(`BT /F1 ${fontSize} Tf 48 ${y} Td (${escapePdf(line)}) Tj ET`);
        y -= lineIndex === 0 ? 24 : 14;
      });
      commands.push(`BT /F1 9 Tf 520 28 Td (${index + 1} / ${pages.length}) Tj ET`);
      const stream = `${commands.join("\n")}\n`;
      objects.push(
        `<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] ` +
        `/Resources << /Font << /F1 3 0 R >> >> /Contents ${streamId} 0 R >>`,
      );
      objects.push(`<< /Length ${encoder.encode(stream).length} >>\nstream\n${stream}endstream`);
    });
    objects[1] = `<< /Type /Pages /Kids [${pageIds.map((id) => `${id} 0 R`).join(" ")}] /Count ${pageIds.length} >>`;

    let document = "%PDF-1.4\n%TD\n";
    const offsets = [0];
    objects.forEach((object, index) => {
      offsets.push(encoder.encode(document).length);
      document += `${index + 1} 0 obj\n${object}\nendobj\n`;
    });
    const xrefOffset = encoder.encode(document).length;
    document += `xref\n0 ${objects.length + 1}\n0000000000 65535 f \n`;
    for (const offset of offsets.slice(1)) document += `${String(offset).padStart(10, "0")} 00000 n \n`;
    document += `trailer\n<< /Size ${objects.length + 1} /Root 1 0 R >>\nstartxref\n${xrefOffset}\n%%EOF\n`;
    return new Blob([encoder.encode(document)], { type: "application/pdf" });
  }

  function savePdf(records, title, filename) {
    const objectUrl = URL.createObjectURL(buildPdf(records, title));
    const link = document.createElement("a");
    link.href = objectUrl;
    link.download = filename;
    link.hidden = true;
    document.body.appendChild(link);
    link.click();
    link.remove();
    window.setTimeout(() => URL.revokeObjectURL(objectUrl), 60000);
  }

  function getReportRecords(pathname) {
    if (pathname === "/api/reports/history.pdf") {
      if (!historyRecords) throw historyLoadError || new Error("Local scan history is still loading. Try again shortly.");
      return { records: historyRecords, title: "ThreatDefender scan history" };
    }
    const match = pathname.match(/^\/api\/reports\/scans\/(\d+)\.pdf$/);
    if (match) {
      const record = historyRecords && historyRecords.find((item) => String(item.id) === match[1]);
      if (!record) throw new Error("This scan is not available in the locally stored history.");
      return { records: [record], title: "ThreatDefender scan report" };
    }
    throw new Error("This report link is not valid.");
  }

  document.addEventListener("click", (event) => {
    const target = event.target instanceof Element ? event.target : null;
    const button = target && target.closest("[data-report-url]");
    if (!button) return;
    event.preventDefault();
    event.stopPropagation();

    const url = new URL(button.dataset.reportUrl, location.origin);
    if (url.origin !== location.origin) {
      if (status) status.textContent = "This report link is not valid.";
      return;
    }

    button.disabled = true;
    try {
      const { records, title } = getReportRecords(url.pathname);
      if (status) status.textContent = "Creating a PDF from scan history stored on this device…";
      savePdf(records, title, button.dataset.reportName || "threatdefender-report.pdf");
      if (status) status.textContent = records.length
        ? `PDF download started with ${records.length} locally stored scan${records.length === 1 ? "" : "s"}.`
        : "Empty history PDF download started; no scans are currently stored.";
    } catch (error) {
      if (status) {
        status.textContent = historyLoadError && !historyRecords
          ? `Could not read local scan history: ${historyLoadError.message}`
          : `Could not create the PDF from local scan history: ${error.message}`;
      }
    } finally {
      button.disabled = false;
    }
  });

  window.addEventListener("td:scan-result", (event) => addScan(event.detail));
  refreshHistory();
})();
