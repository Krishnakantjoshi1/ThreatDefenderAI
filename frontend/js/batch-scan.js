(function () {
  const { api, $ } = TD;
  const MAX_ITEMS = 500;
  const MAX_ITEM_CHARS = 20000;
  const MAX_BATCH_BYTES = 2 * 1024 * 1024;
  const PAGE_SIZE = 25;
  const JOB_STATUSES = new Set(["queued", "pending", "running", "completed", "completed_with_errors", "failed", "cancelled"]);
  const TERMINAL = new Set(["completed", "completed_with_errors", "failed", "cancelled"]);
  let jobId = null;
  let jobGeneration = 0;
  let pollTimer = null;
  let pollDelay = 800;
  let pollFailures = 0;
  let active = false;
  let cancelling = false;
  let currentItems = [];
  let resultsOffset = 0;
  let resultsTotal = 0;
  let resultsLoading = false;
  let pageHidden = false;

  function parseItems() {
    const type = $("#batchType").value;
    const lines = $("#batchInput").value.split(/\r?\n/);
    const items = [];
    const invalid = [];
    const duplicates = [];
    const seen = new Set();
    let bytes = 0;

    lines.forEach((raw, index) => {
      const value = raw.trim();
      if (!value) return;
      if (value.length > MAX_ITEM_CHARS) {
        invalid.push(index + 1);
        return;
      }
      let normalized = value;
      if (type === "url") {
        try {
          const parsed = new URL(value);
          if (!["http:", "https:"].includes(parsed.protocol)) throw new Error("Unsupported URL protocol");
          normalized = parsed.href;
        } catch (error) {
          invalid.push(index + 1);
          return;
        }
      }
      const key = type === "url" ? normalized : value;
      if (seen.has(key)) {
        duplicates.push(index + 1);
        return;
      }
      seen.add(key);
      items.push({ type, value, client_ref: String(index + 1) });
    });

    const tooMany = items.length > MAX_ITEMS;
    const tooLarge = new TextEncoder().encode(JSON.stringify(items)).length > MAX_BATCH_BYTES;
    return { items, invalid, duplicates, tooMany, tooLarge, nonEmpty: lines.filter((line) => line.trim()).length };
  }

  function updateValidation() {
    const result = parseItems();
    $("#batchCount").textContent = `${result.nonEmpty} non-empty line${result.nonEmpty === 1 ? "" : "s"} · ${result.items.length} unique valid item${result.items.length === 1 ? "" : "s"}`;
    const summary = $("#batchValidation");
    summary.replaceChildren();
    if (result.duplicates.length) {
      const duplicateNote = document.createElement("p");
      duplicateNote.textContent = `${result.duplicates.length} duplicate line${result.duplicates.length === 1 ? "" : "s"} will be skipped.`;
      summary.appendChild(duplicateNote);
    }
    if (result.invalid.length) {
      const note = document.createElement("p");
      note.textContent = `Invalid item${result.invalid.length === 1 ? "" : "s"} on line${result.invalid.length === 1 ? "" : "s"}: ${result.invalid.join(", ")}. Fix these lines before submitting.`;
      note.className = "batch-item-error";
      summary.appendChild(note);
    }
    if (result.tooMany) {
      const note = document.createElement("p");
      note.textContent = `The batch exceeds the ${MAX_ITEMS}-item limit.`;
      note.className = "batch-item-error";
      summary.appendChild(note);
    }
    if (result.tooLarge) {
      const note = document.createElement("p");
      note.textContent = "The batch exceeds the 2 MB request limit.";
      note.className = "batch-item-error";
      summary.appendChild(note);
    }
    $("#batchStart").disabled = active || result.invalid.length > 0 || result.tooMany || result.tooLarge || result.items.length === 0;
    return result;
  }

  function stopPolling() {
    if (pollTimer) clearTimeout(pollTimer);
    pollTimer = null;
  }

  function setBatchError(message) {
    const error = $("#batchError");
    error.textContent = message;
    error.hidden = !message;
  }

  function setJobState(data) {
    if (!data || typeof data.status !== "string" ||
        !Number.isSafeInteger(data.total) || !Number.isSafeInteger(data.completed) ||
        !Number.isSafeInteger(data.failed) || data.total < 0 || data.completed < 0 ||
        data.completed > data.total || data.failed < 0 || data.failed > data.total) {
      throw new Error("The batch API returned an invalid progress response.");
    }
    const status = data.status.toLowerCase();
    if (!JOB_STATUSES.has(status)) throw new Error(`The batch API returned an unsupported job status: ${status}`);
    $("#batchStatus").textContent = status.replaceAll("_", " ");
    $("#batchProgressText").textContent = `${data.completed} of ${data.total} completed · ${data.failed} failed`;
    $("#batchProgressBar").max = Math.max(data.total, 1);
    $("#batchProgressBar").value = Math.min(data.completed, data.total);
    $("#batchJobMessage").textContent = cancelling ? "Cancellation requested. Waiting for the job to stop." : "";
    const isTerminal = TERMINAL.has(status);
    active = !isTerminal;
    $("#batchStart").disabled = active || updateValidation().invalid.length > 0;
    $("#batchCancel").hidden = !active || cancelling;
    if (isTerminal) {
      stopPolling();
      $("#batchJobMessage").textContent = status === "completed_with_errors"
        ? "The batch finished with item-level failures. Review the results below."
        : status === "cancelled"
          ? "The batch was cancelled. Completed results remain available below."
          : status === "failed"
            ? "The batch failed. Any completed item results remain available below."
            : "The batch completed successfully.";
      loadResults(0);
      return false;
    }
    return true;
  }

  function schedulePoll(delay = pollDelay) {
    if (pageHidden) return;
    stopPolling();
    pollTimer = setTimeout(pollJob, delay);
  }

  async function pollJob() {
    if (!active || !jobId) return;
    try {
      const data = await api(`/api/scans/jobs/${encodeURIComponent(jobId)}`, { timeoutMs: 15000 });
      if (pageHidden) return;
      pollFailures = 0;
      pollDelay = Math.min(Math.max(pollDelay * 1.25, 1000), 5000);
      if (setJobState(data)) schedulePoll(pollDelay);
    } catch (error) {
      if (error.status === 401) {
        active = false;
        stopPolling();
        $("#batchCancel").hidden = true;
        $("#batchResume").hidden = false;
        $("#batchJobMessage").textContent = "The server requires a valid session. Sign in using the server's supported flow, then resume progress updates.";
        $("#batchStart").disabled = true;
        return;
      }
      pollFailures += 1;
      if (pollFailures >= 6) {
        active = false;
        $("#batchCancel").hidden = true;
        $("#batchResume").hidden = false;
        $("#batchJobMessage").textContent = `Progress updates paused after repeated request failures: ${error.message}`;
        $("#batchStart").disabled = true;
        return;
      }
      $("#batchJobMessage").textContent = `Could not refresh progress. Retrying… (${error.message})`;
      pollDelay = Math.min(pollDelay * 2, 10000);
      schedulePoll(pollDelay);
    }
  }

  function renderResults(data, offset) {
    if (!data || !Array.isArray(data.items)) {
      throw new Error("The batch results API returned an invalid response.");
    }
    if (!Number.isSafeInteger(data.total) || data.total < 0) {
      throw new Error("The batch results API did not return a valid total.");
    }
    resultsOffset = offset;
    resultsTotal = data.total;
    const host = $("#batchResults");
    host.replaceChildren();

    const heading = document.createElement("h3");
    heading.textContent = "Item results";
    host.appendChild(heading);
    const tableWrap = document.createElement("div");
    tableWrap.className = "table-wrap";
    const table = document.createElement("table");
    const head = document.createElement("thead");
    const headerRow = document.createElement("tr");
    ["Item", "Outcome", "Verdict", "Risk"].forEach((label) => {
      const th = document.createElement("th");
      th.textContent = label;
      headerRow.appendChild(th);
    });
    head.appendChild(headerRow);
    table.appendChild(head);

    const body = document.createElement("tbody");
    const retryItems = [];
    data.items.forEach((item, index) => {
      const row = document.createElement("tr");
      const result = item && typeof item.result === "object" && item.result ? item.result : {};
      const score = result.score ?? (item && item.score);
      const outcome = String((item && item.status) || "");
      const failed = Boolean(item && (item.error || outcome.toLowerCase() === "failed"));
      const clientRef = item && item.client_ref != null ? String(item.client_ref) : "";
      const original = currentItems.find((candidate) => candidate.client_ref === clientRef) || currentItems[offset + index];
      if (failed && original) retryItems.push(original);
      const values = [
        clientRef ? `Line ${clientRef}` : `Item ${offset + index + 1}`,
        item && item.error ? `Failed: ${String(item.error)}` : String((item && item.status) || "Completed"),
        String(result.verdict || (item && item.verdict) || "—"),
        Number.isFinite(Number(score)) ? String(score) : "—",
      ];
      values.forEach((value, column) => {
        const cell = document.createElement("td");
        cell.textContent = value;
        if (column === 1 && failed) cell.className = "batch-item-error";
        row.appendChild(cell);
      });
      body.appendChild(row);
    });
    table.appendChild(body);
    tableWrap.appendChild(table);
    host.appendChild(tableWrap);

    if (retryItems.length) {
      const retry = document.createElement("button");
      retry.type = "button";
      retry.className = "report-action";
      retry.textContent = `Retry ${retryItems.length} failed item${retryItems.length === 1 ? "" : "s"} on this page`;
      retry.addEventListener("click", () => submitBatch(retryItems));
      host.appendChild(retry);
    }

    const pager = document.createElement("div");
    pager.className = "row spread";
    pager.style.marginTop = "12px";
    const summary = document.createElement("span");
    summary.className = "small muted";
    summary.textContent = `Showing ${data.items.length ? offset + 1 : 0}-${offset + data.items.length} of ${resultsTotal} results`;
    const controls = document.createElement("div");
    controls.className = "row";
    const previous = document.createElement("button");
    previous.type = "button";
    previous.textContent = "Previous";
    previous.disabled = offset === 0 || resultsLoading;
    previous.addEventListener("click", () => loadResults(Math.max(0, resultsOffset - PAGE_SIZE)));
    const next = document.createElement("button");
    next.type = "button";
    next.textContent = "Next";
    next.disabled = offset + data.items.length >= resultsTotal || resultsLoading;
    next.addEventListener("click", () => loadResults(resultsOffset + PAGE_SIZE));
    controls.append(previous, next);
    pager.append(summary, controls);
    host.appendChild(pager);
  }

  async function loadResults(offset) {
    if (!jobId || resultsLoading) return;
    resultsLoading = true;
    const requestedJobId = jobId;
    const requestedGeneration = jobGeneration;
    $("#batchJobMessage").textContent = "Loading item results…";
    try {
      const query = new URLSearchParams({ limit: String(PAGE_SIZE), offset: String(offset) });
      const data = await api(`/api/scans/jobs/${encodeURIComponent(requestedJobId)}/results?${query}`);
      if (requestedJobId !== jobId || requestedGeneration !== jobGeneration) return;
      resultsLoading = false;
      renderResults(data, offset);
      $("#batchJobMessage").textContent = "";
    } catch (error) {
      $("#batchJobMessage").textContent = `Could not load item results: ${error.message}`;
    } finally {
      resultsLoading = false;
    }
  }

  $("#batchInput").addEventListener("input", updateValidation);
  $("#batchType").addEventListener("change", updateValidation);
  async function submitBatch(items) {
    if (!items.length || active) return;
    setBatchError("");
    $("#batchProgress").hidden = false;
    $("#batchResults").replaceChildren();
    currentItems = items;
    jobGeneration += 1;
    resultsLoading = false;
    $("#batchStatus").textContent = "Submitting batch…";
    $("#batchProgressText").textContent = `0 of ${items.length} completed`;
    $("#batchProgressBar").max = items.length;
    $("#batchProgressBar").value = 0;
    $("#batchStart").disabled = true;
    try {
      const response = await api("/api/scans/batch", {
        method: "POST",
        timeoutMs: 30000,
        body: { items },
      });
      const id = String(response && response.job_id || "");
      if (!/^[A-Za-z0-9_-]{1,128}$/.test(id)) throw new Error("The batch API returned an invalid job ID.");
      jobId = id;
      pollDelay = 800;
      pollFailures = 0;
      cancelling = false;
      if (setJobState(response)) schedulePoll(0);
    } catch (error) {
      $("#batchProgress").hidden = true;
      if (error.status === 404 || error.status === 405) {
        setBatchError("Batch scanning is not available on this server yet. Its API endpoints are not implemented.");
      } else if (error.status === 413) {
        setBatchError("The batch exceeds the server's request-size limit. Remove items or shorten the text and try again.");
      } else if (error.status === 429 || error.status === 503) {
        setBatchError(`The scan queue is full or temporarily unavailable. ${error.message}`);
      } else if (error.status === 401) {
        setBatchError("The server rejected this request because no valid session is available.");
      } else {
        setBatchError(error.message);
      }
      $("#batchStart").disabled = false;
    }
  }

  $("#batchStart").addEventListener("click", () => {
    const parsed = updateValidation();
    if (parsed.invalid.length || parsed.tooMany || parsed.tooLarge) return;
    submitBatch(parsed.items);
  });

  $("#batchCancel").addEventListener("click", async () => {
    if (!jobId || !active || cancelling) return;
    cancelling = true;
    $("#batchCancel").disabled = true;
    $("#batchJobMessage").textContent = "Requesting cancellation…";
    try {
      await api(`/api/scans/jobs/${encodeURIComponent(jobId)}/cancel`, { method: "POST", timeoutMs: 15000 });
      $("#batchCancel").hidden = true;
      schedulePoll(0);
    } catch (error) {
      cancelling = false;
      $("#batchCancel").disabled = false;
      $("#batchJobMessage").textContent = `Could not cancel this job: ${error.message}`;
    }
  });

  $("#batchResume").addEventListener("click", () => {
    if (!jobId || active) return;
    active = true;
    pollFailures = 0;
    pollDelay = 800;
    $("#batchResume").hidden = true;
    $("#batchCancel").hidden = false;
    $("#batchCancel").disabled = false;
    $("#batchJobMessage").textContent = "Resuming progress updates…";
    schedulePoll(0);
  });

  document.querySelectorAll("[role=tab][aria-controls]").forEach((tab) => tab.addEventListener("click", () => {
    const batchSelected = tab.id === "view-batch";
    $("#view-single").setAttribute("aria-selected", String(!batchSelected));
    $("#view-batch").setAttribute("aria-selected", String(batchSelected));
    $("#singlePane").hidden = batchSelected;
    $("#batchPane").hidden = !batchSelected;
    tab.focus();
  }));

  window.addEventListener("pagehide", () => {
    pageHidden = true;
    active = false;
    stopPolling();
  });
  window.addEventListener("pageshow", (event) => {
    if (!event.persisted || !jobId) return;
    pageHidden = false;
    active = true;
    $("#batchResume").hidden = true;
    $("#batchCancel").hidden = false;
    schedulePoll(0);
  });
  updateValidation();
})();
