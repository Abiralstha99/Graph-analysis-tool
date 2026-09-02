# Repository Cleanup Design

## Goal

Restructure the application into clear, testable frontend and backend boundaries while preserving its public API routes and user-facing behaviour. Remove generated and environment-specific files from version control and establish durable project engineering instructions.

## Current-State Findings

- The repository tracks 861 files beneath `backend/.venv`, as well as Python bytecode and generated graph images.
- The frontend has invalid barrel exports for removed component directories and legacy component files.
- Frontend domain types, including `ParsedCSV`, `RangeWeight`, and `ScoringMethod`, are defined in multiple modules.
- The dashboard, graph preview, FTIR service, API application, and chat/analysis routers mix orchestration with domain logic, making them difficult to test and extend.

## Target Architecture

### Frontend

Adopt a feature-oriented structure beneath `frontend/src`:

- `features/auth`: authentication UI, context, API adapter, and auth types.
- `features/analysis`: FTIR analysis API adapter, analysis hooks, calculation helpers, and analysis types.
- `features/dashboard`: dashboard composition and dashboard-specific components.
- `components/ui`: reusable, domain-neutral interface components.
- `lib`: small framework-independent utilities such as series calculations.
- `types`: only truly cross-feature shared types.

Each feature exposes a narrow public barrel. Internal modules import through feature-local relative paths; cross-feature imports use the public feature entry point. Stale barrel exports are removed rather than replaced with placeholders.

`GraphPreview` is decomposed into chart configuration/data transformation helpers and focused visual components. `Dashboard` remains the composition root and owns only coordination state. API services handle transport only; pure analysis calculations remain framework-independent and are covered by unit tests.

### Backend

Organize `backend` by responsibility:

- `api`: FastAPI application factory and routers.
- `schemas`: Pydantic request and response models.
- `services`: graph-analysis, chat, authentication, and file-processing application services.
- `core`: configuration, dependency setup, and error-handling primitives.
- `utils`: focused plotting/data helpers.

Existing HTTP paths, methods, request formats, and response formats remain unchanged. Routers perform validation and translate service outcomes to HTTP responses. Services contain use-case orchestration; helpers contain pure data and plotting transformations. Environment/configuration access is centralized and no module performs configuration or provider setup as an import-time side effect.

## Repository Hygiene

Add root `AGENTS.md` documenting the requested production-quality coding standards, test expectations, and artifact hygiene. Remove tracked virtual-environment files, bytecode caches, and generated graph files; extend ignore rules so they cannot be recommitted. Dependency declarations remain in `backend/requirements.txt` and `frontend/package-lock.json`.

The existing user-owned `.DS_Store` working-tree modification is out of scope and will not be changed or staged.

## Error Handling and Compatibility

The cleanup preserves existing client-visible response schemas and fallback behavior. New internal failures use explicit, actionable exceptions and route-level mapping rather than broad, duplicated `except Exception` blocks. Provider/API keys are validated during application initialization or request handling, never exposed in responses or logs.

## Verification

- Frontend: run the Vitest suite, TypeScript/build checks, and add tests for extracted pure logic.
- Backend: add focused unit tests for extracted services/helpers and verify route imports/application startup without external credentials.
- Repository: confirm no tracked virtual-environment, cache, or generated graph artifacts remain and that ignore rules cover them.

## Scope Boundaries

This work is a behavior-preserving refactor. It does not change the product UI, introduce a new API version, change database schema, replace authentication/database providers, or redesign the analysis methodology.
