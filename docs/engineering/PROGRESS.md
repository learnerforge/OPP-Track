# Engineering progress

## Current phase

P0 integrity remediation complete; P1 persistence and deployed-app correctness in progress.

## Completed

- Audited the deployment, API, data pipeline, legacy frontend trees, workflows,
  and current test commands.
- Recorded verified risks in `issues_working.txt`.
- Added an engineering map, requirements matrix, implementation plan, and test
  report to avoid repeated repository-wide discovery.
- Added a read-only published-data integrity verifier, wired it into the
  guarded publisher and CI, and republished the verified 2,887-item snapshot.
- Made edit saves preserve earlier overridden fields and refuse to write when
  the existing Blob document cannot be read reliably.
- Fixed the API fallback so it retrieves every paginated catalog page.

## Important findings

- Vercel deploys `app/`, while root CI targets legacy `src/`.
- The manifest SHA did not match the canonical/published bytes at audit time.
- Editing is not securely authenticated and can lose prior field overrides.

## Files changed in this batch

- `issues_working.txt`
- `docs/engineering/REPOSITORY_MAP.md`
- `docs/engineering/REQUIREMENTS_MATRIX.md`
- `docs/engineering/IMPLEMENTATION_PLAN.md`
- `docs/engineering/TEST_REPORT.md`
- `docs/engineering/PROGRESS.md`

## Tests run

- `npm run typecheck`, `npm run typecheck:app`, and `npm run typecheck:api`: pass.
- `npm run validate` and `npm run verify:data-integrity`: pass.
- `npm test`: 23/23 pass.
- `npm run build:app`: pass.
- `python -m pytest tests -q`: 13/13 pass.

## Known blockers

- Secure server-side authentication needs a deployment-owned identity/session
  decision and environment configuration; the existing browser-only gate is
  deliberately not claimed as security.

## Next three priorities

1. Replace browser-shipped edit authentication with server-side sessions.
2. Add edit/API regression tests and align CI/package scripts with `app/` and `api/`.
3. Consolidate legacy frontend trees and reconcile product documentation.

