(function () {
  "use strict";
  const { $, $$, esc, icon, api, ago } = MF;
  const panel = $("#panel");
  $("#fdClose").innerHTML = icon("x");
  let tab = "pharmacies", phFilter = "pending", form = null;

  async function init() {
    let me;
    try { me = await MF.requireRole(["admin"]); } catch (e) { panel.innerHTML = err(e); return; }
    if (!me) return;
    MF.renderNav("admin");
    $("#tabs").addEventListener("click", (e) => { const b = e.target.closest("[data-tab]"); if (b) show(b.dataset.tab); });
    show(location.hash.slice(1) || "pharmacies");
  }
  const err = (e) => `<div class="empty">${icon("alert")}<h3>Something went wrong</h3><p>${esc(e.message)}</p></div>`;

  async function show(t) {
    tab = ["pharmacies", "medicines", "categories", "sources", "users"].includes(t) ? t : "pharmacies";
    history.replaceState(null, "", "#" + tab);
    $$("[data-tab]").forEach((b) => b.setAttribute("aria-selected", String(b.dataset.tab === tab)));
    panel.innerHTML = '<div class="skeleton" style="height:180px"></div>';
    try { await ({ pharmacies, medicines, categories, sources, users }[tab])(); } catch (e) { panel.innerHTML = err(e); }
  }

  /* ---------- pharmacies ---------- */
  async function pharmacies() {
    const list = await api.adminPharmacies(phFilter === "all" ? "" : phFilter);
    const chip = (v, l) => `<button class="chip" data-ph="${v}" aria-pressed="${phFilter === v}">${l}</button>`;
    panel.innerHTML = `<div class="toolbar">${chip("pending", "Pending")}${chip("approved", "Approved")}${chip("all", "All")}</div>` +
      (list.length ? `<div class="cards-grid">` + list.map((p) => `<article class="row-card">
        <div class="row-card__main"><h3>${esc(p.name)} <span class="pill" data-t="${p.is_approved ? "ok" : "warn"}">${p.is_approved ? "Approved" : "Pending"}</span></h3>
          <p class="row-card__meta">${esc(p.address)} · ${p.product_count} listing${p.product_count === 1 ? "" : "s"}</p>
          <p class="row-card__meta">Owner: ${esc(p.owner_name || "")} · ${esc(p.owner_email || "")} · created ${esc(ago(p.created_at))}</p></div>
        <div class="row-card__acts">${p.is_approved
          ? `<button class="btn btn--danger btn--sm" data-revoke="${p.pharmacy_id}">Revoke</button>`
          : `<button class="btn btn--primary btn--sm" data-approve="${p.pharmacy_id}">${icon("check")}Approve</button>`}</div></article>`).join("") + `</div>`
        : `<div class="empty">${icon("inbox")}<h3>${phFilter === "pending" ? "Nothing waiting for review" : "No pharmacies"}</h3></div>`);
  }

  /* ---------- medicines ---------- */
  async function medicines(q) {
    const list = await api.medicines(q || "");
    panel.innerHTML = `<div class="toolbar"><label class="visually-hidden" for="mq">Search medicines</label>
      <input class="input" id="mq" type="search" placeholder="Search medicines" value="${esc(q || "")}">
      <span class="toolbar__grow"></span><label class="btn btn--secondary" style="cursor:pointer">${icon("upload")}Import CSV<input type="file" id="medCsv" accept=".csv,.txt" hidden></label><button class="btn btn--primary" id="newMed">${icon("plus")}New medicine</button></div>` +
      (list.length ? `<div class="dt-wrap"><table class="dt"><thead><tr><th>Name</th><th>Generic</th><th>Brand</th><th>Form</th><th>Rx</th><th></th></tr></thead><tbody>` +
        list.map((m) => `<tr><td class="name">${esc(m.name)}</td><td>${esc(m.generic_name || "")}</td><td>${esc(m.brand_name || "")}</td><td>${esc([m.dosage, m.form].filter(Boolean).join(" "))}</td>
          <td>${m.prescription_required ? '<span class="pill" data-t="warn">Rx</span>' : ""}</td>
          <td><div class="acts"><button class="btn btn--secondary btn--sm" data-alias="${m.medicine_id}" data-name="${esc(m.name)}">Aliases</button></div></td></tr>`).join("") + `</tbody></table></div>`
        : `<div class="empty">${icon("pill")}<h3>No medicines found</h3></div>`);
    $("#mq").addEventListener("input", MF.debounce((e) => medicines(e.target.value), 300));
    const mq = $("#mq"); if (q) { mq.focus(); mq.setSelectionRange(q.length, q.length); }
    $("#newMed").onclick = newMedicine;
    $("#medCsv").onchange = async (e) => {
      const f = e.target.files[0]; if (!f) return;
      try { const r = await api.importCatalog(f); MF.toast(`${r.created} added, ${r.existing} already existed`); medicines(); }
      catch (x) { MF.toast(x.message, "error"); }
    };
  }
  function field(id, label, extra) { return `<div class="field"><label class="label" for="${id}">${label}</label><input class="input" id="${id}" ${extra || ""}></div>`; }
  function openForm(title, html, onSubmit) {
    $("#fdTitle").textContent = title; $("#fdBody").innerHTML = html + '<p class="form-error" id="fdErr" role="alert"></p>';
    form = onSubmit; MF.openDialog($("#formDialog"));
  }
  $("#fdForm").addEventListener("submit", async (e) => {
    e.preventDefault();
    try { await form(); MF.closeDialog($("#formDialog")); MF.toast("Saved"); show(tab); }
    catch (x) { $("#fdErr").textContent = x.message; }
  });
  function newMedicine() {
    openForm("New medicine",
      field("fN", "Name", "required") + `<div class="field-row field-row--2">${field("fG", "Generic name")}${field("fB", "Brand name")}</div>
      <div class="field-row field-row--3">${field("fD", "Dosage", 'placeholder="500mg"')}${field("fF", "Form", 'placeholder="Tablet"')}${field("fP", "Package size")}</div>
      <label class="check"><input type="checkbox" id="fR"><span>Prescription required</span></label>`,
      async () => {
        const v = (id) => $(id).value.trim() || null;
        if (!v("#fN")) throw new Error("Name is required.");
        await api.createMedicine({ name: v("#fN"), generic_name: v("#fG"), brand_name: v("#fB"), dosage: v("#fD"), form: v("#fF"), package_size: v("#fP"), prescription_required: $("#fR").checked });
      });
  }
  async function aliasDialog(id, name) {
    const existing = await api.aliases(id);
    openForm("Aliases · " + name,
      `<p class="hint" style="margin-bottom:var(--s-3)">Alternative names customers might search for.</p>
       <p>${existing.length ? existing.map((a) => `<span class="pill">${esc(a.alias_name)}</span>`).join(" ") : '<span class="hint">None yet.</span>'}</p>
       <div style="margin-top:var(--s-4)">${field("fA", "Add alias")}</div>`,
      async () => { const v = $("#fA").value.trim(); if (v) await api.addAlias(id, { alias_name: v }); });
  }

  /* ---------- categories ---------- */
  async function categories() {
    const list = await api.categories();
    panel.innerHTML = `<div class="toolbar"><span class="toolbar__grow"></span><button class="btn btn--primary" id="newCat">${icon("plus")}New category</button></div>` +
      (list.length ? `<div class="cards-grid">${list.map((c) => `<article class="row-card"><div class="row-card__main"><h3>${esc(c.name)}</h3><p class="row-card__meta">${esc(c.description || "")}</p></div></article>`).join("")}</div>`
        : `<div class="empty">${icon("layers")}<h3>No categories yet</h3></div>`);
    $("#newCat").onclick = () => openForm("New category", field("cN", "Name", "required") + field("cD", "Description"),
      async () => { const n = $("#cN").value.trim(); if (!n) throw new Error("Name is required."); await api.createCategory({ name: n, description: $("#cD").value.trim() || null }); });
  }

  /* ---------- crawler data sources ---------- */
  const SRC_NOTE = { ok: "Working", pending: "Not crawled yet", blocked_by_robots: "Site forbids crawlers", unreachable: "Not reachable",
    no_sitemap: "No sitemap found", no_product_data: "No price data on pages" };
  async function sources() {
    const list = await api.webSources();
    panel.innerHTML = `<p class="hint" style="margin-bottom:var(--s-3)">The crawler runs automatically (see <code>scripts/crawl.py</code>) and only reads sites that allow it in robots.txt.</p>
      <div class="dt-wrap"><table class="dt"><thead><tr><th>Website</th><th>Status</th><th>Products</th><th>Last run</th><th></th></tr></thead><tbody>` +
      list.map((s) => `<tr><td class="name">${esc(s.domain)}<div class="sub">${esc(s.detail || "")}</div></td>
        <td><span class="pill" data-t="${s.status === "ok" ? "ok" : s.status === "pending" ? "" : "warn"}">${esc(SRC_NOTE[s.status] || s.status)}</span></td>
        <td class="num">${s.products_total}</td><td>${s.last_run ? esc(ago(s.last_run)) : "–"}</td>
        <td><div class="acts"><button class="btn btn--secondary btn--sm" data-crawl="${esc(s.domain)}">${icon("refresh")}Crawl now</button></div></td></tr>`).join("") + `</tbody></table></div>`;
  }

  /* ---------- users ---------- */
  async function users() {
    const list = await api.users();
    panel.innerHTML = `<div class="dt-wrap"><table class="dt"><thead><tr><th>Name</th><th>Email</th><th>Role</th><th>Status</th></tr></thead><tbody>` +
      list.map((u) => `<tr><td class="name">${esc(u.full_name)}</td><td>${esc(u.email)}</td><td><span class="pill" data-t="${u.role === "admin" ? "warn" : ""}">${esc(u.role.replace("_", " "))}</span></td><td>${u.is_active ? "Active" : "Disabled"}</td></tr>`).join("") + `</tbody></table></div>`;
  }

  panel.addEventListener("click", async (e) => {
    const t = e.target.closest("button"); if (!t) return;
    try {
      if (t.dataset.ph) { phFilter = t.dataset.ph; show("pharmacies"); }
      else if (t.dataset.approve) { await api.approve(t.dataset.approve); MF.toast("Pharmacy approved"); show("pharmacies"); }
      else if (t.dataset.revoke) { if (confirm("Remove this pharmacy from public search?")) { await api.revoke(t.dataset.revoke); MF.toast("Approval revoked"); show("pharmacies"); } }
      else if (t.dataset.crawl) { await api.crawlNow(t.dataset.crawl); MF.toast("Crawl started. Refresh in a minute."); }
      else if (t.dataset.alias) aliasDialog(Number(t.dataset.alias), t.dataset.name);
    } catch (x) { MF.toast(x.message, "error"); }
  });

  init();
})();
