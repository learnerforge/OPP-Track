import type { OpportunityType, OpportunityStatus, UrgencyTier } from '../types/opportunity';

export const STORAGE_KEY = 'opportunities-list';

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

export const URGENCY_STYLES: Record<UrgencyTier, { bg: string; border: string; badge: string; dot: string }> = {
  critical: { bg: 'bg-red-50', border: 'border-red-300', badge: 'bg-red-100 text-red-800', dot: 'bg-red-500' },
  warning:  { bg: 'bg-yellow-50', border: 'border-yellow-300', badge: 'bg-yellow-100 text-yellow-800', dot: 'bg-yellow-500' },
  safe:     { bg: 'bg-green-50', border: 'border-green-300', badge: 'bg-green-100 text-green-800', dot: 'bg-green-500' },
  expired:  { bg: 'bg-gray-50', border: 'border-gray-200', badge: 'bg-gray-100 text-gray-600', dot: 'bg-gray-400' },
};

export const TYPE_COLORS: Record<OpportunityType, string> = {
  Hackathon: 'bg-purple-100 text-purple-800',
  Internship: 'bg-blue-100 text-blue-800',
  Certification: 'bg-teal-100 text-teal-800',
  Competition: 'bg-orange-100 text-orange-800',
};

export const TYPE_ICONS: Record<OpportunityType, string> = {
  Hackathon: '🏆',
  Internship: '💼',
  Certification: '📜',
  Competition: '🎯',
};

export const STATUS_COLORS: Record<OpportunityStatus, string> = {
  'Not Started': 'bg-gray-100 text-gray-700',
  'Applied': 'bg-blue-100 text-blue-700',
  'In Progress': 'bg-amber-100 text-amber-700',
  'Rejected': 'bg-red-100 text-red-700',
  'Completed': 'bg-green-100 text-green-700',
};
