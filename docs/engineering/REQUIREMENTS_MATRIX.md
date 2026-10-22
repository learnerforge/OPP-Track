# Requirements matrix

| ID | Requirement | Evidence | Status | Verification / limitation |
|---|---|---|---|---|
| R1 | Publish a refreshed opportunity catalog | README, workflow, `scripts/` | PARTIAL | Pipeline exists; manifest integrity repair in progress |
| R2 | Serve catalog and metadata via API | `api/`, `docs/API.md` | IMPLEMENTED | Needs API-handler tests |
| R3 | Browse/search/filter the catalog | `app/src/pages/Events.tsx` | PARTIAL | Static loading works; fallback returns at most 100 records |
| R4 | Protect personal edits | `app/src/auth.ts`, `api/edits.ts` | BROKEN | Client-side gate and browser-visible token are not authorization |
| R5 | Preserve edits across catalog publication | `api/_lib/edits.ts` | PARTIAL | Later partial edits overwrite prior overridden fields |
| R6 | Validate and prevent bad data publications | validator, sanity gate, workflow | PARTIAL | Add exact manifest/asset integrity verification |
| R7 | Keep deployment documentation accurate | README/docs | BROKEN | Documents conflict with deployed architecture and catalog state |

