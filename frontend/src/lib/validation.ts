import type { Opportunity } from '@/types/opportunity';

export interface ValidationError {
  field: string;
  message: string;
}

function isValidUrl(str: string): boolean {
  try {
    const u = new URL(str);
    return u.protocol === 'http:' || u.protocol === 'https:';
  } catch {
    return false;
  }
}

export function validateOpportunity(
  opp: Partial<Opportunity>,
  isEdit: boolean
): ValidationError[] {
  const errors: ValidationError[] = [];

  if (!opp.title?.trim()) {
    errors.push({ field: 'title', message: 'Title is required' });
  }
  if (!opp.type) {
    errors.push({ field: 'type', message: 'Type is required' });
  }
  if (!opp.deadline) {
    errors.push({ field: 'deadline', message: 'Deadline is required' });
  }
  if (opp.link && !isValidUrl(opp.link)) {
    errors.push({ field: 'link', message: 'Enter a valid URL' });
  }
  if (isEdit && !opp.id) {
    errors.push({ field: 'id', message: 'Missing opportunity ID for edit' });
  }

  return errors;
}

export function getFieldError(
  errors: ValidationError[],
  field: string
): string | undefined {
  return errors.find(e => e.field === field)?.message;
}
