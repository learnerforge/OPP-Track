# KNOWN_ISSUES_AND_DECISIONS.md

A running log of decisions made, their rationale, and currently open/unresolved questions. Update this file whenever a meaningful decision is made or an open question is resolved — treat it as the project's memory across sessions.

---

## Decision Log

### D1 — No live scraping of 1000+ sites
**Decision:** OppTrack will not scrape external websites. Discovery relies entirely on configuring alerts on existing aggregator platforms (Layer 1).
**Rationale:** 1000+ sites means 1000+ fragile scrapers to maintain, frequent breakage from layout changes, possible bot-blocking, and low marginal yield since aggregators already consolidate almost everything relevant. Cost/maintenance far outweighs benefit for a personal tool.
**Status:** Final for v1 and v2. Would only be revisited if a specific high-value, non-aggregated source is identified with a stable structure (see E12 in `RISKS_AND_EDGE_CASES.md`).

### D2 — Single aggregate storage key instead of one key per opportunity
**Decision:** All opportunities are stored in one JSON array under the key `opportunities-list`, not as individual keys per opportunity.
**Rationale:** The Dashboard always needs the full list to sort/filter; using one key per entry would require N sequential reads on every load, which is slower and against storage best practices (batch related data together).
**Status:** Final for the scale this tool operates at (tens–low hundreds of entries). Revisit only if scale changes dramatically (see E5 in `RISKS_AND_EDGE_CASES.md`).

### D3 — Single-user (private storage) for v1
**Decision:** All storage calls use `shared: false` in v1 — no other user can see Ganesh's data.
**Rationale:** MVP is explicitly scoped to Ganesh only (`PRD.md` §2 Non-Goals). Sharing introduces data-scope complexity (see Open Question Q1 below) that isn't justified until the MVP itself is validated.
**Status:** Final for v1. Open question for v2 below.

### D4 — Derived fields (days remaining, urgency tier) are never persisted
**Decision:** `days_remaining` and color-tier are computed at render time from `deadline` vs. current date, not stored as fields.
**Rationale:** Storing them would risk staleness (e.g., an entry showing "5 days left" three days after being viewed). Computing fresh avoids an entire class of sync bugs.
**Status:** Final.

### D5 — Dates stored as ISO strings, assumed IST end-of-day
**Decision:** All deadlines are stored as `YYYY-MM-DD` strings and treated as IST end-of-day by convention.
**Rationale:** Avoids timezone ambiguity from platforms that list deadlines in UTC or unspecified timezones, while keeping the data model simple (no timezone field needed) given Ganesh operates in a single timezone.
**Status:** Final for v1. See E9 in `RISKS_AND_EDGE_CASES.md`.

### D6 — Feature-gating: v1.1 and v2 features require real usage first
**Decision:** No v1.1 features (tags, stats, weekly review mode) will be built until the MVP has been actively used for 2+ weeks. No v2 features until 3-4+ weeks of MVP usage.
**Rationale:** Prevents building unused features based on speculation rather than real friction encountered during actual use (see R3 in `RISKS_AND_EDGE_CASES.md`).
**Status:** Active constraint — check `TASKS.md` before starting Phase 2 or Phase 3 work.

---

## Open Questions (Unresolved)

### Q1 — Should OppTrack support sharing with MGIT batchmates?
**Context:** Considered as a v2 feature (`PRD.md` §5, `ARCHITECTURE.md` §8).
**Open issue:** If implemented, personal fields (Notes, Status = "Applied"/"Rejected") likely need to stay private even if the base opportunity listing (Title, Link, Deadline) is shared. This requires either (a) two separate keys — one shared, one private, joined by opportunity ID, or (b) a per-user shared key namespaced by username. Neither has been designed yet.
**Decision needed by:** Only before starting Phase 3 (`TASKS.md`). Not urgent.

### Q2 — Should eligibility auto-checking be added?
**Context:** Raised in `PRD.md` §10 Open Questions.
**Open issue:** Could flag opportunities where eligibility text mentions "4th year only" while Ganesh is 3rd year, reducing manual reading. But this requires parsing free-text eligibility strings reliably, which is error-prone (see E10, E11 in `RISKS_AND_EDGE_CASES.md`).
**Current lean:** Likely not worth building — manual reading of a short eligibility field per entry is low-cost. Revisit only if mis-tracking eligibility becomes a repeated real problem.

### Q3 — Should rolling/ongoing deadlines get a dedicated non-date value?
**Context:** Raised in `RISKS_AND_EDGE_CASES.md` E8.
**Open issue:** v1 requires a best-guess date for every entry (using Notes for caveats). Whether a proper "Rolling/Ongoing" deadline type is worth the added complexity is unresolved.
**Current lean:** Defer to v1.1 if it comes up more than a couple of times in practice.

### Q4 — Is a manual backup/export mechanism needed in v1?
**Context:** Raised as a v1.1 candidate in `PRD.md` §5 and `TASKS.md` Phase 2.
**Open issue:** Persistent storage should be durable, but no automatic backup exists if something goes wrong at the platform level. Worth a simple "export as JSON" button even in v1, or acceptable to wait?
**Current lean:** Low priority for MVP (small dataset, low catastrophic risk), but cheap to add — reconsider bundling into Phase 1 if implementation time allows.

---

## Known Issues (Not Yet Fixed / Not Yet Built)

_This section will be populated once OppTrack is actually implemented and used. As of this writing (July 25, 2026), the MVP has not yet been built — see `TASKS.md` Phase 1 for current build status._

| Issue | Severity | Status |
|---|---|---|
| _(none yet — populate after MVP build and first usage cycle)_ | | |

---

## How to Use This Document
- Add a new entry to **Decision Log** whenever a non-trivial choice is made (naming a key, choosing a data shape, deciding to defer a feature).
- Move items from **Open Questions** to **Decision Log** once resolved, keeping a short rationale.
- Add to **Known Issues** as soon as a bug or limitation is discovered during real use — even minor ones, so patterns can be noticed over time.
