(() => {
  const $ = (id) => document.getElementById(id);
  const params = new URLSearchParams(window.location.search);
  const LS_PROMPTS = "jobSearch.defaultPrompts";
  const LS_LANG = "jobSearch.defaultLanguage";

  const state = {
    page: Number(params.get("page") || 1),
    pages: 1,
    jobsReqSeq: 0,
    jobsLoadedOnce: false,
    meta: null,
    drawerJob: null,
    ingestSource: null,
    pipelineSource: null,
  };

  function readControls() {
    return {
      track: $("cv-track").value,
      q: $("job-search").value.trim(),
      page: state.page,
      min_score: Number($("min-score").value || 0),
      order_by: $("sort-by").value || "score",
      source: $("source-filter").value,
      hide_applied: $("hide-applied").checked,
      hide_expired: $("hide-expired").checked,
      academic_roles_only: $("academic-roles-only").checked,
      rogaland_only: $("rogaland-only").checked,
      hide_phd_student: $("hide-phd").checked,
      dedupe_cross_source: $("dedupe").checked,
      use_tech_allowlist: $("tech-allowlist").checked,
      use_tech_defaults: $("tech-defaults").checked,
      extra_include: $("extra-include").value,
      use_noise_defaults: $("noise-defaults").checked,
      extra_exclude: $("extra-exclude").value,
      urgency_days: Number($("urgency-days").value || 7),
    };
  }

  function queryFromControls(extra = {}) {
    const c = { ...readControls(), ...extra };
    const q = new URLSearchParams();
    Object.entries(c).forEach(([k, v]) => {
      if (v === "" || v === undefined || v === null) return;
      q.set(k, String(v));
    });
    return q;
  }

  function syncUrl() {
    const q = queryFromControls();
    const next = `${window.location.pathname}?${q.toString()}`;
    history.replaceState(null, "", next);
  }

  function applyParamsToControls() {
    const p = new URLSearchParams(window.location.search);
    const setVal = (id, key, fallback) => {
      if (!$(id)) return;
      if (p.has(key)) $(id).value = p.get(key);
      else if (fallback !== undefined) $(id).value = fallback;
    };
    const setChk = (id, key, fallback) => {
      if (!$(id)) return;
      if (p.has(key)) $(id).checked = p.get(key) === "true";
      else $(id).checked = fallback;
    };
    setVal("cv-track", "track", "industry");
    setVal("job-search", "q", "");
    setVal("min-score", "min_score", "0");
    setVal("sort-by", "order_by", "score");
    setVal("source-filter", "source", "all");
    setVal("extra-include", "extra_include", "");
    setVal("extra-exclude", "extra_exclude", "");
    setVal("urgency-days", "urgency_days", "7");
    $("urgency-label").textContent = $("urgency-days").value;
    setChk("hide-applied", "hide_applied", true);
    setChk("hide-expired", "hide_expired", true);
    setChk("academic-roles-only", "academic_roles_only", $("cv-track").value === "academic");
    setChk("rogaland-only", "rogaland_only", false);
    setChk("hide-phd", "hide_phd_student", true);
    setChk("dedupe", "dedupe_cross_source", true);
    setChk("tech-allowlist", "use_tech_allowlist", true);
    setChk("tech-defaults", "use_tech_defaults", true);
    setChk("noise-defaults", "use_noise_defaults", true);
    state.page = Number(p.get("page") || 1);
    $("default-prompts").value = localStorage.getItem(LS_PROMPTS) || "";
    $("default-language").value = localStorage.getItem(LS_LANG) || "en";
  }

  async function api(path, opts) {
    const res = await fetch(path, opts);
    const data = await res.json().catch(() => ({}));
    if (!res.ok) {
      const detail = data.detail || res.statusText;
      throw new Error(typeof detail === "string" ? detail : JSON.stringify(detail));
    }
    return data;
  }

  function esc(text) {
    return String(text ?? "").replace(/[&<>"']/g, (ch) => (
      { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[ch]
    ));
  }

  function urgencyClass(row) {
    if (row.expired) return "urgency-expired";
    if (row.apply_soon) return "urgency-soon";
    return "";
  }

  function jobRowHtml(row, { applied = false } = {}) {
    const status = row.app_status || row.status || "";
    const score = row.score_total == null ? "—" : Math.round(row.score_total);
    const applyLabel = row.apply_label || (applied ? "Modify" : "Apply");
    const meta = [row.employer_name || "—", row.location, row.deadline ? `Frist ${row.deadline}` : "", row.source_label]
      .filter(Boolean).join(" · ");
    const badge = status ? `<span class="badge text-bg-light">${esc(status)}</span>` : "";
    const pin = row.pinned ? `<span class="badge text-bg-warning" title="Pinned">Pinned</span>` : "";
    const urg = row.urgency ? `<span class="${urgencyClass(row)}">${esc(row.urgency)}</span>` : "";
    const pinAction = row.pinned ? "unpin" : "pin";
    const pinLabel = row.pinned ? "Unpin" : "Pin";
    const menuId = `job-menu-${esc(row.source)}-${esc(row.uuid)}`.replace(/[^a-zA-Z0-9_-]/g, "_");
    return `<div class="job-row${row.pinned ? " is-pinned" : ""}" data-uuid="${esc(row.uuid)}" data-source="${esc(row.source)}">
      <div>
        <div class="title">${pin} ${esc(row.title || "—")} ${badge} ${urg}</div>
        <div class="job-meta">${esc(meta)}</div>
      </div>
      <div class="score-badge">${esc(score)}</div>
      <div class="d-flex flex-wrap gap-1 justify-content-end job-actions">
        <button class="btn btn-sm btn-outline-secondary" data-action="details">Details</button>
        <button class="btn btn-sm btn-primary" data-action="apply">${esc(applyLabel)}</button>
        <div class="dropdown">
          <button class="btn btn-sm btn-outline-secondary dropdown-toggle" type="button" data-bs-toggle="dropdown" aria-expanded="false" id="${menuId}">More</button>
          <ul class="dropdown-menu dropdown-menu-end" aria-labelledby="${menuId}">
            <li><button class="dropdown-item" type="button" data-quick="${pinAction}">${pinLabel}</button></li>
            <li><button class="dropdown-item" type="button" data-quick="mark_applied">Mark applied</button></li>
            <li><button class="dropdown-item" type="button" data-quick="interested">Mark interested</button></li>
            <li><hr class="dropdown-divider"></li>
            <li><button class="dropdown-item" type="button" data-quick="skip">Skip / trash</button></li>
            <li><button class="dropdown-item" type="button" data-quick="reject">Reject</button></li>
            <li><button class="dropdown-item" type="button" data-quick="mark_expired">Mark expired</button></li>
            <li><button class="dropdown-item" type="button" data-quick="withdraw">Withdraw</button></li>
            <li><hr class="dropdown-divider"></li>
            <li><button class="dropdown-item text-danger" type="button" data-quick="clear">Clear tracking</button></li>
          </ul>
        </div>
      </div>
    </div>`;
  }

  async function quickAction(source, uuid, action) {
    const track = $("cv-track").value;
    await api(`/api/jobs/${encodeURIComponent(source)}/${encodeURIComponent(uuid)}/action`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ track, action }),
    });
    await reloadAll();
  }

  function bindJobList(root) {
    root.querySelectorAll(".job-row").forEach((el) => {
      el.querySelector('[data-action="details"]')?.addEventListener("click", () => {
        openDrawer(el.dataset.source, el.dataset.uuid, "details");
      });
      el.querySelector('[data-action="apply"]')?.addEventListener("click", () => {
        openDrawer(el.dataset.source, el.dataset.uuid, "apply");
      });
      el.querySelectorAll("[data-quick]").forEach((btn) => {
        btn.addEventListener("click", async (ev) => {
          ev.preventDefault();
          const action = btn.dataset.quick;
          if (action === "clear" && !confirm("Clear application tracking for this role?")) return;
          if (action === "skip" && !confirm("Skip / trash this role? It will be hidden from the explorer.")) return;
          if (action === "mark_expired" && !confirm("Mark this posting as expired? It will leave the active list (no FINN request).")) return;
          try {
            await quickAction(el.dataset.source, el.dataset.uuid, action);
          } catch (err) {
            alert(err.message || String(err));
          }
        });
      });
    });
  }

  async function loadOverview() {
    const q = queryFromControls();
    if ($("overview-min-score").value) q.set("min_score", $("overview-min-score").value);
    try {
      const data = await api(`/api/overview?${q}`);
      $("db-missing").classList.add("d-none");
      const m = data.metrics;
      $("metrics-row").innerHTML = [
        ["Active jobs", m.n_active],
        ["Apply soon", m.apply_soon_count],
        ["Applications", m.n_apps],
      ].map(([label, val]) => `<div class="col-12 col-sm-6 col-lg-4">
        <div class="card h-100">
          <div class="card-body py-3">
            <div class="text-muted small">${esc(label)}</div>
            <div class="fs-3">${esc(val)}</div>
          </div>
        </div>
      </div>`).join("");
      ["relevant", "newest"].forEach((key) => {
        document.querySelector(`[data-count="${key}"]`).textContent = data[`${key}_count`] || 0;
        const box = document.querySelector(`[data-list="${key}"]`);
        const rows = data[key] || [];
        box.innerHTML = rows.length ? rows.map((r) => jobRowHtml(r)).join("") : `<p class="text-muted small">None.</p>`;
        bindJobList(box);
      });
      if (!$("overview-min-score").value) $("overview-min-score").value = data.min_score;
    } catch (err) {
      if (String(err.message).includes("Database not found")) {
        $("db-missing").classList.remove("d-none");
      } else {
        console.error(err);
      }
    }
  }

  function skeletonRows(count = 6) {
    return Array.from({ length: count }, () => `<div class="job-row job-skeleton">
      <div>
        <div class="sk-line sk-title"></div>
        <div class="sk-line sk-meta"></div>
      </div>
      <div class="sk-badge"></div>
      <div class="sk-actions"><span class="sk-pill"></span><span class="sk-pill"></span></div>
    </div>`).join("");
  }

  function setJobsLoading(on) {
    $("jobs-progress").classList.toggle("d-none", !on);
    // Show placeholders only on the very first load (later searches keep the
    // previous results visible to avoid flicker).
    if (on && !state.jobsLoadedOnce) $("job-list").innerHTML = skeletonRows();
  }

  function renderPagination(page, pages) {
    state.pages = Math.max(1, pages || 1);
    $("page-total").textContent = state.pages;
    const jump = $("page-jump");
    jump.max = String(state.pages);
    if (document.activeElement !== jump) jump.value = String(page);
    $("page-first").disabled = page <= 1;
    $("page-prev").disabled = page <= 1;
    $("page-next").disabled = page >= state.pages;
    $("page-last").disabled = page >= state.pages;
  }

  async function loadJobs() {
    const q = queryFromControls();
    syncUrl();
    const seq = ++state.jobsReqSeq;
    setJobsLoading(true);
    try {
      const data = await api(`/api/jobs?${q}`);
      if (seq !== state.jobsReqSeq) return; // a newer request superseded this one
      if (data.pages && data.page > data.pages) {
        // Requested page fell out of range (e.g. from a stale URL); clamp once.
        state.page = data.pages;
        loadJobs();
        return;
      }
      $("filter-chips").innerHTML = (data.chips || []).map((c) => `<span class="chip">${esc(c)}</span>`).join("");
      $("results-header").textContent = `${data.total} jobs (page ${data.page} of ${data.pages})`;
      $("job-list").innerHTML = data.jobs.length
        ? data.jobs.map((r) => jobRowHtml(r)).join("")
        : `<p class="text-muted">No jobs match the current filters.</p>`;
      bindJobList($("job-list"));
      renderPagination(data.page, data.pages);
      state.jobsLoadedOnce = true;
    } catch (err) {
      if (seq === state.jobsReqSeq) {
        $("job-list").innerHTML = `<div class="alert alert-danger">${esc(err.message)}</div>`;
        state.jobsLoadedOnce = true;
      }
    } finally {
      if (seq === state.jobsReqSeq) setJobsLoading(false);
    }
  }

  async function loadApplied() {
    const track = $("cv-track").value;
    const showAll = $("applied-show-all").checked;
    const selected = [...$("applied-status").selectedOptions].map((o) => o.value);
    const status = showAll ? (state.meta?.status_options || []).join(",") : selected.join(",");
    const data = await api(`/api/applications?track=${encodeURIComponent(track)}&status=${encodeURIComponent(status)}`);
    $("applied-count").textContent = data.total;
    $("applied-list").innerHTML = data.applications.length
      ? data.applications.map((r) => {
        const extra = r.deanonymize_cmd
          ? `<div class="small font-monospace">${esc(r.deanonymize_cmd)} <button class="btn btn-link btn-sm p-0" data-copy="${esc(r.deanonymize_cmd)}">Copy</button></div>`
          : "";
        const del = `<button class="btn btn-sm btn-outline-danger" data-del-source="${esc(r.source)}" data-del-uuid="${esc(r.uuid)}">Delete</button>`;
        return `<div>${jobRowHtml(r, { applied: true })}${extra}<div class="mb-2">${del}</div></div>`;
      }).join("")
      : `<p class="text-muted small">No applications match the current filter.</p>`;
    bindJobList($("applied-list"));
    $("applied-list").querySelectorAll("[data-copy]").forEach((btn) => {
      btn.addEventListener("click", () => navigator.clipboard.writeText(btn.dataset.copy));
    });
    $("applied-list").querySelectorAll("[data-del-uuid]").forEach((btn) => {
      btn.addEventListener("click", async () => {
        if (!confirm("Delete this application record? CV run folders stay on disk.")) return;
        await api(`/api/applications/${encodeURIComponent(btn.dataset.delSource)}/${encodeURIComponent(btn.dataset.delUuid)}?track=${encodeURIComponent(track)}`, { method: "DELETE" });
        loadApplied();
        loadJobs();
      });
    });
    $("applied-bulk").innerHTML = data.bulk_deanonymize
      ? `<div class="alert alert-light py-2 small"><code>${esc(data.bulk_deanonymize)}</code>
         <button class="btn btn-sm btn-outline-secondary ms-2" id="copy-bulk">Copy</button></div>`
      : "";
    $("copy-bulk")?.addEventListener("click", () => navigator.clipboard.writeText(data.bulk_deanonymize));
  }

  function openOffcanvas(id) {
    const el = $(id);
    const inst = bootstrap.Offcanvas.getOrCreateInstance(el, { scroll: true, backdrop: true });
    inst.show();
  }

  async function openDrawer(source, uuid, mode) {
    const track = $("cv-track").value;
    const detail = await api(`/api/jobs/${encodeURIComponent(source)}/${encodeURIComponent(uuid)}?track=${encodeURIComponent(track)}`);
    state.drawerJob = detail;
    $("drawer-title").textContent = detail.title || "Job";
    if (mode === "apply") {
      const defs = await api(`/api/jobs/${encodeURIComponent(source)}/${encodeURIComponent(uuid)}/apply-defaults?track=${encodeURIComponent(track)}`);
      renderApplyForm(detail, defs);
    } else {
      renderDetails(detail);
    }
    openOffcanvas("jobDrawer");
  }

  function renderDetails(job) {
    const url = job.job_url
      ? `<p><a href="${esc(job.job_url)}" target="_blank" rel="noopener">Open job</a></p>`
      : "";
    const pinAction = job.pinned ? "unpin" : "pin";
    const pinLabel = job.pinned ? "Unpin" : "Pin";
    $("drawer-body").innerHTML = `
      <p class="text-muted">${esc(job.employer_name || "")} · ${esc(job.location || "")}</p>
      ${url}
      <p><strong>Score</strong> ${job.score_total == null ? "—" : Math.round(job.score_total)}
         · keyword hits ${job.score_base ?? "—"} · TEK ${job.boost_tek ?? 0}</p>
      <p><strong>Deadline</strong> ${esc(job.deadline || "—")} ${job.urgency ? `· ${esc(job.urgency)}` : ""}
         ${job.expired || job.job_status === "INACTIVE" ? ` · <span class="text-danger">Expired on FINN</span>` : ""}</p>
      ${job.deadline_unknown
        ? `<div class="alert alert-secondary py-2 mb-2">Deadline not stored (common for FINN search-card rows). Open the listing on FINN to check — we avoid bulk deadline fetches so FINN does not throttle this tool.</div>`
        : ""}
      <p><strong>Status</strong> ${esc(job.app_status || "—")} ${job.pinned ? "· Pinned" : ""}</p>
      <p><strong>Keywords</strong> ${esc(job.matched_keywords || "—")}</p>
      <p><strong>Skills</strong> ${esc(job.matched_skills || "—")}</p>
      <div class="d-flex flex-wrap gap-1 mb-3">
        <button class="btn btn-primary" id="drawer-apply">${esc(job.apply_label || "Apply")}</button>
        <button class="btn btn-outline-secondary" data-drawer-quick="${pinAction}">${pinLabel}</button>
        <button class="btn btn-outline-secondary" data-drawer-quick="mark_applied">Mark applied</button>
        <button class="btn btn-outline-secondary" data-drawer-quick="interested">Interested</button>
        <button class="btn btn-outline-danger" data-drawer-quick="skip">Skip / trash</button>
        <button class="btn btn-outline-danger" data-drawer-quick="reject">Reject</button>
        <button class="btn btn-outline-warning" data-drawer-quick="mark_expired">Mark expired</button>
      </div>
      <h6>Posting</h6>
      <pre class="small" style="white-space:pre-wrap">${esc((job.description_text || "No description stored.").slice(0, 12000))}</pre>
    `;
    $("drawer-apply").addEventListener("click", () => openDrawer(job.source, job.uuid, "apply"));
    $("drawer-body").querySelectorAll("[data-drawer-quick]").forEach((btn) => {
      btn.addEventListener("click", async () => {
        const action = btn.dataset.drawerQuick;
        if (action === "mark_expired" && !confirm("Mark this posting as expired? It will leave the active list (no FINN request).")) return;
        try {
          await quickAction(job.source, job.uuid, action);
          if (action === "mark_expired") {
            bootstrap.Offcanvas.getInstance($("jobDrawer"))?.hide();
            return;
          }
          openDrawer(job.source, job.uuid, "details");
        } catch (err) {
          alert(err.message || String(err));
        }
      });
    });
  }

  function renderApplyForm(job, defs) {
    const d = defs.artifact_defaults || {};
    const academic = defs.show_academic_docs;
    const modify = defs.modify_mode;
    $("drawer-body").innerHTML = `
      <p class="small text-muted">${esc(job.title)} — ${esc(job.employer_name || "—")}</p>
      ${job.job_url ? `<p><a href="${esc(job.job_url)}" target="_blank" rel="noopener">Open job</a></p>` : ""}
      ${defs.existing_run_name ? `<p class="small">Existing run: <code>${esc(defs.existing_run_name)}</code></p>` : ""}
      <label class="form-label">Application language</label>
      <select id="apply-language" class="form-select mb-2">
        <option value="en">English</option>
        <option value="no">Norwegian (Bokmål)</option>
      </select>
      <label class="form-label">Custom prompts</label>
      <textarea id="apply-prompts" class="form-control mb-2" rows="4" placeholder="Per-role tailoring notes"></textarea>
      <div class="form-check"><input class="form-check-input" type="checkbox" id="gen-cover" ${d.generate_cover_letter ? "checked" : ""}><label class="form-check-label" for="gen-cover">Cover letter</label></div>
      ${academic ? `<div class="form-check"><input class="form-check-input" type="checkbox" id="gen-app-letter" ${d.generate_application_letter ? "checked" : ""}><label class="form-check-label" for="gen-app-letter">Application letter</label></div>` : ""}
      ${academic ? `<div class="form-check"><input class="form-check-input" type="checkbox" id="gen-proposal" ${d.generate_research_proposal ? "checked" : ""}><label class="form-check-label" for="gen-proposal">Research proposal</label></div>` : ""}
      ${modify ? `<hr><p class="small">Overwrite existing artifacts</p>
        <div class="form-check"><input class="form-check-input" type="checkbox" id="ow-cv"><label class="form-check-label" for="ow-cv">Overwrite CV</label></div>
        <div class="form-check"><input class="form-check-input" type="checkbox" id="ow-cover"><label class="form-check-label" for="ow-cover">Overwrite cover letter</label></div>
        ${academic ? `<div class="form-check"><input class="form-check-input" type="checkbox" id="ow-app"><label class="form-check-label" for="ow-app">Overwrite application letter</label></div>` : ""}
        ${academic ? `<div class="form-check"><input class="form-check-input" type="checkbox" id="ow-prop"><label class="form-check-label" for="ow-prop">Overwrite research proposal</label></div>` : ""}
      ` : ""}
      <button class="btn btn-primary mt-3" id="start-apply">${esc(defs.apply_label || "Apply")}</button>
      <div id="apply-error" class="text-danger small mt-2"></div>
    `;
    $("apply-language").value = $("default-language").value;
    $("start-apply").addEventListener("click", async () => {
      try {
        await api("/api/apply", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            uuid: job.uuid,
            source: job.source,
            track: $("cv-track").value,
            language: $("apply-language").value,
            apply_prompts: $("apply-prompts").value,
            default_apply_prompts: $("default-prompts").value,
            generate_cover_letter: $("gen-cover")?.checked ?? true,
            generate_application_letter: $("gen-app-letter")?.checked ?? false,
            generate_research_proposal: $("gen-proposal")?.checked ?? false,
            overwrite_cv: $("ow-cv")?.checked ?? false,
            overwrite_cover_letter: $("ow-cover")?.checked ?? false,
            overwrite_application_letter: $("ow-app")?.checked ?? false,
            overwrite_research_proposal: $("ow-prop")?.checked ?? false,
          }),
        });
        watchPipeline();
      } catch (err) {
        $("apply-error").textContent = err.message;
      }
    });
  }

  function setStatusBar(kind, html) {
    const bar = $("status-bar");
    if (!html) {
      bar.className = "status-bar d-none";
      return;
    }
    bar.className = `status-bar ${kind}`;
    bar.innerHTML = html;
  }

  function watchSse(url, onEvent, done) {
    const src = new EventSource(url);
    src.onmessage = (ev) => {
      const data = JSON.parse(ev.data);
      onEvent(data);
      if (done(data)) src.close();
    };
    src.onerror = () => src.close();
    return src;
  }

  function watchIngest() {
    if (state.ingestSource) state.ingestSource.close();
    state.ingestSource = watchSse("/api/ingest/stream", (snap) => {
      renderIngest(snap);
      if (snap.running) {
        const step = snap.step ? ` · ${snap.step.replace(/^\[job-search\]\s*/, "").slice(0, 90)}` : "";
        setStatusBar("running", `Ingest running… ${Math.round(snap.elapsed || 0)}s${step}`);
      } else if (snap.phase === "complete") {
        setStatusBar("complete", `Ingest finished in ${snap.result?.duration_seconds || 0}s`);
        loadOverview();
        loadJobs();
        loadApplied();
      } else if (snap.phase === "error") {
        setStatusBar("error", esc(snap.headline || "Ingest failed"));
      }
    }, (snap) => !snap.running && (snap.phase === "complete" || snap.phase === "error" || !snap.phase));
  }

  function watchPipeline() {
    if (state.pipelineSource) state.pipelineSource.close();
    state.pipelineSource = watchSse("/api/pipeline/stream", (snap) => {
      if (snap.running) {
        setStatusBar("running", `${esc(snap.stage || "Running")} · ${esc(snap.title || "")} (${Math.round(snap.elapsed || 0)}s)`);
      } else if (snap.phase === "complete") {
        const run = snap.result?.run_name;
        const cmd = snap.result?.deanonymize_cmd || (run ? `~/private/cv/cv apply ${run}` : "");
        setStatusBar("complete", `Pipeline complete${run ? `: ${esc(run)}` : ""}${cmd ? ` · <code>${esc(cmd)}</code>` : ""}`);
        loadApplied();
        loadJobs();
      } else if (snap.phase === "error") {
        const err = (snap.result?.errs || []).filter(Boolean).join(" ").slice(0, 280);
        setStatusBar("error", esc(err || "Pipeline failed"));
      }
    }, (snap) => !snap.running);
  }

  function renderIngest(snap) {
    const box = $("ingest-panel");
    if (!snap || !snap.phase) {
      box.innerHTML = "";
      return;
    }
    if (snap.running) {
      box.innerHTML = `<div class="alert alert-info py-2">Running… ${Math.round(snap.elapsed || 0)}s</div>
        <pre class="log-box">${esc((snap.log_lines || []).slice(-20).join("\n"))}</pre>`;
      return;
    }
    if (snap.phase === "error") {
      box.innerHTML = `<div class="alert alert-danger py-2">${esc(snap.headline || "Ingest failed")}</div>
        <pre class="log-box">${esc(snap.result?.stdout_tail || snap.result?.stderr || "")}</pre>
        <button class="btn btn-sm btn-outline-secondary" id="dismiss-ingest">Dismiss</button>`;
    } else if (snap.phase === "complete") {
      const c = snap.result?.active_counts || {};
      box.innerHTML = `<div class="alert alert-success py-2">Finished in ${snap.result?.duration_seconds || 0}s
        · NAV ${c.nav_arbeidsplassen || 0} · FINN ${c.finn_no || 0} · Jobbnorge ${c.jobbnorge || 0}</div>
        <button class="btn btn-sm btn-outline-secondary" id="dismiss-ingest">Dismiss</button>`;
    }
    $("dismiss-ingest")?.addEventListener("click", async () => {
      await api("/api/ingest/dismiss", { method: "POST" });
      box.innerHTML = "";
      setStatusBar("", "");
    });
  }

  function debounce(fn, ms) {
    let t;
    return (...args) => {
      clearTimeout(t);
      t = setTimeout(() => fn(...args), ms);
    };
  }

  async function reloadAll() {
    await Promise.all([loadOverview(), loadJobs(), loadApplied()]);
  }

  function wireEvents() {
    // Filter changes that also affect the overview previews.
    const applyFilters = debounce(() => {
      state.page = 1;
      reloadAll();
    }, 250);
    // Controls that only affect the job explorer list.
    const applyJobFilters = debounce(() => {
      state.page = 1;
      loadJobs();
    }, 250);
    // Search-as-you-type: only reload the job list (overview/applied are unchanged).
    const runSearch = debounce(() => {
      state.page = 1;
      loadJobs();
    }, 250);

    ["cv-track", "source-filter", "academic-roles-only", "dedupe", "hide-phd", "tech-allowlist",
      "tech-defaults", "noise-defaults", "overview-min-score"].forEach((id) => {
      $(id).addEventListener("change", () => {
        if (id === "cv-track" && $("cv-track").value === "academic") {
          $("academic-roles-only").checked = true;
        }
        applyFilters();
      });
    });
    ["min-score", "sort-by", "hide-applied", "hide-expired", "rogaland-only"].forEach((id) => {
      $(id).addEventListener("change", applyJobFilters);
    });
    ["extra-include", "extra-exclude"].forEach((id) => {
      $(id).addEventListener("input", applyFilters);
    });
    $("job-search").addEventListener("input", runSearch);
    $("urgency-days").addEventListener("input", () => {
      $("urgency-label").textContent = $("urgency-days").value;
    });
    $("urgency-days").addEventListener("change", applyFilters);

    function gotoPage(target) {
      const total = Math.max(1, state.pages || 1);
      const next = Math.min(Math.max(1, Number(target) || 1), total);
      if (next === state.page) {
        renderPagination(state.page, total);
        return;
      }
      state.page = next;
      loadJobs();
      $("job-explorer-list-start").scrollIntoView({ behavior: "smooth", block: "start" });
    }

    $("page-first").addEventListener("click", () => gotoPage(1));
    $("page-prev").addEventListener("click", () => gotoPage(state.page - 1));
    $("page-next").addEventListener("click", () => gotoPage(state.page + 1));
    $("page-last").addEventListener("click", () => gotoPage(state.pages));
    $("page-jump").addEventListener("change", () => gotoPage($("page-jump").value));
    $("page-jump").addEventListener("keydown", (ev) => {
      if (ev.key === "Enter") {
        ev.preventDefault();
        gotoPage($("page-jump").value);
      }
    });
    $("applied-status").addEventListener("change", loadApplied);
    $("applied-show-all").addEventListener("change", loadApplied);
    $("default-prompts").addEventListener("change", () => {
      localStorage.setItem(LS_PROMPTS, $("default-prompts").value);
    });
    $("default-language").addEventListener("change", () => {
      localStorage.setItem(LS_LANG, $("default-language").value);
    });
    $("btn-ingest").addEventListener("click", async () => {
      try {
        await api("/api/ingest", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            skip_nav: $("skip-nav").checked,
            skip_finn: $("skip-finn").checked,
            skip_jobbnorge: $("skip-jobbnorge").checked,
            academic_queries_only: $("academic-queries").checked,
          }),
        });
        watchIngest();
      } catch (err) {
        setStatusBar("error", esc(err.message));
      }
    });
  }

  async function init() {
    applyParamsToControls();
    try {
      state.meta = await api("/api/meta");
    } catch (err) {
      $("job-list").innerHTML = `<div class="alert alert-danger">${esc(err.message)}</div>`;
      return;
    }
    (state.meta.status_options || []).forEach((st) => {
      const opt = document.createElement("option");
      opt.value = st;
      opt.textContent = st;
      opt.selected = ["drafted", "applied", "interested"].includes(st);
      $("applied-status").appendChild(opt);
    });
    if (!state.meta.db_exists) $("db-missing").classList.remove("d-none");
    wireEvents();
    await reloadAll();
    const ingest = await api("/api/ingest");
    renderIngest(ingest);
    if (ingest.running) watchIngest();
    const pipe = await api("/api/pipeline");
    if (pipe.running) watchPipeline();
  }

  init();
})();
