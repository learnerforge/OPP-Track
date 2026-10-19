import type { UrgencyTier } from '@/types/opportunity';
import { URGENCY_THRESHOLDS } from '@/lib/constants';

export function todayStr(): string {
  const d = new Date();
  const yyyy = d.getFullYear();
  const mm = String(d.getMonth() + 1).padStart(2, '0');
  const dd = String(d.getDate()).padStart(2, '0');
  return `${yyyy}-${mm}-${dd}`;
}

export function daysBetween(dateA: string, dateB: string): number {
  const a = new Date(dateA + 'T23:59:59');
  const b = new Date(dateB + 'T23:59:59');
  const diffMs = a.getTime() - b.getTime();
  return Math.ceil(diffMs / (1000 * 60 * 60 * 24));
}

export function daysRemaining(deadline: string): number {
  return daysBetween(deadline, todayStr());
}

export function getUrgency(deadline: string, status: string): UrgencyTier {
  if (status === 'Completed') return 'expired';
  const days = daysBetween(deadline, todayStr());
  if (days < 0) return 'expired';
  if (days <= URGENCY_THRESHOLDS.CRITICAL_MAX_DAYS) return 'critical';
  if (days <= URGENCY_THRESHOLDS.WARNING_MAX_DAYS) return 'warning';
  return 'safe';
}

export function isExpiredOrCompleted(deadline: string, status: string): boolean {
  return status === 'Completed' || daysBetween(deadline, todayStr()) < 0;
}

export function isWithinDays(deadline: string, days: number): boolean {
  const remaining = daysRemaining(deadline);
  return remaining >= 0 && remaining <= days;
}

export function getDaysLabel(deadline: string, status: string): string {
  if (status === 'Completed') return 'Done';
  const days = daysBetween(deadline, todayStr());
  if (days < 0) return `Expired ${Math.abs(days)}d ago`;
  if (days === 0) return 'Due today';
  if (days === 1) return '1 day left';
  return `${days} days left`;
}

export function formatDate(iso: string): string {
  const d = new Date(iso + 'T00:00:00');
  return d.toLocaleDateString('en-IN', {
    day: 'numeric',
    month: 'short',
    year: 'numeric',
  });
}
