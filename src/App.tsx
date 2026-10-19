import { useState, useEffect, useCallback } from 'react';
import type { ViewMode, Filters, Opportunity } from './types/opportunity';
import { useOpportunities } from './hooks/useOpportunities';
import { useFilters } from './hooks/useFilters';
import { useReminders } from './hooks/useReminders';
import {
  Header,
  Hero,
  EntryForm,
  OpportunityCard,
  FilterBar,
  EmptyState,
  ArchiveSection,
  WeeklyReviewMode,
  StatsPanel,
  ExportButton,
  ToastProvider,
  useToast,
} from './components';
import { Button } from './components/ui/button';
import { Alert, AlertTitle, AlertDescription } from './components/ui/alert';
import { Skeleton } from './components/ui/skeleton';

const INITIAL_FILTERS: Filters = {
  search: '',
  type: 'All',
  status: 'All',
  source: 'All',
  tag: 'All',
  sortKey: 'deadline',
  sortDir: 'asc',
  dueWithin: 0,
};

function AppContent() {
  const { showToast } = useToast();
  const {
    opportunities,
    loading,
    error,
    saveError,
    addOpportunity,
    updateOpportunity,
    deleteOpportunity,
    changeStatus,
    retrySave,
    retryLoad,
  } = useOpportunities();

  const [viewMode, setViewMode] = useState<ViewMode>('dashboard');
  const [showForm, setShowForm] = useState(false);
  const [editingOpp, setEditingOpp] = useState<Opportunity | null>(null);
  const [filters, setFilters] = useState<Filters>(INITIAL_FILTERS);

  const { active, archived, sources, allTags, totalCount } = useFilters(
    opportunities,
    filters
  );

  const {
    enabled: remindersEnabled,
    supported: remindersSupported,
    toggle: toggleReminders,
  } = useReminders(opportunities);

  const handleCancel = useCallback(() => {
    setShowForm(false);
    setEditingOpp(null);
  }, []);

  useEffect(() => {
    function handleKeyDown(e: KeyboardEvent) {
      if (e.key === 'Escape') {
        handleCancel();
      }
    }
    if (showForm || editingOpp) {
      document.addEventListener('keydown', handleKeyDown);
      return () => document.removeEventListener('keydown', handleKeyDown);
    }
  }, [showForm, editingOpp, handleCancel]);

  function handleAdd() {
    setEditingOpp(null);
    setShowForm(true);
  }

  function handleSaveNew(opp: Opportunity) {
    const { id: _id, date_added: _da, ...rest } = opp;
    addOpportunity(rest);
    setShowForm(false);
    showToast('Opportunity added to your board');
  }

  function handleEdit(opp: Opportunity) {
    setShowForm(false);
    setEditingOpp(opp);
  }

  function handleSaveEdit(opp: Opportunity) {
    updateOpportunity(opp);
    setEditingOpp(null);
    showToast('Opportunity updated');
  }

  function handleDelete(id: string) {
    deleteOpportunity(id);
    showToast('Opportunity deleted', 'info');
  }

  if (loading) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-paper">
        <div className="w-full max-w-5xl px-5 py-10">
          <Skeleton className="mb-3 h-4 w-40" />
          <Skeleton className="mb-6 h-10 w-3/4" />
          <div className="grid grid-cols-2 gap-6 sm:grid-cols-4">
            <Skeleton className="h-16" />
            <Skeleton className="h-16" />
            <Skeleton className="h-16" />
            <Skeleton className="h-16" />
          </div>
          <div className="mt-10 space-y-3">
            <Skeleton className="h-24" />
            <Skeleton className="h-24" />
            <Skeleton className="h-24" />
          </div>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-paper px-4">
        <Alert
          variant="destructive"
          className="max-w-md border-critical/30 bg-critical-soft"
        >
          <AlertTitle className="font-display text-lg tracking-tight">
            Couldn't load your data
          </AlertTitle>
          <AlertDescription>
            <p className="mb-4">{error}</p>
            <Button size="sm" variant="destructive" onClick={retryLoad}>
              Retry
            </Button>
          </AlertDescription>
        </Alert>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-paper text-ink">
      <Header
        viewMode={viewMode}
        onViewChange={setViewMode}
        onAdd={handleAdd}
        showForm={showForm || !!editingOpp}
        remindersEnabled={remindersEnabled}
        remindersSupported={remindersSupported}
        onToggleReminders={toggleReminders}
      />

      {viewMode === 'dashboard' && <Hero opportunities={opportunities} />}

      <main className="mx-auto max-w-5xl space-y-5 px-5 py-8">
        {saveError && (
          <Alert
            variant="destructive"
            role="alert"
            className="flex items-center justify-between border-warning/30 bg-warning-soft text-warning"
          >
            <AlertTitle className="text-warning">
              Storage error — changes may not be saved.
            </AlertTitle>
            <button
              onClick={retrySave}
              className="shrink-0 text-xs font-medium underline hover:no-underline"
            >
              Retry save
            </button>
          </Alert>
        )}

        {showForm && <EntryForm onSave={handleSaveNew} onCancel={handleCancel} />}
        {editingOpp && (
          <EntryForm
            onSave={handleSaveEdit}
            onCancel={handleCancel}
            initial={editingOpp}
            isEdit
          />
        )}

        {viewMode === 'dashboard' && (
          <>
            {opportunities.length === 0 && !showForm && !editingOpp ? (
              <EmptyState onAdd={handleAdd} />
            ) : (
              <>
                {opportunities.length > 0 && (
                  <div className="flex flex-col gap-4">
                    <FilterBar
                      filters={filters}
                      onFilterChange={setFilters}
                      sources={sources}
                      allTags={allTags}
                      activeCount={active.length + archived.length}
                      totalCount={totalCount}
                    />
                    <div className="flex items-center justify-end">
                      <ExportButton opportunities={opportunities} />
                    </div>
                  </div>
                )}

                {active.length > 0 && (
                  <section aria-labelledby="active-heading">
                    <h3
                      id="active-heading"
                      className="kicker mb-3 border-b border-rule pb-2"
                    >
                      active ({active.length})
                    </h3>
                    <div className="space-y-2">
                      {active.map(opp => (
                        <OpportunityCard
                          key={opp.id}
                          opp={opp}
                          onEdit={handleEdit}
                          onDelete={handleDelete}
                          onChangeStatus={changeStatus}
                        />
                      ))}
                    </div>
                  </section>
                )}

                {archived.length > 0 && (
                  <ArchiveSection
                    archived={archived}
                    onEdit={handleEdit}
                    onDelete={handleDelete}
                    onChangeStatus={changeStatus}
                  />
                )}

                {opportunities.length > 0 &&
                  active.length === 0 &&
                  archived.length === 0 && (
                    <div className="rounded-lg border border-dashed border-rule py-12 text-center">
                      <p className="kicker mb-2">no matches</p>
                      <p className="text-sm text-ink-muted">
                        No opportunities match your filters.
                      </p>
                    </div>
                  )}
              </>
            )}
          </>
        )}

        {viewMode === 'weekly-review' && (
          <WeeklyReviewMode
            opportunities={opportunities}
            onEdit={handleEdit}
            onDelete={handleDelete}
            onChangeStatus={changeStatus}
          />
        )}

        {viewMode === 'stats' && <StatsPanel opportunities={opportunities} />}
      </main>

      <footer className="border-t border-rule">
        <div className="mx-auto flex max-w-5xl flex-col gap-2 px-5 py-8 sm:flex-row sm:items-center sm:justify-between">
          <p className="font-display text-sm font-semibold tracking-tight text-ink">
            OppTrack
          </p>
          <p className="kicker">
            personal opportunity tracker · deadlines, sorted
          </p>
        </div>
      </footer>
    </div>
  );
}

export default function App() {
  return (
    <ToastProvider>
      <AppContent />
    </ToastProvider>
  );
}
