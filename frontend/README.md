# MedFind web app

Plain HTML/CSS/JS, no build step. Served by the API at `/app/`.

| Page | For | File |
|---|---|---|
| Search & compare | everyone | `index.html` + `js/search.js` |
| Log in / register | everyone | `login.html` + `js/login.js` |
| My pharmacy | pharmacy owners | `dashboard.html` + `js/dashboard.js` |
| Admin | admins | `admin.html` + `js/admin.js` |

Shared: `css/medfind.css` (design tokens, light/dark), `css/app.css`, `js/core.js` (API client, session, icons, helpers), `js/demo.js` (sample data when the API is unreachable).

## Run
    uvicorn app.main:app --reload          # or: docker compose up --build
    python -m scripts.seed_demo            # demo data + accounts (docker: docker compose exec api python -m scripts.seed_demo)
Open http://localhost:8000/app/

Demo accounts (after seeding): `admin@medfind.test` and `owner@medfind.test`, password `Passw0rd!demo`.
