# Engineering standards

This repository is maintained as a production-quality application. Changes must
follow these standards:

1. Preserve existing behavior: keep HTTP paths, methods, request and response
   formats, UI copy, and analysis methodology stable unless a change is
   explicitly requested.
2. Keep boundaries focused: organize code by feature and responsibility, keep
   services transport-independent where practical, and limit cross-feature
   imports to public entry points.
3. Handle failures explicitly: use actionable exceptions and route-level error
   mapping; do not add broad, duplicated exception handlers.
4. Protect configuration and secrets: centralize environment access, defer
   provider setup until application initialization or request handling, and
   never expose environment values in responses or logs.
5. Test behavior at its seams: add focused tests for pure transformations and
   services, preserve route-level regression coverage, and run the relevant
   frontend and backend suites before handing off changes.
6. Keep changes reviewable: make the smallest coherent change, preserve
   dependency declarations, inspect diffs for accidental edits, and document
   verification evidence.

## Test expectations

- Frontend changes should run the relevant Vitest tests and the production
  build (`npm run test -- --run` and `npm run build` from `frontend`).
- Backend changes should run the relevant pytest tests (`pytest backend/tests
  -q`) and verify application imports without external credentials.
- Refactors must include regression coverage for public routes and extracted
  pure logic where applicable.

## Generated-artifact hygiene

Do not commit local virtual environments, Python bytecode caches, or generated
graph images. These artifacts are ignored by Git and should be removed from the
working tree when cleaning them up. Keep dependency declarations in
`backend/requirements.txt` and `frontend/package-lock.json`; do not replace
them with generated environment contents.
