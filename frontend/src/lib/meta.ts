import type { OpportunityStatus, OpportunityType } from '@/types/opportunity';

/* Display metadata for status + type. Chips render as small mono pills
   against the warm paper. Kept DRY across the app. */

export const STATUS_META: Record<
  OpportunityStatus,
  { label: string; className: string }
> = {
  'Not Started': { label: 'not started', className: 'bg-ink-faint/15 text-ink-soft' },
  Applied: { label: 'applied', className: 'bg-accent/10 text-accent' },
  'In Progress': { label: 'in progress', className: 'bg-warning/10 text-warning' },
  Rejected: { label: 'rejected', className: 'bg-critical/10 text-critical' },
  Completed: { label: 'done', className: 'bg-safe/10 text-safe' },
};

export const TYPE_META: Record<
  OpportunityType,
  { label: string; glyph: string; className: string }
> = {
  Hackathon: { label: 'hackathon', glyph: '◆', className: 'bg-accent/10 text-accent' },
  Internship: { label: 'internship', glyph: '▲', className: 'bg-safe/10 text-safe' },
  Certification: { label: 'certification', glyph: '●', className: 'bg-warning/10 text-warning' },
  Competition: { label: 'competition', glyph: '■', className: 'bg-critical/10 text-critical' },
};
