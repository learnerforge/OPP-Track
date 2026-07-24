# PRD: OppTrack — Personal Opportunity Discovery & Tracking System

**Author:** Ganesh (3rd Year, MGIT)
**Document owner:** Ganesh
**Status:** Draft v1.0
**Date:** July 25, 2026

---

## 1. Problem Statement

There are 1000+ websites (college portals, company career pages, hackathon platforms, MOOC providers) publishing hackathons, internships, and MNC certification programs. Manually checking all of them takes 3-4 days per cycle, by which time:

- Deadlines have already passed for time-sensitive opportunities
- Eligibility windows (year of study, branch, CGPA cutoff) have closed
- Duplicate effort is spent revisiting the same low-yield sites

**Core insight:** The long tail of 1000+ sites is not where the leverage is. Opportunities already consolidate into a small number of aggregator platforms (Unstop, Reskilll, Devfolio, HackerEarth, Internshala, LinkedIn, MOOC skill portals). The bottleneck isn't *discovery volume*, it's the lack of a **single, filtered, deadline-sorted view** — and no system to make sure nothing found is later forgotten.

---

## 2. Goals

### Primary Goal
Reduce time spent discovering + tracking opportunities from **3-4 days/cycle to under 30 minutes/week**, while increasing the number of eligible opportunities Ganesh actually applies to.

### Success Metrics
| Metric | Baseline | Target |
|---|---|---|
| Time spent searching per week | ~5-6 hrs | ≤ 30 min |
| Missed deadlines (found late/forgotten) | Unknown, assumed high | 0 |
| Opportunities tracked per month | Ad hoc | 15-25 |
| Opportunities applied to per month | Ad hoc | 8-12 |

### Non-Goals (v1)
- Not building a live 24/7 scraper of 1000 sites (low ROI, high maintenance, fragile, and several major platforms are relatively easy to search directly, so a scraper is not needed for MVP)
- Not a public product — single-user tool for Ganesh initially (may extend to MGIT peers later)
- Not handling resume/application submission automation in v1

---

## 3. User Persona

**Ganesh, 3rd year engineering student, MGIT**
- Wants to participate in every eligible hackathon, internship, and MNC certification
- Time-constrained due to coursework
- Comfortable with basic tech tools; not necessarily a backend/infra person
- Needs the system to be low-maintenance — if it requires daily manual upkeep, it will be abandoned

---

## 4. Solution Overview — Two Layers

The system has two complementary layers. Layer 1 solves *discovery* (finding things). Layer 2 solves *tracking* (not losing/forgetting what was found). Layer 2 is the part we build as software; Layer 1 is mostly configuration, not code.

### Layer 1 — Discovery (Set up once, ~1 hour total)
Replace "checking 1000 sites" with monitoring a small set of high-yield channels:

**Hackathons**
- Unstop (filter: year = 3rd, hackathons + case studies)
- Reskilll
- Devfolio
- HackerEarth
- Devpost / MLH (for global/remote ones)

**Internships**
- Internshala (saved search + daily email alert)
- Unstop (internship tab)
- LinkedIn (saved search + alert: "Internship" + domain + India)

**MNC Certifications/Courses**
- Google Cloud Skills Boost, Microsoft Learn, AWS Skill Builder (free tier certs)
- Coursera / edX (financial-aid filter for free access)
- Unstop (also lists many cert programs)

