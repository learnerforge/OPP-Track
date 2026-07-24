# CODING_RULES.md

Conventions for any code written for OppTrack (whether by Claude or by Ganesh directly). Goal: keep a single-file personal tool maintainable despite its small scope.

---

## 1. General Principles

1. **Simplicity over cleverness.** This is a personal tool, not a production SaaS product. Prefer the obvious, readable solution over a "smart" abstraction.
2. **Single-file artifact by default.** Keep component, styles, and logic in one file unless a specific piece of complexity justifies splitting (per artifact conventions).
3. **No premature architecture.** Don't build for scale (multi-user, high volume) until v2 is actually greenlit (see `TASKS.md` Phase 3 gating).
4. **Every storage operation is wrapped in try/catch.** No exceptions — a failed read/write must never crash the whole dashboard (see `RISKS_AND_EDGE_CASES.md` E2, E3).

---

## 2. Data Handling Rules

- **Single source of truth:** all opportunity data lives under the one key `opportunities-list` (see `ARCHITECTURE.md` §4). Do not introduce a second key for the same data.
- **Derived fields are never stored.** `days_remaining` and urgency tier are always computed at render time from `deadline` and the current date — never persisted, to avoid staleness bugs.
- **IDs are generated client-side** at creation time and never reused or regenerated on edit.
- **Dates are stored as ISO strings (`YYYY-MM-DD`)** — never as `Date` objects or locale-formatted strings, to keep sorting and parsing unambiguous.
- **Never overwrite the full stored list without first successfully reading it.** Always read-modify-write, not blind-write, to avoid clobbering data from a previous session.

---

## 3. Naming Conventions

- **Variables/functions:** camelCase (`loadOpportunities`, `daysRemaining`)
- **Data model fields:** snake_case in storage (`date_added`, `days_remaining`) to match the JSON schema defined in `ARCHITECTURE.md` §4 — keep storage schema stable even if UI-layer variables use camelCase
- **Component names:** PascalCase (`AddEntryForm`, `DashboardView`, `OpportunityCard`)
- **Storage keys:** kebab-case, prefixed by domain (`opportunities-list`), per the persistent-storage key design pattern

---

## 4. UI/UX Rules

- **Add Entry must take < 15 seconds.** Any change that adds a required field or extra step to entry needs explicit justification against this NFR (`PRD.md` §6).
- **Never block the UI on a storage round-trip for reads that already have local state.** Use optimistic updates (update in-memory state immediately, persist in the background).
- **Always show a loading state on first load**, and a distinct **error state** (not a blank screen) if the initial read fails.
- **Urgency color-coding must be consistent everywhere it appears** (Dashboard, Weekly Review, any future view) — define the tier logic once, reuse it, don't duplicate the threshold values in multiple places.
- **Destructive actions (delete) require confirmation.** No silent deletes.

---

## 5. Error Handling Rules

- Every `window.storage.get/set/delete` call must be in a try/catch block.
- On read failure: show an error state with a retry button; do not fall back to an empty list silently (that could look like data loss when it's actually a transient error) — distinguish "no data yet" (key never existed) from "failed to load" (error thrown).
- On write failure: preserve the user's unsaved input/optimistic UI state, show a retry option, never lose what the user just typed.

---

## 6. Styling Rules

- Use Tailwind core utility classes only (per artifact platform constraints — no custom Tailwind config, no compiler-dependent classes).
- Keep the design clean and legible over decorative — this is a tool used quickly, repeatedly, often on mobile between classes.
- Reuse a single color-tier mapping (🔴/🟡/🟢/⚪) as constants, not inline hardcoded hex values scattered through the code.

---

## 7. What NOT to Do

- Do not add `localStorage`/`sessionStorage` calls — unsupported in this artifact environment; use the provided `window.storage` API only.
- Do not introduce a backend service, API server, or database — out of architecture scope (`ARCHITECTURE.md` §9).
- Do not hardcode today's date — always compute dynamically (`new Date()`), since this tool will be used across many future sessions.
- Do not build scraping logic into this codebase under any circumstance — discovery is explicitly out of scope for this tool (`ARCHITECTURE.md` §1, `RISKS_AND_EDGE_CASES.md` E12).
- Do not add multi-user/shared-storage code paths until the v2 sharing decision in `KNOWN_ISSUES_AND_DECISIONS.md` is explicitly resolved.

---

## 8. Testing / Verification Expectations

Before considering any change "done":
- [ ] Add an entry, reload the page/session, confirm it persists
- [ ] Add entries with deadlines: today, tomorrow, next week, next month, yesterday — confirm correct urgency tier and archive behavior
- [ ] Filter by each Type and Status value, confirm correct subset shown
- [ ] Delete an entry, confirm removal persists after reload
- [ ] Simulate a storage read failure (if feasible) and confirm the error state renders instead of a crash
