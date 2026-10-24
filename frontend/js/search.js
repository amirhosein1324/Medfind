/* Public search page: typeahead, location, filters, sort, cards/table, details. */
(function () {
  "use strict";
  const { $, $$, esc, icon, money, statusHTML, freshnessHTML, ageHours, ago, api, store, KEYS } = MF;

  const state = {
    q: "",
    loc: store.json(KEYS.loc, null),
    raw: [],
    demo: false,
    productId: null,
    sort: "best",
    view: store.get("medfind_view") === "table" ? "table" : "cards",
    filters: { inStock: false, verified: false, maxKm: 50 },
    seq: 0,
    ctrl: null,
  };

  const AVAIL_RANK = { available: 0, limited_stock: 1, unknown: 2, out_of_stock: 3 };
  const QUICK = I18N.lang === "fa" ? ["پاراستامول", "ایبوپروفن", "آموکسی‌سیلین", "ستیریزین", "امپرازول"] : ["Paracetamol", "Ibuprofen", "Amoxicillin", "Cetirizine", "Omeprazole"];

  MF.renderNav("search");

  /* ---------------------------------------------------- static icon slots */
  const slots = {
    ".searchbar__icon": "search", ".searchbar__go-icon": "search", "#locBtnIcon": "locate",
    "#sampleFlag": null, "#samplePin": "pin", "#why1": "search", "#why2": "clock", "#why3": "shield",
    "#filtersBtnIcon": "sliders", "#viewCards": "cards", "#viewTable": "table",
    "#filtersClose": "x", "#connClose": "x", "#demoBannerIcon": "alert",
  };
  Object.keys(slots).forEach((sel) => { const el = $(sel); if (el && slots[sel]) el.innerHTML = icon(slots[sel]); });
  $("#sampleFlag").innerHTML = icon("check") + "<span>Best match</span>";
  $("#sampleStatusA").innerHTML = icon("check-circle") + "<span>Available</span>";
  $("#sampleStatusB").innerHTML = icon("minus-circle") + "<span>Limited stock</span>";

  /* ------------------------------------------------------------- quick chips */
  const quick = $("#quick");
  quick.innerHTML = '<span class="quick__label">Try:</span>' +
    QUICK.map((n) => `<button class="chip" type="button" data-q="${esc(n)}">${esc(n)}</button>`).join("");
  quick.addEventListener("click", (e) => {
    const b = e.target.closest("[data-q]");
    if (b) { $("#q").value = b.dataset.q; runSearch(b.dataset.q); }
  });

  /* --------------------------------------------------------------- typeahead */
  const input = $("#q");
  const cb = MF.combobox({
    input, list: $("#suggest"), minChars: 2,
    fetch: async (q) => {
      let list;
      try {
        const [a, b] = await Promise.all([api.medicines(q), api.webSuggest(q).catch(() => [])]);
        const seen = new Set(a.map((m) => m.name.toLowerCase()));
        list = a.slice(0, 5).concat(b.filter((m) => !seen.has(m.name.toLowerCase())));
      } catch (e) { list = window.MFDemo ? MFDemo.medicines(q) : []; }
      return (list || []).slice(0, 8);
    },
    render: (m) => `<span>${esc(m.name)}</span><small>${esc(m.generic_name || m.brand_name || "")}</small>`,
    onPick: (m) => { input.value = m.name; runSearch(m.name); },
  });

  $("#searchForm").addEventListener("submit", (e) => {
    e.preventDefault();
    cb.close();
    const q = input.value.trim();
    if (q) runSearch(q);
  });

  /* ---------------------------------------------------------------- location */
  function paintLoc() {
    const on = !!state.loc;
    const b = $("#locBtn");
    b.setAttribute("aria-pressed", String(on));
    $("#locBtnText").textContent = on ? "Location on" : "Use my location";
    $("#locHint").textContent = on
      ? "Showing distance from you. Click again to turn it off."
      : "Location stays in your browser and is only used to measure distance.";
    $$("[data-filter=maxKm]").forEach((r) => { r.disabled = !on; });
    $$("[data-loc-hint]").forEach((p) => { p.hidden = on; });
    if (!on) state.filters.maxKm = 50;
    syncFilterControls();
  }
  $("#locBtn").addEventListener("click", () => {
    if (state.loc) {
      state.loc = null; store.set(KEYS.loc, null); paintLoc();
      if (state.q) runSearch(state.q, true);
      return;
    }
    if (!navigator.geolocation) { MF.toast("Your browser can't share a location.", "error"); return; }
    $("#locBtnText").textContent = "Locating…";
    navigator.geolocation.getCurrentPosition(
      (p) => {
        state.loc = { lat: p.coords.latitude, lon: p.coords.longitude };
        store.set(KEYS.loc, JSON.stringify(state.loc));
        paintLoc();
        if (state.q) runSearch(state.q, true);
      },
      () => { paintLoc(); MF.toast("Couldn't get your location. Check the browser permission.", "error"); },
      { enableHighAccuracy: false, timeout: 10000, maximumAge: 300000 }
    );
  });

  /* ----------------------------------------------------------------- filters */
  function buildFilters(host) {
    host.innerHTML = "";
    host.appendChild($("#filtersTpl").content.cloneNode(true));
    host.addEventListener("change", onFilter);
    host.addEventListener("input", (e) => { if (e.target.matches("[data-filter=maxKm]")) onFilter(e); });
    host.addEventListener("click", (e) => {
      if (e.target.closest("[data-clear-filters]")) {
        state.filters = { inStock: false, verified: false, maxKm: 50 };
        syncFilterControls(); render();
      }
    });
  }
  function onFilter(e) {
    const t = e.target.closest("[data-filter]");
    if (!t) return;
    const k = t.dataset.filter;
    state.filters[k] = t.type === "checkbox" ? t.checked : Number(t.value);
    syncFilterControls(); render();
  }
  function syncFilterControls() {
    $$("[data-filter]").forEach((el) => {
      const k = el.dataset.filter;
      if (el.type === "checkbox") el.checked = !!state.filters[k]; else el.value = state.filters[k];
    });
    $$("[data-out=maxKm]").forEach((o) => {
      o.textContent = state.filters.maxKm >= 50 ? "Any distance" : "Within " + state.filters.maxKm + " km";
    });
    const n = (state.filters.inStock ? 1 : 0) + (state.filters.verified ? 1 : 0) + (state.filters.maxKm < 50 ? 1 : 0);
    const c = $("#filtersCount");
    c.hidden = !n; c.textContent = n;
  }
  buildFilters($("#filtersDesktop"));
  buildFilters($("#filtersMobile"));
  $("#filtersBtn").addEventListener("click", () => MF.openDialog($("#filtersSheet")));
  $("#filtersDone").addEventListener("click", () => {});
  paintLoc();

  /* -------------------------------------------------------------- sort / view */
  $("#sortSel").addEventListener("change", (e) => { state.sort = e.target.value; render(); });
  function setView(v) {
    state.view = v; store.set("medfind_view", v);
    $("#viewCards").setAttribute("aria-pressed", String(v === "cards"));
    $("#viewTable").setAttribute("aria-pressed", String(v === "table"));
    render();
  }
  $("#viewCards").addEventListener("click", () => setView("cards"));
  $("#viewTable").addEventListener("click", () => setView("table"));
  $("#viewCards").setAttribute("aria-pressed", String(state.view === "cards"));
  $("#viewTable").setAttribute("aria-pressed", String(state.view === "table"));

  /* ------------------------------------------------------------------ search */
  async function runSearch(q, keepProduct) {
    state.q = q;
    if (!keepProduct) state.productId = null;
    const url = new URL(location.href);
    url.searchParams.set("q", q);
    history.replaceState(null, "", url);

    const my = ++state.seq;
    if (state.ctrl) state.ctrl.abort();
    state.ctrl = new AbortController();

    $("#hero").classList.add("is-compact");
    $("#why").hidden = true;
    $("#results").hidden = false;
    $("#resultsTitle").textContent = "Searching…";
    $("#resultsSub").textContent = "";
    $("#products").hidden = true;
    $("#resultList").innerHTML = skeletons();

    const params = { q };
    if (state.loc) { params.latitude = state.loc.lat; params.longitude = state.loc.lon; }

    try {
      let data;
      try {
        data = await api.search(params, state.ctrl.signal);
        state.demo = false;
      } catch (e) {
        if (e.name === "AbortError") return;
        if (!e.network || !window.MFDemo) throw e;
        data = MFDemo.search(q, state.loc);
        state.demo = true;
      }
      if (my !== state.seq) return;
      state.raw = data || [];
      $("#demoBanner").hidden = !state.demo;
      render(true);
      loadWeb(q, my);
    } catch (e) {
      if (my !== state.seq) return;
      $("#resultsTitle").textContent = "Something went wrong";
      $("#resultList").innerHTML = `<div class="empty">${icon("alert")}<h3>We couldn't run that search</h3><p>${esc(e.message)}</p>
        <button class="btn btn--secondary" type="button" id="retry">Try again</button></div>`;
      $("#retry").addEventListener("click", () => runSearch(q));
    }
  }

  /* ------------------------------------------------ results from other websites */
  const toman = (v) => Math.round(Number(v)).toLocaleString("en-US");
  const fmtPrice = (v, cur) => v == null ? "" : cur === "IRT" ? toman(v) + " Toman" : (v < 1 ? Number(v).toFixed(4).replace(/0+$/, "").replace(/\.$/, ".00") : Number(v).toFixed(2)) + " " + (cur || "");
  let webGroups = [], webSort = "relevance";

  function groupCard(g) {
    const unknown = g.offers.every((o) => o.availability === "unknown");
    const none = g.available === 0 && !unknown;
    const title = g.generic || g.name;
    const chips = [g.strength, g.form].filter(Boolean).map((c) => `<span class="tag" dir="ltr">${esc(c)}</span>`).join("");
    const range = g.max_price != null && g.min_price != null && Number(g.max_price) > Number(g.min_price)
      ? `<span class="pcard__range">${esc(I18N.t("Up to {p}", { p: fmtPrice(g.max_price, g.currency) }))}</span>` : "";
    const unit = g.price_unit ? `<span class="pcard__unit">/ ${esc(g.price_unit)}</span>` : "";
    const count = g.offer_count > 1 ? `<span class="pcard__count">${esc(I18N.t("{n} listings", { n: g.offer_count }))}</span>` : "";
    return `<a class="pcard" href="product.html?k=${encodeURIComponent(g.key)}">
      <div class="pcard__img">${g.image_url ? `<img src="${esc(MF.safeUrl(g.image_url) || "")}" alt="" loading="lazy" referrerpolicy="no-referrer">` : icon("pill")}
        ${g.form ? `<span class="pcard__form" dir="ltr">${esc(g.form)}</span>` : ""}</div>
      <div class="pcard__body">
        <h3 class="pcard__name">${esc(title)}</h3>
        ${g.title_fa ? `<div class="pcard__fa" dir="auto">${esc(g.title_fa)}</div>` : ""}
        ${chips ? `<div class="pcard__tags">${chips}</div>` : ""}
        <div class="pcard__price">${g.min_price != null
          ? `<span class="hint">${none ? "Last price" : "From"}</span><strong class="num">${esc(fmtPrice(g.min_price, g.currency))}</strong>${unit}${range ? "<br>" + range : ""}`
          : '<span class="hint">Price not listed</span>'}</div>
        <div class="pcard__meta">
          <span class="pcard__src" title="${esc(g.cheapest_shop || "")}" data-nofa>${esc(g.cheapest_shop || "")}</span>${count}</div>
        <div class="pcard__foot">
          <span class="pcard__stock" data-none="${none}" data-unk="${unknown}">${none ? "Out of stock" : unknown ? "Stock unknown" : esc(I18N.t("{n} in stock", { n: g.available }))}</span>
          <span class="pcard__go">${icon("chevron")}</span></div>
      </div></a>`;
  }

  function paintGroups() {
    const host = $("#webGrid"); if (!host) return;
    const list = webGroups.slice().sort(webSort === "price"
      ? (a, b) => (a.min_price == null) - (b.min_price == null) || a.min_price - b.min_price
      : webSort === "shops" ? (a, b) => b.shops - a.shops : () => 0);
    host.innerHTML = list.map(groupCard).join("");
    $$("[data-wsort]").forEach((b) => b.setAttribute("aria-pressed", String(b.dataset.wsort === webSort)));
  }

  async function loadWeb(q, my) {
    const host = $("#webResults");
    host.hidden = true;
    if (state.demo) return;
    host.hidden = false;
    host.innerHTML = `<h2 class="web__title" id="webTitle">Medicines found online</h2><div class="pgrid">${[1, 2, 3].map(() => '<div class="skeleton" style="height:210px;border-radius:14px"></div>').join("")}</div>`;
    try {
      const res = await api.webSearch(q);
      if (my !== state.seq) return;
      if (!res.enabled || !res.groups.length) { host.hidden = true; return; }
      webGroups = res.groups; webSort = "relevance";
      const sites = new Set(res.items.map((i) => i.source_domain)).size;
      if (!state.raw.length) {
        $("#resultList").innerHTML = "";
        $("#resultsTitle").textContent = `Results for “${q}”`;
        $("#resultsSub").textContent = `${webGroups.length} medicine${webGroups.length === 1 ? "" : "s"} from ${sites} online pharmac${sites === 1 ? "y" : "ies"}`;
      }
      host.innerHTML = `<div class="web__head"><div><h2 class="web__title" id="webTitle">Medicines found online</h2>
        <p class="hint">Prices are collected automatically from pharmacy websites and may be out of date. Open a medicine to compare shops.</p></div>
        <div class="web__sort" role="group" aria-label="Sort online results">
          <button class="chip" type="button" data-wsort="relevance" aria-pressed="true">Best match</button>
          <button class="chip" type="button" data-wsort="price" aria-pressed="false">Cheapest</button>
          <button class="chip" type="button" data-wsort="shops" aria-pressed="false">Most shops</button></div></div>
        <div class="pgrid" id="webGrid"></div>`;
      paintGroups();
      $$("[data-wsort]", host).forEach((b) => b.addEventListener("click", () => { webSort = b.dataset.wsort; paintGroups(); }));
    } catch (e) { if (my === state.seq) host.hidden = true; }
  }

  function skeletons() {
    return [1, 2, 3].map(() => `<div class="result result--skel" aria-hidden="true">
      <div class="skeleton skel-line" style="width:40%"></div><div class="skeleton skel-line" style="width:65%"></div>
      <div class="skeleton skel-line" style="width:30%"></div></div>`).join("");
  }

  /* ---------------------------------------------------------- derive + render */
  function visible() {
    const f = state.filters;
    let list = state.raw.filter((r) => {
      if (state.productId && r.medicine_id !== state.productId) return false;
      if (f.inStock && r.availability !== "available" && r.availability !== "limited_stock") return false;
      if (f.verified && !r.is_verified) return false;
      if (state.loc && f.maxKm < 50 && (r.distance_km == null || r.distance_km > f.maxKm)) return false;
      return true;
    });
    const price = (r) => (r.price == null ? Infinity : Number(r.price));
    const dist = (r) => (r.distance_km == null ? Infinity : r.distance_km);
    const stale = (r) => (ageHours(r.last_updated) > MF.CFG.staleHours ? 1 : 0);
    const cmp = {
      best: (a, b) => (AVAIL_RANK[a.availability] ?? 9) - (AVAIL_RANK[b.availability] ?? 9) || stale(a) - stale(b) ||
        (state.loc ? dist(a) - dist(b) : 0) || price(a) - price(b),
      nearest: (a, b) => dist(a) - dist(b) || price(a) - price(b),
      price: (a, b) => price(a) - price(b) || dist(a) - dist(b),
      updated: (a, b) => ageHours(a.last_updated) - ageHours(b.last_updated),
    }[state.sort];
    return list.sort(cmp);
  }

  function render(focus) {
    if (!state.q) return;
    const list = visible();
    const title = $("#resultsTitle");
    title.textContent = state.raw.length ? `Results for “${state.q}”` : `No results for “${state.q}”`;
    const phs = new Set(list.map((r) => r.pharmacy_id)).size;
    $("#resultsSub").textContent = list.length
      ? `${list.length} listing${list.length === 1 ? "" : "s"} from ${phs} pharmac${phs === 1 ? "y" : "ies"}`
      : "";
    $("#liveStatus").textContent = `${list.length} results`;
    renderProducts();

    const host = $("#resultList");
    if (!list.length) {
      const filtered = state.raw.length > 0;
      host.innerHTML = `<div class="empty">${icon(filtered ? "sliders" : "search")}
        <h3>${filtered ? "Nothing matches your filters" : "No pharmacy lists this yet"}</h3>
        <p>${filtered ? "Try removing a filter or widening the distance." : "Check the spelling, or try the generic or brand name."}</p>
        ${filtered ? '<button class="btn btn--secondary" type="button" id="clearF">Clear filters</button>' : ""}</div>`;
      const c = $("#clearF");
      if (c) c.addEventListener("click", () => { state.filters = { inStock: false, verified: false, maxKm: 50 }; syncFilterControls(); render(); });
    } else if (state.view === "table") {
      host.innerHTML = tableHTML(list);
    } else {
      host.innerHTML = list.map((r, i) => cardHTML(r, i === 0 && state.sort === "best" && r.availability === "available")).join("");
    }
    if (focus) title.focus({ preventScroll: true });
    if (focus) title.scrollIntoView({ block: "start", behavior: "smooth" });
  }

  function renderProducts() {
    const host = $("#products");
    const groups = new Map();
    state.raw.forEach((r) => {
      const g = groups.get(r.medicine_id) || { name: r.medicine, n: 0 };
      g.n++; groups.set(r.medicine_id, g);
    });
    if (groups.size < 2) { host.hidden = true; return; }
    host.hidden = false;
    const chip = (id, label, n) =>
      `<button class="chip" type="button" data-pid="${id}" aria-pressed="${(state.productId || 0) === id}">${esc(label)} <span class="count">${n}</span></button>`;
    host.innerHTML = chip(0, "All", state.raw.length) +
      Array.from(groups, ([id, g]) => chip(id, g.name, g.n)).join("");
  }
  $("#products").addEventListener("click", (e) => {
    const b = e.target.closest("[data-pid]");
    if (!b) return;
    state.productId = Number(b.dataset.pid) || null;
    render();
  });

  /* --------------------------------------------------------------- templates */
  function distText(r) { return r.distance_km == null ? "" : (r.distance_km < 10 ? r.distance_km.toFixed(1) : Math.round(r.distance_km)) + " km"; }
  function isStale(r) { return ageHours(r.last_updated) > MF.CFG.staleHours; }

  function cardHTML(r, best) {
    const verified = r.is_verified ? `<span class="verified" title="Verified pharmacy">${icon("shield")}<span class="visually-hidden">Verified</span></span>` : "";
    const flags = (best ? `<span class="flag">${icon("check")}Best match</span>` : "") +
      (r.prescription_required ? `<span class="flag flag--soft">Rx only</span>` : "");
    const phone = MF.telHref(r.phone);
    const stale = isStale(r)
      ? `<div class="stale-note">${icon("alert")}<span>This listing hasn't been confirmed in over ${MF.CFG.staleHours} hours. Call before you go.</span></div>` : "";
    const stock = r.availability === "limited_stock" && r.stock_quantity != null ? `<span class="result__stock">Only ${r.stock_quantity} left</span>` : "";
    return `<article class="result${best ? " result--best" : ""}" data-pid="${r.product_id}">
      <div class="result__top">
        <div>
          ${flags ? `<div class="result__flags">${flags}</div>` : ""}
          <h3 class="result__name">${esc(r.pharmacy)}${verified}</h3>
          <p class="result__med">${esc(r.medicine)}${r.medicine_detail ? " · " + esc(r.medicine_detail) : ""}</p>
          <div class="result__loc">
            ${r.distance_km != null ? `<span class="dist">${icon("navigation")}${esc(distText(r))}</span>` : ""}
            <span>${icon("pin")}${esc(r.address)}</span>
            ${r.opening_hours ? `<span>${icon("clock")}${esc(r.opening_hours)}</span>` : ""}
          </div>
        </div>
        <div class="result__buy">
          ${r.price != null ? `<div class="price">${esc(money(r.price))}</div>` : `<div class="price price--none">Price not listed</div>`}
          ${statusHTML(r.availability)}${stock}
        </div>
      </div>
      ${stale}
      <div class="result__foot">
        ${freshnessHTML(r.last_updated)}
        <div class="result__actions" style="margin-left:auto">
          ${phone ? `<a class="btn btn--secondary btn--sm" href="${esc(phone)}">${icon("phone")}Call</a>` : ""}
          <a class="btn btn--secondary btn--sm" href="${esc(MF.directionsUrl(r))}" target="_blank" rel="noopener">${icon("navigation")}Directions</a>
          <button class="btn btn--ghost btn--sm" type="button" data-details="${r.product_id}">Details</button>
        </div>
      </div>
    </article>`;
  }

  function tableHTML(list) {
    const bestId = list[0] && state.sort === "best" && list[0].availability === "available" ? list[0].product_id : null;
    return `<div class="cmp-wrap"><table class="cmp"><thead><tr>
      <th scope="col">Pharmacy</th><th scope="col">Medicine</th><th scope="col" class="r">Price</th>
      <th scope="col">Status</th><th scope="col" class="r">Distance</th><th scope="col">Confirmed</th><th scope="col"><span class="visually-hidden">Actions</span></th>
      </tr></thead><tbody>` + list.map((r) => `<tr class="${r.product_id === bestId ? "is-best" : ""}">
      <th scope="row" style="text-align:left;font-weight:inherit"><div class="cmp__name">${esc(r.pharmacy)}${r.is_verified ? `<span class="verified">${icon("shield")}</span>` : ""}</div><div class="cmp__sub">${esc(r.address)}</div></th>
      <td>${esc(r.medicine)}</td>
      <td class="r cmp__price">${r.price != null ? esc(money(r.price)) : '<span class="cmp__sub">n/a</span>'}</td>
      <td>${statusHTML(r.availability)}</td>
      <td class="r">${esc(distText(r)) || '<span class="cmp__sub">n/a</span>'}</td>
      <td>${freshnessHTML(r.last_updated)}</td>
      <td><button class="btn btn--ghost btn--sm" type="button" data-details="${r.product_id}">Details</button></td></tr>`).join("") +
      `</tbody></table></div>`;
  }

  /* ------------------------------------------------------------ details dialog */
  let dlg;
  function openDetails(id) {
    const r = state.raw.find((x) => x.product_id === id);
    if (!r) return;
    if (!dlg) {
      dlg = document.createElement("dialog");
      dlg.className = "sheet sheet--bottom";
      dlg.setAttribute("aria-labelledby", "detTitle");
      document.body.appendChild(dlg);
    }
    const site = MF.safeUrl(r.website), tel = MF.telHref(r.phone);
    const row = (ic, label, val) => val ? `<div style="display:flex;gap:.75rem;padding:.7rem 0;border-top:1px solid var(--line)">${icon(ic)}<div><div class="hint">${label}</div><div>${val}</div></div></div>` : "";
    dlg.innerHTML = `<div class="sheet__form">
      <div class="sheet__head"><h2 id="detTitle">${esc(r.pharmacy)}</h2><button class="btn btn--ghost btn--icon" type="button" data-close-dialog aria-label="Close">${icon("x")}</button></div>
      <div class="sheet__body">
        <p style="color:var(--ink-2)">${esc(r.medicine)}${r.medicine_detail ? " · " + esc(r.medicine_detail) : ""}${r.generic_name ? " (" + esc(r.generic_name) + ")" : ""}</p>
        <div style="display:flex;flex-wrap:wrap;align-items:center;gap:.75rem;margin:.9rem 0">
          ${r.price != null ? `<span class="price">${esc(money(r.price))}</span>` : ""}${statusHTML(r.availability)}${freshnessHTML(r.last_updated)}
        </div>
        ${r.prescription_required ? `<p class="rx-note">${icon("file")}A valid prescription is required.</p>` : ""}
        ${row("pin", "Address", esc(r.address) + (r.distance_km != null ? " · " + esc(distText(r)) + " away" : ""))}
        ${row("clock", "Opening hours", esc(r.opening_hours))}
        ${row("phone", "Phone", tel ? `<a href="${esc(tel)}">${esc(r.phone)}</a>` : "")}
        ${row("globe", "Website", site ? `<a href="${esc(site)}" target="_blank" rel="noopener">${esc(site.replace(/^https?:\/\//, ""))}</a>` : "")}
        <p class="hint" style="margin-top:1rem">Last confirmed ${esc(ago(r.last_updated))}. Stock changes quickly, so call before you travel.</p>
      </div>
      <div class="sheet__foot">
        ${tel ? `<a class="btn btn--secondary" href="${esc(tel)}">${icon("phone")}Call</a>` : ""}
        <a class="btn btn--primary" href="${esc(MF.directionsUrl(r))}" target="_blank" rel="noopener">${icon("navigation")}Directions</a>
      </div></div>`;
    MF.openDialog(dlg);
  }
  $("#resultList").addEventListener("click", (e) => {
    const b = e.target.closest("[data-details]");
    if (b) openDetails(Number(b.dataset.details));
  });

  /* ------------------------------------------------------- API address dialog */
  document.addEventListener("click", (e) => {
    if (e.target.closest("[data-open-connection]")) {
      $("#connInput").value = MF.getBase();
      MF.openDialog($("#connectionDialog"));
    }
  });
  $("#connectionForm").addEventListener("submit", () => {
    MF.setBase($("#connInput").value);
    if (state.q) runSearch(state.q, true);
  });

  /* -------------------------------------------------------------- initial URL */
  const initial = new URLSearchParams(location.search).get("q");
  if (initial) { input.value = initial; runSearch(initial); }
})();
