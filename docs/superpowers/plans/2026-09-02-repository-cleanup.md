# Repository Cleanup Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make the application easier to extend and test by introducing feature-oriented frontend modules, layered backend modules, and clean repository hygiene without changing public behavior.

**Architecture:** Keep React routes and FastAPI endpoint contracts stable while moving implementation behind narrowly scoped feature and service modules. Backend configuration and database access remain simple modules at the `backend/` root. Extract pure transformations before moving their consumers so each behavioral seam has an executable test.

**Tech Stack:** React 18, TypeScript, Vite, Vitest, Chakra UI, FastAPI, Pydantic, pytest.

**Spec:** `docs/superpowers/specs/2026-09-02-repository-cleanup-design.md`

## Global Constraints

- Preserve HTTP paths, methods, request formats, response formats, UI copy, and analysis methodology.
- Never expose environment values in output or logs; do not perform provider setup at import time.
- Keep cross-feature frontend imports limited to public feature entry points.
- Do not change the user-owned `.DS_Store` in the primary checkout.

---

### Task 1: Establish project instructions and repository hygiene

**Files:** Create `AGENTS.md`; modify `.gitignore`; delete tracked `backend/.venv/**`, `backend/**/__pycache__/**`, and `backend/static/generated_graphs/**`.

- [ ] Write a regression command: `git ls-files 'backend/.venv/**' 'backend/**/__pycache__/**' 'backend/static/generated_graphs/**'`.
- [ ] Run it and confirm the baseline lists runtime artifacts.
- [ ] Add `AGENTS.md` with the user's six engineering standards, test expectations, and generated-artifact hygiene requirements.
- [ ] Add `backend/.venv/`, `backend/**/__pycache__/`, and `backend/static/generated_graphs/` to `.gitignore`.
- [ ] Use `git rm -r --cached` for the exact tracked artifact paths; remove them from this cleanup worktree.
- [ ] Re-run the regression command and `git check-ignore backend/.venv backend/__pycache__ backend/static/generated_graphs/example.png`; the former prints nothing and the latter succeeds.
- [ ] Commit with `git add AGENTS.md .gitignore backend && git commit -m "chore: establish repository hygiene"`.

### Task 2: Repair shared frontend contracts

**Files:** Modify `frontend/src/types/common.ts`, `types/api.ts`, `types/index.ts`, `components/index.ts`, `components/shared/index.ts`, `services/auth.ts`, `services/ftirAnalysis.ts`, and `services/ftirApi.ts`; create `frontend/src/types/__tests__/common.test.ts`.

- [ ] Write a failing test that asserts `getSampleStatus(85) === 'good'`, `getSampleStatus(70) === 'warning'`, and `getSampleStatus(69) === 'critical'`.
- [ ] Run `npm run test -- --run src/types/__tests__/common.test.ts` and `npm run build` from `frontend`; record current barrel-resolution failures.
- [ ] Make `types/common.ts` the only cross-feature definition for `User`, `ParsedCSV`, `RangeWeight`, and `ScoringMethod`; services import those types rather than redefine them.
- [ ] Delete barrel exports for nonexistent component folders and legacy files rather than adding compatibility placeholders.
- [ ] Re-run the focused test and `npm run build`; both must pass.
- [ ] Commit with `git add frontend/src/types frontend/src/components frontend/src/services && git commit -m "refactor: consolidate frontend contracts"`.

### Task 3: Extract frontend analysis transformations

**Files:** Create `frontend/src/features/analysis/lib/series.ts` and `series.test.ts`; modify `frontend/src/lib/series.ts` and `components/dashboard/GraphPreview.tsx`.

- [ ] Write failing tests for `diff({x:[1,2],y:[3,5]}, {x:[1,2],y:[4,1]}).y` equaling `[1,-4]`, and for mismatched series raising an error.
- [ ] Run `npm run test -- --run src/features/analysis/lib/series.test.ts`; confirm the test fails because the feature module does not exist.
- [ ] Implement `diff(baseline: Series, sample: Series): DiffResult` with explicit length validation and a single mapping operation.
- [ ] Update only `GraphPreview` to consume the feature utility; retain a legacy re-export only if an existing consumer requires it.
- [ ] Run the focused test, full frontend test suite, and production build.
- [ ] Commit with `git add frontend/src/features frontend/src/lib frontend/src/components/dashboard/GraphPreview.tsx && git commit -m "refactor: isolate analysis series logic"`.

