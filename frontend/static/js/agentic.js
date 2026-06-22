/* Frontend controller for the agentic HITL review flow. */
(() => {
  const API = window.AGENTIC_API_URL || "/api";

  const $ = (id) => document.getElementById(id);
  const show = (el) => el.classList.remove("hidden");
  const hide = (el) => el.classList.add("hidden");

  let sessionId = null;
  let pollTimer = null;
  let comments = [];
  let checksCatalog = [];        // [{id, display_name, description, severity, enabled_by_default, applies_to}]
  let templatesCatalog = {};     // {template_id: {...}}

  // ---------- API ----------
  function redirectToLogin() {
    window.location.href = "/login";
  }

  async function api(path, opts = {}) {
    const res = await fetch(API + path, {
      ...opts,
      credentials: "include",
      headers: { ...(opts.headers || {}), ...(opts.body && !(opts.body instanceof FormData) ? { "Content-Type": "application/json" } : {}) },
    });
    if (res.status === 401) {
      redirectToLogin();
      throw new Error("401: authentication required");
    }
    if (!res.ok) {
      let detail = "";
      try { detail = (await res.json()).error; } catch { detail = await res.text(); }
      throw new Error(`${res.status}: ${detail}`);
    }
    if (res.status === 204) return null;
    return res.json();
  }

  // ---------- auth ----------
  async function ensureAuthenticated() {
    try {
      const me = await api("/me");
      if (me && me.username) {
        const el = $("userName");
        if (el) el.textContent = me.username;
      }
      return true;
    } catch {
      redirectToLogin();
      return false;
    }
  }

  async function logout() {
    try {
      await fetch(`${API}/logout`, { method: "POST", credentials: "include" });
    } catch { /* ignore */ }
    redirectToLogin();
  }

  // ---------- catalog loading ----------
  async function loadCatalogs() {
    try {
      const [c, t] = await Promise.all([api("/checks"), api("/templates")]);
      checksCatalog = (c && c.checks) || [];
      templatesCatalog = (t && t.templates) || {};
      renderChecks();
    } catch (e) {
      console.warn("Failed to load /checks or /templates:", e);
      $("checksContainer").innerHTML = `<span class="muted small">Could not load check catalog (${escapeHtml(e.message)}). Defaults will be used.</span>`;
      $("checksSummary").textContent = "(unavailable)";
    }
  }

  function renderChecks() {
    const host = $("checksContainer");
    host.innerHTML = "";
    if (!checksCatalog.length) {
      host.innerHTML = `<span class="muted small">No checks reported by backend.</span>`;
      return;
    }
    const docType = $("documentType").value;
    for (const ck of checksCatalog) {
      const applies = ck.applies_to || ["ANY"];
      const relevant = !docType || applies.includes("ANY") || applies.includes(docType);
      const row = document.createElement("label");
      row.className = "check-row" + (relevant ? "" : " check-irrelevant");
      row.title = ck.description || "";
      const checked = ck.enabled_by_default && relevant ? "checked" : "";
      row.innerHTML = `
        <input type="checkbox" class="check-cb" data-id="${escapeHtml(ck.id)}" ${checked} />
        <span class="check-name">${escapeHtml(ck.display_name || ck.id)}</span>
        <span class="badge sev-${(ck.severity || "moderate").toLowerCase()}">${escapeHtml(ck.severity || "")}</span>
        <span class="muted small check-scope">${escapeHtml(applies.join(", "))}</span>
      `;
      host.appendChild(row);
    }
    updateChecksSummary();
    host.querySelectorAll(".check-cb").forEach((cb) =>
      cb.addEventListener("change", updateChecksSummary)
    );
  }

  function updateChecksSummary() {
    const boxes = document.querySelectorAll("#checksContainer .check-cb");
    const total = boxes.length;
    const selected = Array.from(boxes).filter((b) => b.checked).length;
    $("checksSummary").textContent = `(${selected} of ${total} selected)`;
  }

  function collectSelectedChecks() {
    const boxes = document.querySelectorAll("#checksContainer .check-cb");
    if (!boxes.length) return null;  // catalog never loaded → let backend use defaults
    const all = Array.from(boxes);
    const selected = all.filter((b) => b.checked).map((b) => b.dataset.id);
    // If user kept everything ticked, omit the list so backend applies its own defaults.
    if (selected.length === all.length) return null;
    return selected;
  }

  function setAllChecks(state) {
    document.querySelectorAll("#checksContainer .check-cb").forEach((cb) => { cb.checked = state; });
    updateChecksSummary();
  }

  function resetChecksToDefaults() {
    const docType = $("documentType").value;
    const byId = Object.fromEntries(checksCatalog.map((c) => [c.id, c]));
    document.querySelectorAll("#checksContainer .check-cb").forEach((cb) => {
      const ck = byId[cb.dataset.id];
      if (!ck) return;
      const applies = ck.applies_to || ["ANY"];
      const relevant = !docType || applies.includes("ANY") || applies.includes(docType);
      cb.checked = !!ck.enabled_by_default && relevant;
    });
    updateChecksSummary();
  }

  function renderContextBox(s) {
    const box = $("contextBox");
    if (!box) return;
    const tm = s.template_match;
    const pp = s.pre_pass_summary;
    const dt = s.document_type;
    if (!tm && !pp && !dt) { hide(box); return; }
    const parts = [];
    if (dt) parts.push(`<div><strong>Document type:</strong> ${escapeHtml(dt)}</div>`);
    if (tm) {
      const status = tm.status || "?";
      const cls = `tm-${status}`;
      parts.push(
        `<div class="template-match ${cls}">` +
        `<strong>Template:</strong> <span class="badge">${escapeHtml(status)}</span> ` +
        `${tm.found_id ? `<code>${escapeHtml(tm.found_id)}</code>` : ""} ` +
        `<span class="muted small">${escapeHtml(tm.message || "")}</span>` +
        `</div>`
      );
    }
    if (pp) {
      parts.push(
        `<div class="pre-pass"><strong>Pre-pass:</strong> ` +
        `${pp.glossary_terms} glossary, ${pp.req_tags} REQ, ${pp.ver_tags} VER, ` +
        `${pp.test_cases} test rows, ${pp.revision_entries} revisions, ${pp.authors.length} authors` +
        `</div>`
      );
    }
    box.innerHTML = parts.join("");
    show(box);
  }

  // ---------- upload ----------
  $("uploadForm").addEventListener("submit", async (e) => {
    e.preventDefault();
    const fd = new FormData();
    fd.append("document", $("document").files[0]);
    fd.append("template", $("template").files[0]);
    fd.append("brand", $("brand").value || "Philips");
    const docType = $("documentType").value;
    if (docType) fd.append("document_type", docType);
    const minSev = $("minSeverity").value;
    if (minSev) fd.append("min_severity", minSev);
    const maxPer = $("maxPerSection").value;
    if (maxPer) fd.append("max_per_section", maxPer);
    const selected = collectSelectedChecks();
    if (selected !== null) fd.append("enabled_checks", selected.join(","));
    try {
      const out = await api("/sessions", { method: "POST", body: fd });
      sessionId = out.session_id;
      hide($("uploadStep"));
      show($("progressStep"));
      startPolling();
    } catch (err) {
      alert("Failed to start session: " + err.message);
    }
  });

  // ---------- polling ----------
  function startPolling() {
    stopPolling();
    pollTimer = setInterval(pollOnce, 1500);
    pollOnce();
  }
  function stopPolling() {
    if (pollTimer) { clearInterval(pollTimer); pollTimer = null; }
  }

  async function pollOnce() {
    try {
      const s = await api(`/sessions/${sessionId}`);
      const p = s.progress || {};
      const live = s.live || {};
      $("progressBar").style.width = (p.percent || 0) + "%";
      $("progressBar").textContent = (p.percent || 0) + "%";
      $("progressLabel").textContent = p.label || s.status;
      const lf = (live.in_flight || []);
      const liveBits = [];
      if (live.total != null) liveBits.push(`${live.completed || 0}/${live.total} done`);
      if (lf.length) liveBits.push(`waiting on: ${lf.slice(0, 4).join(", ")}${lf.length > 4 ? "…" : ""}`);
      const dbg = `stage: ${p.stage || s.status} · findings: ${s.findings_count ?? "?"} · drafts: ${s.draft_comment_count ?? "?"}`;
      $("stageLabel").textContent = liveBits.length ? `${liveBits.join(" · ")} — ${dbg}` : dbg;

      renderContextBox(s);

      if (s.status === "awaiting_review") {
        stopPolling();
        await loadComments(s);
        hide($("progressStep"));
        show($("reviewStep"));
      } else if (s.status === "done") {
        stopPolling();
        await showResults(s);
      } else if (s.status === "error") {
        stopPolling();
        alert("Agent error: " + (s.error || "unknown"));
      }
    } catch (e) {
      console.warn("poll failed", e);
    }
  }

  // ---------- review ----------
  async function loadComments(sessionStatus) {
    const data = await api(`/sessions/${sessionId}/comments`);
    comments = (data.draft_comments || []).map((c) => ({ ...c }));
    if (sessionStatus && Array.isArray(sessionStatus.errors) && sessionStatus.errors.length) {
      $("errorsBox").textContent = sessionStatus.errors.join("\n");
      show($("errorsBox"));
    } else {
      hide($("errorsBox"));
    }
    renderComments();
  }

  function severityClass(sev) {
    return "sev-" + (sev || "moderate").toLowerCase();
  }

  function getFiltered() {
    const q = ($("filterText").value || "").toLowerCase();
    const sev = $("filterSeverity").value;
    const dec = $("filterDecision").value;
    return comments.filter((c) => {
      if (sev && c.severity !== sev) return false;
      if (dec && (c.decision || "pending") !== dec) return false;
      if (!q) return true;
      const blob = `${c.heading || ""} ${c.evidence || ""} ${c.message || ""} ${c.check_id || ""}`.toLowerCase();
      return blob.includes(q);
    });
  }

  function renderComments() {
    const list = $("commentsList");
    list.innerHTML = "";
    const visible = getFiltered();
    const counts = comments.reduce((acc, c) => {
      acc[c.decision || "pending"] = (acc[c.decision || "pending"] || 0) + 1;
      return acc;
    }, {});
    const totalIssues = comments.reduce((n, c) => n + (c.issue_count || 1), 0);
    $("reviewSummary").textContent =
      `${comments.length} heading group(s), ${totalIssues} underlying issue(s) · ` +
      `${counts.approved || 0} approved · ${counts.rejected || 0} rejected · ` +
      `${counts.pending || 0} pending · showing ${visible.length}`;

    if (!visible.length) {
      list.innerHTML = `<p class="muted">No comments match the current filter.</p>`;
      return;
    }

    for (const c of visible) {
      const card = document.createElement("div");
      const decision = c.decision || "pending";
      card.className = `comment-card severity-${(c.severity || "moderate").toLowerCase()} decision-${decision}`;
      const items = Array.isArray(c.items) ? c.items : [];
      const itemsHtml = items.map((it, i) => `
        <li class="issue-item">
          <span class="badge ${severityClass(it.severity)}">${it.severity || ""}</span>
          <span class="badge">${escapeHtml(it.check_id || "")}</span>
          <span class="issue-msg">${escapeHtml(it.message || "")}</span>
          ${it.evidence ? `<div class="issue-evidence">"${escapeHtml(it.evidence)}"</div>` : ""}
        </li>`).join("");
      card.innerHTML = `
        <div class="comment-meta">
          <span class="badge ${severityClass(c.severity)}">${c.severity || ""}</span>
          <span class="badge">${c.issue_count || items.length || 1} issue(s)</span>
          <span class="muted small">id: ${c.id}</span>
        </div>
        <div class="comment-heading">📍 ${escapeHtml(c.heading || "(document-wide)")}</div>
        <details class="issue-details">
          <summary>Show ${items.length || 1} underlying finding(s)</summary>
          <ul class="issues-list">${itemsHtml}</ul>
        </details>
        <label class="muted small">Comment text inserted under this heading (editable):</label>
        <textarea class="comment-message" data-id="${c.id}" rows="${Math.min(12, 3 + (items.length || 0))}">${escapeHtml(c.edited_message || c.message || "")}</textarea>
        <div class="comment-actions">
          <button class="btn btn-approve" data-action="approved" data-id="${c.id}">✅ Approve heading</button>
          <button class="btn btn-reject"  data-action="rejected" data-id="${c.id}">❌ Reject heading</button>
          <button class="btn btn-secondary" data-action="pending" data-id="${c.id}">↩️ Reset</button>
        </div>
      `;
      list.appendChild(card);
    }

    list.querySelectorAll("button[data-action]").forEach((b) => {
      b.addEventListener("click", onDecisionClick);
    });
    list.querySelectorAll("textarea.comment-message").forEach((t) => {
      t.addEventListener("input", onEdit);
    });
  }

  function escapeHtml(s) {
    return String(s).replace(/[&<>"']/g, (c) => ({ "&":"&amp;","<":"&lt;",">":"&gt;","\"":"&quot;","'":"&#39;" }[c]));
  }

  let saveTimer = null;
  function scheduleSave() {
    if (saveTimer) clearTimeout(saveTimer);
    saveTimer = setTimeout(syncDecisions, 250);
  }

  async function syncDecisions() {
    const decisions = comments.map((c) => ({
      id: c.id,
      decision: c.decision || "pending",
      edited_message: c.edited_message,
    }));
    try {
      await api(`/sessions/${sessionId}/bulk`, {
        method: "POST",
        body: JSON.stringify({ decisions }),
      });
    } catch (e) {
      console.warn("sync failed", e);
    }
  }

  function onDecisionClick(e) {
    const id = e.currentTarget.dataset.id;
    const action = e.currentTarget.dataset.action;
    const c = comments.find((x) => x.id === id);
    if (!c) return;
    c.decision = action;
    renderComments();
    scheduleSave();
  }

  function onEdit(e) {
    const id = e.target.dataset.id;
    const c = comments.find((x) => x.id === id);
    if (!c) return;
    c.edited_message = e.target.value;
    scheduleSave();
  }

  ["filterText", "filterSeverity", "filterDecision"].forEach((id) =>
    $(id).addEventListener("input", renderComments)
  );

  $("approveAllBtn").addEventListener("click", () => {
    for (const c of getFiltered()) c.decision = "approved";
    renderComments();
    scheduleSave();
  });
  $("rejectAllBtn").addEventListener("click", () => {
    for (const c of getFiltered()) c.decision = "rejected";
    renderComments();
    scheduleSave();
  });

  $("finalizeBtn").addEventListener("click", async () => {
    $("finalizeBtn").disabled = true;
    try {
      await syncDecisions();
      await api(`/sessions/${sessionId}/resume`, { method: "POST" });
      hide($("reviewStep"));
      show($("progressStep"));
      startPolling();
    } catch (e) {
      alert("Failed to finalize: " + e.message);
      $("finalizeBtn").disabled = false;
    }
  });

  // ---------- results ----------
  async function showResults(s) {
    hide($("progressStep"));
    show($("resultsStep"));
    $("downloadDoc").href    = `${API}/sessions/${sessionId}/download/review_doc`;
    $("downloadReport").href = `${API}/sessions/${sessionId}/download/report_md`;
    $("downloadDoc").style.display    = s.has_review_doc ? "" : "none";
    $("downloadReport").style.display = s.has_report_md  ? "" : "none";
    const approved = comments.filter((c) => c.decision === "approved").length;
    $("resultsSummary").textContent = `${approved} approved comment(s) inserted into the document.`;
    if (s.errors && s.errors.length) {
      $("errorsBox").textContent = s.errors.join("\n");
      show($("errorsBox"));
    }
  }

  $("newReviewBtn").addEventListener("click", () => {
    sessionId = null;
    comments = [];
    $("uploadForm").reset();
    hide($("resultsStep"));
    show($("uploadStep"));
    resetChecksToDefaults();
    hide($("contextBox"));
  });

  // ---------- init ----------
  $("documentType").addEventListener("change", resetChecksToDefaults);
  $("checksAllBtn").addEventListener("click", () => setAllChecks(true));
  $("checksNoneBtn").addEventListener("click", () => setAllChecks(false));
  $("checksDefaultsBtn").addEventListener("click", resetChecksToDefaults);
  const logoutBtn = $("logoutBtn");
  if (logoutBtn) logoutBtn.addEventListener("click", logout);

  (async () => {
    if (await ensureAuthenticated()) {
      loadCatalogs();
    }
  })();
})();
