import { useState, useCallback, useEffect, useRef } from 'react';
import type { Opportunity } from '../types/opportunity';
import { loadOpportunities, saveOpportunities, StorageError } from '../lib/storage';
import { generateId, todayStr } from '../utils';

interface UseOpportunitiesReturn {
  opportunities: Opportunity[];
  loading: boolean;
  error: string | null;
  saveError: string | null;
  addOpportunity: (opp: Omit<Opportunity, 'id' | 'date_added'>) => void;
  updateOpportunity: (opp: Opportunity) => void;
  deleteOpportunity: (id: string) => void;
  changeStatus: (id: string, status: Opportunity['status']) => void;
  retrySave: () => void;
  retryLoad: () => void;
}

export function useOpportunities(): UseOpportunitiesReturn {
  const [opps, setOpps] = useState<Opportunity[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [saveError, setSaveError] = useState<string | null>(null);
  const pendingWrite = useRef<Opportunity[] | null>(null);
  const saveErrorTimer = useRef<ReturnType<typeof setTimeout> | null>(null);

  const load = useCallback(() => {
    setLoading(true);
    setError(null);
    try {
      const { data } = loadOpportunities();
      setOpps(data);
    } catch (e) {
      if (e instanceof StorageError) {
        setError(e.message);
      } else {
        setError('An unexpected error occurred while loading data.');
      }
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  const showSaveError = useCallback((msg: string) => {
    setSaveError(msg);
    if (saveErrorTimer.current) clearTimeout(saveErrorTimer.current);
    saveErrorTimer.current = setTimeout(() => setSaveError(null), 8000);
  }, []);

  const persist = useCallback(
    (list: Opportunity[]) => {
      try {
        saveOpportunities(list);
        setSaveError(null);
        pendingWrite.current = null;
        if (saveErrorTimer.current) clearTimeout(saveErrorTimer.current);
        return true;
      } catch (e) {
        pendingWrite.current = list;
        if (e instanceof StorageError) {
          showSaveError(e.message);
        } else {
          showSaveError('Failed to save changes.');
        }
        return false;
      }
    },
    [showSaveError]
  );

  const readCurrentStorage = useCallback((): Opportunity[] => {
    try {
      const { data } = loadOpportunities();
      return data;
    } catch {
      return opps;
    }
  }, [opps]);

  const addOpportunity = useCallback(
    (opp: Omit<Opportunity, 'id' | 'date_added'>) => {
      const newOpp: Opportunity = {
        ...opp,
        id: generateId(),
        date_added: todayStr(),
      };
      const current = readCurrentStorage();
      const updated = [...current, newOpp];
      setOpps(updated);
      if (!persist(updated)) {
        setOpps(current);
      }
    },
    [readCurrentStorage, persist]
  );

  const updateOpportunity = useCallback(
    (opp: Opportunity) => {
      const current = readCurrentStorage();
      const updated = current.map(o => (o.id === opp.id ? opp : o));
      setOpps(updated);
      if (!persist(updated)) {
        setOpps(current);
      }
    },
    [readCurrentStorage, persist]
  );

  const deleteOpportunity = useCallback(
    (id: string) => {
      const current = readCurrentStorage();
      const updated = current.filter(o => o.id !== id);
      setOpps(updated);
      if (!persist(updated)) {
        setOpps(current);
      }
    },
    [readCurrentStorage, persist]
  );

  const changeStatus = useCallback(
    (id: string, status: Opportunity['status']) => {
      const current = readCurrentStorage();
      const updated = current.map(o => (o.id === id ? { ...o, status } : o));
      setOpps(updated);
      if (!persist(updated)) {
        setOpps(current);
      }
    },
    [readCurrentStorage, persist]
  );

  const retrySave = useCallback(() => {
    if (pendingWrite.current) {
      persist(pendingWrite.current);
    }
  }, [persist]);

  return {
    opportunities: opps,
    loading,
    error,
    saveError,
    addOpportunity,
    updateOpportunity,
    deleteOpportunity,
    changeStatus,
    retrySave,
    retryLoad: load,
  };
}
