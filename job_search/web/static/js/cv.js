(() => {
  const $ = (id) => document.getElementById(id);
  const IDENTITY_KEYS = [
    ["name", "Name"],
    ["date_of_birth", "Date of birth"],
    ["email", "Email"],
    ["phone", "Phone"],
    ["location", "Location"],
    ["work_permit", "Work permit"],
    ["github_url", "GitHub URL"],
    ["linkedin_url", "LinkedIn URL"],
    ["scholar_url", "Google Scholar URL"],
    ["orcid_url", "ORCID URL"],
  ];
  const ANON = {
    github_url: "https://github.com/cv-placeholder",
    linkedin_url: "https://linkedin.com/in/cv-placeholder",
    scholar_url: "https://scholar.google.com/citations?user=cv-placeholder",
    orcid_url: "https://orcid.org/0000-0000-0000-0000",
  };
  const URL_META = {
    github_url: "_github_url",
    linkedin_url: "_linkedin_url",
    scholar_url: "_google_scholar_url",
    orcid_url: "_orcid_url",
  };
  const MAPPING_INSTRUCTIONS = [
    "Do NOT store this file inside the git repo or paste it to an AI agent.",
    "Keep it outside the project (Download folder or ~/private/cv/cv_identity_mapping.json).",
    "Fake keys match the anonymized markdown the tailoring pipeline uses.",
    "Apply with: ~/private/cv/cv apply <run_id>",
  ];

  const state = {
    sourceId: null,
    kind: "new",
    sources: null,
  };

  function pair(fake = "", real = "") {
    return { fake: fake || "", real: real || "" };
  }

  function asPair(value) {
    if (value && typeof value === "object") {
      return pair(value.fake || "", value.real || "");
    }
    return pair(typeof value === "string" ? value : "", "");
  }

  function emptyRole() {
    return { title: "", employer: pair(), dates: pair(), bullets: [""] };
  }

  function emptyEdu() {
    return { degree: "", school: pair(), years: pair(), field: "", thesis: pair() };
  }

  function emptyTrack(academic) {
    const track = {
      profile: "",
      skills: "",
      keywords: "",
      experience: [emptyRole()],
      education: [emptyEdu()],
      publications: "",
    };
    if (academic) track.teaching = "";
    return track;
  }

  function flash(message, kind = "success") {
    const el = $("flash");
    el.className = `alert alert-${kind}`;
    el.textContent = message;
    el.classList.remove("d-none");
  }

  function esc(value) {
    return String(value ?? "")
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;");
  }

  function pairInputs(name, fake, real, { textarea = false } = {}) {
    const tag = textarea ? "textarea" : "input";
    const extra = textarea ? " rows=\"3\"" : ` type="text"`;
    return `<div class="pair-grid mb-2">
      <div>
        <label class="form-label small d-md-none">Fake</label>
        <${tag} class="form-control form-control-sm" data-fake="${esc(name)}"${extra}>${textarea ? esc(fake) : ""}</${tag}>
      </div>
      <div>
        <label class="form-label small d-md-none">Real</label>
        <${tag} class="form-control form-control-sm" data-real="${esc(name)}"${extra}>${textarea ? esc(real) : ""}</${tag}>
      </div>
    </div>`;
  }

  function fillIdentityFields(identity) {
    const wrap = $("identity-fields");
    wrap.innerHTML = IDENTITY_KEYS.map(([key, label]) => {
      const p = asPair(identity[key] || (ANON[key] ? pair(ANON[key]) : pair()));
      return `<label class="form-label small mb-1 mt-2">${esc(label)}</label>${pairInputs(key, p.fake, p.real)}`;
    }).join("");
    IDENTITY_KEYS.forEach(([key]) => {
      const p = asPair(identity[key] || (ANON[key] ? pair(ANON[key]) : pair()));
      wrap.querySelector(`[data-fake="${key}"]`).value = p.fake;
      wrap.querySelector(`[data-real="${key}"]`).value = p.real;
    });
    $("seniority").value = identity.seniority_years ?? "";
  }

  function renderPairList(containerId, rows, kind) {
    const el = $(containerId);
    const items = rows && rows.length ? rows : [kind === "languages" ? { name: pair(), level: pair() } : pair()];
    el.innerHTML = items.map((row, idx) => {
      if (kind === "languages") {
        const name = asPair(row.name);
        const level = asPair(row.level);
        return `<div class="border rounded p-2 mb-2" data-row="${idx}">
          <div class="small text-muted mb-1">Language name</div>
          ${pairInputs(`lang-name-${idx}`, name.fake, name.real)}
          <div class="small text-muted mb-1">Level</div>
          ${pairInputs(`lang-level-${idx}`, level.fake, level.real)}
        </div>`;
      }
      const p = asPair(row);
      const prefix = kind === "hobbies" ? "hobby" : "loc";
      return `<div class="mb-2" data-row="${idx}">${pairInputs(`${prefix}-${idx}`, p.fake, p.real)}</div>`;
    }).join("");
    items.forEach((row, idx) => {
      if (kind === "languages") {
        const name = asPair(row.name);
        const level = asPair(row.level);
        el.querySelector(`[data-fake="lang-name-${idx}"]`).value = name.fake;
        el.querySelector(`[data-real="lang-name-${idx}"]`).value = name.real;
        el.querySelector(`[data-fake="lang-level-${idx}"]`).value = level.fake;
        el.querySelector(`[data-real="lang-level-${idx}"]`).value = level.real;
      } else {
        const p = asPair(row);
        const prefix = kind === "hobbies" ? "hobby" : "loc";
        el.querySelector(`[data-fake="${prefix}-${idx}"]`).value = p.fake;
        el.querySelector(`[data-real="${prefix}-${idx}"]`).value = p.real;
      }
    });
  }

  function readPairList(containerId, kind) {
    const nodes = [...$(containerId).querySelectorAll(":scope > [data-row]")];
    return nodes.map((node, idx) => {
      if (kind === "languages") {
        return {
          name: pair(node.querySelector(`[data-fake="lang-name-${idx}"]`)?.value, node.querySelector(`[data-real="lang-name-${idx}"]`)?.value),
          level: pair(node.querySelector(`[data-fake="lang-level-${idx}"]`)?.value, node.querySelector(`[data-real="lang-level-${idx}"]`)?.value),
        };
      }
      const prefix = kind === "hobbies" ? "hobby" : "loc";
      return pair(node.querySelector(`[data-fake="${prefix}-${idx}"]`)?.value, node.querySelector(`[data-real="${prefix}-${idx}"]`)?.value);
    });
  }

  function skillsValue(track) {
    if (Array.isArray(track.skills)) return track.skills.join(", ");
    return track.skills || "";
  }

  function keywordsValue(track) {
    if (Array.isArray(track.keywords)) return track.keywords.join(", ");
    return track.keywords || "";
  }

  function pubsValue(track) {
    if (Array.isArray(track.publications)) return track.publications.filter(Boolean).join("\n");
    return track.publications || "";
  }

  function renderTrack(trackName, track) {
    const academic = trackName === "academic";
    const el = $(academic ? "tab-academic" : "tab-industry");
    const roles = track.experience && track.experience.length ? track.experience : [emptyRole()];
    const edus = track.education && track.education.length ? track.education : [emptyEdu()];
    el.innerHTML = `
      <label class="form-label">${academic ? "Summary" : "Profile"}</label>
      <textarea class="form-control mb-3" data-track-field="profile" rows="5">${esc(track.profile || "")}</textarea>
      <label class="form-label">Skills (comma-separated)</label>
      <input class="form-control form-control-sm mb-2" data-track-field="skills" value="${esc(skillsValue(track))}">
      <label class="form-label">Keywords (comma-separated, used for matching)</label>
      <input class="form-control form-control-sm mb-3" data-track-field="keywords" value="${esc(keywordsValue(track))}">
      <h4 class="h6">Experience</h4>
      <div data-roles></div>
      <button type="button" class="btn btn-sm btn-outline-secondary mb-3" data-add-role>Add role</button>
      <h4 class="h6">Education</h4>
      <div data-edu></div>
      <button type="button" class="btn btn-sm btn-outline-secondary mb-3" data-add-edu>Add education</button>
      <label class="form-label">${academic ? "Research and publications" : "Selected publications"} (one per line)</label>
      <textarea class="form-control mb-3" data-track-field="publications" rows="4">${esc(pubsValue(track))}</textarea>
      ${academic ? `<label class="form-label">Teaching and supervision</label>
      <textarea class="form-control" data-track-field="teaching" rows="4">${esc(track.teaching || "")}</textarea>` : ""}
    `;
    const rolesEl = el.querySelector("[data-roles]");
    roles.forEach((role) => rolesEl.appendChild(roleNode(role)));
    const eduEl = el.querySelector("[data-edu]");
    edus.forEach((row) => eduEl.appendChild(eduNode(row)));
    el.querySelector("[data-add-role]").addEventListener("click", () => rolesEl.appendChild(roleNode(emptyRole())));
    el.querySelector("[data-add-edu]").addEventListener("click", () => eduEl.appendChild(eduNode(emptyEdu())));
  }

  function roleNode(role) {
    const wrap = document.createElement("div");
    wrap.className = "border rounded p-2 mb-2";
    const emp = asPair(role.employer);
    const dates = asPair(role.dates);
    wrap.innerHTML = `
      <label class="form-label small">Title</label>
      <input class="form-control form-control-sm mb-2" data-role-title value="${esc(role.title || "")}">
      <div class="small text-muted">Employer</div>
      ${pairInputs("employer", emp.fake, emp.real)}
      <div class="small text-muted">Dates</div>
      ${pairInputs("dates", dates.fake, dates.real)}
      <label class="form-label small">Bullets (one per line, fake/career text the AI sees)</label>
      <textarea class="form-control form-control-sm" data-role-bullets rows="3">${esc((role.bullets || []).join("\n"))}</textarea>
      <button type="button" class="btn btn-link btn-sm px-0" data-remove>Remove role</button>
    `;
    wrap.querySelector('[data-fake="employer"]').value = emp.fake;
    wrap.querySelector('[data-real="employer"]').value = emp.real;
    wrap.querySelector('[data-fake="dates"]').value = dates.fake;
    wrap.querySelector('[data-real="dates"]').value = dates.real;
    wrap.querySelector("[data-remove]").addEventListener("click", () => wrap.remove());
    return wrap;
  }

  function eduNode(row) {
    const wrap = document.createElement("div");
    wrap.className = "border rounded p-2 mb-2";
    const school = asPair(row.school);
    const years = asPair(row.years);
    const thesis = asPair(row.thesis);
    wrap.innerHTML = `
      <label class="form-label small">Degree</label>
      <input class="form-control form-control-sm mb-2" data-edu-degree value="${esc(row.degree || "")}">
      <div class="small text-muted">School</div>
      ${pairInputs("school", school.fake, school.real)}
      <div class="small text-muted">Years</div>
      ${pairInputs("years", years.fake, years.real)}
      <label class="form-label small">Field</label>
      <input class="form-control form-control-sm mb-2" data-edu-field value="${esc(row.field || "")}">
      <div class="small text-muted">Thesis</div>
      ${pairInputs("thesis", thesis.fake, thesis.real, { textarea: true })}
      <button type="button" class="btn btn-link btn-sm px-0" data-remove>Remove education</button>
    `;
    wrap.querySelector('[data-fake="school"]').value = school.fake;
    wrap.querySelector('[data-real="school"]').value = school.real;
    wrap.querySelector('[data-fake="years"]').value = years.fake;
    wrap.querySelector('[data-real="years"]').value = years.real;
    wrap.querySelector('[data-fake="thesis"]').value = thesis.fake;
    wrap.querySelector('[data-real="thesis"]').value = thesis.real;
    wrap.querySelector("[data-remove]").addEventListener("click", () => wrap.remove());
    return wrap;
  }

  function readIdentity() {
    const identity = {};
    IDENTITY_KEYS.forEach(([key]) => {
      identity[key] = pair(
        $("identity-fields").querySelector(`[data-fake="${key}"]`)?.value,
        $("identity-fields").querySelector(`[data-real="${key}"]`)?.value,
      );
    });
    identity.languages = readPairList("languages", "languages");
    identity.hobbies = readPairList("hobbies", "hobbies");
    identity.locations_preferred = readPairList("locations", "locations");
    const years = $("seniority").value;
    identity.seniority_years = years === "" ? null : Number(years);
    return identity;
  }

  function readTrack(trackName) {
    const academic = trackName === "academic";
    const el = $(academic ? "tab-academic" : "tab-industry");
    const field = (name) => el.querySelector(`[data-track-field="${name}"]`)?.value || "";
    const experience = [...el.querySelectorAll("[data-roles] > div")].map((node) => ({
      title: node.querySelector("[data-role-title]")?.value || "",
      employer: pair(node.querySelector('[data-fake="employer"]')?.value, node.querySelector('[data-real="employer"]')?.value),
      dates: pair(node.querySelector('[data-fake="dates"]')?.value, node.querySelector('[data-real="dates"]')?.value),
      bullets: (node.querySelector("[data-role-bullets]")?.value || "").split("\n").map((s) => s.trim()).filter(Boolean),
    }));
    const education = [...el.querySelectorAll("[data-edu] > div")].map((node) => ({
      degree: node.querySelector("[data-edu-degree]")?.value || "",
      school: pair(node.querySelector('[data-fake="school"]')?.value, node.querySelector('[data-real="school"]')?.value),
      years: pair(node.querySelector('[data-fake="years"]')?.value, node.querySelector('[data-real="years"]')?.value),
      field: node.querySelector("[data-edu-field]")?.value || "",
      thesis: pair(node.querySelector('[data-fake="thesis"]')?.value, node.querySelector('[data-real="thesis"]')?.value),
    }));
    const track = {
      profile: field("profile"),
      skills: field("skills").split(",").map((s) => s.trim()).filter(Boolean),
      keywords: field("keywords").split(",").map((s) => s.trim()).filter(Boolean),
      experience,
      education,
      publications: field("publications").split("\n").map((s) => s.trim()).filter(Boolean),
    };
    if (academic) track.teaching = field("teaching");
    return track;
  }

  function fakeOnly(value) {
    if (Array.isArray(value)) return value.map(fakeOnly);
    if (value && typeof value === "object") {
      const out = {};
      Object.entries(value).forEach(([k, v]) => {
        if (k === "real") return;
        out[k] = fakeOnly(v);
      });
      return out;
    }
    return value;
  }

  function addPair(out, fake, real) {
    const f = (fake || "").trim();
    const r = (real || "").trim();
    if (f && r && f !== r) out[f] = r;
  }

  function buildMapping(identity, industry, academic) {
    const out = { _instructions: MAPPING_INSTRUCTIONS.slice() };
    IDENTITY_KEYS.forEach(([key]) => {
      const p = asPair(identity[key]);
      if (URL_META[key]) {
        if (p.real.startsWith("http://") || p.real.startsWith("https://")) {
          if (!p.real.startsWith("REPLACE_WITH_")) out[URL_META[key]] = p.real;
        }
        addPair(out, p.fake || ANON[key], p.real);
        return;
      }
      addPair(out, p.fake, p.real);
    });
    (identity.languages || []).forEach((row) => {
      const name = asPair(row.name);
      const level = asPair(row.level);
      addPair(out, name.fake, name.real);
      const fakeLine = name.fake ? `- ${name.fake}${level.fake ? ` (${level.fake})` : ""}` : "";
      const realName = name.real || name.fake;
      const realLevel = level.real || level.fake;
      const realLine = (name.real || level.real) ? `- ${realName}${realLevel ? ` (${realLevel})` : ""}` : "";
      addPair(out, fakeLine, realLine);
    });
    (identity.hobbies || []).forEach((row) => {
      const p = asPair(row);
      addPair(out, p.fake, p.real);
      addPair(out, p.fake ? `- ${p.fake}` : "", p.real ? `- ${p.real}` : "");
    });
    (identity.locations_preferred || []).forEach((row) => addPair(out, asPair(row).fake, asPair(row).real));
    [industry, academic].forEach((track) => {
      (track.experience || []).forEach((role) => {
        addPair(out, asPair(role.employer).fake, asPair(role.employer).real);
        addPair(out, asPair(role.dates).fake, asPair(role.dates).real);
      });
      (track.education || []).forEach((row) => {
        addPair(out, asPair(row.school).fake, asPair(row.school).real);
        addPair(out, asPair(row.years).fake, asPair(row.years).real);
        addPair(out, asPair(row.thesis).fake, asPair(row.thesis).real);
      });
    });
    return out;
  }

  function applyForm(payload, { asNew = false } = {}) {
    state.sourceId = asNew ? null : payload.source_id || null;
    state.kind = asNew ? "new" : payload.kind || "new";
    $("form-title").textContent = asNew ? "New CV (from placeholder)" : (state.sourceId || "New CV");
    $("source-badge").textContent = state.kind;
    $("cv-slug").value = "";
    if (state.kind === "user" && state.sourceId && state.sourceId.startsWith("user:")) {
      $("cv-slug").value = state.sourceId.slice(5);
    }
    fillIdentityFields(payload.identity || {});
    renderPairList("languages", payload.identity?.languages, "languages");
    renderPairList("hobbies", payload.identity?.hobbies, "hobbies");
    renderPairList("locations", payload.identity?.locations_preferred, "locations");
    renderTrack("industry", payload.industry || emptyTrack(false));
    renderTrack("academic", payload.academic || emptyTrack(true));
    const includeI = $("include-industry");
    const includeA = $("include-academic");
    includeI.checked = isActive("industry", state.sourceId);
    includeA.checked = isActive("academic", state.sourceId);
    if (asNew) {
      includeI.checked = false;
      includeA.checked = false;
    }
  }

  function isActive(track, sourceId) {
    if (!sourceId || !state.sources) return false;
    return (state.sources.tracks[track]?.sources || []).some((s) => s.id === sourceId && s.active);
  }

  async function loadSources() {
    const res = await fetch("/api/cv/sources");
    state.sources = await res.json();
    const wrap = $("source-lists");
    wrap.innerHTML = ["industry", "academic"].map((track) => {
      const sources = state.sources.tracks[track]?.sources || [];
      const rows = sources.map((src) => `
        <div class="cv-source-row">
          <div class="form-check mt-1">
            <input class="form-check-input" type="checkbox" data-activate="${esc(track)}" data-id="${esc(src.id)}" ${src.active ? "checked" : ""}>
          </div>
          <div>
            <button type="button" class="btn btn-link btn-sm p-0" data-load="${esc(src.id)}">${esc(src.label)}</button>
            <div class="small text-muted">${esc(src.filename)}${src.read_only ? " · read-only placeholder" : ""}</div>
          </div>
        </div>`).join("") || `<p class="small text-muted">No ${track} CVs found.</p>`;
      return `<h3 class="h6 text-uppercase mt-3">${track}</h3>${rows}`;
    }).join("");
    wrap.querySelectorAll("[data-load]").forEach((btn) => {
      btn.addEventListener("click", () => loadDocument(btn.getAttribute("data-load")));
    });
    wrap.querySelectorAll("[data-activate]").forEach((box) => {
      box.addEventListener("change", async () => {
        const track = box.getAttribute("data-activate");
        const sourceId = box.checked ? box.getAttribute("data-id") : "";
        const resAct = await fetch("/api/cv/activate", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ track, source_id: sourceId || null }),
        });
        if (!resAct.ok) {
          flash(await errorText(resAct), "danger");
          box.checked = !box.checked;
          return;
        }
        await loadSources();
        flash(box.checked ? `Using ${box.getAttribute("data-id")} for ${track}.` : `Cleared ${track} selection (default file will be used).`);
      });
    });
  }

  async function loadDocument(sourceId) {
    const res = await fetch(`/api/cv/document?source_id=${encodeURIComponent(sourceId)}`);
    if (!res.ok) {
      flash(await errorText(res), "danger");
      return;
    }
    applyForm(await res.json());
  }

  async function loadBlank() {
    const res = await fetch("/api/cv/blank");
    applyForm(await res.json(), { asNew: true });
    $("form-title").textContent = "New CV";
  }

  async function errorText(res) {
    try {
      const data = await res.json();
      return data.detail || res.statusText;
    } catch {
      return res.statusText;
    }
  }

  function collect() {
    return {
      identity: readIdentity(),
      industry: readTrack("industry"),
      academic: readTrack("academic"),
    };
  }

  async function saveCv() {
    const { identity, industry, academic } = collect();
    const body = {
      identity: fakeOnly(identity),
      industry: fakeOnly(industry),
      academic: fakeOnly(academic),
      activate: {
        industry: $("include-industry").checked,
        academic: $("include-academic").checked,
      },
    };
    if (state.kind === "personal" && state.sourceId === "personal") {
      body.source_id = "personal";
    } else if (state.kind === "user" && state.sourceId) {
      body.source_id = state.sourceId;
      body.slug = $("cv-slug").value.trim() || state.sourceId.slice(5);
    } else {
      const slug = $("cv-slug").value.trim() || (identity.name.fake || "cv");
      body.slug = slug;
    }
    if (state.kind === "demo") {
      flash("The placeholder is read-only. Use Modify placeholder, then Save fake CV as a new slug.", "warning");
      return;
    }
    const res = await fetch("/api/cv", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    });
    if (!res.ok) {
      flash(await errorText(res), "danger");
      return;
    }
    const data = await res.json();
    state.sourceId = data.source_id;
    state.kind = data.source_id === "personal" ? "personal" : "user";
    await loadSources();
    flash(`Saved fake markdown for ${data.source_id}. Download the mapping JSON separately.`);
  }

  async function preview() {
    const { identity, industry, academic } = collect();
    const res = await fetch("/api/cv/preview", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        identity: fakeOnly(identity),
        industry: fakeOnly(industry),
        academic: fakeOnly(academic),
      }),
    });
    if (!res.ok) {
      flash(await errorText(res), "danger");
      return;
    }
    const data = await res.json();
    $("preview-card").classList.remove("d-none");
    $("preview-industry").textContent = data.markdown.industry || "";
    $("preview-academic").textContent = data.markdown.academic || "";
  }

  function downloadMapping() {
    const { identity, industry, academic } = collect();
    const mapping = buildMapping(identity, industry, academic);
    const blob = new Blob([JSON.stringify(mapping, null, 2) + "\n"], { type: "application/json" });
    const a = document.createElement("a");
    a.href = URL.createObjectURL(blob);
    a.download = "cv_identity_mapping.json";
    a.click();
    URL.revokeObjectURL(a.href);
    flash("Downloaded mapping JSON. Keep it outside this repo and away from the AI agent.");
  }

  async function saveMappingRemote() {
    const { identity, industry, academic } = collect();
    const mapping = buildMapping(identity, industry, academic);
    const res = await fetch("/api/cv/save-mapping", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ mapping }),
    });
    if (!res.ok) {
      flash(await errorText(res), "danger");
      return;
    }
    const data = await res.json();
    flash(`Merged mapping into ${data.path}. Do not copy that file into this project.`);
  }

  function importMapping(file) {
    const reader = new FileReader();
    reader.onload = () => {
      try {
        const mapping = JSON.parse(reader.result);
        applyMappingToForm(mapping);
        flash("Filled Real columns from the imported JSON. Nothing was saved to disk.");
      } catch {
        flash("Could not parse that JSON file.", "danger");
      }
    };
    reader.readAsText(file);
  }

  function applyMappingToForm(mapping) {
    if (!mapping || typeof mapping !== "object") return;
    IDENTITY_KEYS.forEach(([key]) => {
      const fakeEl = $("identity-fields").querySelector(`[data-fake="${key}"]`);
      const realEl = $("identity-fields").querySelector(`[data-real="${key}"]`);
      if (!fakeEl || !realEl) return;
      if (URL_META[key] && mapping[URL_META[key]]) {
        realEl.value = mapping[URL_META[key]];
        return;
      }
      if (mapping[fakeEl.value]) realEl.value = mapping[fakeEl.value];
    });
    const fillList = (containerId, prefix) => {
      const nodes = [...$(containerId).children];
      nodes.forEach((node, idx) => {
        const fakeEl = node.querySelector(`[data-fake="${prefix}-${idx}"]`);
        const realEl = node.querySelector(`[data-real="${prefix}-${idx}"]`);
        if (fakeEl && realEl && mapping[fakeEl.value]) realEl.value = mapping[fakeEl.value];
      });
    };
    fillList("hobbies", "hobby");
    fillList("locations", "loc");
    [...$("languages").children].forEach((node, idx) => {
      const fakeEl = node.querySelector(`[data-fake="lang-name-${idx}"]`);
      const realEl = node.querySelector(`[data-real="lang-name-${idx}"]`);
      if (fakeEl && realEl && mapping[fakeEl.value]) realEl.value = mapping[fakeEl.value];
    });
    ["tab-industry", "tab-academic"].forEach((id) => {
      $(id).querySelectorAll("[data-roles] > div, [data-edu] > div").forEach((node) => {
        node.querySelectorAll("[data-fake]").forEach((fakeEl) => {
          const name = fakeEl.getAttribute("data-fake");
          const realEl = node.querySelector(`[data-real="${name}"]`);
          if (realEl && mapping[fakeEl.value]) realEl.value = mapping[fakeEl.value];
        });
      });
    });
  }

  $("btn-new").addEventListener("click", loadBlank);
  $("btn-from-placeholder").addEventListener("click", async () => {
    const res = await fetch("/api/cv/document?source_id=demo");
    if (!res.ok) {
      flash(await errorText(res), "danger");
      return;
    }
    applyForm(await res.json(), { asNew: true });
    flash("Placeholder loaded. Save as a new slug so the committed demo files stay unchanged.", "info");
  });
  $("btn-save").addEventListener("click", saveCv);
  $("btn-preview").addEventListener("click", preview);
  $("btn-download").addEventListener("click", downloadMapping);
  $("btn-save-mapping").addEventListener("click", saveMappingRemote);
  $("import-mapping").addEventListener("change", (ev) => {
    const file = ev.target.files && ev.target.files[0];
    if (file) importMapping(file);
    ev.target.value = "";
  });
  document.querySelectorAll("[data-add]").forEach((btn) => {
    btn.addEventListener("click", () => {
      const kind = btn.getAttribute("data-add");
      if (kind === "languages") {
        renderPairList("languages", [...readPairList("languages", "languages"), { name: pair(), level: pair() }], "languages");
      } else if (kind === "hobbies") {
        renderPairList("hobbies", [...readPairList("hobbies", "hobbies"), pair()], "hobbies");
      } else {
        renderPairList("locations", [...readPairList("locations", "locations"), pair()], "locations");
      }
    });
  });

  loadSources().then(loadBlank);
})();
