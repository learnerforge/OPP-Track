# frontend/PLAN.md

Working prototype of **OppTrack as an event website** — a public, deployable frontend with account creation, login, and a Supabase-backed database. Written in the same phased/checklist style as `docs/TASKS.md`. Work proceeds per this plan.

**Stack:** Vite · React 18 · TypeScript · Tailwind CSS v4 · shadcn/ui · React Router · Supabase (Auth + Postgres) · Vercel.

**Design:** editorial style inspired by heapheaphurray.com — warm paper, near-black ink, Space Grotesk display, Space Mono kicker labels, serif-italic accents, big stat bands.

---

## Phase 0 — Scaffold & Design System
- [x] Create `frontend/` directory (self-contained app, independent of parent `src/`)
- [x] `package.json` with React, Supabase, React Router, shadcn deps
- [x] `vite.config.ts` — React + Tailwind v4 plugins, `@` alias
- [x] `tsconfig.json` — strict, `@/*` path alias
- [x] `src/index.css` — Tailwind v4 `@theme` tokens (paper/ink/semantic), fonts, base styles
- [x] Vendor shadcn/ui components into `src/components/ui/`
- [x] `src/lib/utils.ts` (`cn`), `src/lib/meta.ts` (status/type display metadata)

**Exit criteria:** `npm install` succeeds; design tokens + fonts present in CSS.

---

## Phase 1 — Supabase Wiring
- [x] `src/lib/supabase.ts` — typed client from `VITE_SUPABASE_URL` / `VITE_SUPABASE_ANON_KEY`
- [x] `src/types/opportunity.ts` — data model matching DB schema
- [x] `supabase/schema.sql` — `profiles` + `opportunities` tables, RLS policies, `updated_at` trigger
- [x] `.env.example` + `.gitignore` (never commit keys)
- [x] `src/context/AuthContext.tsx` — session state, `signUp`, `signIn`, `signOut`, `onAuthStateChange`
- [x] Route guard: unauthenticated users redirected to `/auth`

**Exit criteria:** App compiles with Supabase client; schema file ready to paste into Supabase SQL editor.

---

## Phase 2 — Auth (create account + login)
- [x] `/auth` page with Sign in / Create account toggle
- [x] Email + password forms with client-side validation + error surfacing
- [x] Email-confirmation notice on signup
- [x] Loading + error states on submit
- [x] Header shows logged-in email + Sign out

**Exit criteria:** User can create an account, sign in, and land on the dashboard; sign out returns to landing.

---

## Phase 3 — Event Website (public landing)
- [x] Marketing landing: masthead nav, hero headline + stat band, how-it-works, feature grid, CTA
- [x] Responsive + editorial styling; CTA routes to `/auth`

**Exit criteria:** Landing renders as a polished public event/opportunity site driving signups.

---

## Phase 4 — Dashboard (protected, DB-backed)
- [x] `useOpportunities` hook — Supabase CRUD scoped to `auth.uid()`
- [x] Dashboard: hero stat band, filter bar, opportunity cards, add/edit dialog, archive
- [x] Optimistic UI + loading skeleton + error/retry; delete confirmation
- [x] Weekly Review + Stats views

**Exit criteria:** Logged-in user can create, read, update, delete their own entries — persisted to Supabase, isolated per user.

---

## Phase 5 — Deploy on Vercel
- [x] `vercel.json` — Vite framework, SPA rewrite to `index.html`
- [x] `README.md` — setup, Supabase env vars, deploy steps, SQL migration
- [x] Production build passes (`npm run build`)

**Exit criteria:** `npm run build` green; repo importable to Vercel with two env vars set.

---

## Manual smoke checklist (before calling "done")
- [x] `npm run dev` serves landing at `/` — verified (dev server on 5174, `/` + `/dashboard` SPA fallback serve `index.html`; `App.tsx` transform clean)
- [ ] Sign up creates account; sign in reaches dashboard — **requires a real Supabase project + `.env.local`** (code path complete: AuthContext, `/auth` page, guards)
- [ ] Add entry → appears sorted by deadline; persists after reload — **requires Supabase credentials** (CRUD + RLS in `useOpportunities` + `schema.sql`)
- [ ] Edit / delete / status change work; archive captures completed/expired — **requires Supabase credentials**
- [ ] Filter + search return correct subsets — **requires data in the table**
- [ ] Sign out returns to landing; protected route redirects when logged out — **requires Supabase credentials**

**Verified without credentials:** `npm install` → `npm run build` green (`tsc` strict + 1755 modules), `npm run preview` serves production bundle at `/` and `/dashboard`, fonts + design tokens present in built CSS.

---
