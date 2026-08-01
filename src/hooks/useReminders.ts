import { useCallback, useEffect, useRef, useState } from 'react';
import type { Opportunity } from '../types/opportunity';
import { daysRemaining } from '../utils';

const REMINDER_WINDOW_DAYS = 2;
const CHECK_INTERVAL_MS = 5 * 60 * 1000;
const STORAGE_KEY = 'opptrack-reminders';

interface UseRemindersReturn {
  enabled: boolean;
  supported: boolean;
  toggle: () => void;
}

function isNotificationSupported(): boolean {
  return typeof window !== 'undefined' && 'Notification' in window;
}

function readStored(): boolean {
  try {
    return localStorage.getItem(STORAGE_KEY) === 'on';
  } catch {
    return false;
  }
}

export function useReminders(opportunities: Opportunity[]): UseRemindersReturn {
  const [enabled, setEnabled] = useState(readStored);
  const notifiedRef = useRef<Set<string>>(new Set());

  const toggle = useCallback(() => {
    if (!isNotificationSupported()) return;

    if (enabled) {
      setEnabled(false);
      try {
        localStorage.removeItem(STORAGE_KEY);
      } catch {
        /* ignore storage errors */
      }
      return;
    }

    if (Notification.permission === 'granted') {
      setEnabled(true);
      try {
        localStorage.setItem(STORAGE_KEY, 'on');
      } catch {
        /* ignore storage errors */
      }
      return;
    }

    Notification.requestPermission().then(permission => {
      if (permission === 'granted') {
        setEnabled(true);
        try {
          localStorage.setItem(STORAGE_KEY, 'on');
        } catch {
          /* ignore storage errors */
        }
      }
    });
  }, [enabled]);

  useEffect(() => {
    if (
      !enabled ||
      !isNotificationSupported() ||
      Notification.permission !== 'granted'
    ) {
      return;
    }

    function fire() {
      const today = new Date().toDateString();
      for (const opp of opportunities) {
        if (opp.status === 'Completed' || opp.status === 'Rejected') continue;
        const days = daysRemaining(opp.deadline);
        if (days < 0 || days > REMINDER_WINDOW_DAYS) continue;

        const key = `${opp.id}:${today}`;
        if (notifiedRef.current.has(key)) continue;
        notifiedRef.current.add(key);

        const label = days === 0 ? 'due today' : `due in ${days} day${days === 1 ? '' : 's'}`;
        const notification = new Notification(`⏰ ${opp.title}`, {
          body: `${label} · ${opp.type}${opp.source ? ` · via ${opp.source}` : ''}`,
          tag: key,
        });
        notification.onclick = () => {
          window.focus();
          notification.close();
        };
      }
    }

    fire();
    const interval = setInterval(fire, CHECK_INTERVAL_MS);
    return () => clearInterval(interval);
  }, [enabled, opportunities]);

  return {
    enabled,
    supported: isNotificationSupported(),
    toggle,
  };
}
