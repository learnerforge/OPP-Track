# Test report

## Baseline (2026-10-22)

| Command | Result | Notes |
|---|---|---|
| `npm run typecheck` | PASS | Root legacy `src/` |
| `npm run typecheck:app` | PASS | Deployed app |
| `npm run typecheck:api` | PASS | Vercel functions |
| `npm run validate` | PASS | 2,887 records, 70 sources; three allowed duplicate-title warnings |
| `npm run verify:data-integrity` | PASS | Canonical file and served snapshot hash to `0072aef6…` |
| `npm test` | PASS | 23 legacy migration tests |
| `npm run build:app` | PASS | Production Vite build completed |
| `pytest tests -q` | PASS | 13 sanity-gate tests |

The initial sandbox blocked `esbuild` and temp-directory operations; the final
test/build commands were rerun with approved local execution and passed.

