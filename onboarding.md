# MRG Labs Graphing App — Codebase Onboarding

You’re looking at `PIPELINE.md`, which maps the whole app. Below is a **codebase-level** onboarding grounded in the real source (not only the doc). One critical gotcha up front: **PIPELINE.md and the code disagree in places** — trust the code when modifying.

---

# 1. Purpose

This app lets lab users upload a **baseline FTIR CSV** and **multiple sample CSVs**, overlay them interactively, score how abnormal each sample looks vs baseline, export PNG comparison graphs, and optionally ask Gemini for AI analysis/chat.

It exists to turn raw spectroscopy CSVs into a usable comparison workflow for the Schneider Prize challenge — not just charts, but **ranked anomaly scores**, **weighted wavelength regions**, and **batch export**.

**In short:** React frontend owns interactive preview + scoring; FastAPI backend owns auth, PNG generation, and AI; MySQL stores users/graphs. Most day-to-day analysis runs **in the browser**, not on the server.

---

# 2. Architecture

```
Browser (Vite/React)
├── App.tsx                 → routing + AuthProvider
├── AuthContext             → session-aware auth state
├── Dashboard               → orchestrates uploads, scores, export UI
├── FileUploadBox           → Papa Parse → ParsedCSV
├── GraphPreview            → Chart.js + LIVE scoring (this is the hot path)
├── SampleSidebar           → selection + score badges
├── ExportDialog            → POST /generate_graphs
└── Chatbox / AI UI         → /analysis/*, chat routes

                    credentials: 'include' (session cookie)
                              │
                              ▼
FastAPI (backend/app.py)
├── /register, /login, /logout, /change_password
├── /generate_graphs        → utils/plotter.generate_and_save
├── /api/v1/files           → MySQL graphs table (auth probe)
├── /analysis/*             → graph_analysis.py (Gemini)
└── chat router             → chatbox.py
                              │
                    ┌─────────┴─────────┐
                    ▼                   ▼
                 MySQL              Gemini API
```

**Who calls what**

| Layer | Typically called by | Depends on |
|--------|---------------------|------------|
| `AuthContext` | `App`, `ProtectedRoute`, Login/Signup, Dashboard | `services/auth.ts` |
| `Dashboard` | Router via `ProtectedRoute` | uploads, GraphPreview, ExportDialog, Auth |
| `GraphPreview` | Dashboard | `lib/series.diff`, Chart.js |
| `FTIRAnalysisService` | **Currently unused by UI** | `lib/series` |
| `useFTIRAnalysis` / `ftirApi` | **Currently unused by Dashboard** | backend analysis APIs |
| `app.py` | Frontend fetch calls | MySQL, plotter, routers |
| `plotter.py` | `/generate_graphs` | pandas, matplotlib |

---

# 3. Exports (key public surfaces)

### Frontend — `auth.ts`

| Export | Purpose | Inputs | Outputs | Side effects | When called |
|--------|---------|--------|---------|--------------|-------------|
| `register` | Create account | `{username, password}` | `AuthResponse` | POST `/register` | Signup form |
| `login` | Authenticate | credentials | `AuthResponse` | Sets httpOnly session cookie | Login / post-register |
| `logout` | End session | — | void | Clears server session | Profile menu |
| `changePassword` | Update password | current + new | status | Needs auth cookie | Change password dialog |
| `checkAuth` | Probe session | — | `boolean` | GET `/api/v1/files` | App mount via AuthContext |

### Frontend — `AuthContext.tsx`

| Export | Purpose | Side effects | When |
|--------|---------|--------------|------|
| `AuthProvider` | Holds `user`, `isLoading`, auth methods | localStorage `username`; calls auth service | Wraps app |
| `useAuth` | Consumer hook | Throws if outside provider | Any protected UI |

### Frontend — `GraphPreview` (default export)

- **Purpose:** Interactive overlay chart + **canonical scoring** used by Dashboard.
- **Inputs:** baseline/samples (`ParsedCSV`), weights, scoring method, `onScoreUpdate`.
- **Outputs:** Chart UI; calls `onScoreUpdate(scores)` when scores change.
- **Side effects:** Registers Chart.js plugins; mutates parent score state.

### Frontend — `FTIRAnalysisService` (`ftirAnalysis.ts`)

| Method | Purpose | Notes |
|--------|---------|-------|
| `performAnalysis(...)` | Scores + deviation payload | Parallel implementation; **not wired into Dashboard** |
| `calculateDeviationData(...)` | Weighted \|δ\| heatmap data | Same |

