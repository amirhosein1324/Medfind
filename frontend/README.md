# MedFind — Pharmacy Dashboard (frontend)

Plain HTML/CSS/JS, no build step, no framework. Lets a pharmacy owner log
in, manage their pharmacies, edit listing prices/stock/availability inline,
and see a log of recent changes.

## Running it

The backend must be running first (see the main `README.md`), and must have
CORS enabled — it already is, via `CORSMiddleware` in `app/main.py`.

Serve this folder with any static file server (opening `dashboard.html`
directly via `file://` will work for viewing, but some browsers block
`fetch()` from `file://` origins, so a local server is safer):

```bash
cd frontend
python -m http.server 5500
```

Then open `http://127.0.0.1:5500/dashboard.html`.

A small **API base URL** bar at the top of the page lets you point the
dashboard at any backend — `http://127.0.0.1:8000` by default (matches
`uvicorn --reload`), or `http://localhost:8000` if you're running it via
`docker compose up`. Click **Save** after changing it.

## Using it

1. **Register** (link under the login form) as a pharmacy owner, or log in
   with an existing account.
2. **Create a pharmacy** — it starts pending admin approval, same as the API
   requires. An admin has to approve it (via the API or a future admin UI)
   before it's publicly searchable, but you can still manage its listings
   as the owner in the meantime.
3. **Add a listing** — you'll need a medicine's ID. There's no medicine
   picker yet (see Known limitations below), so look one up first via
   `GET /api/medicines/?q=paracetamol` (e.g. in the API's `/docs` page).
4. **Edit price or stock inline** — click the number, type a new value,
   press Enter or click away. The row flashes green to confirm the save.
5. **Change availability** — use the dropdown in the Status column.
6. **Recent changes** — every edit is logged and shown at the bottom of the
   page, newest first.

## Known limitations (intentional, for a first pass)

- **No medicine picker** — adding a listing requires typing a medicine ID
  by hand. A searchable picker (calling `GET /api/medicines/?q=`) is a
  natural next addition.
- **No pharmacy editing** — you can create a pharmacy but not yet edit its
  address/hours/etc. after creation (the backend doesn't expose that yet
  either).
- **Token storage** — the JWT is kept in `localStorage` for convenience
  across page reloads. Fine for local development; for a production
  deployment, consider a shorter token lifetime and/or an httpOnly cookie
  issued by a backend session endpoint instead.
- **No admin view** — approving pharmacies still has to be done via the API
  directly (`PATCH /api/pharmacies/{id}/approve`) or a separate admin UI.

## Design notes

Built to the breakpoints and accessibility standards from the UI/UX spec:
mobile-first CSS with breakpoints at 375px (base), 768px (tablet — the
pharmacy rail appears), and 1440px (desktop — more breathing room). All
interactive elements are at least 48px tall. Colors were chosen for WCAG
2.1 AA contrast (4.5:1+ for text). Typography uses the IBM Plex family:
serif for headings, sans for UI text, monospace for every number — prices,
stock counts, and timestamps all read like a ledger.
