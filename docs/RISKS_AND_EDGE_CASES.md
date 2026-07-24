# RISKS_AND_EDGE_CASES.md

## 1. Product-Level Risks

### R1 — Tool is built but not used consistently
**Risk:** Ganesh sets up OppTrack but doesn't form the habit of logging opportunities as he finds them, and the tool goes stale.
**Mitigation:** Keep entry time under 15 seconds (hard NFR, see `PRD.md` §6). Tie usage to the "weekly 20-minute ritual" habit already recommended in Layer 1. Do not add friction (e.g., mandatory fields beyond Title/Type/Deadline) in v1.

### R2 — Layer 1 alerts don't catch everything
**Risk:** Some opportunities (especially MGIT-specific or hyper-local ones) never appear on Unstop/Internshala/etc., and are missed entirely regardless of how good OppTrack is.
**Mitigation:** Monthly manual check of college notice boards / department WhatsApp / placement cell announcements as a supplementary (not primary) channel. This is explicitly a human process gap, not something OppTrack-the-tool can fix.

### R3 — Feature creep before MVP validation
**Risk:** Building v1.1/v2 features (tags, stats, browser extension) before confirming the MVP is actually used, wasting effort on unused features.
**Mitigation:** Hard gate in `TASKS.md` — Phase 2 does not start until Phase 1 has 2+ weeks of real usage.

### R4 — False sense of completeness
**Risk:** Ganesh might assume "if it's not in OppTrack, it doesn't exist," and stop actively watching for new opportunity types outside his current Layer 1 setup (e.g., a new platform emerges).
**Mitigation:** Periodic (quarterly) review of whether Layer 1 source list is still current/complete — note this as an ongoing task in `TASKS.md`.

---

## 2. Data & Storage Edge Cases

### E1 — First-time load, no data exists yet
**Case:** `window.storage.get('opportunities-list')` throws/returns null because the key has never been set.
**Handling:** Treat as empty list `[]`, not an error. Show the empty-state UI ("Add your first opportunity").

### E2 — Storage write fails mid-session
**Case:** Network hiccup or storage service error during `saveOpportunities()`.
**Handling:** Keep the optimistic UI update visible but show a non-blocking "not saved — retry" indicator on that entry. Never silently drop data without informing the user. Provide a manual "Retry Save" action.

### E3 — Malformed/corrupted stored data
**Case:** JSON parse fails on load (e.g., partial write from a previous crash).
**Handling:** Catch the parse error, show a clear error state ("Couldn't load your saved data") rather than crashing the whole dashboard. Do not auto-overwrite the corrupted key — surface the raw error so data can potentially be recovered manually before any new write happens.

### E4 — Duplicate entries
**Case:** Ganesh accidentally adds the same opportunity twice (e.g., forgets he already logged it).
**Handling:** v1: no automatic dedup (accept the risk — low cost, manual delete is easy). v1.1 candidate: soft-warn if a new entry's Title + Link closely matches an existing entry.

### E5 — Value size limits
**Case:** The single aggregate key (`opportunities-list`) approaches the 5MB storage value limit if the list grows very large.
**Handling:** Unlikely at personal-use scale (an opportunity object is ~300-500 bytes; 5MB supports roughly 10,000+ entries), but if Ganesh's usage ever scales to sharing with many MGIT batchmates, revisit key-sharding strategy at that point (not a v1 concern).

---

## 3. Date/Deadline Edge Cases

### E6 — Deadline is today
**Case:** `deadline === today`.
**Handling:** Treat as 🔴 highest urgency (0 days remaining), not as "expired." Only move to Archive once `deadline < today`.

### E7 — Deadline already passed at time of entry
**Case:** Ganesh logs something after its deadline has already passed (e.g., logging historical record for reference).
**Handling:** Allow it — auto-place in Archive immediately rather than blocking entry. Useful for record-keeping ("things I looked at but missed") which can itself inform Layer 1 review (R4).

### E8 — Ambiguous or rolling deadlines
**Case:** Some opportunities say "applications reviewed on a rolling basis" or "ongoing" rather than a fixed date.
**Handling:** Allow a non-date placeholder value (e.g., leave deadline field with a special "Rolling/Ongoing" option) that sorts to the bottom of the urgency-based list rather than breaking date parsing. (Flagged as a v1.1 refinement — v1 MVP can require a best-guess date and rely on Notes field for caveats.)

### E9 — Timezone ambiguity
**Case:** "Deadline: July 30" — is that IST end of day? Some platforms list deadlines in UTC.
**Handling:** Treat all dates as IST end-of-day by convention (Ganesh's local timezone) unless the Notes field specifies otherwise. Document this convention in the UI (e.g., small helper text near the date field).

---

## 4. Eligibility Edge Cases

### E10 — Eligibility criteria that change after logging
**Case:** An opportunity's eligibility (e.g., CGPA cutoff) is updated by the organizer after Ganesh already logged it.
**Handling:** Out of scope for automatic detection (no live scraping, per `ARCHITECTURE.md` §1). Mitigation is behavioral: always re-check the original link before applying, treat OppTrack's Eligibility field as "last known" not "guaranteed current."

### E11 — Opportunity not actually eligible (logged by mistake)
**Case:** Ganesh logs something and later realizes he doesn't meet eligibility.
**Handling:** Use Status = "Rejected" (or a future "Not Eligible" status option) rather than deleting — preserves a record for pattern-recognition ("I keep finding things requiring 4th year — maybe adjust Layer 1 filters").

---

## 5. Scope-Boundary Risks (Why Certain Things Are Explicitly Not Built)

### E12 — Temptation to "just add a scraper for X site"
**Risk:** Over time, pressure to scrape one more site "since it's easy" could snowball back into the original 1000-site maintenance problem.
**Handling:** Any scraping proposal must be evaluated against: (a) does an aggregator already cover this? (b) is the site's structure stable enough to not break weekly? Default answer should be "add it to Layer 1 alerts/bookmarks instead," not "add a scraper."

### E13 — Multi-user sharing introduces data-scope bugs
**Risk:** If v2 shared-mode is ever built, mixing `shared: true` and `shared: false` storage calls incorrectly could leak Ganesh's personal notes/status to other users.
**Handling:** If/when v2 sharing is built, keep personal fields (Notes, Status) in a private key even if the core opportunity listing is shared — see `KNOWN_ISSUES_AND_DECISIONS.md` for the open design question.
