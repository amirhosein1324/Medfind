/*
 * MedFind frontend settings. Edit this file to customise the UI.
 *
 *   apiBase    "" = auto. When the UI is served by the API itself (/app/) it
 *              talks to the same origin; when opened some other way it uses
 *              http://127.0.0.1:8000. Set a full URL to force a backend.
 *              (Visitors can also change it from the footer without editing code.)
 *   currency   symbol shown before prices.
 *   staleHours listings older than this show a "may be out of date" warning.
 *   agingHours listings older than this stop counting as "fresh".
 */
window.MEDFIND_CONFIG = {
  apiBase: "",
  currency: "$",
  staleHours: 48,
  agingHours: 6,
};
