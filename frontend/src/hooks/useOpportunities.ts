import { useCallback, useEffect, useState } from 'react';
import type { Opportunity } from '@/types/opportunity';
import { supabase } from '@/lib/supabase';
import { useAuth } from '@/context/AuthContext';

interface UseOpportunitiesReturn {
  opportunities: Opportunity[];
  loading: boolean;
  error: string | null;
  addOpportunity: (opp: Omit<Opportunity, 'id' | 'user_id'>) => Promise<void>;
  updateOpportunity: (opp: Opportunity) => Promise<void>;
  deleteOpportunity: (id: string) => Promise<void>;
  changeStatus: (id: string, status: Opportunity['status']) => Promise<void>;
  retryLoad: () => void;
}

/** Map a DB row (snake_case) into the app's Opportunity shape. */
function rowToOpportunity(row: Record<string, unknown>): Opportunity {
  return {
    id: row.id as string,
    user_id: row.user_id as string,
    title: row.title as string,
    type: row.type as Opportunity['type'],
    source: (row.source as string) ?? '',
    link: (row.link as string) ?? '',
    deadline: row.deadline as string,
    eligibility: (row.eligibility as string) ?? '',
    tags: (row.tags as string[]) ?? [],
    status: row.status as Opportunity['status'],
    notes: (row.notes as string) ?? '',
    date_added: row.date_added as string,
    location: (row.location as string) ?? null,
    prize_pool: (row.prize_pool as string) ?? null,
    participants: (row.participants as string) ?? null,
    organizer: (row.organizer as string) ?? null,
    duration: (row.duration as string) ?? null,
    quality_score: (row.quality_score as number) ?? null,
  };
}

export function useOpportunities(): UseOpportunitiesReturn {
  const { session } = useAuth();
  const userId = session?.user?.id;

  const [opps, setOpps] = useState<Opportunity[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [reloadKey, setReloadKey] = useState(0);

  useEffect(() => {
    if (!userId) {
      setOpps([]);
      setLoading(false);
      return;
    }

    let cancelled = false;
    setLoading(true);
    setError(null);

    supabase
      .from('opportunities')
      .select('*')
      .order('deadline', { ascending: true })
      .then(({ data, error: err }) => {
        if (cancelled) return;
        if (err) {
          setError(err.message);
          setOpps([]);
        } else {
          setOpps((data ?? []).map(rowToOpportunity));
        }
        setLoading(false);
      });

    return () => {
      cancelled = true;
    };
  }, [userId, reloadKey]);

  const addOpportunity = useCallback(
    async (opp: Omit<Opportunity, 'id' | 'user_id'>) => {
      if (!userId) return;
      const { error: err } = await supabase
        .from('opportunities')
        .insert({ ...opp, user_id: userId });
      if (err) {
        setError(err.message);
        return;
      }
      setReloadKey(k => k + 1);
    },
    [userId]
  );

  const updateOpportunity = useCallback(async (opp: Opportunity) => {
    const { id, user_id: _u, ...rest } = opp;
    // Optimistic update.
    setOpps(prev => prev.map(o => (o.id === id ? { ...o, ...rest } : o)));
    const { error: err } = await supabase
      .from('opportunities')
      .update(rest)
      .eq('id', id);
    if (err) {
      setError(err.message);
      setReloadKey(k => k + 1);
    }
  }, []);

  const deleteOpportunity = useCallback(async (id: string) => {
    const snapshot: Opportunity[] = [];
    setOpps(prev => {
      snapshot.push(...prev);
      return prev.filter(o => o.id !== id);
    });
    const { error: err } = await supabase
      .from('opportunities')
      .delete()
      .eq('id', id);
    if (err) {
      setError(err.message);
      setOpps(snapshot);
    }
  }, []);

  const changeStatus = useCallback(
    async (id: string, status: Opportunity['status']) => {
      setOpps(prev => prev.map(o => (o.id === id ? { ...o, status } : o)));
      const { error: err } = await supabase
        .from('opportunities')
        .update({ status })
        .eq('id', id);
      if (err) {
        setError(err.message);
        setReloadKey(k => k + 1);
      }
    },
    []
  );

  const retryLoad = useCallback(() => setReloadKey(k => k + 1), []);

  return {
    opportunities: opps,
    loading,
    error,
    addOpportunity,
    updateOpportunity,
    deleteOpportunity,
    changeStatus,
    retryLoad,
  };
}
