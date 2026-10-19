# ENGINE — runbook for the scheduled data engine (milestone E5)

Operational reference for the three GitHub Actions workflows in
`.github/workflows/`, the publish/restore procedures, and the `src/` freeze.
Sources of record: `fullstack.md` §6.3, §11.6, §14.1. Everything below describes
what these files do today — nothing aspirational.

---

## 1. What runs, and when

| Workflow | Trigger | Scrape command | Timeout |
|---|---|---|---|
| `verify.yml` | `push`, `pull_request`, `workflow_dispatch` | — (freeze check + typecheck + test + build + validate + Python tests) | 15 min |
| `scrape-full.yml` | `schedule: "0 */8 * * *"` (**00:00 / 08:00 / 16:00 UTC** = 05:30 / 13:30 / 21:30 IST, decided 2026-10-19) + manual | `run_all.py --multi --detailed --enrich --validate` | 120 min |
| `scrape-quick.yml` | `workflow_dispatch` **only** (no schedule) | `run_all.py --multi --validate` | 30 min |

Shared guard rails on both scrape workflows:

- `concurrency: {group: data-publish, cancel-in-progress: false}` — the two can
  never overlap, so there is exactly **one writer** at any time.
- `env: TZ: UTC` — all date handling on the runner is UTC.
- `permissions: contents: write` (commit/push) **+ `issues: write`** (the single
  failure alert — GitHub grants the token no issue access otherwise, and the
  no-secrets rule rules out alternatives).
- Caches: pip (`requirements.txt`), npm (`package-lock.json`), and
  `~/.cache/ms-playwright` (browser binaries, keyed on `requirements.txt`).

`verify.yml` details: checkout with `fetch-depth: 0` (the freeze checker needs
merge-base history), Node pinned from `.nvmrc` (22.22.3), Python 3.13 with pip
cache, then in order: `npm ci` → `scripts/check_freeze.py` → `npm run typecheck`
→ `npm test` → `npm run build` → `npm run validate` → Python unittest discovery
→ `scripts/sanity_gate.py --current … --allow-init` (best-effort,
`continue-on-error: true` until the E2 CLI is confirmed — delete that flag to
make it blocking). The freeze check compares `--base origin/<base_ref>` on pull
requests and `--base <push-before-SHA>` on pushes; other events use the default
`origin/main` with an in-script fallback chain.

Schedules only fire from the repository's **default branch** (`master`). GitHub
also disables scheduled workflows after ~60 days without repository activity —
re-enable under the workflow's "..." menu if the schedule goes quiet.

### ⚠️ Actions-minutes budget — OPEN DECISION

| | |
|---|---|
| Chosen cadence costs | 3 full runs/day × ~75 min ≈ **6,800 Actions min/month** |
| Repo is **private** → free tier | **2,000 min/month** |
| Options (§11.6) | **(i)** make the repo **public** at deploy (recommended anyway for a public catalog, unlimited minutes) · **(ii)** pay for a larger plan · **(iii)** degrade to every-8-h *quick* + *weekly full* (~1,400 min/month) |
| If nothing changes | the quota is hit mid-month, remaining runs **queue**, and the E8 freshness watchdog fires — that is the intended alarm |

This must be settled before E5 goes live; until then, treat scheduled-run
failures with a `cancel`/`queued` status as the budget, not as pipeline breakage.

---

## 2. The publish sequence (what `scrape-full.yml` / `scrape-quick.yml` do)

Both workflows run the identical guarded sequence (only the scrape flags and
timeout differ):

1. `pip install -r requirements.txt` → cached Chromium via
   `python -m patchright install --with-deps chromium` **and**
   `python -m playwright install --with-deps chromium` (scrapling's
   `StealthyFetcher` drives **patchright**; the two pin different chromium
   revisions, so both are installed into the shared ms-playwright cache).
2. Scrape → writes `data/scraped_opportunities.json` (atomic).
3. `npm run validate` — publish gate; **fail = stop, nothing is published.**
4. `python scripts/sanity_gate.py --current data/scraped_opportunities.json
   --previous data/manifest.json` — regression gate (±20 % totals, per-source
   bounds); fail = stop.
5. `python scripts/publish_dataset.py --with-seeds` — manifest + `sha256`,
   `public/data/` copy, seed regeneration (the only allowed write to
   `src/lib/storage.ts`), backup rotation, publish report.
6. **Commit, only if there is something to commit:** skipped entirely when
   `git status --porcelain` is empty *or* when the explicit file set
   (`data/scraped_opportunities.json data/manifest.json data/scraper_health.json
   data/reports public/data src/lib/storage.ts`) has no diff. Identity:
   `github-actions[bot]`; message:
   `data: publish <sha8> (<count> items) [skip ci]`. Push is retried up to
   3× with `git pull --rebase` (single-writer discipline).
7. Upload artifacts: raw JSON + `data/reports/`, `retention-days: 90`,
   named `dataset-<run number>`.
8. `curl -fsS "$PROD_URL/api/health"` — only when the repository variable
   `PROD_URL` is set (Settings → Secrets and variables → Actions → Variables);
   the step is skipped otherwise. An HTTP failure fails the job.
9. On job failure **only**: one issue titled **`data-pipeline-alert`** is
   created — or, if one is already open, the run URL is commented onto it.
   Never more than one open alert issue.

A `[skip ci]` marker keeps Actions from re-running on the bot commit.
**Watch-out:** Vercel's Git integration also honours `[skip ci]` (it can skip
the rebuild the stage-1 freshness model depends on) — confirm on first publish
that the data commit still triggers a Vercel deployment; if it does not, drop
the marker (GITHUB_TOKEN pushes already do not re-trigger Actions workflows).

