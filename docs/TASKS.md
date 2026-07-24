# TASKS.md

Task list derived from `PRD.md` §5 (Features) and §8 (Rollout Plan). Organized by phase. Check off as completed.

---

## Phase 0 — Layer 1 Setup (Human config, no code)
Owner: Ganesh · Est. time: ~1 hour, one-time

- [ ] Create Unstop account; set filter for year = 3rd year, relevant branch; enable notifications
- [ ] Create/verify Reskilll account; browse and bookmark active hackathons
- [ ] Create Internshala account; set saved search + enable daily email alert
- [ ] Set up LinkedIn saved search: "Internship" + domain keywords + India; enable alert
- [ ] Set up a Google Alert: `"hackathon" OR "internship" 3rd year engineering India 2026`
- [ ] Join 2-3 curated Telegram/Discord channels for Indian student hackathons/internships
- [ ] Bookmark Google Cloud Skills Boost, Microsoft Learn, AWS Skill Builder, Coursera financial-aid page
- [ ] Note down all Layer 1 sources in `docs/KNOWN_ISSUES_AND_DECISIONS.md` (or a simple `SOURCES.md`) for future reference

**Exit criteria:** Ganesh receives at least one automated alert/notification from each configured platform within a week, without manually visiting the site.

---

## Phase 1 — OppTrack MVP Build ✅
Owner: Claude (build) / Ganesh (review) · Target: functional artifact usable immediately

### 1.1 Data Layer
- [x] Define opportunity data model (per `ARCHITECTURE.md` §4) — `src/types/opportunity.ts`
- [x] Implement `loadOpportunities()` — read `opportunities-list` key, handle "key doesn't exist yet" as empty list — `src/lib/storage.ts`
- [x] Implement `saveOpportunities(list)` — write full list, wrapped in try/catch — `src/lib/storage.ts`
- [x] Implement unique ID generator — `src/utils/date.ts`

### 1.2 Add Entry Form
- [x] Build form UI: Title, Type (dropdown), Source, Link, Deadline (date picker), Eligibility (text), Status (dropdown, default "Not Started"), Notes — `src/components/EntryForm.tsx`
- [x] Client-side validation: Title, Type, Deadline required; Link should look like a URL — `src/utils/validation.ts`
- [x] On submit: generate ID + `date_added`, append to list, persist, reset form — `src/hooks/useOpportunities.ts`
- [x] Show success confirmation (brief, non-blocking)

### 1.3 Dashboard View
- [x] Render list sorted ascending by `deadline` — `src/hooks/useFilters.ts`
- [x] Compute `days_remaining` per entry at render time (not stored) — `src/utils/date.ts`
- [x] Apply urgency color tiers (🔴/🟡/🟢/⚪) per `ARCHITECTURE.md` §3.3 — `src/utils/date.ts` + `src/components/OpportunityCard.tsx`
- [x] Move `Completed` or expired (`deadline < today`) entries into a collapsed "Archive" section — `src/components/ArchiveSection.tsx`
- [x] Empty state: friendly message + prompt to add first opportunity when list is empty — `src/components/EmptyState.tsx`

### 1.4 Filter/Search
- [x] Filter by Type (Hackathon/Internship/Certification/All) — `src/components/FilterBar.tsx`
- [x] Filter by Status — `src/components/FilterBar.tsx`
- [x] Filter by Source (dynamic list from existing entries) — `src/components/FilterBar.tsx`
- [x] Free-text search on Title — `src/components/FilterBar.tsx`

### 1.5 Edit/Delete
- [x] Allow editing any field of an existing entry (e.g., updating Status as Ganesh progresses) — `src/components/EntryForm.tsx` + `src/hooks/useOpportunities.ts`
- [x] Allow deleting an entry (with confirmation, since deletes are destructive) — `src/components/OpportunityCard.tsx`

### 1.6 Polish & Error Handling
- [x] Loading state on initial storage read — `src/App.tsx`
- [x] Error state + retry option if storage read/write fails — `src/App.tsx`
- [x] Responsive layout — usable on mobile and desktop — Tailwind responsive classes throughout
- [x] Manual smoke test: add 5 sample entries covering all types/statuses, verify sort/filter/countdown correctness across deadline edge cases (today, tomorrow, past, far future)

**Exit criteria:** Ganesh can add, view, filter, edit, and delete opportunities, and data persists across a page reload/new session. ✅

---

## Phase 2 — v1.1 Enhancements ✅
- [x] Weekly Review Mode — filtered view of "closing soon" + "new/unstarted" entries — `src/components/WeeklyReviewMode.tsx`
- [x] Tags field — add/filter by custom tags (e.g., "AI/ML", "Free", "Paid") — `src/components/FilterBar.tsx` + `src/components/EntryForm.tsx`
- [x] Simple stats panel — counts of Found vs. Applied vs. Completed, this month — `src/components/StatsPanel.tsx`
- [x] Manual export (e.g., copy-as-JSON or CSV) as a lightweight backup mechanism — `src/components/ExportButton.tsx`

**Exit criteria:** All v1.1 features implemented and functional.

---

## Phase 3 — v2 Exploration (only if MVP sustained 3-4+ weeks)
- [ ] Evaluate feasibility of a browser extension / bookmarklet for one-click add
- [ ] Evaluate sharing OppTrack with MGIT batchmates (requires shared-storage design decision — see `KNOWN_ISSUES_AND_DECISIONS.md`)
- [ ] Evaluate Google Calendar sync for deadline reminders
- [ ] Evaluate email digest auto-import feasibility (likely deferred indefinitely — outside artifact sandbox capability)

---

## Ongoing / Maintenance Tasks (not phase-bound)
- [ ] Monthly manual audit of college notice boards / department WhatsApp groups (supplements Layer 1 — see `RISKS_AND_EDGE_CASES.md`)
- [ ] Periodically review whether Layer 1 sources are still yielding relevant results; swap out low-value channels
- [ ] Revisit `KNOWN_ISSUES_AND_DECISIONS.md` when any open question is resolved
