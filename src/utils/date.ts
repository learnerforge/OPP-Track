import type { UrgencyTier } from '../types/opportunity';
import { URGENCY_THRESHOLDS } from '../constants';

export function generateId(): string {
  const ts = Date.now();
  const rand = Math.random().toString(36).substring(2, 6);
  return `opp_${ts}_${rand}`;
}

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

export function formatDate(dateStr: string): string {
  if (!dateStr) return '';
  const d = new Date(dateStr + 'T00:00:00');
  return d.toLocaleDateString('en-IN', { day: 'numeric', month: 'short', year: 'numeric' });
}

export function isExpiredOrCompleted(deadline: string, status: string): boolean {
  return status === 'Completed' || daysBetween(deadline, todayStr()) < 0;
}

export function getDaysLabel(deadline: string, status: string): string {
  if (status === 'Completed') return 'Completed';
  const days = daysRemaining(deadline);
  if (days < 0) return 'Expired';
  if (days === 0) return 'Today!';
  if (days === 1) return '1 day left';
  return `${days} days left`;
}

export function isWithinDays(dateStr: string, numDays: number): boolean {
  const days = daysBetween(dateStr, todayStr());
  return days >= 0 && days <= numDays;
}