**Fast-signal channels (catch things before they're indexed elsewhere)**
- 2-3 curated Telegram/Discord channels for Indian student hackathons/internships
- Google Alerts for `"hackathon" OR "internship" 3rd year engineering India 2026`

Action item: Each platform above should have saved filters + notifications turned on **once**, so opportunities arrive as emails/notifications rather than requiring active searching.

### Layer 2 — Tracking (What we build: "OppTrack")
A lightweight personal dashboard where every opportunity Ganesh finds (via Layer 1) gets logged once, then the system handles sorting, reminders, and eligibility checks — nothing is written twice, nothing is forgotten.

---

## 5. Features (OppTrack Tool)

### MVP (v1) — Must Have
1. **Add Opportunity** — quick-entry form: Title, Type (Hackathon/Internship/Certification), Source platform, Link, Deadline date, Eligibility notes, Status (Not Started/Applied/In Progress/Rejected/Completed)
2. **Dashboard view** — sorted by deadline (soonest first), color-coded by urgency:
   - 🔴 ≤ 2 days left
   - 🟡 3-7 days left
   - 🟢 8+ days left
   - ⚪ Completed/Expired (archived, not deleted)
3. **Filter/search** — by type, status, or platform
4. **Persistent storage** — data survives across sessions (no re-entry needed)
5. **Deadline countdown** — days remaining shown per entry automatically

### v1.1 — Should Have
6. **Weekly review mode** — a single screen showing "this week's action items" (what's closing soon + what's new/unstarted)
7. **Tags** — e.g., "AI/ML", "Web Dev", "Free Cert", "Paid" for quick filtering by interest
8. **Notes field per entry** — application status notes, contact person, next steps
9. **Simple stats** — opportunities found vs. applied vs. completed per month (progress tracking toward goals)

### v2 — Nice to Have (Future)
10. Browser extension / bookmarklet — "Add to OppTrack" button while browsing any site, auto-fills link + title
11. Shareable version for MGIT batchmates (multi-user, shared board)
12. Email digest auto-import — parse Unstop/Internshala alert emails and auto-suggest entries (requires email API access — out of scope for personal-use v1)
13. Calendar sync (Google Calendar) for deadline reminders

---

## 6. Non-Functional Requirements

- **Zero backend maintenance** — must run as a single self-contained artifact/webpage, no server to manage
- **Fast entry** — adding a new opportunity should take under 15 seconds
- **Accessible anywhere** — usable on both mobile and laptop
- **Data durability** — entries must persist across sessions without manual export/import
- **No fragile scraping dependency** — the tool must not depend on scraping third-party sites (they change layout often, break scrapers, and may block bots); it depends only on Ganesh pasting a link he found via Layer 1

---

## 7. Proposed Architecture

Since 1000-site live scraping is explicitly out of scope (Section 2), the architecture is intentionally simple:

```
[Layer 1: Alerts]  →  Ganesh sees an opportunity  →  [OppTrack: Add Entry]
   (Unstop, Internshala,                                    ↓
    Telegram, Google Alerts,                        [Persistent Storage]
    LinkedIn, etc.)                                          ↓
                                                    [Dashboard: sorted,
                                                     filtered, countdown]
```

**Implementation choice:** A single HTML/React artifact using key-value persistent storage (per-user, private data) — no external server, no database to maintain, works instantly, accessible from any device via the same link/session.

**Data model (per entry):**
```json
{
  "id": "opp_1234",
  "title": "Smart India Hackathon 2026",
  "type": "Hackathon | Internship | Certification",
  "source": "Unstop",
  "link": "https://...",
  "deadline": "2026-08-10",
  "eligibility": "3rd/4th year, teams of 4",
  "tags": ["AI/ML", "Free"],
  "status": "Not Started | Applied | In Progress | Rejected | Completed",
  "notes": "",
  "date_added": "2026-07-25"
}
```

---

## 8. Rollout Plan

| Phase | Action | Time |
|---|---|---|
| Phase 0 | Set up Layer 1 filters/alerts on Unstop, Reskilll, Internshala, LinkedIn, Google Alerts, Telegram channels | ~1 hour, one-time |
| Phase 1 | Build & start using OppTrack MVP (Add Entry, Dashboard, Countdown, Storage) | Immediate |
| Phase 2 | Add v1.1 features (weekly review, tags, stats) based on real usage friction | 1-2 weeks in |
| Phase 3 | Evaluate v2 features (browser extension, sharing with MGIT peers) only if MVP is actively used for 3-4 weeks | 1 month+ |

---

## 9. Risks & Mitigations

| Risk | Mitigation |
|---|---|
| Tool is set up but not used consistently | Keep entry time under 15 seconds; tie to the "weekly 20-min ritual" habit from Layer 1 |
| Missing opportunities Layer 1 doesn't catch | Periodically (monthly) audit college notice boards / department WhatsApp groups as a supplementary manual check |
| Data loss | Use durable persistent storage; consider periodic manual export as backup in v1.1 |
| Feature creep before MVP is validated | Strictly hold v1.1/v2 features until MVP has been used for real for 2+ weeks |

---

## 10. Open Questions

- Should OppTrack be single-user only, or shared with a few MGIT friends from the start (adds complexity: shared vs. private data separation)?
- Should eligibility auto-check be added later (e.g., flag opportunities where CGPA/year criteria don't match), or is manual reading of eligibility sufficient?

---

## 11. Next Step

Build the OppTrack MVP as an interactive artifact (dashboard + add-entry form + persistent storage), ready to use today, while Ganesh sets up the Layer 1 alerts in parallel.
