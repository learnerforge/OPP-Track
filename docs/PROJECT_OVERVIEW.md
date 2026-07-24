# PROJECT_OVERVIEW.md

## Project Name
**OppTrack** — Personal Opportunity Discovery & Tracking System

## One-Line Summary
A personal dashboard that lets Ganesh log every hackathon, internship, and certification opportunity he finds (via a small set of curated alert channels) into one deadline-sorted view, so nothing is missed or forgotten.

## Background
Ganesh is a 3rd year engineering student at MGIT who wants to participate in every eligible hackathon, internship, and MNC certification program. There are 1000+ websites publishing such opportunities, and manually checking them takes 3-4 days per cycle — by which point many deadlines and eligibility windows have already closed.

Full problem context and rationale live in `PRD.md` (project root). This document summarizes the project for anyone (including future-Ganesh) who needs a quick orientation without reading the full PRD.

## Problem Being Solved
Not a *discovery volume* problem — it's a **consolidation and tracking** problem:
1. Opportunities already funnel into a handful of aggregator platforms (Unstop, Reskilll, Devfolio, HackerEarth, Internshala, LinkedIn, MOOC portals).
2. What's missing is a single place to log, sort by deadline, and track application status — so found opportunities don't silently expire in browser tabs, WhatsApp forwards, or bookmarks.

## Solution Structure
The overall system has two layers; **only Layer 2 is software** we build and maintain:

| Layer | What it is | Where it's documented |
|---|---|---|
| Layer 1 — Discovery | One-time setup of alerts/filters on Unstop, Reskilll, Internshala, LinkedIn, Google Alerts, Telegram channels | `PRD.md` §4 |
| Layer 2 — Tracking (OppTrack) | The actual tool: add entry → dashboard → deadline countdown → status tracking | This `docs/` folder + `PRD.md` §5–7 |

## Goals
- Cut opportunity-discovery/tracking time from ~5-6 hrs/week to ≤ 30 min/week
- Zero missed deadlines for opportunities already logged
- Increase the number of eligible opportunities actually applied to (target: 8-12/month)

## Non-Goals
- Not a live scraper of 1000+ sites (fragile, high-maintenance, low ROI — see `RISKS_AND_EDGE_CASES.md`)
- Not a public multi-tenant product in v1 (single user: Ganesh)
- Not an application-submission automation tool

## Primary User
Ganesh, 3rd year, MGIT. Secondary/future users: MGIT batchmates (v2, not in current scope).

## Current Scope (MVP)
1. Add Opportunity form (title, type, source, link, deadline, eligibility, status)
2. Dashboard sorted by deadline with urgency color-coding
3. Filter/search by type, status, platform
4. Persistent storage across sessions
5. Automatic deadline countdown

See `TASKS.md` for the full task breakdown and `ARCHITECTURE.md` for technical design.

## Key Documents in This Project
- `PRD.md` — full product requirements, rationale, metrics, rollout plan
- `docs/PROJECT_OVERVIEW.md` — this file
- `docs/ARCHITECTURE.md` — technical design and data model
- `docs/TASKS.md` — implementation task breakdown by phase
- `docs/RISKS_AND_EDGE_CASES.md` — known risks, failure modes, and edge cases
- `docs/CODING_RULES.md` — conventions for any code written for this project
- `docs/KNOWN_ISSUES_AND_DECISIONS.md` — decision log and open issues

## Status
Draft / Pre-build. MVP not yet implemented as of this writing (July 25, 2026).
