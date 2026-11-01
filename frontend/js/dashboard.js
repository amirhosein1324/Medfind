(function () {
  "use strict";
  const { $, $$, esc, icon, api, money, freshnessHTML, ageHours, ago } = MF;
  const root = $("#main");
  $("#addClose").innerHTML = icon("x");
  $("#impClose").innerHTML = icon("x");
  const S = { pharmacies: [], pid: null, listings: [], q: "", dirty: new Map(), pickedMed: null };

  const STATUS_OPTS = [["available", "Available"], ["limited_stock", "Limited stock"], ["out_of_stock", "Out of stock"], ["unknown", "Not confirmed"]];
  const cur = () => S.pharmacies.find((p) => p.pharmacy_id === S.pid);

  async function init() {
    let me;
    try { me = await MF.requireRole(["pharmacy_owner", "admin"]); }
    catch (e) { return fail(e); }
    if (!me) return;
    MF.renderNav("dashboard");
    try { S.pharmacies = await api.myPharmacies(); } catch (e) { return fail(e); }
    if (!S.pharmacies.length) return renderSetup();
    S.pid = S.pharmacies[0].pharmacy_id;
    await load();
  }
  function fail(e) {
    root.innerHTML = `<div class="empty">${icon("alert")}<h3>Couldn't load your dashboard</h3><p>${esc(e.message)}</p><button class="btn btn--secondary" onclick="location.reload()">Retry</button></div>`;
  }

  /* ---------- first-time setup ---------- */
  function renderSetup() {
    root.innerHTML = `<div class="setup"><div class="page__head"><div><h1>Set up your pharmacy</h1><p>An admin reviews new pharmacies before they show up in search.</p></div></div>
      <form class="panel" id="setupForm" novalidate>
        <div class="field"><label class="label" for="pn">Pharmacy name</label><input class="input" id="pn" required></div>
        <div class="field"><label class="label" for="pa">Address</label><input class="input" id="pa" required></div>
        <div class="field-row field-row--2">
          <div class="field"><label class="label" for="plat">Latitude</label><input class="input" id="plat" type="number" step="any"></div>
          <div class="field"><label class="label" for="plon">Longitude</label><input class="input" id="plon" type="number" step="any"></div>
        </div>
        <p style="margin-top:var(--s-2)"><button class="btn btn--secondary btn--sm" type="button" id="geo">${icon("locate")}Use my current location</button> <span class="hint">Needed so customers see distance.</span></p>
        <div class="field-row field-row--2" style="margin-top:var(--s-4)">
          <div class="field"><label class="label" for="pp">Phone</label><input class="input" id="pp" type="tel"></div>
          <div class="field"><label class="label" for="pw">Website</label><input class="input" id="pw" type="url" placeholder="https://"></div>
        </div>
        <div class="field"><label class="label" for="ph">Opening hours</label><input class="input" id="ph" placeholder="Mon-Sat 8:00-20:00"></div>
        <p class="form-error" id="setupErr" role="alert"></p>
        <button class="btn btn--primary btn--lg" type="submit">Submit for approval</button>
      </form></div>`;
    $("#geo").onclick = () => navigator.geolocation
      ? navigator.geolocation.getCurrentPosition((p) => { $("#plat").value = p.coords.latitude.toFixed(6); $("#plon").value = p.coords.longitude.toFixed(6); },
        () => MF.toast("Couldn't get your location.", "error"))
      : MF.toast("Location isn't available in this browser.", "error");
    $("#setupForm").onsubmit = async (e) => {
      e.preventDefault();
      const num = (id) => ($(id).value === "" ? null : Number($(id).value));
      const body = { name: $("#pn").value.trim(), address: $("#pa").value.trim(), latitude: num("#plat"), longitude: num("#plon"),
        phone: $("#pp").value.trim() || null, website: $("#pw").value.trim() || null, opening_hours: $("#ph").value.trim() || null };
      if (!body.name || !body.address) { $("#setupErr").textContent = "Name and address are required."; return; }
      try { await api.createPharmacy(body); MF.toast("Submitted. We'll review it shortly."); await init(); }
      catch (x) { $("#setupErr").textContent = x.message; }
    };
  }

  /* ---------- main view ---------- */
  async function load() {
    try { S.listings = await api.listings(S.pid); } catch (e) { return fail(e); }
    S.dirty.clear();
    renderMain();
    loadHistory();
  }

  function stats() {
    const l = S.listings.filter((x) => x.is_active !== false);
    return {
      total: l.length,
      avail: l.filter((x) => x.availability_status === "available").length,
      out: l.filter((x) => x.availability_status === "out_of_stock").length,
      stale: l.filter((x) => ageHours(x.last_updated) > MF.CFG.staleHours).length,
    };
  }

  function renderMain() {
    const p = cur(), st = stats();
    root.innerHTML = `
      ${p.is_approved ? "" : `<div class="banner banner--info pending-banner" role="status">${icon("clock")}<span><strong>Waiting for approval.</strong> Your pharmacy isn't visible in search yet. You can add listings now.</span></div>`}
      <div class="page__head">
        <div><h1>${esc(p.name)}</h1><p>${esc(p.address)}${p.is_approved ? ' · <span class="pill" data-t="ok">Live in search</span>' : ""}</p></div>
        <div class="page__actions">
          ${S.pharmacies.length > 1 ? `<label class="visually-hidden" for="pharmSel">Pharmacy</label><select class="select" id="pharmSel" style="width:auto">${S.pharmacies.map((x) => `<option value="${x.pharmacy_id}"${x.pharmacy_id === S.pid ? " selected" : ""}>${esc(x.name)}</option>`).join("")}</select>` : ""}
          <button class="btn btn--secondary" id="confirmAll">${icon("check-circle")}Everything is up to date</button>
          <button class="btn btn--secondary" id="impBtn">${icon("upload")}Import file</button>
          <button class="btn btn--primary" id="addBtn">${icon("plus")}Add medicine</button>
        </div>
      </div>
      <div class="stats">
        <div class="stat"><div class="stat__n">${st.total}</div><div class="stat__l">Listings</div></div>
        <div class="stat" data-tone="ok"><div class="stat__n">${st.avail}</div><div class="stat__l">Available</div></div>
        <div class="stat" data-tone="${st.out ? "bad" : ""}"><div class="stat__n">${st.out}</div><div class="stat__l">Out of stock</div></div>
        <div class="stat" data-tone="${st.stale ? "warn" : "ok"}"><div class="stat__n">${st.stale}</div><div class="stat__l">Need confirming (${MF.CFG.staleHours}h+)</div></div>
      </div>
      <div class="toolbar"><label class="visually-hidden" for="filt">Filter listings</label>
        <input class="input" id="filt" type="search" placeholder="Filter by medicine name" value="${esc(S.q)}"></div>
      <div id="tableHost"></div>
      <div class="two-col"><div><h2 class="section-title">Recent changes</h2><ul class="hist" id="hist"><li class="hint">Loading…</li></ul></div></div>`;
    paintTable();
    $("#filt").oninput = (e) => { S.q = e.target.value; paintTable(); };
    $("#addBtn").onclick = openAdd;
    $("#impBtn").onclick = () => { $("#impResult").innerHTML = ""; $("#impForm").reset(); MF.openDialog($("#impDialog")); };
    $("#confirmAll").onclick = confirmAll;
    const sel = $("#pharmSel"); if (sel) sel.onchange = () => { S.pid = Number(sel.value); load(); };
  }

  function paintTable() {
    const q = S.q.trim().toLowerCase();
    const rows = S.listings.filter((x) => !q || (x.medicine_name || "").toLowerCase().includes(q));
    const host = $("#tableHost");
    if (!S.listings.length) {
      host.innerHTML = `<div class="empty">${icon("pill")}<h3>No medicines listed yet</h3><p>Add the medicines you stock so people can find them.</p><button class="btn btn--primary" id="emptyAdd">${icon("plus")}Add your first medicine</button></div>`;
      $("#emptyAdd").onclick = openAdd; return;
    }
    if (!rows.length) { host.innerHTML = `<div class="empty">${icon("search")}<h3>No match</h3></div>`; return; }
    host.innerHTML = `<div class="dt-wrap"><table class="dt"><thead><tr><th>Medicine</th><th>Price</th><th>Status</th><th>Stock</th><th>Confirmed</th><th><span class="visually-hidden">Actions</span></th></tr></thead><tbody>` +
      rows.map((x) => `<tr data-id="${x.product_id}">
        <td><div class="name">${esc(x.medicine_name || "Medicine #" + x.medicine_id)}</div><div class="sub">${esc(x.medicine_detail || "")}</div></td>
        <td><label class="visually-hidden" for="pr${x.product_id}">Price</label><input class="input in-price num" id="pr${x.product_id}" data-f="price" type="number" min="0" step="0.01" value="${x.price == null ? "" : Number(x.price)}"></td>
        <td><label class="visually-hidden" for="st${x.product_id}">Status</label><select class="select in-status" id="st${x.product_id}" data-f="availability_status">${STATUS_OPTS.map(([v, l]) => `<option value="${v}"${v === x.availability_status ? " selected" : ""}>${l}</option>`).join("")}</select></td>
        <td><label class="visually-hidden" for="sk${x.product_id}">Stock</label><input class="input in-stock num" id="sk${x.product_id}" data-f="stock_quantity" type="number" min="0" step="1" value="${x.stock_quantity == null ? "" : x.stock_quantity}"></td>
        <td>${freshnessHTML(x.last_updated)}</td>
        <td><div class="acts"><button class="btn btn--primary btn--sm" data-save disabled>Save</button><button class="btn btn--secondary btn--sm" data-confirm title="Confirm nothing has changed">${icon("check")}<span>Confirm</span></button></div></td></tr>`).join("") +
      `</tbody></table></div>`;
    $$("tr[data-id]", host).forEach((tr) => {
      const id = Number(tr.dataset.id);
      tr.addEventListener("input", () => {
        tr.classList.add("is-dirty"); $("[data-save]", tr).disabled = false; S.dirty.set(id, true);
      });
      $("[data-save]", tr).onclick = () => save(id, tr);
      $("[data-confirm]", tr).onclick = () => confirmOne(id);
    });
  }

  async function save(id, tr) {
    const f = (n) => $(`[data-f=${n}]`, tr).value;
    const body = { availability_status: f("availability_status") };
    if (f("price") !== "") body.price = Number(f("price"));
    if (f("stock_quantity") !== "") body.stock_quantity = Number(f("stock_quantity"));
    const btn = $("[data-save]", tr); btn.disabled = true;
    try {
      const u = await api.updateListing(id, body);
      Object.assign(S.listings.find((x) => x.product_id === id), u);
      MF.toast("Saved"); renderMain(); loadHistory();
    } catch (e) { btn.disabled = false; MF.toast(e.message, "error"); }
  }
  async function confirmOne(id) {
    try { const u = await api.confirmListing(id); Object.assign(S.listings.find((x) => x.product_id === id), u); MF.toast("Confirmed"); renderMain(); loadHistory(); }
    catch (e) { MF.toast(e.message, "error"); }
  }
  async function confirmAll() {
    if (S.dirty.size && !confirm("You have unsaved edits. Confirm everything as it is stored now?")) return;
    try { await api.confirmAll(S.pid); MF.toast("All listings confirmed"); await load(); }
    catch (e) { MF.toast(e.message, "error"); }
  }

  async function loadHistory() {
    const host = $("#hist"); if (!host) return;
    try {
      const h = await api.history(S.pid);
      host.innerHTML = h.length ? h.slice(0, 12).map((u) => {
        const bits = [];
        if (String(u.old_price) !== String(u.new_price)) bits.push(`${esc(money(u.old_price) || "–")} <span class="arrow">→</span> ${esc(money(u.new_price) || "–")}`);
        if (u.old_status !== u.new_status) bits.push(`${esc(u.old_status || "–")} <span class="arrow">→</span> ${esc(u.new_status || "–")}`);
        if (u.old_stock !== u.new_stock) bits.push(`stock ${u.old_stock ?? "–"} <span class="arrow">→</span> ${u.new_stock ?? "–"}`);
        return `<li><strong>${esc(u.medicine_name)}</strong><span>${bits.join(" · ") || "Confirmed, no change"}</span><span class="when">${esc(ago(u.updated_at))}</span></li>`;
      }).join("") : `<li class="hint">No changes yet.</li>`;
    } catch (e) { host.innerHTML = `<li class="hint">${esc(e.message)}</li>`; }
  }

  /* ---------- add listing ---------- */
  let cb;
  function openAdd() {
    S.pickedMed = null; $("#addForm").reset(); $("#addErr").textContent = ""; $("#addPicked").textContent = "Pick a medicine from the list.";
    if (!cb) cb = MF.combobox({
      input: $("#addMed"), list: $("#addSuggest"), minChars: 2,
      fetch: (q) => api.medicines(q).then((l) => l.slice(0, 8)),
      render: (m) => `<span>${esc(m.name)}</span><small>${esc(m.generic_name || "")}</small>`,
      onPick: (m) => { S.pickedMed = m; $("#addMed").value = m.name; $("#addPicked").textContent = "Selected: " + m.name; },
    });
    MF.openDialog($("#addDialog"));
  }
  $("#addMed").addEventListener("input", () => { S.pickedMed = null; });
  $("#addForm").addEventListener("submit", async (e) => {
    e.preventDefault();
    if (!S.pickedMed) { $("#addErr").textContent = "Choose a medicine from the suggestions."; return; }
    const body = { medicine_id: S.pickedMed.medicine_id, availability_status: $("#addStatus").value };
    if ($("#addPrice").value !== "") body.price = Number($("#addPrice").value);
    if ($("#addStock").value !== "") body.stock_quantity = Number($("#addStock").value);
    try { await api.addListing(S.pid, body); MF.closeDialog($("#addDialog")); MF.toast("Listing added"); await load(); }
    catch (x) { $("#addErr").textContent = x.message; }
  });

  /* ---------- bulk import ---------- */
  $("#impTpl").onclick = () => {
    const csv = "medicine,price,status,stock\nParacetamol 500mg,4.20,available,40\nIbuprofen 400mg,5.40,limited_stock,3\n";
    const a = document.createElement("a");
    a.href = URL.createObjectURL(new Blob([csv], { type: "text/csv" })); a.download = "medfind-stock-template.csv"; a.click();
    URL.revokeObjectURL(a.href);
  };
  $("#impForm").addEventListener("submit", async (e) => {
    e.preventDefault();
    const f = $("#impFile").files[0]; if (!f) return;
    const go = $("#impGo"), out = $("#impResult"); go.disabled = true; go.textContent = "Importing…";
    try {
      const r = await api.importStock(S.pid, f);
      out.innerHTML = `<div class="banner banner--info">${icon("check-circle")}<span><strong>${r.created} added, ${r.updated} updated, ${r.skipped} skipped.</strong></span></div>` +
        (r.problems.length ? `<ul class="hist" style="margin-top:var(--s-3);max-height:12rem;overflow:auto">${r.problems.map((p) => `<li><strong>Row ${p.row}${p.medicine ? " · " + esc(p.medicine) : ""}</strong><span>${esc(p.reason)}</span></li>`).join("")}</ul>` : "");
      await load();
    } catch (x) { out.innerHTML = `<p class="form-error">${esc(x.message)}</p>`; }
    go.disabled = false; go.textContent = "Import";
  });

  init();
})();
