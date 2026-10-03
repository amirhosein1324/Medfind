/**
 * app.js — page logic for the MedFind pharmacy dashboard.
 * No framework: plain DOM rendering driven by a small state object.
 */

(() => {
  "use strict";

  const state = {
    user: null,
    pharmacies: [],
    activePharmacyId: null,
    listings: [],
    history: [],
    listingFilter: "",
  };

  // ---------- Element refs ----------
  const el = {
    configBar: document.getElementById("configBar"),
    apiBaseInput: document.getElementById("apiBaseInput"),
    apiBaseSave: document.getElementById("apiBaseSave"),

    loginScreen: document.getElementById("loginScreen"),
    loginForm: document.getElementById("loginForm"),
    loginEmail: document.getElementById("loginEmail"),
    loginPassword: document.getElementById("loginPassword"),
    loginError: document.getElementById("loginError"),
    showRegister: document.getElementById("showRegister"),

    registerForm: document.getElementById("registerForm"),
    regName: document.getElementById("regName"),
    regEmail: document.getElementById("regEmail"),
    regPassword: document.getElementById("regPassword"),
    registerError: document.getElementById("registerError"),
    registerSuccess: document.getElementById("registerSuccess"),
    showLogin: document.getElementById("showLogin"),

    appScreen: document.getElementById("appScreen"),
    userName: document.getElementById("userName"),
    logoutBtn: document.getElementById("logoutBtn"),

    mobileSwitcher: document.getElementById("mobileSwitcher"),
    mobilePharmacySelect: document.getElementById("mobilePharmacySelect"),

    pharmacyList: document.getElementById("pharmacyList"),
    newPharmacyBtn: document.getElementById("newPharmacyBtn"),
    emptyNewPharmacyBtn: document.getElementById("emptyNewPharmacyBtn"),

    noPharmacyState: document.getElementById("noPharmacyState"),
    pharmacyPanel: document.getElementById("pharmacyPanel"),
    activePharmacyName: document.getElementById("activePharmacyName"),
    activePharmacyMeta: document.getElementById("activePharmacyMeta"),
    approvalFlag: document.getElementById("approvalFlag"),

    listingSearch: document.getElementById("listingSearch"),
    addListingBtn: document.getElementById("addListingBtn"),
    listingsBody: document.getElementById("listingsBody"),
    listingsEmpty: document.getElementById("listingsEmpty"),

    historyList: document.getElementById("historyList"),
    historyEmpty: document.getElementById("historyEmpty"),

    modalBackdrop: document.getElementById("modalBackdrop"),
    newPharmacyModal: document.getElementById("newPharmacyModal"),
    npName: document.getElementById("npName"),
    npAddress: document.getElementById("npAddress"),
    npLat: document.getElementById("npLat"),
    npLng: document.getElementById("npLng"),
    newPharmacyError: document.getElementById("newPharmacyError"),

    addListingModal: document.getElementById("addListingModal"),
    alMedicineId: document.getElementById("alMedicineId"),
    alPrice: document.getElementById("alPrice"),
    alStock: document.getElementById("alStock"),
    alStatus: document.getElementById("alStatus"),
    addListingError: document.getElementById("addListingError"),

    toast: document.getElementById("toast"),
  };

  // ---------- Toast ----------
  let toastTimer = null;
  function showToast(message) {
    el.toast.textContent = message;
    el.toast.classList.add("visible");
    clearTimeout(toastTimer);
    toastTimer = setTimeout(() => el.toast.classList.remove("visible"), 2600);
  }

  function friendlyError(err) {
    return err && err.message ? err.message : "Something went wrong. Please try again.";
  }

  // ---------- Modal helpers ----------
  function openModal(modalEl) {
    el.modalBackdrop.hidden = false;
    modalEl.hidden = false;
    const firstField = modalEl.querySelector("input, select");
    if (firstField) firstField.focus();
  }
  function closeModals() {
    el.modalBackdrop.hidden = true;
    el.newPharmacyModal.hidden = true;
    el.addListingModal.hidden = true;
    el.newPharmacyError.textContent = "";
    el.addListingError.textContent = "";
  }
  document.querySelectorAll("[data-close-modal]").forEach((btn) =>
    btn.addEventListener("click", closeModals)
  );
  el.modalBackdrop.addEventListener("click", (e) => {
    if (e.target === el.modalBackdrop) closeModals();
  });

  // ---------- View switching ----------
  function showLoginView() {
    el.loginScreen.hidden = false;
    el.appScreen.hidden = true;
  }
  function showAppView() {
    el.loginScreen.hidden = true;
    el.appScreen.hidden = false;
  }

  el.showRegister.addEventListener("click", () => {
    el.loginForm.hidden = true;
    el.registerForm.hidden = false;
  });
  el.showLogin.addEventListener("click", () => {
    el.registerForm.hidden = true;
    el.loginForm.hidden = false;
  });

  // ---------- Config bar ----------
  el.apiBaseInput.value = MedFindAPI.getBase();
  el.apiBaseSave.addEventListener("click", () => {
    MedFindAPI.setBase(el.apiBaseInput.value.trim());
    showToast("API base URL saved.");
  });

  // ---------- Auth ----------
  el.loginForm.addEventListener("submit", async (e) => {
    e.preventDefault();
    el.loginError.textContent = "";
    try {
      const { access_token } = await MedFindAPI.login(
        el.loginEmail.value.trim(),
        el.loginPassword.value
      );
      MedFindAPI.setToken(access_token);
      await bootstrapApp();
    } catch (err) {
      el.loginError.textContent = friendlyError(err);
    }
  });

  el.registerForm.addEventListener("submit", async (e) => {
    e.preventDefault();
    el.registerError.textContent = "";
    el.registerSuccess.textContent = "";
    try {
      await MedFindAPI.register({
        full_name: el.regName.value.trim(),
        email: el.regEmail.value.trim(),
        password: el.regPassword.value,
      });
      el.registerSuccess.textContent = "Account created. You can log in now.";
      el.registerForm.reset();
      setTimeout(() => {
        el.registerForm.hidden = true;
        el.loginForm.hidden = false;
        el.registerSuccess.textContent = "";
      }, 1200);
    } catch (err) {
      el.registerError.textContent = friendlyError(err);
    }
  });

  el.logoutBtn.addEventListener("click", () => {
    MedFindAPI.setToken(null);
    state.user = null;
    state.pharmacies = [];
    state.activePharmacyId = null;
    showLoginView();
  });

  // ---------- Pharmacy rendering ----------
  function renderPharmacyList() {
    el.pharmacyList.innerHTML = "";
    el.mobilePharmacySelect.innerHTML = "";

    state.pharmacies.forEach((pharmacy) => {
      const li = document.createElement("li");
      const btn = document.createElement("button");
      btn.type = "button";
      btn.className = "rail-item" + (pharmacy.pharmacy_id === state.activePharmacyId ? " active" : "");
      btn.innerHTML = `${escapeHtml(pharmacy.name)}<span class="pharmacy-status">${
        pharmacy.is_approved ? "active" : "pending approval"
      }</span>`;
      btn.addEventListener("click", () => selectPharmacy(pharmacy.pharmacy_id));
      li.appendChild(btn);
      el.pharmacyList.appendChild(li);

      const opt = document.createElement("option");
      opt.value = pharmacy.pharmacy_id;
      opt.textContent = pharmacy.name;
      opt.selected = pharmacy.pharmacy_id === state.activePharmacyId;
      el.mobilePharmacySelect.appendChild(opt);
    });
  }

  el.mobilePharmacySelect.addEventListener("change", () => {
    selectPharmacy(Number(el.mobilePharmacySelect.value));
  });

  async function selectPharmacy(pharmacyId) {
    state.activePharmacyId = pharmacyId;
    renderPharmacyList();
    await loadPharmacyDetail();
  }

  function activePharmacy() {
    return state.pharmacies.find((p) => p.pharmacy_id === state.activePharmacyId) || null;
  }

  async function loadPharmacyDetail() {
    const pharmacy = activePharmacy();
    if (!pharmacy) {
      el.noPharmacyState.hidden = false;
      el.pharmacyPanel.hidden = true;
      return;
    }

    el.noPharmacyState.hidden = true;
    el.pharmacyPanel.hidden = false;

    el.activePharmacyName.textContent = pharmacy.name;
    el.activePharmacyMeta.textContent = pharmacy.address;
    el.approvalFlag.textContent = pharmacy.is_approved ? "Approved" : "Pending approval";
    el.approvalFlag.className = "status-flag " + (pharmacy.is_approved ? "ok" : "pending");

    try {
      const [listings, history] = await Promise.all([
        MedFindAPI.getListings(pharmacy.pharmacy_id),
        MedFindAPI.getHistory(pharmacy.pharmacy_id).catch(() => []), // non-fatal if it 403s for some reason
      ]);
      state.listings = listings;
      state.history = history;
      renderListings();
      renderHistory();
    } catch (err) {
      showToast(friendlyError(err));
    }
  }

  // ---------- Listings table ----------
  const STATUS_LABEL = {
    available: "available",
    limited_stock: "limited stock",
    out_of_stock: "out of stock",
    unknown: "unknown",
  };

  function formatPrice(price) {
    return price === null || price === undefined ? "—" : Number(price).toFixed(2);
  }

  el.listingSearch.addEventListener("input", () => {
    state.listingFilter = el.listingSearch.value.trim().toLowerCase();
    renderListings();
  });

  function renderListings() {
    const filtered = state.listings.filter((item) =>
      !state.listingFilter || (item.medicine_name || `#${item.medicine_id}`).toLowerCase().includes(state.listingFilter)
    );

    el.listingsBody.innerHTML = "";
    el.listingsEmpty.hidden = state.listings.length !== 0;

    filtered.forEach((item) => {
      const tr = document.createElement("tr");
      tr.dataset.productId = item.product_id;

      const nameTd = document.createElement("td");
      nameTd.textContent = item.medicine_name || `Medicine #${item.medicine_id}`;

      const priceTd = buildEditableCell(item, "price", formatPrice(item.price));
      const stockTd = buildEditableCell(
        item,
        "stock_quantity",
        item.stock_quantity === null || item.stock_quantity === undefined ? "—" : item.stock_quantity
      );

      const statusTd = document.createElement("td");
      const select = document.createElement("select");
      select.className = "status-select status-" + item.availability_status;
      Object.entries(STATUS_LABEL).forEach(([value, label]) => {
        const opt = document.createElement("option");
        opt.value = value;
        opt.textContent = label;
        opt.selected = value === item.availability_status;
        select.appendChild(opt);
      });
      select.addEventListener("change", () =>
        saveListingChange(item.product_id, { availability_status: select.value }, tr)
      );
      statusTd.appendChild(select);

      tr.append(nameTd, priceTd, stockTd, statusTd);
      el.listingsBody.appendChild(tr);
    });
  }

  function buildEditableCell(item, field, displayValue) {
    const td = document.createElement("td");
    td.className = "num-col";

    const span = document.createElement("button");
    span.type = "button";
    span.className = "editable-cell";
    span.textContent = displayValue;
    span.setAttribute("aria-label", `Edit ${field.replace("_", " ")} for ${item.medicine_name || "listing"}`);

    span.addEventListener("click", () => {
      const input = document.createElement("input");
      input.type = "number";
      input.step = field === "price" ? "0.01" : "1";
      input.min = "0";
      input.value = field === "price" ? (item.price ?? "") : (item.stock_quantity ?? "");

      td.innerHTML = "";
      td.appendChild(input);
      input.focus();
      input.select();

      const commit = () => {
        const raw = input.value.trim();
        const value = raw === "" ? null : Number(raw);
        const tr = td.closest("tr");
        saveListingChange(item.product_id, { [field]: value }, tr);
      };

      input.addEventListener("blur", commit);
      input.addEventListener("keydown", (e) => {
        if (e.key === "Enter") input.blur();
        if (e.key === "Escape") renderListings();
      });
    });

    td.appendChild(span);
    return td;
  }

  async function saveListingChange(productId, patch, rowEl) {
    try {
      const updated = await MedFindAPI.updateListing(productId, patch);
      const idx = state.listings.findIndex((l) => l.product_id === productId);
      if (idx !== -1) state.listings[idx] = { ...state.listings[idx], ...updated };
      renderListings();

      const newRow = el.listingsBody.querySelector(`tr[data-product-id="${productId}"]`);
      if (newRow) {
        newRow.classList.add("row-saved");
        newRow.addEventListener("animationend", () => newRow.classList.remove("row-saved"), { once: true });
      }
      showToast("Saved.");
      loadPharmacyHistoryOnly();
    } catch (err) {
      showToast(friendlyError(err));
      renderListings();
    }
  }

  async function loadPharmacyHistoryOnly() {
    const pharmacy = activePharmacy();
    if (!pharmacy) return;
    try {
      state.history = await MedFindAPI.getHistory(pharmacy.pharmacy_id);
      renderHistory();
    } catch (_) {
      /* non-fatal */
    }
  }

  // ---------- History ----------
  function describeChange(item) {
    const parts = [];
    if (item.old_price !== item.new_price) {
      parts.push(`price ${formatPrice(item.old_price)} → ${formatPrice(item.new_price)}`);
    }
    if (item.old_stock !== item.new_stock) {
      parts.push(`stock ${item.old_stock ?? "—"} → ${item.new_stock ?? "—"}`);
    }
    if (item.old_status !== item.new_status) {
      parts.push(`${STATUS_LABEL[item.old_status] || item.old_status} → ${STATUS_LABEL[item.new_status] || item.new_status}`);
    }
    return parts.join(", ") || "updated";
  }

  function renderHistory() {
    el.historyList.innerHTML = "";
    el.historyEmpty.hidden = state.history.length !== 0;

    state.history.forEach((item) => {
      const li = document.createElement("li");
      li.className = "history-item";
      const time = new Date(item.updated_at);
      const timeStr = isNaN(time) ? "" : time.toLocaleString([], { dateStyle: "short", timeStyle: "short" });
      li.innerHTML = `<span class="history-time">${timeStr}</span><span>${escapeHtml(
        item.medicine_name
      )} — <span class="history-change">${escapeHtml(describeChange(item))}</span></span>`;
      el.historyList.appendChild(li);
    });
  }

  // ---------- New pharmacy ----------
  function openNewPharmacyModal() {
    el.newPharmacyModal.reset();
    el.newPharmacyError.textContent = "";
    openModal(el.newPharmacyModal);
  }
  el.newPharmacyBtn.addEventListener("click", openNewPharmacyModal);
  el.emptyNewPharmacyBtn.addEventListener("click", openNewPharmacyModal);

  el.newPharmacyModal.addEventListener("submit", async (e) => {
    e.preventDefault();
    el.newPharmacyError.textContent = "";
    try {
      const payload = {
        name: el.npName.value.trim(),
        address: el.npAddress.value.trim(),
      };
      if (el.npLat.value) payload.latitude = Number(el.npLat.value);
      if (el.npLng.value) payload.longitude = Number(el.npLng.value);

      const pharmacy = await MedFindAPI.createPharmacy(payload);
      state.pharmacies.push(pharmacy);
      closeModals();
      await selectPharmacy(pharmacy.pharmacy_id);
      showToast("Pharmacy created — pending admin approval.");
    } catch (err) {
      el.newPharmacyError.textContent = friendlyError(err);
    }
  });

  // ---------- Add listing ----------
  el.addListingBtn.addEventListener("click", () => {
    el.addListingModal.reset();
    el.addListingError.textContent = "";
    openModal(el.addListingModal);
  });

  el.addListingModal.addEventListener("submit", async (e) => {
    e.preventDefault();
    el.addListingError.textContent = "";
    const pharmacy = activePharmacy();
    if (!pharmacy) return;

    try {
      const payload = {
        medicine_id: Number(el.alMedicineId.value),
        availability_status: el.alStatus.value,
      };
      if (el.alPrice.value) payload.price = Number(el.alPrice.value);
      if (el.alStock.value) payload.stock_quantity = Number(el.alStock.value);

      await MedFindAPI.addListing(pharmacy.pharmacy_id, payload);
      closeModals();
      await loadPharmacyDetail();
      showToast("Listing added.");
    } catch (err) {
      el.addListingError.textContent = friendlyError(err);
    }
  });

  // ---------- Bootstrap ----------
  async function bootstrapApp() {
    try {
      state.user = await MedFindAPI.getMe();
      el.userName.textContent = state.user.full_name;

      state.pharmacies = await MedFindAPI.getMyPharmacies();
      state.activePharmacyId = state.pharmacies.length ? state.pharmacies[0].pharmacy_id : null;

      renderPharmacyList();
      showAppView();
      await loadPharmacyDetail();
    } catch (err) {
      MedFindAPI.setToken(null);
      showLoginView();
      el.loginError.textContent = "Session expired. Please log in again.";
    }
  }

  function escapeHtml(str) {
    const div = document.createElement("div");
    div.textContent = str ?? "";
    return div.innerHTML;
  }

  // ---------- Init ----------
  (async function init() {
    if (MedFindAPI.getToken()) {
      await bootstrapApp();
    } else {
      showLoginView();
    }
  })();
})();
