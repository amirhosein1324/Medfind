/*
 * MedFind frontend settings. Edit this file to customise the UI.
 *
 *   apiBase    "" = auto. When the UI is served by the API itself (/app/) it
 *              talks to the same origin; otherwise it uses http://127.0.0.1:8000.
 *   staleHours listings older than this show a "may be out of date" warning.
 *   agingHours listings older than this stop counting as "fresh".
 *   mapLink    "Directions" link for a pharmacy with coordinates ({lat}, {lon}).
 *   mapSearch  "Directions" link when only an address is known ({q}).
 *              Any map site works, e.g. a domestic one such as Neshan or Balad.
 * All prices are shown in Toman and dates in the Jalali (Persian) calendar.
 */
window.MEDFIND_CONFIG = {
  apiBase: "",
  staleHours: 48,
  agingHours: 6,
  mapLink: "https://www.openstreetmap.org/?mlat={lat}&mlon={lon}#map=17/{lat}/{lon}",
  mapSearch: "https://www.openstreetmap.org/search?query={q}",
};
