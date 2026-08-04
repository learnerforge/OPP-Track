# Research Workflow

How OppTrack's opportunity data is researched and shipped, so updates are repeatable
instead of ad-hoc. The app runtime is unchanged by this process — data still lives in
`src/lib/storage.ts` (`SEED_DATA`) and ships to users through the version migration.

## Where the data lives

| Layer | Location | Purpose |
| --- | --- | --- |
| Source of truth | `SEED_DATA` in `src/lib/storage.ts` | The curated opportunities. **Edit here.** |
| Version marker | `SEED_VERSION` in `src/lib/storage.ts` | Bump when `SEED_DATA` changes so the migration re-ships it. |
| Runtime copy | `localStorage` key `opportunities-list` | What the browser actually reads/writes. |
| Migration | `loadOpportunities()` in `src/lib/storage.ts` | On version bump: refreshes `Not Started` seeds from `SEED_DATA`, preserves user-edited statuses, drops orphaned `seed_*` ids. |

## The loop

1. **Audit a seed range** — verify each entry against its live page (title, deadline,
   eligibility, status, link, prizes). Use the agent-reach skill for web research.
2. **Record findings** — append a dated entry to `docs/RESEARCH_LOG.md` before editing.
3. **Apply edits** — change only the affected entries in `SEED_DATA` in
   `src/lib/storage.ts`. Do not touch `loadOpportunities`/`saveOpportunities`.
4. **Validate** — `npm run validate` (must be 0 errors). Then `npm run validate:links`
   to HTTP-check every link (network calls; catches dead pages like the old Qualcomm URL).
5. **Bump the version** — increment `SEED_VERSION` whenever `SEED_DATA` changed in a way
   existing users should receive (edits to `Not Started` entries, new seeds, removed
   seeds). If the diff only touches entries users may already have edited (e.g. a note
   on an `Applied` seed), the migration won't ship it — note that in the log.
6. **Test** — `npm test` (migration regression tests must all pass).
7. **Build check** — `npm run typecheck && npm run build`.
8. **Ship** — restart the dev server (`npm run dev`); tell the user to hard-refresh
   (Ctrl+Shift+R). The migration delivers the update on load.

## Verification checklist (per seed)

- [ ] Title matches the live page exactly (no year suffix unless the page has one)
- [ ] `deadline` is the real submission/registration close date from the page
- [ ] `status` is one of `Not Started | Applied | In Progress | Rejected | Completed` —
      closed/ended events are expressed via `notes` + `deadline`, **never** a new status
- [ ] `link` resolves (run `npm run validate:links`) or is intentionally empty
      (email-only applications like `seed_003`)
- [ ] `eligibility`, `tags`, `notes` are accurate and note "closed" / "watch next cycle"
      where registration has ended
- [ ] no duplicate title (validator enforces this)

## Conventions

- **Never add a new status value.** The union is closed (`src/types/opportunity.ts`).
  "Registration closed" / "Event over" goes in `notes` (see `seed_032`, `seed_039`,
  `seed_113` for the pattern), and the deadline should reflect reality.
- **Stale entries get flagged by the validator.** `npm run validate` warns when a
  `Not Started` seed has a passed deadline — that's the signal to either close it out
  (status + notes) or fix the deadline.
- **Orphaned `seed_*` ids are dropped by the migration.** If a seed is removed from
  `SEED_DATA`, existing users' copies of it disappear on next load. Record removals in
  the research log.
- **No scraping at runtime.** Discovery is a dev-time research activity only
  (`docs/CODING_RULES.md`).