### Frontend — `diff` (`lib/series.ts`)

- Exact X-match only (`Map` lookup). Sample points with no exact baseline X are dropped. Used by GraphPreview deviation math.

### Backend — `app.py`

| Endpoint | Purpose | Auth? |
|----------|---------|-------|
| `POST /register` | Insert bcrypt-hashed user | No |
| `POST /login` | Verify password; set `request.session['user_id']` | No |
| `POST /logout` | `session.clear()` | Implicit |
| `POST /change_password` | Verify old, update hash | Yes (`Depends(get_current_user_id)`) |
| `POST /generate_graphs` | Matplotlib PNGs → ZIP | **No auth currently** |
| `GET /api/v1/files` | List user’s graphs | Yes |
| `GET /health` | Liveness | No |

### Backend — `generate_and_save` (`plotter.py`)

- Reads CSVs with `header=1`, remaps wavenumbers to equal visual spacing, saves PNGs under `static/generated_graphs/`, returns static-relative paths.

---

# 4. Function Walkthrough (the paths that matter)

### A. Login (`auth.login` → `app.login` → `AuthContext.login`)

1. Frontend POSTs JSON with `credentials: 'include'` so the browser stores the session cookie.
2. Backend looks up user by username (parameterized SQL — good).
3. `bcrypt.checkpw` verifies hash; failures return the same 401 (“invalid credentials”) — intentional to avoid user enumeration.
4. `request.session['user_id'] = id` — Starlette signs a cookie; **there is no separate `sessions` MySQL table** despite what PIPELINE.md says.
5. AuthContext stores username in `localStorage` only for display after reload — **not** the source of truth for auth. Cookie is.

**Why this shape:** Cookie sessions keep passwords off the client and work with CORS + credentials. localStorage username is a UX shortcut and can desync (you can appear “User” if localStorage is empty but cookie is valid).

### B. Protected route

```
isLoading → spinner
!isAuthenticated → Navigate /login
else → children
```

**Assumption:** `isAuthenticated === !!user`, and `user` is set only after `checkAuth` or login. `checkAuth` treats any successful `/api/v1/files` as logged in — so DB outages look like “logged out.”

### C. Upload → parse (`FileUploadBox`)

Papa Parse turns CSV → `{filename, x[], y[], ...}` in React state. Raw `File` objects are kept separately for backend export (`baselineFile` / `sampleFiles`).

**Why dual state:** Chart needs numbers; `/generate_graphs` needs multipart file uploads. Don’t drop either when refactoring.

### D. Scoring (LIVE path in `GraphPreview`)

1. `useMemo` over baseline, samples, weights, method.
2. For each sample, compute overlap / diffs (often via `diff()` or index walks).
3. Apply wavelength weights (oxidation bands can be weighted higher).
4. Map metric → 0–100 score (higher = more similar / better).
5. Push scores to Dashboard via `onScoreUpdate` → sidebar badges.

**Why scoring lives in GraphPreview:** Historical — visualization and scoring grew together. `FTIRAnalysisService` was later extracted as a “cleaner” service but **Dashboard still comments that GraphPreview recalculates scores**. If you change scoring formulas, change **GraphPreview first** or you’ll “fix” the unused service and ship no UI change.

**Important TS concepts:** `useMemo` for expensive score calc; floating-point wavelength matching with epsilon (`0.001`); exact Map keys in `diff` vs tolerance matching elsewhere — **inconsistency risk**.

### E. Export (`/generate_graphs` → `generate_and_save`)

1. Multipart upload baseline + samples.
2. `read_csv(..., header=1)` — **assumes row 0 is junk/header metadata**, columns 0/1 are X/Y.
3. Custom FTIR axis remapping (4000→550 cm⁻¹ equal visual spacing).
4. Save PNGs, zip them, return `FileResponse`.

**Why Agg/matplotlib on server:** Browser Chart.js is interactive; export needs print-quality static images. Different rendering stacks → exported PNGs may not pixel-match the preview.

### F. AI analysis (`graph_analysis.py`)

Optional Gemini path: build matplotlib image + stats → prompt model → JSON insights. Soft-fails if `GEMINI_API_KEY` / packages missing (`GENAI_AVAILABLE` flags).

---

# 5. Dependencies

