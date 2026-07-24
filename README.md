# OPP-Track

## Description

A personal opportunity discovery and tracking dashboard for students. Log hackathons, internships, and certifications you find — then let OppTrack handle sorting by deadline, urgency color-coding, countdown timers, and status tracking so nothing is ever missed or forgotten.

## Tech Stack

- **React 18** with TypeScript
- **Vite** for fast development and optimized builds
- **Tailwind CSS** for styling
- **No backend** — runs as a single self-contained web app
- **Persistent storage** — data survives sessions via the platform storage API (`window.storage`)

## Features

### MVP (Phase 1)
- **Add Entry** — quick form (<15 seconds) to log any opportunity
- **Dashboard** — deadline-sorted view with urgency color-coding
  - 🔴 ≤ 2 days left
  - 🟡 3–7 days left
  - 🟢 8+ days left
  - ⚪ Completed/Expired (auto-archived)
- **Filter & Search** — by type, status, source, tag, or title text
- **Status tracking** — Not Started → Applied → In Progress → Rejected/Completed
- **Edit & Delete** — update any field, delete with confirmation
- **Persistent storage** — entries persist across sessions
- **Responsive** — works on mobile and desktop
- **Zero maintenance** — no server, no database, no build step required

### v1.1 (Phase 2)
- **Weekly Review Mode** — focused view of opportunities closing within 7 days + newly added unstarted entries
- **Tags** — add/filter by custom tags (AI/ML, Free, Paid, etc.)
- **Statistics Panel** — counts by status, type, and monthly progress
- **Export** — download as JSON or CSV, copy to clipboard

## Installation

### Quick Start (Development)

```bash
# Install dependencies
npm install

# Start dev server
npm run dev

# Open in browser
# http://localhost:5173
```

### Build for Production

```bash
npm run build

# Output in dist/ — serve with any static file server
npm run preview
```

### Artifact Mode (Single File)

The project can also be deployed as a single HTML artifact. The `index.html` at the project root serves as the artifact entry point.

## Project Structure

```
OPP-Track/
├── index.html                  # HTML entry point
├── package.json                # Dependencies and scripts
├── vite.config.ts              # Vite build configuration
├── tailwind.config.js          # Tailwind CSS configuration
├── tsconfig.json               # TypeScript configuration
├── postcss.config.js           # PostCSS configuration
├── public/
│   └── favicon.svg             # App icon
├── src/
│   ├── main.tsx                # React DOM entry point
│   ├── App.tsx                 # Main application component
│   ├── index.css               # Global styles
│   ├── vite-env.d.ts           # TypeScript declarations
│   ├── types/
│   │   └── opportunity.ts      # Data model types
│   ├── constants/
│   │   └── index.ts            # App constants, colors, options
│   ├── utils/
│   │   ├── index.ts            # Utility barrel export
│   │   ├── date.ts             # Date helpers, urgency logic
│   │   ├── validation.ts       # Form validation
│   │   └── export.ts           # JSON/CSV export
│   ├── lib/
│   │   └── storage.ts          # Storage abstraction layer
│   ├── hooks/
│   │   ├── index.ts            # Hooks barrel export
│   │   ├── useOpportunities.ts # CRUD + persistence hook
│   │   └── useFilters.ts       # Client-side filtering hook
│   └── components/
│       ├── index.ts            # Components barrel export
│       ├── Header.tsx          # App header with nav tabs
│       ├── EntryForm.tsx       # Add/Edit opportunity form
│       ├── OpportunityCard.tsx # Individual opportunity display
│       ├── FilterBar.tsx       # Search and filter controls
│       ├── EmptyState.tsx      # Empty state prompt
│       ├── ArchiveSection.tsx  # Collapsed archive section
│       ├── WeeklyReviewMode.tsx # Weekly review view (v1.1)
│       ├── StatsPanel.tsx      # Statistics dashboard (v1.1)
│       └── ExportButton.tsx    # Export dropdown (v1.1)
└── docs/
    ├── PRD.md                  # Product requirements
    ├── ARCHITECTURE.md         # Technical design
    ├── PROJECT_OVERVIEW.md     # Quick orientation
    ├── TASKS.md                # Task breakdown
    ├── CODING_RULES.md         # Code conventions
    ├── RISKS_AND_EDGE_CASES.md # Risks and edge cases
    └── KNOWN_ISSUES_AND_DECISIONS.md # Decision log
```

## Usage

1. Open the app in your browser
2. Click **+ Add** to log a new opportunity
3. Fill in at minimum: Title, Type, Deadline
4. Opportunities appear sorted by deadline with urgency indicators
5. Use the filter bar to search by title, type, status, source, or tag
6. Update status as you progress through applications
7. Switch to **Weekly Review** for a focused view of closing-soon items
8. Check **Stats** for an overview of your tracking progress
9. Use **Export** to backup your data as JSON or CSV

## Target Audience

Students (initially single-user personal tool, expandable to peers).

## License

MIT
