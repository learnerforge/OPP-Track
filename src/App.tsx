import { useState, useEffect, useCallback } from 'react';
import type { ViewMode, Filters, Opportunity } from './types/opportunity';
import { useOpportunities } from './hooks/useOpportunities';
import { useFilters } from './hooks/useFilters';
import { useReminders } from './hooks/useReminders';
import {
  Header,
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
    showToast('Opportunity deleted');
  }

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="text-center">
          <div className="inline-block w-8 h-8 border-[3px] border-indigo-200 border-t-indigo-600 rounded-full animate-spin mb-3" />
          <p className="text-sm text-gray-500">Loading your opportunities...</p>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="min-h-screen flex items-center justify-center px-4">
        <div className="bg-red-50 border border-red-200 rounded-xl p-6 max-w-md text-center">
          <div className="text-3xl mb-3">⚠️</div>
          <h2 className="text-lg font-semibold text-red-800 mb-2">
            Couldn't load your data
          </h2>
          <p className="text-sm text-red-600 mb-4">{error}</p>
          <button
            onClick={retryLoad}
            className="bg-red-600 hover:bg-red-700 text-white font-medium px-5 py-2 rounded-lg text-sm transition-colors"
          >
            Retry
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-50">
      <Header
        viewMode={viewMode}
        onViewChange={setViewMode}
        onAdd={handleAdd}
        showForm={showForm}
        remindersEnabled={remindersEnabled}
        remindersSupported={remindersSupported}
        onToggleReminders={toggleReminders}
      />

      <main className="max-w-4xl mx-auto px-4 py-6 space-y-4">
        {saveError && (
          <div
            role="alert"
            className="bg-amber-50 border border-amber-200 rounded-lg p-3 flex items-center justify-between"
          >
            <span className="text-sm text-amber-700">
              Storage error — changes may not be saved.
            </span>
            <button
              onClick={retrySave}
              className="text-xs font-medium text-amber-800 underline hover:no-underline"
            >
              Retry Save
            </button>
          </div>
        )}

        {showForm && (
          <EntryForm onSave={handleSaveNew} onCancel={handleCancel} />
        )}
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
                  <div className="flex items-center justify-between">
                    <FilterBar
                      filters={filters}
                      onFilterChange={setFilters}
                      sources={sources}
                      allTags={allTags}
                      activeCount={active.length + archived.length}
                      totalCount={totalCount}
                    />
                    <ExportButton opportunities={opportunities} />
                  </div>
                )}

                {active.length > 0 && (
                  <div>
                    <h3 className="text-sm font-semibold text-gray-500 uppercase tracking-wide mb-2 px-1">
                      Active ({active.length})
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
                  </div>
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
                    <div className="text-center py-12">
                      <p className="text-gray-400 text-sm">
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

        {viewMode === 'stats' && (
          <StatsPanel opportunities={opportunities} />
        )}
      </main>

      <footer className="text-center py-6 text-xs text-gray-400">
        OppTrack — Personal Opportunity Tracker
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