| Dependency | Type | Why needed | If removed |
|------------|------|------------|------------|
| React + Vite + TS | External | SPA UI | No app |
| React Router | External | Auth-gated routes | Flat pages / broken redirects |
| Chakra UI | External | Layout/forms | Rebuild UI |
| Chart.js + zoom plugin | External | Interactive overlay | Preview dead |
| Papa Parse | External | CSV → arrays | Uploads break |
| FastAPI / Starlette | External | API + SessionMiddleware | No backend |
| bcrypt | External | Password hashing | Insecure/plain auth |
| mysql.connector | External | Users + graphs | Auth/files fail |
| pandas / matplotlib | External | CSV + PNG export / AI plots | Export & AI break |
| google.generativeai | External (optional) | AI insights/chat | AI features degrade |
| `lib/series.diff` | Internal | Shared delta calc | Duplicate math / bugs |
| `AuthContext` | Internal | Single auth source for UI | Prop-drilling hell |
| `plotter.py` | Internal | Export pipeline | `/generate_graphs` empty |

---

# 6. Design Patterns

| Pattern | Where | Why |
|---------|-------|-----|
| **Service layer** | `auth.ts`, `ftirApi.ts`, `FTIRAnalysisService` | Isolate HTTP/domain from components |
| **Provider / Context (Observer-ish)** | `AuthProvider` | Broadcast auth without prop drilling |
| **Route guard** | `ProtectedRoute` | Client-side gate before Dashboard |
| **Dependency injection (FastAPI)** | `Depends(get_current_user_id)` | Reusable auth on endpoints |
| **Router composition** | `include_router(analysis_router)` | Split AI/chat from core app |
| **Middleware** | CORS + SessionMiddleware | Cookies + cross-origin Vite→API |
| **Facade (attempted)** | `useFTIRAnalysis` | Loading/abort/error around API — underused |

Not really MVC or Repository — it’s a classic **SPA + thin API** with some domain logic still stuck in UI (`GraphPreview`).

---

# 7. Error Handling

**Expected**

- Bad credentials → 401
- Duplicate username → IntegrityError → 400
- Missing DB env → `RuntimeError` / 500
- Invalid CSV → exceptions in plotter / Papa validation
- Gemini missing key → warnings / degraded AI
- Analysis NaNs → `AnalysisError` or neutral score `50` in service; GraphPreview has its own thresholds

**How handled**

- Auth: throw `Error` with `detail` from FastAPI; UI toasts
- Scoring service: catch → log → return 50 / null (fail soft so UI stays up)
- Export: catch-all → JSON 400 `{error}`
- `verify_password`: swallow exceptions → `False` (treat corrupt hashes as bad login)

**Gaps / failure modes**

1. **PIPELINE.md is wrong on sessions** — don’t implement against the doc’s UUID `sessions` table without verifying schema.
2. **`/generate_graphs` is unauthenticated** — anyone who can hit the API can generate zips (DoS / abuse).
3. **Duplicate scoring** — GraphPreview vs `FTIRAnalysisService` formulas diverge (hybrid weights differ).
4. **`diff()` exact X only** vs scoring’s `0.001` tolerance — slight grid mismatch → dropped points.
5. **Auth probe couples to DB** — `/api/v1/files` failure = “logged out.”
6. **Register then auto-login** — if login fails after register succeeds, user exists but UI looks failed.
7. **SESSION_SECRET fallback** to `secrets.token_urlsafe(32)` on each process start if env unset → sessions die on restart.
8. **CSV `header=1`** assumption will silently mis-parse differently shaped files.

---

# 8. Data Flow (realistic path)

**User Action:** Log in → upload baseline + samples → pick scoring method → select sample → Export

```
User submits Login form
    ↓
auth.login() → POST /login (credentials: include)
    ↓
MySQL: SELECT user; bcrypt verify
    ↓
SessionMiddleware sets signed cookie (user_id)
    ↓
AuthContext.setUser + localStorage username
    ↓
Navigate /dashboard (ProtectedRoute passes)
    ↓
FileUploadBox: FileReader + Papa Parse → ParsedCSV in Dashboard state
    ↓
GraphPreview useMemo: score each sample (browser CPU)
    ↓
onScoreUpdate → sampleScores → SampleSidebar badges
    ↓
Chart.js renders baseline vs selected sample; DeviationHeatBar from diffs
    ↓
User clicks Export → ExportDialog multipart POST /generate_graphs
    ↓
plotter.generate_and_save → PNG files on disk
    ↓
ZIP FileResponse → browser download
```

