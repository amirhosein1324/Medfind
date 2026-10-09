/*
 * MedFind web core: settings, API client, session, theme, icons, helpers.
 * Plain browser JavaScript, no build step. Exposes one global: MF.
 */
(function () {
  "use strict";

  const CFG = Object.assign(
    { apiBase: "", currency: "$", staleHours: 48, agingHours: 6 },
    window.MEDFIND_CONFIG || {}
  );

  const KEYS = {
    base: "medfind_api_base",
    token: "medfind_token",
    user: "medfind_user",
    theme: "medfind_theme",
    loc: "medfind_loc",
    recent: "medfind_recent",
  };

  /* ---------------------------------------------------------------- storage */
  const store = {
    get(k) { try { return localStorage.getItem(k); } catch (_) { return null; } },
    set(k, v) {
      try { v == null ? localStorage.removeItem(k) : localStorage.setItem(k, v); } catch (_) { /* private mode */ }
    },
    json(k, fallback) {
      try { const v = JSON.parse(localStorage.getItem(k)); return v == null ? fallback : v; }
      catch (_) { return fallback; }
    },
  };

  /* ------------------------------------------------------------ small utils */
  const $ = (sel, root) => (root || document).querySelector(sel);
  const $$ = (sel, root) => Array.from((root || document).querySelectorAll(sel));

  function esc(value) {
    return String(value == null ? "" : value).replace(/[&<>"']/g, (c) => (
      { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]
    ));
  }

  function debounce(fn, ms) {
    let t;
    return function (...args) { clearTimeout(t); t = setTimeout(() => fn.apply(this, args), ms); };
  }

  /** Only allow http(s) links from user-supplied data (blocks javascript: URLs). */
  function safeUrl(url) {
    try {
      const u = new URL(String(url).trim());
      return u.protocol === "http:" || u.protocol === "https:" ? u.href : null;
    } catch (_) { return null; }
  }

  function telHref(phone) {
    const digits = String(phone || "").replace(/[^\d+]/g, "");
    return digits.length >= 5 ? "tel:" + digits : null;
  }

  function directionsUrl(item) {
    if (item.latitude != null && item.longitude != null) {
      return "https://www.google.com/maps/dir/?api=1&destination=" + item.latitude + "," + item.longitude;
    }
    return "https://www.google.com/maps/search/?api=1&query=" + encodeURIComponent(item.address || item.pharmacy || "");
  }

  function haversineKm(lat1, lon1, lat2, lon2) {
    const R = 6371, rad = (d) => (d * Math.PI) / 180;
    const dLat = rad(lat2 - lat1), dLon = rad(lon2 - lon1);
    const a = Math.sin(dLat / 2) ** 2 + Math.cos(rad(lat1)) * Math.cos(rad(lat2)) * Math.sin(dLon / 2) ** 2;
    return 2 * R * Math.asin(Math.sqrt(a));
  }

  /* ------------------------------------------------------- dates & numbers */
  /** The API returns naive UTC timestamps (no "Z"); treat them as UTC. */
  function parseUTC(s) {
    if (!s) return null;
    const str = String(s);
    const hasTZ = /[zZ]$|[+-]\d\d:?\d\d$/.test(str);
    const d = new Date(hasTZ ? str : str + "Z");
    return isNaN(d) ? null : d;
  }

  function ageHours(s) {
    const d = parseUTC(s);
    return d ? Math.max(0, (Date.now() - d.getTime()) / 36e5) : Infinity;
  }

  function ago(s) {
    const d = parseUTC(s);
    if (!d) return "unknown";
    const sec = Math.max(0, Math.round((Date.now() - d.getTime()) / 1000));
    if (sec < 45) return "just now";
    const m = Math.round(sec / 60);
    if (m < 60) return m + " min ago";
    const h = Math.round(m / 60);
    if (h < 24) return h + (h === 1 ? " hour ago" : " hours ago");
    const days = Math.round(h / 24);
    if (days < 30) return days + (days === 1 ? " day ago" : " days ago");
    return d.toLocaleDateString();
  }

  /** Maps listing age to the freshness meter: tier colour + lit bars (1-5). */
  function freshness(hours) {
    if (hours <= 1) return { tier: "fresh", bars: 5 };
    if (hours <= CFG.agingHours) return { tier: "fresh", bars: 4 };
    if (hours <= 24) return { tier: "aging", bars: 3 };
    if (hours <= CFG.staleHours) return { tier: "aging", bars: 2 };
    return { tier: "stale", bars: 1 };
  }

  function freshnessHTML(updatedAt) {
    const h = ageHours(updatedAt);
    const f = freshness(h);
    const bars = [1, 2, 3, 4, 5].map((n) => `<i class="${n <= f.bars ? "on" : ""}"></i>`).join("");
    return `<span class="fresh" data-tier="${f.tier}" title="Last updated ${esc(ago(updatedAt))}">
      <span class="fresh__bars" aria-hidden="true">${bars}</span>
      <span class="fresh__text">Updated ${esc(ago(updatedAt))}</span></span>`;
  }

  function money(v) {
    if (v == null || v === "") return "";
    const n = Number(v);
    return isNaN(n) ? "" : CFG.currency + n.toFixed(2);
  }

  /* ------------------------------------------------------------------ icons */
  const ICON = {
    search: '<circle cx="11" cy="11" r="7"/><path d="m20 20-3.5-3.5"/>',
    pin: '<path d="M12 21s-7-6.2-7-11a7 7 0 0 1 14 0c0 4.8-7 11-7 11z"/><circle cx="12" cy="10" r="2.5"/>',
    locate: '<circle cx="12" cy="12" r="3"/><circle cx="12" cy="12" r="7.5"/><path d="M12 2v2.5M12 19.5V22M2 12h2.5M19.5 12H22"/>',
    phone: '<path d="M5 4h4l2 5-2.5 1.5a11 11 0 0 0 5 5L15 13l5 2v4a2 2 0 0 1-2 2A15 15 0 0 1 3 6a2 2 0 0 1 2-2z"/>',
    clock: '<circle cx="12" cy="12" r="9"/><path d="M12 7v5l3 2"/>',
    check: '<path d="m5 12.5 4.5 4.5L19 7.5"/>',
    "check-circle": '<circle cx="12" cy="12" r="9"/><path d="m8 12.5 2.8 2.8L16 9.5"/>',
    "minus-circle": '<circle cx="12" cy="12" r="9"/><path d="M8 12h8"/>',
    "x-circle": '<circle cx="12" cy="12" r="9"/><path d="m9 9 6 6M15 9l-6 6"/>',
    "help-circle": '<circle cx="12" cy="12" r="9"/><path d="M9.5 9.5a2.5 2.5 0 1 1 3.5 2.3c-.7.4-1 .9-1 1.7M12 16.8v.1"/>',
    shield: '<path d="M12 3 5 6v5.5c0 4.2 2.8 7.6 7 9.5 4.2-1.9 7-5.3 7-9.5V6z"/><path d="m9 12 2.2 2.2L15.5 10"/>',
    alert: '<path d="M12 3.5 2.8 19.5h18.4z"/><path d="M12 10v4M12 17v.1"/>',
    x: '<path d="M6 6l12 12M18 6 6 18"/>',
    plus: '<path d="M12 5v14M5 12h14"/>',
    sun: '<circle cx="12" cy="12" r="4"/><path d="M12 2.5v2M12 19.5v2M2.5 12h2M19.5 12h2M5.3 5.3l1.4 1.4M17.3 17.3l1.4 1.4M5.3 18.7l1.4-1.4M17.3 6.7l1.4-1.4"/>',
    moon: '<path d="M20 14.5A8.5 8.5 0 1 1 9.5 4a7 7 0 0 0 10.5 10.5z"/>',
    sliders: '<path d="M4 7h9M17 7h3M4 17h3M11 17h9"/><circle cx="15" cy="7" r="2"/><circle cx="9" cy="17" r="2"/>',
    navigation: '<path d="m4 11 16-7-7 16-2-7z"/>',
    external: '<path d="M14 4h6v6M20 4l-9 9M18 14v5a1 1 0 0 1-1 1H5a1 1 0 0 1-1-1V7a1 1 0 0 1 1-1h5"/>',
    chevron: '<path d="m6 9 6 6 6-6"/>',
    upload: '<path d="M12 16V4M7 9l5-5 5 5M4 16v3a1 1 0 0 0 1 1h14a1 1 0 0 0 1-1v-3"/>',
    download: '<path d="M12 4v12M7 11l5 5 5-5M4 16v3a1 1 0 0 0 1 1h14a1 1 0 0 0 1-1v-3"/>',
    refresh: '<path d="M20 11a8 8 0 0 0-14.5-4M4 4v4h4M4 13a8 8 0 0 0 14.5 4M20 20v-4h-4"/>',
    store: '<path d="M4 9.5 5.5 4h13L20 9.5M4 9.5a2.5 2.5 0 0 0 5 0 2.5 2.5 0 0 0 5 0 2.5 2.5 0 0 0 5 0M5.5 12.5V20h13v-7.5M10 20v-4.5h4V20"/>',
    cards: '<rect x="4" y="4" width="16" height="7" rx="2"/><rect x="4" y="13" width="16" height="7" rx="2"/>',
    table: '<rect x="3.5" y="5" width="17" height="14" rx="2"/><path d="M3.5 10h17M9.5 5v14"/>',
    user: '<circle cx="12" cy="8" r="4"/><path d="M4 21a8 8 0 0 1 16 0"/>',
    logout: '<path d="M9 4H5a1 1 0 0 0-1 1v14a1 1 0 0 0 1 1h4M16 8l4 4-4 4M20 12H9"/>',
    globe: '<circle cx="12" cy="12" r="9"/><path d="M3 12h18M12 3c3 3.2 3 14.8 0 18M12 3c-3 3.2-3 14.8 0 18"/>',
    inbox: '<path d="M4 13 6.5 5h11L20 13v6H4zM4 13h5l1 2h4l1-2h5"/>',
    file: '<path d="M7 3h7l5 5v13H7zM14 3v5h5M10 13h6M10 17h6"/>',
    pill: '<rect x="2.5" y="8.5" width="19" height="7" rx="3.5" transform="rotate(-40 12 12)"/><path d="m9.2 7.8 7 8.4"/>',
    layers: '<path d="m12 3 9 5-9 5-9-5zM3 13l9 5 9-5M3 17.5l9 5 9-5"/>',
    users: '<circle cx="9" cy="8" r="3.5"/><path d="M2.5 20a6.5 6.5 0 0 1 13 0M16 4.8a3.5 3.5 0 0 1 0 6.4M18 14a6 6 0 0 1 3.5 6"/>',
    book: '<path d="M5 4h10a3 3 0 0 1 3 3v13H8a3 3 0 0 1-3-3zM5 17a3 3 0 0 1 3-3h10"/>',
  };

  function icon(name, cls) {
    return `<svg class="icon${cls ? " " + cls : ""}" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true" focusable="false">${ICON[name] || ""}</svg>`;
  }

  const LOGO = `<svg class="logo" viewBox="0 0 32 32" aria-hidden="true" focusable="false"><rect width="32" height="32" rx="9" fill="var(--brand)"/><g transform="rotate(-45 16 16)"><rect x="6" y="11.25" width="20" height="9.5" rx="4.75" fill="none" stroke="var(--on-brand)" stroke-width="2"/><path d="M16 11.25h5.25a4.75 4.75 0 0 1 0 9.5H16z" fill="var(--on-brand)"/></g></svg>`;

  const STATUS = {
    available: { label: "Available", icon: "check-circle" },
    limited_stock: { label: "Limited stock", icon: "minus-circle" },
    out_of_stock: { label: "Out of stock", icon: "x-circle" },
    unknown: { label: "Not confirmed", icon: "help-circle" },
  };

  function statusHTML(key) {
    const s = STATUS[key] || STATUS.unknown;
    return `<span class="status" data-s="${esc(key in STATUS ? key : "unknown")}">${icon(s.icon)}<span>${s.label}</span></span>`;
  }

  /* ---------------------------------------------------------------- toasts */
  let toastRegion;
  function toast(message, kind) {
    if (!toastRegion) {
      toastRegion = document.createElement("div");
      toastRegion.className = "toasts";
      toastRegion.setAttribute("role", "status");
      toastRegion.setAttribute("aria-live", "polite");
      document.body.appendChild(toastRegion);
    }
    const el = document.createElement("div");
    el.className = "toast" + (kind ? " toast--" + kind : "");
    el.textContent = message;
    toastRegion.appendChild(el);
    setTimeout(() => { el.classList.add("out"); setTimeout(() => el.remove(), 250); }, kind === "error" ? 5200 : 2800);
  }

  /* ------------------------------------------------------------ API client */
  function defaultBase() {
    if (CFG.apiBase) return CFG.apiBase;
    if (location.protocol.indexOf("http") === 0 && location.pathname.indexOf("/app") === 0) return location.origin;
    return "http://127.0.0.1:8000";
  }
  const getBase = () => (store.get(KEYS.base) || defaultBase()).replace(/\/+$/, "");
  const setBase = (url) => store.set(KEYS.base, url ? String(url).trim().replace(/\/+$/, "") : null);

  function qs(params) {
    const p = new URLSearchParams();
    Object.keys(params || {}).forEach((k) => {
      const v = params[k];
      if (v !== undefined && v !== null && v !== "") p.set(k, v);
    });
    const s = p.toString();
    return s ? "?" + s : "";
  }

  async function request(path, opts) {
    const o = Object.assign({ method: "GET", auth: true }, opts || {});
    const headers = {};
    if (o.auth) {
      const t = store.get(KEYS.token);
      if (t) headers.Authorization = "Bearer " + t;
    }
    let payload = o.body;
    if (o.body && !o.form) {
      headers["Content-Type"] = "application/json";
      payload = JSON.stringify(o.body);
    }

    let res;
    try {
      res = await fetch(getBase() + path, { method: o.method, headers, body: payload, signal: o.signal });
    } catch (e) {
      if (e && e.name === "AbortError") throw e;
      const err = new Error("Can't reach the MedFind API at " + getBase() + ". Is the server running?");
      err.network = true;
      throw err;
    }

    if (res.status === 204) return null;
    let data = null;
    try { data = await res.json(); } catch (_) { /* no body */ }

    if (!res.ok) {
      let msg = data && data.detail;
      if (Array.isArray(msg)) {
        msg = msg.map((d) => (d.loc ? d.loc[d.loc.length - 1] + ": " : "") + d.msg).join("; ");
      }
      const err = new Error(msg || "Request failed (" + res.status + ")");
      err.status = res.status;
      throw err;
    }
    return data;
  }

  const post = (path, body) => request(path, { method: "POST", body });
  const patch = (path, body) => request(path, { method: "PATCH", body });

  const api = {
    login(email, password) {
      const f = new URLSearchParams();
      f.set("username", email);
      f.set("password", password);
      return request("/api/auth/login", { method: "POST", body: f, form: true, auth: false });
    },
    register: (body) => request("/api/users/", { method: "POST", body, auth: false }),
    me: () => request("/api/users/me"),
    users: () => request("/api/users/"),

    medicines: (q, signal) => request("/api/medicines/" + qs({ q }), { signal }),
    createMedicine: (b) => post("/api/medicines/", b),
    aliases: (id) => request("/api/medicines/" + id + "/aliases"),
    addAlias: (id, b) => post("/api/medicines/" + id + "/aliases", b),
    categories: () => request("/api/medicines/categories"),
    createCategory: (b) => post("/api/medicines/categories", b),

    search: (params, signal) => request("/api/search/" + qs(params), { signal, auth: false }),

    myPharmacies: () => request("/api/pharmacies/mine"),
    createPharmacy: (b) => post("/api/pharmacies/", b),
    listings: (pid) => request("/api/pharmacies/" + pid + "/products"),
    addListing: (pid, b) => post("/api/pharmacies/" + pid + "/products", b),
    updateListing: (id, b) => patch("/api/pharmacies/products/" + id, b),
    confirmListing: (id) => post("/api/pharmacies/products/" + id + "/confirm"),
    confirmAll: (pid) => post("/api/pharmacies/" + pid + "/confirm-all"),
    history: (pid) => request("/api/pharmacies/" + pid + "/updates"),

    adminPharmacies: (status) => request("/api/pharmacies/admin/all" + qs({ status })),
    approve: (id) => patch("/api/pharmacies/" + id + "/approve"),
    revoke: (id) => patch("/api/pharmacies/" + id + "/revoke"),
  };

  /* --------------------------------------------------------------- session */
  const session = {
    token: () => store.get(KEYS.token),
    user: () => store.json(KEYS.user, null),
    set(token, user) { store.set(KEYS.token, token); store.set(KEYS.user, JSON.stringify(user)); },
    clear() { store.set(KEYS.token, null); store.set(KEYS.user, null); },
  };

  function homeFor(role) {
    return role === "admin" ? "admin.html" : role === "pharmacy_owner" ? "dashboard.html" : "index.html";
  }

  function goToLogin() {
    const here = location.pathname.split("/").pop() || "index.html";
    location.replace("login.html?next=" + encodeURIComponent(here + location.search));
  }

  /** Redirects to login (or the right home page) unless the user has an allowed role. */
  async function requireRole(roles) {
    if (!session.token()) { goToLogin(); return null; }
    try {
      const me = await api.me();
      session.set(session.token(), me);
      if (roles.indexOf(me.role) === -1) { location.replace(homeFor(me.role)); return null; }
      return me;
    } catch (e) {
      if (e.network) throw e;
      session.clear();
      goToLogin();
      return null;
    }
  }

  function logout() {
    session.clear();
    location.href = "index.html";
  }

  /* ----------------------------------------------------------------- theme */
  function currentTheme() { return document.documentElement.dataset.theme === "dark" ? "dark" : "light"; }
  function setTheme(t) {
    document.documentElement.dataset.theme = t;
    store.set(KEYS.theme, t);
    $$("[data-theme-toggle]").forEach((b) => b.setAttribute("aria-label", t === "dark" ? "Switch to light theme" : "Switch to dark theme"));
  }
  document.addEventListener("click", (e) => {
    const b = e.target.closest("[data-theme-toggle]");
    if (b) setTheme(currentTheme() === "dark" ? "light" : "dark");
  });

  /* ------------------------------------------------------------------- nav */
  function renderNav(active) {
    const host = document.getElementById("siteNav");
    if (!host) return;
    const user = session.user();
    const loggedIn = !!(session.token() && user);

    const links = [{ href: "index.html", label: "Find medicine", key: "search" }];
    if (loggedIn && user.role === "pharmacy_owner") links.push({ href: "dashboard.html", label: "My pharmacy", key: "dashboard" });
    if (loggedIn && user.role === "admin") links.push({ href: "admin.html", label: "Admin", key: "admin" });
    if (!loggedIn) links.push({ href: "login.html?mode=register&role=pharmacy_owner", label: "For pharmacies", key: "pharmacies" });

    const account = loggedIn
      ? `<span class="nav__user">${esc(user.full_name || user.email)}</span>
         <button class="btn btn--ghost btn--sm" type="button" data-logout>${icon("logout")}<span>Log out</span></button>`
      : `<a class="btn btn--primary btn--sm" href="login.html">Log in</a>`;

    host.className = "nav";
    host.innerHTML = `<div class="nav__inner wrap">
      <a class="brand" href="index.html" aria-label="MedFind home">${LOGO}<span class="brand__name">MedFind</span></a>
      <nav class="nav__links" aria-label="Main">
        ${links.map((l) => `<a href="${l.href}"${l.key === active ? ' aria-current="page"' : ""}>${esc(l.label)}</a>`).join("")}
      </nav>
      <div class="nav__actions">
        <button class="btn btn--ghost btn--icon" type="button" data-theme-toggle aria-label="Switch theme">${icon("moon", "i-moon")}${icon("sun", "i-sun")}</button>
        ${account}
      </div>
    </div>`;
    const lo = host.querySelector("[data-logout]");
    if (lo) lo.addEventListener("click", logout);
    setTheme(currentTheme());
  }

  /* --------------------------------------------------------------- dialogs */
  function openDialog(dlg) {
    if (!dlg.open) dlg.showModal();
    const first = dlg.querySelector("[autofocus], input:not([type=hidden]), select, textarea, button.btn--primary");
    if (first && typeof first.focus === "function") first.focus();
  }
  function closeDialog(dlg) { if (dlg && dlg.open) dlg.close(); }

  document.addEventListener("click", (e) => {
    const closer = e.target.closest("[data-close-dialog]");
    if (closer) { closeDialog(closer.closest("dialog")); return; }
    if (e.target instanceof HTMLDialogElement && e.target.classList.contains("sheet")) {
      const r = e.target.getBoundingClientRect();
      const inside = e.clientX >= r.left && e.clientX <= r.right && e.clientY >= r.top && e.clientY <= r.bottom;
      if (!inside) closeDialog(e.target); // click on the backdrop
    }
  });

  /* -------------------------------------------------------------- combobox */
  /**
   * Accessible type-ahead. fetch(q) -> Promise<items[]>; render(item) -> inner HTML;
   * onPick(item) is called when the user chooses an option (click or Enter).
   */
  function combobox(cfg) {
    const input = cfg.input, list = cfg.list;
    const minChars = cfg.minChars == null ? 1 : cfg.minChars;
    let items = [], active = -1, seq = 0;
    if (!list.id) list.id = "cb" + Math.random().toString(36).slice(2, 8);

    input.setAttribute("role", "combobox");
    input.setAttribute("aria-autocomplete", "list");
    input.setAttribute("aria-expanded", "false");
    input.setAttribute("aria-controls", list.id);
    list.setAttribute("role", "listbox");
    list.hidden = true;

    function close() {
      list.hidden = true;
      active = -1;
      input.setAttribute("aria-expanded", "false");
      input.removeAttribute("aria-activedescendant");
    }
    function open() { list.hidden = false; input.setAttribute("aria-expanded", "true"); }
    function paint() {
      list.innerHTML = items.map((it, i) =>
        `<li role="option" id="${list.id}-${i}" data-i="${i}" aria-selected="${i === active}">${cfg.render(it)}</li>`).join("");
      if (items.length) open(); else close();
    }
    function setActive(i) {
      active = (i + items.length) % items.length;
      Array.from(list.children).forEach((li, idx) => li.setAttribute("aria-selected", String(idx === active)));
      input.setAttribute("aria-activedescendant", list.id + "-" + active);
      list.children[active].scrollIntoView({ block: "nearest" });
    }
    function pick(i) { const it = items[i]; close(); if (it) cfg.onPick(it); }

    const run = debounce(async () => {
      const q = input.value.trim();
      if (q.length < minChars) { items = []; paint(); return; }
      const my = ++seq;
      try {
        const res = await cfg.fetch(q);
        if (my !== seq) return;
        items = res || [];
        active = -1;
        paint();
      } catch (_) { items = []; paint(); }
    }, 160);

    input.addEventListener("input", run);
    input.addEventListener("focus", () => { if (items.length) open(); });
    input.addEventListener("keydown", (e) => {
      if (e.key === "ArrowDown" && items.length) { e.preventDefault(); if (list.hidden) open(); setActive(active + 1); }
      else if (e.key === "ArrowUp" && items.length) { e.preventDefault(); setActive(active - 1); }
      else if (e.key === "Enter" && active >= 0 && !list.hidden) { e.preventDefault(); pick(active); }
      else if (e.key === "Escape") { close(); }
    });
    list.addEventListener("mousedown", (e) => {
      const li = e.target.closest("li[data-i]");
      if (!li) return;
      e.preventDefault();
      pick(Number(li.dataset.i));
    });
    document.addEventListener("click", (e) => {
      if (e.target !== input && !list.contains(e.target)) close();
    });
    return { close, reset() { items = []; paint(); } };
  }

  window.MF = {
    CFG, KEYS, store, $, $$, esc, debounce, safeUrl, telHref, directionsUrl, haversineKm,
    parseUTC, ageHours, ago, freshness, freshnessHTML, money,
    icon, LOGO, STATUS, statusHTML, toast,
    api, getBase, setBase, session, homeFor, requireRole, logout, goToLogin,
    renderNav, setTheme, currentTheme, openDialog, closeDialog, combobox,
  };
})();
