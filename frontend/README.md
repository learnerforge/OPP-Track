# OppTrack — Frontend

A working prototype of **OppTrack as an event website**: account creation, login, and a Supabase-backed database for tracking hackathons, internships, certifications, and competitions. Editorial design — warm paper, near-black ink, Space Grotesk display, Space Mono kicker labels.

**Stack:** Vite · React 18 · TypeScript · Tailwind CSS v4 · shadcn/ui · React Router · Supabase (Auth + Postgres) · Vercel

See [`PLAN.md`](./PLAN.md) for the phased build plan this app was built against.

---

## Quick start (local)

```bash
cd frontend
npm install
cp .env.example .env.local   # Windows: copy .env.example .env.local
# fill in your Supabase URL + anon key (see below)
npm run dev
```

App runs at `http://localhost:5173`.

| Script | Purpose |
| --- | --- |
| `npm run dev` | Vite dev server |
| `npm run build` | `tsc` typecheck + production build to `dist/` |
| `npm run preview` | Serve the production build locally |
| `npm run typecheck` | Typecheck only |

> The app compiles and runs without Supabase credentials (placeholder client + in-UI warning), but auth and data require a configured project.

---

## 1. Create the Supabase project

1. Create a project at [supabase.com](https://supabase.com).
2. Open **SQL Editor → New query**, paste the entire contents of [`supabase/schema.sql`](./supabase/schema.sql), and **Run**.
   - Creates `profiles` (auto-row on signup) and `opportunities` tables, an `updated_at` trigger, an index, and **Row Level Security** policies so each user only sees their own rows.
3. Grab your credentials from **Project Settings → API**:
   - `Project URL` → `VITE_SUPABASE_URL`
   - `anon public` key → `VITE_SUPABASE_ANON_KEY`
4. Put them in `.env.local` (local) — see [`.env.example`](./.env.example).

Optional for a frictionless prototype: **Authentication → Sign In / Up →** disable *Confirm email* so new accounts can sign in immediately. (With confirmation on, the app shows a "check your inbox" notice instead.)

---

## 2. Deploy to Vercel

The `frontend/` folder is a self-contained Vite app — deploy **this folder** as the project root.

1. Push the repo to GitHub/GitLab/Bitbucket.
2. In [Vercel](https://vercel.com) → **Add New → Project** → import the repo.
3. **Root Directory:** `frontend` (Settings → General → Root Directory).
   - Framework preset: **Vite** (auto-detected via `vercel.json`).
   - Build: `npm run build` · Output: `dist`
4. **Environment Variables** (Settings → Environment Variables):
   - `VITE_SUPABASE_URL` = your project URL
   - `VITE_SUPABASE_ANON_KEY` = your anon public key
5. Deploy. `vercel.json` rewrites all routes to `index.html` so client-side routing (`/auth`, `/dashboard`) works on refresh.

After first deploy: **Supabase → Authentication → URL Configuration** → add the Vercel domain to *Site URL* and *Redirect URLs* if you later enable email confirmation / OAuth.

---

## Project structure

```
frontend/
├── PLAN.md                    # phased build plan (source of truth)
├── index.html                 # fonts + meta
├── vercel.json                # SPA rewrites for Vercel
├── supabase/schema.sql        # tables, triggers, RLS — paste into SQL editor
└── src/
    ├── App.tsx                # router + RequireAuth / RedirectIfAuthed guards
    ├── index.css              # Tailwind v4 @theme design tokens
    ├── context/AuthContext.tsx # session, signIn / signUp / signOut
    ├── hooks/
    │   ├── useOpportunities.ts # Supabase CRUD (RLS-scoped per user)
    │   └── useFilters.ts       # filter / sort / active vs archive
    ├── lib/
    │   ├── supabase.ts         # client (placeholder-safe)
    │   ├── constants.ts        # type/status options, urgency styles
    │   ├── date.ts             # countdown + urgency tiers
    │   ├── validation.ts       # entry form rules
    │   └── meta.ts             # status/type display metadata
    ├── pages/                  # Landing, Auth, Dashboard
    └── components/
        ├── ui/                 # vendored shadcn/ui primitives
        ├── Header.tsx  EntryForm.tsx  OpportunityCard.tsx
        ├── FilterBar.tsx  StatsPanel.tsx  ArchiveSection.tsx
        ├── EmptyState.tsx  Toast.tsx
```

## Features

- **Auth:** create account, sign in, sign out; route guards; session persistence.
- **Database:** every entry stored in Postgres, scoped by `auth.uid()` through RLS.
- **Dashboard:** add / edit / delete entries, status dropdowns, search + filters (type, status, source, tag, due-within), sorting, urgency countdowns.
- **Stats view:** totals, due-this-week, completion rate, per-category bars.
- **Archive:** expired/completed entries collapsed, with restore or permanent delete.
- **Toasts:** non-blocking feedback for every mutation.

## Troubleshooting

| Symptom | Fix |
| --- | --- |
| "Supabase not configured" banner | Fill `.env.local` / Vercel env vars, restart dev server. |
| `relation "public.opportunities" does not exist` | Run `supabase/schema.sql` in the SQL editor. |
| `row-level security policy` errors | Re-run `schema.sql` (policies are part of it). |
| 404 on refresh at `/dashboard` | On Vercel, confirm `vercel.json` is present at the project root (`frontend/`). |
| Email never arrives | Disable *Confirm email* in Supabase Auth settings for local prototyping. |
