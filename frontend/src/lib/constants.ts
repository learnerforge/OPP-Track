import type { OpportunityType, OpportunityStatus, UrgencyTier } from '@/types/opportunity';

export const TYPE_OPTIONS: readonly OpportunityType[] = [
  'Hackathon',
  'Internship',
  'Certification',
  'Competition',
] as const;

export const STATUS_OPTIONS: readonly OpportunityStatus[] = [
  'Not Started',
  'Applied',
  'In Progress',
  'Rejected',
  'Completed',
] as const;

export const URGENCY_THRESHOLDS = {
  CRITICAL_MAX_DAYS: 2,
  WARNING_MAX_DAYS: 7,
} as const;

/* Editorial urgency — warm ink + a single signal colour per tier. */
export const URGENCY_STYLES: Record<
  UrgencyTier,
  { bg: string; border: string; badge: string; dot: string; text: string }
> = {
  critical: {
    bg: 'bg-critical-soft',
    border: 'border-critical/30',
    badge: 'bg-critical/10 text-critical',
    dot: 'bg-critical',
    text: 'text-critical',
  },
  warning: {
    bg: 'bg-warning-soft',
    border: 'border-warning/30',
    badge: 'bg-warning/10 text-warning',
    dot: 'bg-warning',
    text: 'text-warning',
  },
  safe: {
    bg: 'bg-safe-soft',
    border: 'border-safe/30',
    badge: 'bg-safe/10 text-safe',
    dot: 'bg-safe',
    text: 'text-safe',
  },
  expired: {
    bg: 'bg-muted',
    border: 'border-rule',
    badge: 'bg-ink-faint/10 text-ink-muted',
    dot: 'bg-ink-faint',
    text: 'text-ink-muted',
  },
};
