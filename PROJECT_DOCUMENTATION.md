**Project:** EduExit — Student Exit Request System

**Overview**
- **Purpose:**: A small approval workflow where students submit campus exit requests and admins review/act on them.
- **Stack:**: Python backend (SQLite service), FastAPI wrapper, static frontend (HTML/CSS/JS).
- **Local servers:**: API served by `uvicorn` (default at `http://127.0.0.1:8000`), static site served from `approval-system/nn` (example `python -m http.server 8001`).

**Repository Layout (key files)**
- **Root:**: `cli.py`, `README.md`, `requirements.txt`
- **Core service:**: `src/` — contains `approval_system`, `db.py`, and `service.py` for DB and business logic.
- **Approval-system wrapper:**: `approval-system/` — contains `app.py` (original Streamlit), `api.py` (FastAPI wrapper), `requirements.txt` (API deps).
- **Static frontend:**: `approval-system/nn/` — contains `index.html`, `style.css`, `script.js` (frontend UI + logic).
- **Tests:**: `tests/test_service.py`

**How it works (high level)**
- The core logic and DB operations live in `src/service.py` and `src/db.py` and use an SQLite file (e.g. `approval.db`).
- `approval-system/api.py` exposes a lightweight REST API that calls into the core service to list/create users, send letters/requests, and perform actions on requests.
- The static frontend (`index.html` + `script.js`) calls the API (base `http://127.0.0.1:8000/api`) to create students, send requests, list pending requests, and administer users.

**Main API endpoints (as used by the frontend)**
- `GET /api/users` — list users
- `POST /api/users` — create user (body: `{ name, role }`)
- `PUT /api/users/{id}/password` — reset user's password
- `DELETE /api/users/{id}` — delete user
- `GET /api/letters` — list letters/requests
- `POST /api/send` — create/send a letter (body: `{ sender_id, title, body }`)
- `POST /api/act` — perform action on a letter (body: `{ letter_id, actor_name, actor_role, action, comments?, recommendations? }`).
  Actions now include `approve`, `reject`, or `comment`; the latter allows any non-student user to append commentary without changing approval status.

**Frontend behavior and UX notes**
- **Student flow**: Login on `loginPage` (name + matric). If the student doesn't exist, the frontend creates a `Student` user via `POST /api/users`. Then the student can write an exit request in the `textarea` and click `Send Request`.
- **Admin flow**: Admin logs in with the UI password `admin123` (UI-side only). Admin can view pending requests, accept/decline, and manage students (add/reset/delete).
- **Word limit**: The request textarea enforces a 1000-word hard limit client-side. The input is trimmed at 1000 words as you type and submission is blocked if >1000 words.
- **Debugging**: An on-page debug panel (`Debug`) is created by the frontend to capture client errors and messages for users without DevTools.

**How to run locally (quick)**
1. Install Python dependencies for API (from `approval-system/requirements.txt`):

```bash
python -m pip install -r approval-system/requirements.txt
```

2. Start the API (from project root or `approval-system/`):

```bash
uvicorn approval-system.api:app --reload --host 127.0.0.1 --port 8000
```

3. Serve the static frontend (from `approval-system/nn`):

```bash
cd approval-system/nn
python -m http.server 8001
# Open http://127.0.0.1:8001/
```

4. Use the UI. If `index.html` is opened from `file://` the app may fail; open it by HTTP as shown above.

**Developer notes**
- **DB location:** The FastAPI wrapper initializes/uses a SQLite DB (e.g., `approval.db`) in the `approval-system` workspace — verify path in `approval-system/api.py`.
- **CORS:** The API includes CORS middleware to allow the static frontend to call it locally.
- **Script caching:** `index.html` references `script.js?v=2` to avoid stale cached JS during development.
- **Safe DOM access:** `script.js` uses helper functions (`el()`, `setText()`, `setTextBySelector()`) to avoid null DOM writes and has client-side guards in place.

**Known issues & troubleshooting**
- If you see repeated console errors like "Cannot set properties of null (setting 'textContent')", hard-reload the frontend (Ctrl+F5) to ensure `script.js?v=2` is loaded; code was patched to guard DOM access.
- Ensure both servers are running and the frontend is opened over `http://` not `file://`.
- If API endpoints return 4xx/5xx, check `uvicorn` logs for the raw request payloads and confirm the frontend is hitting the correct base URL `http://127.0.0.1:8000/api`.

**Tests & verification**
- There is a unit test `tests/test_service.py` for core service behavior; run with `pytest` in the workspace.
- Quick manual smoke tests used during development:
  - `GET /api/users` — verify user list
  - `POST /api/users` — create test user
  - `POST /api/send` — create a request
  - `PUT /api/users/{id}/password` — reset password
  - `DELETE /api/users/{id}` — delete user

**Files I changed during frontend work**
- `approval-system/api.py` — added FastAPI wrapper for the core service (new file)
- `approval-system/requirements.txt` — updated/added FastAPI/Uvicorn deps
- `approval-system/nn/index.html` — updated UI and switched to `script.js?v=2`
- `approval-system/nn/script.js` — implemented frontend logic, safe DOM helpers, word counter (1000-word limit), student/admin flows, debug panel
- `approval-system/nn/style.css` — CSS tweaks to prevent text overflow (if present)

**Next recommended steps**
- Run the manual smoke tests described above to confirm end-to-end behavior.
- Add simple API integration tests to assert endpoints used by the UI.
- Consider securing admin actions (remove UI-only password, add server-side auth).
- Persist admin settings (admin pass, default passwords) in DB rather than only in the frontend.

**Contact / Help**
- If you want, I can: run the smoke tests here, commit these changes, or expand the README with screenshots and step-by-step screenshots for onboarding.

---
Generated on 2026-02-19.
