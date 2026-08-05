# Research Log

Dated record of opportunity data audits and corrections. Append a new entry per
research session. Each entry: date, seeds touched, sources verified, what changed,
version bump (if any).

## 2026-08-05 — v6 audit (SEED_VERSION 5 → 6)

**Scope:** full 5-way parallel audit of all 206 `SEED_DATA` entries against live
pages (Devpost, DoraHacks, Unstop, Devfolio, Internshala, official event sites).

**Method:** 5 research agents, each verified a batch of 42/42/42/42/38 seeds by
fetching every live link (JS pages cross-checked via search snippets + official
secondary sources). 140 OK / 62 FIX / 0 DEAD / 4 UNVERIFIED; all fixes applied.

**Batch 1–2 (seeds 001–089):** SPOC extended, MIT $25.88→₹25L, What The Tech,
Outreachy, Teach For India, Adaption, TA Hackathon, Accenture, HackSavvy, ISRO BAH,
CDL/Oracle notes, Wexa link, Hackfest "The Agentic Era", Neurobots, DEMUX,
MunichTech, Y-Hack, Prasunethon, Tech Horizon. (`seed_003/012/015/031` flagged
UNVERIFIED — links left as-is.)

**Batch 3 (seeds 090–131):** `seed_091` deadline → 2026-08-11 (4,165 regs, not low
competition); `seed_092` → 2026-10-23 (single-phase Oct 24–Nov 1); `seed_093` →
2026-08-14 (2,911 regs); `seed_097` → 2026-08-15; `seed_107/108` registration
CLOSED notes; `seed_125` UG-only + min 1 female member/team.

**Batch 4 (seeds 132–173):** `seed_135` not a hackathon, 37 regs, swag-only;
`seed_144` reg Aug 9 + female-member rule; `seed_145` reg Aug 15, hybrid;
`seed_146` in-person Coimbatore; `seed_147` reg closed Jul 30, in-person;
`seed_156` → 2026-08-20; `seed_158` → 2026-08-10, offline Sep 25-26;
`seed_160` Africa-only (India ineligible), $16.5K; `seed_163` 382 regs, students
only; `seed_169` IIT-T region only, Aug 29-30; `seed_171` Sep 30 idea deadline,
₹10L; `seed_173` → 2026-08-18. (`seed_165` GIH window Oct 15–Dec 30 and
`seed_172` graVITas "Coming Soon" noted but not applied — pending confirmation.)

**Batch 5 (seeds 174–212):** `seed_176` Hacktoberfest 2026 unannounced;
`seed_177/182/183/208` → Completed (concluded events); `seed_178/179/180/181/182/
198/199` participant counts refreshed; `seed_181` pool $100 + TKS scholarship;
`seed_184` → 2026-09-18, event Oct 16; `seed_185` invite-only select colleges;
`seed_194` ₹1L pool; `seed_195` $25K pool, invite-only in-person HK;
`seed_196` approved-applicants only, $70K breakdown; `seed_200` 112 hackers;
`seed_201` reg → 2026-08-08; `seed_207` 2026 edition concluded; `seed_210` Juspay
careers shows no openings.

**Removed:** `seed_187` (Adobe India Hackathon 2026) — duplicate/renamed; merged
into `seed_201` (Adobe University Hackathon 2026). `SEED_DATA` = 205 entries.

**Verification:** `npm run validate` 0 errors (12 stale-deadline warnings);
`tests/migration.test.mjs` 29/29 pass; `npm run typecheck` + `npm run build` green.

## 2026-08-04 — v5 audit (SEED_VERSION 4 → 5)

**Scope:** full `SEED_DATA` audit against live pages (Devpost, DoraHacks, Unstop,
Devfolio, lablab.ai, Devfolio sites, careers pages).

**Round A (seeds 001–070):** fixed titles, deadlines, links, and eligibility for
~18 entries. Highlights:

- `seed_018` Push to Prod → `pushtoprod-india.devfolio.co` (Anthropic × Elevation
  Capital; in-person Aug 8, Basecamp Bengaluru)
- `seed_021/022/024` Microsoft / Qualcomm / Amazon intern links replaced (old URLs dead)
- `seed_032` Chanakya Fellowship → `tihiitb.org/programs/hr-skill-development/cfp-2026/`,
  deadline 2026-07-12, notes "2026 cycle closed"
- `seed_038` NexHack 2.0 venue corrected: IITM Janakpuri, New Delhi (NOT IIT Madras)
- `seed_039` Adaption Part 2: registration ENDED (915 teams), winners Aug 17
- `seed_049` Build with DataHub → `hack2skill.com/event/bah2026/` (BHARAT hackathon page)
- `seed_068` Dora Hack 2.0: women-led, online Aug 20-23, vibe-coding friendly

**Round B (seeds 105–143):** `seed_105` deadline 2026-12-18; `seed_106` R2 online
Aug 7-8; `seed_113` CLOSED (deadline 2026-01-20, status Completed); `seed_125`
Hybrid, offline finale Sep 11-12 Pune; `seed_126` offline Oct 4-6 PMEC Berhampur;
`seed_129` pre-reg Aug 18 → submission Sep 5; `seed_140` Nov 6-9, deadline 2026-11-09.

**Round C (seeds 174–212):** `seed_174` MLH Fellowship link; `seed_186` Zoho
Cliqtrix 2025 (next edition ~Nov 2026); `seed_190` NIT Warangal Ignite (Ignite 36,
Sep 27-28 2025); `seed_192` concluded (R1 extended 20 Mar 2026, R2 Apr 10-12);
`seed_200` WEEX deadline 2026-08-31; `seed_204` Goldman title 2026, closed 10 May
2026; `seed_205` Flipkart GRiD 8.0, regs ended 12 Jul 2026; `seed_210/211` Juspay
and Samsung PRISM links.

**Removed:** orphaned duplicates `seed_016`, `seed_020`, `seed_040`, `seed_046`,
`seed_052`, `seed_189` dropped from `SEED_DATA` (migration removes them for existing
users too). `SEED_DATA` = 206 entries, 0 duplicate titles.

**Linked correction:** Qualcomm URL `qualcomm.com/careers/internships` was 404 →
`qualcomm.com/company/careers/internships-and-early-in-career-opportunities/india`.

**Verification:** `npm run validate` 0 errors; `tests/migration.test.mjs` 29/29 pass;
`npm run typecheck` + `npm run build` green.
