import { useState, useEffect, useMemo } from 'react';
import type { Filters, Opportunity } from '@/types/opportunity';
import { Header } from '@/components/Header';
import { useAuth } from '@/context/AuthContext';
import { useOpportunities } from '@/hooks/useOpportunities';
import { useFilters } from '@/hooks/useFilters';
import { EntryForm } from '@/components/EntryForm';
import { OpportunityCard } from '@/components/OpportunityCard';
import { FilterBar } from '@/components/FilterBar';
import { StatsPanel } from '@/components/StatsPanel';
import { ArchiveSection } from '@/components/ArchiveSection';
import { EmptyState } from '@/components/EmptyState';
import { useToast } from '@/components/Toast';
import { Button } from '@/components/ui/button';
import { Skeleton } from '@/components/ui/skeleton';
import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert';
import { todayStr } from '@/lib/date';
import { isSupabaseConfigured } from '@/lib/supabase';

const DEFAULT_FILTERS: Filters = {
  search: '',
  type: 'All',
  status: 'All',
  source: 'All',
  tag: 'All',
  sortKey: 'deadline',
  sortDir: 'asc',
  dueWithin: 0,
};

type Tab = 'dashboard' | 'stats';

export function Dashboard() {
  const { session } = useAuth();
  const { showToast } = useToast();
  const {
    opportunities,
    loading,
    error,
    addOpportunity,
    updateOpportunity,
    deleteOpportunity,
    changeStatus,
    retryLoad,
  } = useOpportunities();

  const [filters, setFilters] = useState<Filters>(DEFAULT_FILTERS);
  const [tab, setTab] = useState<Tab>('dashboard');
  const [formOpen, setFormOpen] = useState(false);
  const [editing, setEditing] = useState<Opportunity | null>(null);

  const { active, archived, sources, allTags, totalCount } = useFilters(
    opportunities,
    filters
  );

  // Keep "due within N days" meaningful as the date rolls over.
  const [, setTick] = useState(0);
  useEffect(() => {
    const id = setInterval(() => setTick(t => t + 1), 60 * 60 * 1000);
    return () => clearInterval(id);
  }, []);

  function openNew() {
    setEditing(null);
    setFormOpen(true);
  }

  function openEdit(opp: Opportunity) {
    setEditing(opp);
    setFormOpen(true);
  }

  async function handleSave(opp: Opportunity) {
    if (editing) {
      await updateOpportunity({ ...opp, id: editing.id, user_id: editing.user_id });
      showToast(`Updated “${opp.title}”.`);
    } else {
      const { id: _id, user_id: _uid, ...rest } = opp;
      await addOpportunity({
        ...rest,
        date_added: rest.date_added || todayStr(),
      });
      showToast(`Added “${opp.title}”.`);
    }
    setFormOpen(false);
    setEditing(null);
  }

  async function handleDelete(id: string) {
    const target = opportunities.find(o => o.id === id);
    await deleteOpportunity(id);
    showToast(target ? `Deleted “${target.title}”.` : 'Entry deleted.', 'info');
  }

  async function handleChangeStatus(id: string, status: Opportunity['status']) {
    await changeStatus(id, status);
    showToast(`Status → ${status}.`, 'info');
  }

  async function handleRestore(opp: Opportunity) {
    // Restring the deadline to today so it re-enters the active list.
    await updateOpportunity({ ...opp, deadline: todayStr() });
    showToast(`Restored “${opp.title}” to active.`);
  }

  const headerAction = useMemo(
    () => (formOpen ? undefined : openNew),
    [formOpen]
  );

  return (
    <div className="min-h-screen bg-paper">
      <Header onNewEntry={headerAction} />

      <main className="mx-auto max-w-6xl px-4 py-8 sm:px-6 sm:py-10">
        <div className="mb-6 flex flex-wrap items-end justify-between gap-4">
          <div>
            <p className="kicker mb-2">your ledger</p>
            <h1 className="font-display text-3xl font-bold tracking-tight text-ink sm:text-4xl">
              Dashboard
            </h1>
          </div>

          <div
            role="tablist"
            aria-label="Dashboard views"
            className="flex rounded-lg border border-rule bg-surface p-1"
          >
            {(['dashboard', 'stats'] as Tab[]).map(t => (
              <button
                key={t}
                role="tab"
                aria-selected={tab === t}
                onClick={() => setTab(t)}
                className={`rounded-md px-4 py-1.5 font-mono text-xs uppercase tracking-wide transition-colors focus-ring ${
                  tab === t
                    ? 'bg-ink text-paper'
                    : 'text-ink-muted hover:bg-muted'
                }`}
              >
                {t === 'dashboard' ? 'entries' : 'stats'}
              </button>
            ))}
          </div>
        </div>

        {!isSupabaseConfigured && (
          <Alert className="mb-6 border-warning/40 bg-warning-soft">
            <AlertTitle className="text-warning">
              Missing Supabase credentials
            </AlertTitle>
            <AlertDescription className="text-ink-soft">
              Copy <code className="font-mono text-xs">.env.example</code> to{' '}
              <code className="font-mono text-xs">.env.local</code>, fill in your
              project URL and anon key, and run{' '}
              <code className="font-mono text-xs">supabase/schema.sql</code> in the
              Supabase SQL editor.
            </AlertDescription>
          </Alert>
        )}

        {error && (
          <Alert variant="destructive" className="mb-6" role="alert">
            <AlertTitle>Couldn’t load your entries</AlertTitle>
            <AlertDescription className="flex flex-wrap items-center gap-3">
              <span>{error}</span>
              <Button size="sm" variant="outline" onClick={retryLoad}>
                Retry
              </Button>
            </AlertDescription>
          </Alert>
        )}

        {tab === 'stats' ? (
          loading ? (
            <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
              {Array.from({ length: 8 }).map((_, i) => (
                <Skeleton key={i} className="h-24" />
              ))}
            </div>
          ) : (
            <StatsPanel opportunities={opportunities} />
          )
        ) : (
          <div className="space-y-6">
            <FilterBar
              filters={filters}
              onFilterChange={setFilters}
              sources={sources}
              allTags={allTags}
              activeCount={active.length}
              totalCount={totalCount}
            />

            {loading ? (
              <div className="space-y-3">
                {Array.from({ length: 4 }).map((_, i) => (
                  <Skeleton key={i} className="h-32" />
                ))}
              </div>
            ) : active.length === 0 ? (
              totalCount === 0 ? (
                <EmptyState
                  title="Nothing tracked yet"
                  description="Log your first hackathon, internship, or certification and OppTrack starts the countdown."
                  actionLabel="+ Add your first entry"
                  onAction={openNew}
                />
              ) : (
                <EmptyState
                  title="No entries match these filters"
                  description="Loosen the search, widen the due-window, or clear the filters to see everything again."
                  actionLabel="Clear filters"
                  onAction={() => setFilters(DEFAULT_FILTERS)}
                />
              )
            ) : (
              <div className="space-y-3">
                {active.map(opp => (
                  <OpportunityCard
                    key={opp.id}
                    opp={opp}
                    onEdit={openEdit}
                    onDelete={handleDelete}
                    onChangeStatus={handleChangeStatus}
                  />
                ))}
              </div>
            )}

            {!loading && archived.length > 0 && (
              <ArchiveSection
                opportunities={archived}
                onRestore={handleRestore}
                onDelete={handleDelete}
              />
            )}
          </div>
        )}

        {/* Floating add button on small screens */}
        <button
          onClick={openNew}
          aria-label="Add a new opportunity"
          className="fixed bottom-5 right-5 z-30 flex h-14 w-14 items-center justify-center rounded-full bg-ink text-2xl text-paper shadow-lg transition-transform hover:scale-105 focus-ring sm:hidden"
        >
          +
        </button>

        {formOpen && (
          <EntryForm
            onSave={handleSave}
            onCancel={() => {
              setFormOpen(false);
              setEditing(null);
            }}
            initial={editing ?? undefined}
            isEdit={!!editing}
          />
        )}

        {session?.user?.email && (
          <p className="mt-10 border-t border-rule pt-4 text-center font-mono text-[11px] text-ink-faint">
            signed in as {session.user.email}
          </p>
        )}
      </main>
    </div>
  );
}
