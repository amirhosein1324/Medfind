(function () {
  "use strict";
  const { $, icon, api, session } = MF;
  MF.renderNav("");

  const qp = new URLSearchParams(location.search);
  const next = qp.get("next");
  const safeNext = next && /^[\w./-]+\.html([?#].*)?$/.test(next) ? next : null;

  const POINTS = {
    pharmacy_owner: ["Appear in search the moment an admin approves you", "Update price and stock in a few clicks", "Show customers exactly when you last confirmed"],
    customer: ["Compare price and distance across pharmacies", "See how fresh every listing is", "No account needed just to search"],
  };
  function pitch(role) {
    const owner = role === "pharmacy_owner";
    $("#pitchTitle").textContent = owner ? "Put your stock in front of people who need it" : "Find your medicine without the phone calls";
    $("#pitchText").textContent = owner ? "Create a pharmacy owner account to list your pharmacy." : "Create a free account to keep your preferences.";
    $("#pitchPoints").innerHTML = POINTS[owner ? "pharmacy_owner" : "customer"].map((t) => `<li>${icon("check-circle")}<span>${t}</span></li>`).join("");
  }

  function setMode(mode) {
    const reg = mode === "register";
    $("#tabLogin").setAttribute("aria-selected", String(!reg));
    $("#tabReg").setAttribute("aria-selected", String(reg));
    $("#formLogin").hidden = reg; $("#formReg").hidden = !reg;
    document.title = (reg ? "Create account" : "Log in") + " · MedFind";
    if (reg) pitch(document.querySelector("input[name=role]:checked").value);
    else { $("#pitchTitle").textContent = "Welcome back to MedFind"; $("#pitchText").textContent = "Log in to manage your pharmacy's listings or your account."; $("#pitchPoints").innerHTML = ""; }
  }
  $("#tabLogin").onclick = () => setMode("login");
  $("#tabReg").onclick = () => setMode("register");
  const role = qp.get("role") === "pharmacy_owner" ? "pharmacy_owner" : "customer";
  document.querySelector(`input[name=role][value=${role}]`).checked = true;
  document.querySelectorAll("input[name=role]").forEach((r) => r.addEventListener("change", () => pitch(r.value)));
  setMode(qp.get("mode") === "register" ? "register" : "login");

  async function signIn(email, password) {
    const t = await api.login(email, password);
    session.set(t.access_token, null);
    const me = await api.me();
    session.set(t.access_token, me);
    location.href = safeNext || MF.homeFor(me.role);
  }
  function busy(btn, on, label) { btn.disabled = on; btn.textContent = on ? "Please wait…" : label; }

  $("#formLogin").addEventListener("submit", async (e) => {
    e.preventDefault();
    const err = $("#liErr"); err.textContent = "";
    const email = $("#liEmail").value.trim(), pw = $("#liPass").value;
    if (!email || !pw) { err.textContent = "Enter your email and password."; return; }
    busy($("#liBtn"), true);
    try { await signIn(email, pw); }
    catch (x) { err.textContent = x.status === 401 ? "Wrong email or password." : x.message; session.clear(); busy($("#liBtn"), false, "Log in"); }
  });

  $("#formReg").addEventListener("submit", async (e) => {
    e.preventDefault();
    const err = $("#rgErr"); err.textContent = "";
    const body = {
      full_name: $("#rgName").value.trim(), email: $("#rgEmail").value.trim(), password: $("#rgPass").value,
      phone: $("#rgPhone").value.trim() || null, role: document.querySelector("input[name=role]:checked").value,
    };
    if (!body.full_name || !body.email) { err.textContent = "Enter your name and email."; return; }
    if (body.password.length < 8) { err.textContent = "Password must be at least 8 characters."; return; }
    busy($("#rgBtn"), true);
    try { await api.register(body); await signIn(body.email, body.password); }
    catch (x) { err.textContent = x.message; session.clear(); busy($("#rgBtn"), false, "Create account"); }
  });
})();