---

## 3. Running the pipeline locally (Windows)

Prerequisites: Python 3.13 (`python --version` → 3.13.x), Node 22.22.3
(`nvm use` reads `.nvmrc`), git.

```bat
:: one-time setup
pip install -r requirements.txt
python -m patchright install chromium
python -m playwright install chromium
npm ci

:: full pass (same flags as scrape-full)
python scripts/scrapers/run_all.py --multi --detailed --enrich --validate
npm run validate

:: publish half (E2/E3 scripts; present after those milestones land)
python scripts/sanity_gate.py --current data/scraped_opportunities.json --previous data/manifest.json
python scripts/publish_dataset.py --with-seeds
```

`npm ci` and `npm run build` need the committed `package.json` /
`package-lock.json` to be in sync — if `npm ci` fails locally, fix the
lockfile before blaming the pipeline.

## 4. Manual quick pass

- **Via Actions (preferred):** repo → *Actions* → *scrape-quick* → *Run
  workflow* → branch `master`. 10–20 min, publishes exactly like the scheduled
  run. This is the recovery tool when one source went stale — the first run
  after enabling workflows should be this (§11.8 step 3).
- **Locally:** `python scripts/scrapers/run_all.py --multi --validate`, then the
  publish half from §3.

---

## 5. Verifying integrity

| Check | How |
|---|---|
| Byte integrity | `sha256` of `data/scraped_opportunities.json` must equal `manifest.json.sha256`: `python -c "import hashlib,pathlib;print(hashlib.sha256(pathlib.Path('data/scraped_opportunities.json').read_bytes()).hexdigest())"` |
| Live health | `GET <PROD_URL>/api/health` — 200, fresh `age_hours`, `sha8` matching the manifest (E4) |
| Live manifest | `GET <PROD_URL>/data/manifest.json` — counts sane (E3+) |
| Idempotence | Re-run publish on unchanged data → no diff → **no commit** (the porcelain guard). A second identical quick run must produce no data commit. |
| Audit trail | every publish writes `data/reports/publish-*.md`; every run uploads `dataset-<run>` artifacts (90 days) even when it fails |
| Freeze | `python scripts/check_freeze.py` — see §7 |

---

## 6. Restore drill

Goal: a bad publish is undone inside **one** Vercel deploy.

1. **Revert the bad data commit** (history is the restore path, §14.8 item 4):
   `git log --oneline -10 -- data/scraped_opportunities.json` →
   `git revert <sha>` → push → Vercel rebuilds with the previous dataset.
   Confirm with `/api/health` freshness/`sha8`.
2. **Tag the restored state** so it can't be squashed away anonymously:
   `git tag -a data-restore-YYYYMMDD && git push origin data-restore-YYYYMMDD`
   (the *weekly* tags themselves arrive with E8).
3. **Backup copy:** `data/backups/` holds the rotated copies (7 daily + 8
   weekly, written by `scripts/rotate_backups.py` once E1 lands). Copy the
   wanted snapshot over `data/scraped_opportunities.json`, commit, push.
4. **Release archive:** attach the restored `data/scraped_opportunities.json`
   (plus manifest) to a GitHub Release (*Releases* → *Draft a new release*,
   tag `data-restore-YYYYMMDD`) so it survives history maintenance.
5. Re-run the publish sequence (§2) so manifest, `public/data/` and seeds are
   regenerated from the restored file — never restore only one of the four
   views of the data.

---

## 7. Alert response — `data-pipeline-alert`

The scrape workflows open **one** issue with that exact title on failure and
append the run URL on every subsequent failure while it stays open.

1. Open the run URL in the issue body; identify the failed step:
   - **Scrape step** → per-source errors are in the log; sources fail soft
     inside the pipeline, so a red scrape step usually means timeout/infra.
   - **Node validation / sanity gate** → the dataset is *bad*; nothing was
     published. Read the gate output (which counts regressed, which source
     collapsed) — this is the "broken scraper publishes a tiny dataset" rail.
   - **Health poll** → data published but the live URL didn't reflect it:
     check the Vercel deployment of the data commit (§2 watch-out).
   - **Commit/push step** → concurrent push won the rebase race or a path set
     changed; re-run the workflow.
2. Recover with a **manual `scrape-quick`** run (§4) once the cause is fixed.
3. Close the issue after a green run — a later failure re-opens by creating a
   fresh issue (the workflow only comments while one is open).

---

## 8. The `src/` freeze (§14.1)

- **Nothing under `src/` changes** except `src/lib/storage.ts`, written only by
  `scripts/regenerate_seeds.py` (Exception A), and paths allowed by
  [`docs/FREEZE_ALLOWLIST.md`](FREEZE_ALLOWLIST.md) (Exception B — today: none;
  the E6 patch lines there are commented out).
- CI enforces it: `verify.yml` runs `scripts/check_freeze.py` on every
  push/PR; violations exit 1 with per-path reasons.
- Locally:

  ```bat
  python scripts\check_freeze.py             :: committed range only (never flags your uncommitted work)
  python scripts\check_freeze.py --worktree  :: also inspect uncommitted src/ changes
  python scripts\check_freeze.py --base HEAD~1  :: inspect a specific range
  ```

- To grant an exception: edit `docs/FREEZE_ALLOWLIST.md` (uncomment / add a
  bare `src/...` path), justify it in review, and **retire the entry when its
  milestone is done** — an entry left behind silently lifts the freeze.
