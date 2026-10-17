(function () {
  "use strict";
  const { $, esc, icon, api, ago, statusHTML } = MF;
  MF.renderNav("search");
  const root = $("#main");
  const key = new URLSearchParams(location.search).get("k");
  const money = (v, cur) => v == null ? "–" : cur === "IRT" ? Math.round(Number(v)).toLocaleString("en-US") + " Toman" : Number(v).toFixed(2) + " " + (cur || "");
  const short = (v) => Number(v) >= 1e6 ? (Number(v) / 1e6).toFixed(2).replace(/\.?0+$/, "") + "M" : Number(v) >= 1e3 ? Math.round(Number(v) / 1e3) + "k" : String(Math.round(Number(v)));

  function chart(h, cur) {
    if (h.length < 2) return `<div class="empty" style="padding:var(--s-5)">${icon("clock")}<p>The price chart builds up as we re-check the shops (about every 6 hours). Come back soon.</p></div>`;
    const W = 640, H = 220, L = 52, R = 14, T = 14, B = 28;
    const ys = h.map((p) => p.min_price), lo = Math.min(...ys), hi = Math.max(...ys), pad = (hi - lo) * 0.15 || hi * 0.1 || 1;
    const y0 = Math.max(0, lo - pad), y1 = hi + pad;
    const t = (d) => new Date(d).getTime(), t0 = t(h[0].date), t1 = t(h[h.length - 1].date) || t0 + 1;
    const X = (d) => L + ((t(d) - t0) / (t1 - t0 || 1)) * (W - L - R);
    const Y = (v) => T + (1 - (v - y0) / (y1 - y0)) * (H - T - B);
    const pts = h.map((p) => `${X(p.date).toFixed(1)},${Y(p.min_price).toFixed(1)}`);
    const grid = [0, 0.5, 1].map((f) => { const v = y0 + (y1 - y0) * f, y = Y(v); return `<line class="grid" x1="${L}" x2="${W - R}" y1="${y}" y2="${y}"/><text x="${L - 8}" y="${y + 4}" text-anchor="end">${short(v)}</text>`; }).join("");
    const last = h[h.length - 1];
    return `<div class="chart"><svg viewBox="0 0 ${W} ${H}" role="img" aria-label="Lowest price over time, from ${esc(money(h[0].min_price, cur))} to ${esc(money(last.min_price, cur))}">
      ${grid}<polygon class="area" points="${L},${H - B} ${pts.join(" ")} ${X(last.date).toFixed(1)},${H - B}"/>
      <polyline class="line" points="${pts.join(" ")}"/>
      ${h.length <= 40 ? h.map((p) => `<circle class="dot" r="3.5" cx="${X(p.date).toFixed(1)}" cy="${Y(p.min_price).toFixed(1)}"><title>${esc(p.date)}: ${esc(money(p.min_price, cur))}</title></circle>`).join("") : ""}
      <text x="${L}" y="${H - 8}">${esc(h[0].date)}</text><text x="${W - R}" y="${H - 8}" text-anchor="end">${esc(last.date)}</text></svg></div>`;
  }

  async function init() {
    if (!key) { root.innerHTML = `<div class="empty">${icon("search")}<h3>No product selected</h3><a class="btn btn--primary" href="index.html">Search medicines</a></div>`; return; }
    try {
      const g = await api.webProduct(key);
      document.title = g.name + " · MedFind";
      const cur = g.currency, inStock = g.offers.filter((o) => o.availability !== "out_of_stock");
      const bestUrl = inStock.length && inStock[0].price != null ? inStock[0].url : null;
      const avg = (() => { const p = inStock.filter((o) => o.price != null).map((o) => Number(o.price)); return p.length ? p.reduce((a, b) => a + b, 0) / p.length : null; })();
      root.innerHTML = `<a class="crumb" href="index.html" id="back">${icon("chevron", "").replace("<svg", '<svg style="transform:rotate(90deg)"')} Back to results</a>
        <div class="pp__head">
          <div class="pp__img">${g.image_url ? `<img src="${esc(MF.safeUrl(g.image_url) || "")}" alt="" referrerpolicy="no-referrer">` : icon("pill")}</div>
          <div><h1>${esc(g.name)}</h1>${g.title_fa ? `<p class="pp__fa" dir="auto">${esc(g.title_fa)}</p>` : ""}
            <div class="pp__stats">
              <div class="pp__stat pp__stat--best"><b>${esc(money(g.min_price, cur))}</b><span>Lowest price</span></div>
              <div class="pp__stat"><b>${avg != null ? esc(money(avg, cur)) : "–"}</b><span>Average</span></div>
              <div class="pp__stat"><b>${g.shops}</b><span>Shop${g.shops === 1 ? "" : "s"} · ${g.available} in stock</span></div>
            </div></div></div>
        <h2>Prices in ${g.shops} shop${g.shops === 1 ? "" : "s"}</h2>
        <ul class="offers">${g.offers.map((o) => `<li class="offer${o.url === bestUrl ? " offer--best" : ""}${o.availability === "out_of_stock" ? " offer--out" : ""}">
          <div><div class="offer__shop">${esc(o.shop)}${o.url === bestUrl ? '<span class="flag">Cheapest</span>' : ""}</div>
            <div class="offer__title" dir="auto">${esc(o.title)}</div><div class="hint">checked ${esc(ago(o.fetched_at))}</div></div>
          <div class="offer__side"><span class="offer__price">${esc(money(o.price, o.currency))}</span>${statusHTML(o.availability)}
            <a class="btn btn--primary btn--sm" href="${esc(MF.safeUrl(o.url) || "#")}" target="_blank" rel="noopener nofollow">Go to shop ${icon("external")}</a></div></li>`).join("")}</ul>
        <h2>Price history</h2>${chart(g.history, cur)}
        <p style="margin-top:var(--s-5)"><a class="btn btn--secondary" href="index.html?q=${encodeURIComponent(g.generic || g.name)}">${icon("pin")}Also check partner pharmacies near you</a></p>`;
      $("#back").addEventListener("click", (e) => { if (history.length > 1 && document.referrer) { e.preventDefault(); history.back(); } });
    } catch (e) {
      root.innerHTML = `<div class="empty">${icon("alert")}<h3>${e.status === 404 ? "We can't find that medicine" : "Couldn't load this page"}</h3><p>${esc(e.message)}</p><a class="btn btn--primary" href="index.html">Search medicines</a></div>`;
    }
  }
  init();
})();
