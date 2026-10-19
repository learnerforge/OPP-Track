-- OppTrack — Supabase schema
-- Run this in your Supabase project: SQL Editor → New query → paste → Run.
-- Creates a profiles table (one row per auth user) and an opportunities table
-- scoped to each user via Row Level Security (RLS).

-- ---------------------------------------------------------------------------
-- profiles: one row per authenticated user, auto-created on signup via trigger
-- ---------------------------------------------------------------------------
create table if not exists public.profiles (
  id uuid primary key references auth.users (id) on delete cascade,
  email text,
  created_at timestamptz not null default now()
);

-- Auto-create a profile row when a new auth user signs up.
create or replace function public.handle_new_user()
returns trigger
language plpgsql
security definer set search_path = public
as $$
begin
  insert into public.profiles (id, email)
  values (new.id, new.email)
  on conflict (id) do update set email = excluded.email;
  return new;
end;
$$;

drop trigger if exists on_auth_user_created on auth.users;
create trigger on_auth_user_created
  after insert on auth.users
  for each row execute function public.handle_new_user();

-- ---------------------------------------------------------------------------
-- opportunities: the tracked events / opportunities, one owner per row
-- ---------------------------------------------------------------------------
create table if not exists public.opportunities (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references auth.users (id) on delete cascade,
  title text not null,
  type text not null default 'Hackathon'
    check (type in ('Hackathon', 'Internship', 'Certification', 'Competition')),
  source text not null default '',
  link text not null default '',
  deadline date not null,
  eligibility text not null default '',
  tags text[] not null default '{}',
  status text not null default 'Not Started'
    check (status in ('Not Started', 'Applied', 'In Progress', 'Rejected', 'Completed')),
  notes text not null default '',
  date_added date not null default current_date,
  location text,
  prize_pool text,
  participants text,
  organizer text,
  duration text,
  quality_score numeric,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

-- Keep updated_at fresh on every update.
create or replace function public.set_updated_at()
returns trigger
language plpgsql
as $$
begin
  new.updated_at = now();
  return new;
end;
$$;

drop trigger if exists set_opportunities_updated_at on public.opportunities;
create trigger set_opportunities_updated_at
  before update on public.opportunities
  for each row execute function public.set_updated_at();

-- Helpful index for the common "my entries, soonest deadline first" query.
create index if not exists opportunities_user_deadline_idx
  on public.opportunities (user_id, deadline);

-- ---------------------------------------------------------------------------
-- Row Level Security: a user can only ever see/modify their own rows
-- ---------------------------------------------------------------------------
alter table public.profiles enable row level security;
alter table public.opportunities enable row level security;

-- profiles policies
create policy "profiles_select_own"
  on public.profiles for select
  using (auth.uid() = id);

create policy "profiles_update_own"
  on public.profiles for update
  using (auth.uid() = id)
  with check (auth.uid() = id);

-- opportunities policies
create policy "opportunities_select_own"
  on public.opportunities for select
  using (auth.uid() = user_id);

create policy "opportunities_insert_own"
  on public.opportunities for insert
  with check (auth.uid() = user_id);

create policy "opportunities_update_own"
  on public.opportunities for update
  using (auth.uid() = user_id)
  with check (auth.uid() = user_id);

create policy "opportunities_delete_own"
  on public.opportunities for delete
  using (auth.uid() = user_id);