### Task 4: Establish backend configuration and schema boundaries

**Files:** Create `backend/config.py`, `backend/database.py`, `backend/schemas/chat.py`, and `backend/tests/test_config.py`; modify `backend/app.py`, `backend/chatbox.py`, and `backend/graph_analysis.py`.

- [ ] Write a failing test: set `GEMINI_API_KEY` with `monkeypatch`, call `Settings.from_environment()`, and assert the returned `gemini_api_key` matches.
- [ ] Run `pytest backend/tests/test_config.py -q`; confirm it fails because `backend.config` is absent.
- [ ] Implement frozen `Settings` with `from_environment()` in `backend/config.py`, and move database connection helpers to `backend/database.py`. Move chat Pydantic schemas from `chatbox.py` to `schemas/chat.py`; update imports without altering route schemas.
- [ ] Defer environment reads and provider initialization to application initialization or request handling; preserve existing error/fallback responses.
- [ ] Run focused tests and `python -c 'from backend.app import app; print(app.title)'`.
- [ ] Commit with `git add backend/config.py backend/database.py backend/schemas backend/tests backend/app.py backend/chatbox.py backend/graph_analysis.py && git commit -m "refactor: separate backend configuration and schemas"`.

### Task 5: Extract backend graph-statistics service

**Files:** Create `backend/services/graph_statistics.py` and `backend/tests/test_graph_statistics.py`; modify `backend/graph_analysis.py`.

- [ ] Write a failing test for `summarize_series([1.0,3.0], [2.0,6.0])` asserting `differences.mean_diff == 2.0` and `baseline_stats.count == 2`.
- [ ] Run `pytest backend/tests/test_graph_statistics.py -q`; confirm failure because the service is absent.
- [ ] Implement `summarize_series(baseline: Sequence[float], sample: Sequence[float]) -> dict[str, dict[str, float | int]]` using pure Python calculations.
- [ ] Delegate statistics generation from the router while preserving its JSON response keys and fallback behavior.
- [ ] Run focused tests and add a route-level assertion of response keys.
- [ ] Commit with `git add backend/services backend/tests backend/graph_analysis.py && git commit -m "refactor: isolate graph statistics service"`.

### Task 6: Complete feature-oriented frontend moves

**Files:** Create public entry points under `frontend/src/features/{auth,dashboard,analysis}`; move auth components/context, dashboard components, FTIR hook, and FTIR API adapter; modify `App.tsx`, `pages/Dashboard.tsx`, and affected imports.

- [ ] Write a failing app-route test that navigates to `/login`, renders `App`, and asserts the sign-in button is present.
- [ ] Run `npm run test -- --run src/features/auth/app-routing.test.tsx`; verify it exposes the pre-move feature boundary.
- [ ] Use `git mv` to relocate feature-owned modules. Internal imports remain feature-local; cross-feature imports use the public feature entry points. Keep component props, routes, and rendered copy unchanged.
- [ ] Run the focused route test, full frontend test suite, and production build.
- [ ] Commit with `git add frontend/src && git commit -m "refactor: organize frontend by feature"`.

### Task 7: Final regression verification

**Files:** Modify `README.md` only if setup instructions reference removed environments or generated files.

- [ ] Run `git ls-files 'backend/.venv/**' 'backend/**/__pycache__/**' 'backend/static/generated_graphs/**'` and `rg 'SampleSidebar\\.old|ExportDialog\\.old|components/(ftir|modals|samples)' frontend/src`; both must print nothing.
- [ ] Run `(cd frontend && npm run test -- --run && npm run build)`, `pytest backend/tests -q`, and `python -c 'from backend.app import app; print(app.title)'`.
- [ ] Run `git diff --check` and inspect `git status --short`; update README only if validation exposed stale setup information.
- [ ] Commit documentation only if changed: `git add README.md && git commit -m "docs: clarify local setup"`.
