# ARCHITECTURE.md

## 1. Design Philosophy
OppTrack is deliberately **not** a scraping system, not a multi-service backend, and not a database-hosting project. The core insight driving the architecture:

> Discovery (finding opportunities) is solved by configuring alerts on existing aggregator platforms — a one-time human setup task, not software. The software only needs to solve **tracking**: capture what Ganesh finds, store it durably, and present it sorted by urgency.

This keeps the system to a single self-contained component with no server to run, no scraper to maintain, and no external API dependency for its core function.

## 2. High-Level System Diagram

```
┌─────────────────────────────────────────────────────────────┐
│  LAYER 1 — Discovery (outside this codebase, human-config)   │
│  Unstop | Reskilll | Devfolio | HackerEarth | Internshala |  │
│  LinkedIn Alerts | Google Alerts | Telegram/Discord channels │
└───────────────────────────┬───────────────────────────────────┘
                            │  Ganesh manually pastes link/title
                            ▼
┌─────────────────────────────────────────────────────────────┐
│  LAYER 2 — OppTrack (this codebase)                          │
│                                                                │
│  ┌──────────────┐   ┌───────────────┐   ┌──────────────────┐ │
│  │ Add Entry     │──▶│ Storage Layer │──▶│ Dashboard/View    │ │
│  │ Form          │   │ (key-value,   │   │ (sort, filter,    │ │
│  │               │   │  persistent)  │   │  countdown)       │ │
│  └──────────────┘   └───────────────┘   └──────────────────┘ │
└─────────────────────────────────────────────────────────────┘
```

## 3. Components

### 3.1 Add Entry Component
- Renders a form with fields: Title, Type, Source, Link, Deadline, Eligibility, Tags, Status, Notes
- On submit: validates required fields (Title, Type, Deadline), generates a unique ID, writes to Storage Layer
- Target interaction time: < 15 seconds per entry (per PRD §6 NFR)

### 3.2 Storage Layer
- Uses the artifact persistent key-value storage API (`window.storage.get/set/delete/list`)
- **Scope: private/per-user (`shared = false`)** — this is personal data, not shared with other users
- Key design: single aggregate key holding the full opportunity list (see §4 Data Model), rather than one key per opportunity, to minimize round trips and keep read/write atomic per update
  - Key: `opportunities-list`
  - Value: JSON-serialized array of opportunity objects
- All reads/writes wrapped in try/catch; UI shows a loading state on initial load and a clear error state if storage fails (see `RISKS_AND_EDGE_CASES.md` §Storage Failures)

### 3.3 Dashboard/View Component
- Reads the full list from Storage Layer on mount
- Client-side sort: ascending by `deadline`, with expired/completed entries moved to a collapsed "Archive" section
- Client-side filter: by `type`, `status`, `tags`, `source` — no server round trip needed since dataset size is small (tens to low hundreds of entries)
- Urgency color-coding computed at render time from `deadline - today`:
  - 🔴 ≤ 2 days
  - 🟡 3–7 days
  - 🟢 8+ days
  - ⚪ Expired or Status = Completed (auto-archived)
- Countdown value (`days remaining`) is **derived**, never stored — always computed fresh against current date to avoid staleness

### 3.4 Weekly Review Mode (v1.1)
- A filtered view of the Dashboard: entries with `days remaining ≤ 7` OR `status = Not Started` and `date_added` within last 7 days
- No separate storage needed — pure derived view over the same dataset

## 4. Data Model

Single source of truth: an array of opportunity objects stored under key `opportunities-list`.

```json
{
  "id": "opp_<timestamp>_<random4>",
  "title": "string, required",
  "type": "Hackathon | Internship | Certification",
  "source": "string, e.g. 'Unstop', 'Internshala', 'Direct/Company site'",
  "link": "string (URL), required",
  "deadline": "ISO date string YYYY-MM-DD, required",
  "eligibility": "string, free text",
  "tags": ["string", "..."],
  "status": "Not Started | Applied | In Progress | Rejected | Completed",
  "notes": "string, free text",
  "date_added": "ISO date string YYYY-MM-DD, auto-set on creation"
}
```

**ID generation:** `opp_` + `Date.now()` + 4 random alphanumeric chars, to guarantee uniqueness without a backend sequence.

**Why one aggregate key instead of one key per opportunity:**
Per the storage system's design guidance, records that are read/updated together should be combined into a single key. Since the Dashboard always needs the *full* list to sort/filter, and entries are added/edited one at a time but always displayed together, a single `opportunities-list` key avoids N sequential storage calls on every dashboard load.

## 5. Technology Choice

- **Implementation form:** Single-file React artifact (or HTML/JS artifact — React preferred for state management of filters/sort)
- **Styling:** Tailwind core utility classes (per artifact constraints)
- **State:** React `useState` for in-memory list, filters, and form state; Storage Layer is the durability layer, not the primary state
- **No external network calls** required for core functionality — this is intentional (see §1)

## 6. Data Flow — Add Entry

1. User fills Add Entry form, clicks Save
2. Component validates required fields client-side
3. New object appended to in-memory list (optimistic update — dashboard reflects it immediately)
4. Full updated list serialized and written to `opportunities-list` via `window.storage.set`
5. On write failure: revert optimistic update, show retry option (see `RISKS_AND_EDGE_CASES.md`)

## 7. Data Flow — Load Dashboard

1. On mount, call `window.storage.get('opportunities-list')`
2. If key doesn't exist yet (first-ever use): treat as empty list, no error
3. Parse JSON, compute derived fields (days remaining, urgency tier) at render time
4. Render sorted/filtered view

## 8. Future Architecture Considerations (v2, not built now)

- **Browser extension:** would need a separate small extension codebase communicating with OppTrack via a shared storage key or export/import — out of scope until MVP is validated (per `PRD.md` §8 Phase 3 gating)
- **Multi-user sharing (MGIT batchmates):** would require switching relevant keys to `shared = true` and adding a namespacing scheme (e.g., `opportunities-shared:<batch>`) — deferred, see `KNOWN_ISSUES_AND_DECISIONS.md`
- **Email digest auto-import:** would require an email-reading integration outside the artifact sandbox — explicitly deferred per `PRD.md` §5 v2

## 9. Explicit Non-Architecture (What We Are NOT Building)

- No backend server, no database service, no hosting infra
- No live web scraper of external sites
- No scheduled/cron job system — the tool is reactive (opens when Ganesh opens it), not a background daemon
- No authentication system (single-user personal tool)
