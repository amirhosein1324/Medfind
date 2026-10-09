/*
 * Sample data for the public search page. Used ONLY when the API can't be
 * reached, so the interface can still be explored. Pharmacies are placed
 * around the visitor's location (or a default centre) so distances work
 * anywhere. Everything here is fictional.
 */
(function () {
  "use strict";

  const CENTER = { lat: 50.1109, lon: 8.6821 };

  const MEDS = [
    { id: 1, name: "Paracetamol 500mg", generic: "Paracetamol", brand: "Panadol", detail: "500mg Tablet", rx: false, base: 4.2, aliases: ["Panadol Extra", "Acetaminophen"] },
    { id: 2, name: "Paracetamol 1000mg", generic: "Paracetamol", brand: "Dafalgan", detail: "1000mg Effervescent tablet", rx: false, base: 6.1, aliases: ["Acetaminophen 1000"] },
    { id: 3, name: "Ibuprofen 400mg", generic: "Ibuprofen", brand: "Advil", detail: "400mg Tablet", rx: false, base: 5.4, aliases: ["Nurofen"] },
    { id: 4, name: "Amoxicillin 500mg", generic: "Amoxicillin", brand: "Amoxil", detail: "500mg Capsule", rx: true, base: 9.8, aliases: [] },
    { id: 5, name: "Cetirizine 10mg", generic: "Cetirizine", brand: "Zyrtec", detail: "10mg Tablet", rx: false, base: 7.3, aliases: ["Allergy relief"] },
    { id: 6, name: "Omeprazole 20mg", generic: "Omeprazole", brand: "Losec", detail: "20mg Capsule", rx: false, base: 8.9, aliases: ["Prilosec"] },
    { id: 7, name: "Vitamin D3 1000 IU", generic: "Cholecalciferol", brand: "", detail: "1000 IU Softgel", rx: false, base: 11.5, aliases: ["Vitamin D"] },
    { id: 8, name: "Salbutamol 100mcg", generic: "Salbutamol", brand: "Ventolin", detail: "100mcg Inhaler", rx: true, base: 12.4, aliases: ["Albuterol"] },
    { id: 9, name: "Loratadine 10mg", generic: "Loratadine", brand: "Claritin", detail: "10mg Tablet", rx: false, base: 6.7, aliases: [] },
    { id: 10, name: "Metformin 500mg", generic: "Metformin", brand: "Glucophage", detail: "500mg Tablet", rx: true, base: 5.9, aliases: [] },
  ];

  // dx/dy: kilometres east/north of the visitor (or the default centre).
  const PHARMACIES = [
    { id: 1, name: "Green Cross Pharmacy", address: "12 Linden Street", dx: 0.7, dy: 0.5, phone: "+1 555 0101", hours: "Mon-Sat 8:00-20:00", verified: true, website: "https://example.com/green-cross" },
    { id: 2, name: "Riverside Pharmacy", address: "48 Quay Road", dx: -1.6, dy: 1.1, phone: "+1 555 0102", hours: "Daily 9:00-21:00", verified: true, website: "" },
    { id: 3, name: "Northgate Apotheke", address: "3 Northgate Square", dx: 0.3, dy: 3.2, phone: "+1 555 0103", hours: "Mon-Fri 8:30-18:30", verified: true, website: "https://example.com/northgate" },
    { id: 4, name: "Parkview Pharmacy", address: "210 Park Avenue", dx: 2.9, dy: -1.2, phone: "+1 555 0104", hours: "Mon-Sun 7:00-23:00", verified: false, website: "" },
    { id: 5, name: "Old Town Pharmacy", address: "7 Cobble Lane", dx: -0.4, dy: -0.9, phone: "+1 555 0105", hours: "Mon-Fri 9:00-17:30", verified: true, website: "" },
    { id: 6, name: "Harbor Health Pharmacy", address: "91 Dockside Way", dx: -4.8, dy: -2.4, phone: "+1 555 0106", hours: "Mon-Sat 8:00-19:00", verified: false, website: "https://example.com/harbor" },
    { id: 7, name: "Westfield Pharmacy", address: "5 Westfield Mall", dx: -6.5, dy: 1.8, phone: "+1 555 0107", hours: "Daily 10:00-22:00", verified: true, website: "" },
    { id: 8, name: "Sunrise Pharmacy", address: "66 Maple Court", dx: 5.2, dy: 4.1, phone: "+1 555 0108", hours: "Mon-Fri 8:00-19:00", verified: false, website: "" },
    { id: 9, name: "Central Station Pharmacy", address: "Platform Level, Central Station", dx: 1.2, dy: -2.0, phone: "+1 555 0109", hours: "Daily 6:00-22:00", verified: true, website: "https://example.com/central" },
    { id: 10, name: "Hillside Family Pharmacy", address: "18 Hillside Drive", dx: -8.9, dy: 6.3, phone: "", hours: "Mon-Fri 9:00-17:00", verified: false, website: "" },
  ];

  // Small deterministic PRNG so the sample data is stable between reloads.
  function rng(seed) {
    let t = seed + 0x6d2b79f5;
    return function () {
      t = Math.imul(t ^ (t >>> 15), t | 1);
      t ^= t + Math.imul(t ^ (t >>> 7), t | 61);
      return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
    };
  }

  function listing(pharm, med) {
    const r = rng(pharm.id * 1000 + med.id);
    if (r() < 0.22) return null; // this pharmacy doesn't stock it
    const roll = r();
    const availability = roll < 0.55 ? "available" : roll < 0.75 ? "limited_stock" : roll < 0.9 ? "out_of_stock" : "unknown";
    const priceRoll = r();
    const price = availability === "out_of_stock" && priceRoll < 0.3 ? null : Math.round(med.base * (0.85 + r() * 0.4) * 100) / 100;
    const ageRoll = r();
    const minutes = ageRoll < 0.3 ? 2 + r() * 50 : ageRoll < 0.6 ? 60 + r() * 400 : ageRoll < 0.85 ? 900 + r() * 1800 : 3300 + r() * 6000;
    const stock = availability === "out_of_stock" ? 0 : availability === "limited_stock" ? 1 + Math.floor(r() * 4) : 8 + Math.floor(r() * 60);
    return { availability, price, minutes, stock };
  }

  function haversine(lat1, lon1, lat2, lon2) {
    const R = 6371, rad = (d) => (d * Math.PI) / 180;
    const dLat = rad(lat2 - lat1), dLon = rad(lon2 - lon1);
    const a = Math.sin(dLat / 2) ** 2 + Math.cos(rad(lat1)) * Math.cos(rad(lat2)) * Math.sin(dLon / 2) ** 2;
    return 2 * R * Math.asin(Math.sqrt(a));
  }

  function matches(med, q) {
    const hay = [med.name, med.generic, med.brand].concat(med.aliases).join("|").toLowerCase();
    return hay.indexOf(q) !== -1;
  }

  function medicines(q) {
    const s = String(q || "").trim().toLowerCase();
    return MEDS.filter((m) => !s || matches(m, s)).map((m) => ({
      medicine_id: m.id, name: m.name, generic_name: m.generic, brand_name: m.brand,
      prescription_required: m.rx,
    }));
  }

  function search(q, loc) {
    const s = String(q || "").trim().toLowerCase();
    if (!s) return [];
    const origin = loc ? { lat: loc.lat, lon: loc.lon } : CENTER;
    const out = [];
    MEDS.filter((m) => matches(m, s)).forEach((med) => {
      PHARMACIES.forEach((ph) => {
        const l = listing(ph, med);
        if (!l) return;
        const lat = origin.lat + ph.dy / 110.574;
        const lon = origin.lon + ph.dx / (111.32 * Math.cos((origin.lat * Math.PI) / 180));
        out.push({
          product_id: ph.id * 100 + med.id,
          medicine_id: med.id,
          medicine: med.name,
          pharmacy_id: ph.id,
          pharmacy: ph.name,
          price: l.price,
          availability: l.availability,
          stock_quantity: l.stock,
          last_updated: new Date(Date.now() - l.minutes * 60000).toISOString().replace("Z", ""),
          address: ph.address,
          latitude: lat,
          longitude: lon,
          distance_km: loc ? Math.round(haversine(loc.lat, loc.lon, lat, lon) * 100) / 100 : null,
          medicine_detail: med.detail,
          generic_name: med.generic,
          phone: ph.phone || null,
          website: ph.website || null,
          opening_hours: ph.hours,
          is_verified: ph.verified,
          prescription_required: med.rx,
        });
      });
    });
    return out;
  }

  window.MFDemo = { medicines, search };
})();