AI path (separate): upload files to `/analysis/...` → stats + image → Gemini → JSON back to Chat/analysis UI.

---

# 9. Important Concepts Before You Modify

1. **Session cookies vs JWT** — This app uses **server-signed session cookies**, not JWT. Always send `credentials: 'include'`. Changing CORS origins without matching cookie settings breaks auth silently.
2. **`async/await` + fetch error handling** — `response.ok` is not automatic throw; services manually parse `detail`.
3. **React Context + loading gate** — Never render protected UI before `isLoading` is false or you’ll flash-redirect to login.
4. **Client vs server analysis** — Preview/scoring is client-side; PNG/AI is server-side. Changing one doesn’t update the other.
5. **CSV contract** — Backend `header=1`, columns 0/1 = X/Y. Frontend Papa config must stay compatible with export.
6. **Floating-point wavelength identity** — Spectroscopy X grids often “almost” match; exact `Map` keys vs epsilon matching is a real bug source.
7. **FastAPI `Depends` lifecycle** — Auth dependency runs before the route body; raising `HTTPException(401)` short-circuits.
8. **Soft failure culture** — Many analysis paths return score `50` instead of failing hard. “Looks fine” can mean “calculation failed.”

---

# 10. Potential Improvements

| Area | Critique | Suggestion |
|------|----------|------------|
| **Separation of concerns** | Scoring buried in ~800-line GraphPreview | Make GraphPreview call `FTIRAnalysisService` only; delete duplicate math |
| **Dead code** | `useFTIRAnalysis` / parts of `ftirApi` unused | Wire up or delete to reduce confusion |
| **Docs drift** | PIPELINE.md sessions/email story ≠ code (username + SessionMiddleware) | Treat code as source of truth; update PIPELINE |
| **Security** | Unauthed generate_graphs; weak password min length (6); SESSION_SECRET auto-gen | Require auth; force env secret; stronger password policy |
| **Testability** | Pure math mixed with Chart.js | Unit-test scoring in `ftirAnalysis` / `series`; keep UI dumb |
| **Performance** | O(n²) `findIndex` in scoring loops | Index by wavelength Map once per series |
| **Naming** | “anomaly score” where higher = better/similar | Rename to `similarityScore` or document clearly |
| **Maintainability** | Dual ParsedCSV types (types vs ftirAnalysis) | Single shared type module |
| **Scalability** | Sync matplotlib per request; files on local disk | Queue + object storage if traffic grows |
| **Auth UX** | Username only in localStorage | Return username from a `/me` endpoint |

---

# 11. Interview Questions

1. Why does the frontend call `/api/v1/files` to check auth instead of a dedicated `/me` endpoint, and what failure modes does that create?
2. Walk through what happens if baseline and sample X grids don’t share exact float values — where does `diff()` diverge from GraphPreview scoring?
3. `/generate_graphs` doesn’t use `Depends(get_current_user_id)` while `/api/v1/files` does. What’s the security implication, and how would you fix it without breaking the export dialog?
4. There are two scoring implementations (`GraphPreview` and `FTIRAnalysisService`). How would you consolidate them safely, and how would you regression-test FTIR score thresholds?
5. SessionMiddleware falls back to a random `SESSION_SECRET` if env vars are missing. What happens across multi-worker or restart deployments?

---

# 12. Knowledge Check (onboarding notes)

- App = FTIR baseline-vs-samples: preview, score, export PNG ZIP, optional Gemini AI.
- **Auth = Starlette session cookie + bcrypt + MySQL users** — not JWT; PIPELINE’s sessions-table story is outdated.
- **Dashboard owns state**; GraphPreview owns **live scoring** and chart; sidebar only displays.
- CSV parsed client-side (Papa); raw Files kept for multipart export.
- **Change scoring in GraphPreview** (or unify into `FTIRAnalysisService` first) — the service file alone won’t change the UI today.
- Export = FastAPI → pandas/matplotlib → disk → ZIP; axis remapping is FTIR-specific.
- AI lives in separate routers (`graph_analysis`, `chatbox`) and soft-degrades without Gemini.
- Dual analysis stacks exist (client GraphPreview vs unused service/hook vs server AI) — know which path you’re on.
- Biggest footguns: doc drift, duplicate score math, exact vs epsilon X matching, unauthed export, SESSION_SECRET.
- Before modifying: preserve `credentials: 'include'`, CSV `header=1` contract, and score callback wiring to the sidebar.
