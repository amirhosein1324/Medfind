/**
 * api.js — thin wrapper around fetch() for the MedFind backend.
 * No build step, no dependencies: plain functions returning parsed JSON
 * (or throwing an Error with the backend's `detail` message on failure).
 */

const MedFindAPI = (() => {
  const STORAGE_KEY_BASE = "medfind_api_base";
  const STORAGE_KEY_TOKEN = "medfind_token";

  function getBase() {
    return localStorage.getItem(STORAGE_KEY_BASE) || "http://127.0.0.1:8000";
  }

  function setBase(url) {
    localStorage.setItem(STORAGE_KEY_BASE, url.replace(/\/+$/, ""));
  }

  function getToken() {
    return localStorage.getItem(STORAGE_KEY_TOKEN);
  }

  function setToken(token) {
    if (token) localStorage.setItem(STORAGE_KEY_TOKEN, token);
    else localStorage.removeItem(STORAGE_KEY_TOKEN);
  }

  async function request(path, { method = "GET", body, form = false, auth = true } = {}) {
    const headers = {};
    if (auth) {
      const token = getToken();
      if (token) headers["Authorization"] = `Bearer ${token}`;
    }

    let payload = body;
    if (body && !form) {
      headers["Content-Type"] = "application/json";
      payload = JSON.stringify(body);
    }

    const res = await fetch(`${getBase()}${path}`, { method, headers, body: payload });

    if (res.status === 204) return null;

    let data = null;
    try {
      data = await res.json();
    } catch (_) {
      // some error responses (network-level) have no JSON body
    }

    if (!res.ok) {
      const message =
        (data && (data.detail || JSON.stringify(data))) || `Request failed (${res.status})`;
      const err = new Error(message);
      err.status = res.status;
      throw err;
    }

    return data;
  }

  return {
    getBase,
    setBase,
    getToken,
    setToken,

    // ---- Auth ----
    login(email, password) {
      const form = new URLSearchParams();
      form.set("username", email);
      form.set("password", password);
      return request("/api/auth/login", { method: "POST", body: form, form: true, auth: false });
    },

    register({ full_name, email, password, role = "pharmacy_owner" }) {
      return request("/api/users/", {
        method: "POST",
        body: { full_name, email, password, role },
        auth: false,
      });
    },

    getMe() {
      return request("/api/users/me");
    },

    // ---- Pharmacies ----
    getMyPharmacies() {
      return request("/api/pharmacies/mine");
    },

    createPharmacy(payload) {
      return request("/api/pharmacies/", { method: "POST", body: payload });
    },

    // ---- Listings ----
    getListings(pharmacyId) {
      return request(`/api/pharmacies/${pharmacyId}/products`);
    },

    addListing(pharmacyId, payload) {
      return request(`/api/pharmacies/${pharmacyId}/products`, {
        method: "POST",
        body: payload,
      });
    },

    updateListing(productId, payload) {
      return request(`/api/pharmacies/products/${productId}`, {
        method: "PATCH",
        body: payload,
      });
    },

    // ---- History ----
    getHistory(pharmacyId) {
      return request(`/api/pharmacies/${pharmacyId}/updates`);
    },
  };
})();
