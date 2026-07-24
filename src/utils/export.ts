import type { Opportunity } from '../types/opportunity';

export function exportAsJSON(opps: Opportunity[]): string {
  return JSON.stringify(opps, null, 2);
}

export function exportAsCSV(opps: Opportunity[]): string {
  if (opps.length === 0) return '';

  const headers = [
    'Title',
    'Type',
    'Source',
    'Link',
    'Deadline',
    'Eligibility',
    'Tags',
    'Status',
    'Notes',
    'Date Added',
  ];

  const rows = opps.map(opp => [
    escapeCSV(opp.title),
    escapeCSV(opp.type),
    escapeCSV(opp.source),
    escapeCSV(opp.link),
    escapeCSV(opp.deadline),
    escapeCSV(opp.eligibility),
    escapeCSV(opp.tags.join('; ')),
    escapeCSV(opp.status),
    escapeCSV(opp.notes),
    escapeCSV(opp.date_added),
  ]);

  return [headers.join(','), ...rows.map(r => r.join(','))].join('\n');
}

function escapeCSV(value: string): string {
  if (value.includes(',') || value.includes('"') || value.includes('\n')) {
    return `"${value.replace(/"/g, '""')}"`;
  }
  return value;
}

export function downloadFile(
  content: string,
  filename: string,
  mimeType: string
): void {
  const blob = new Blob([content], { type: mimeType });
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = filename;
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
  URL.revokeObjectURL(url);
}

export function copyToClipboard(text: string): Promise<boolean> {
  return navigator.clipboard
    .writeText(text)
    .then(() => true)
    .catch(() => false);
}

export function getExportFilename(extension: string): string {
  const date = todayFilename();
  return `opptrack-export-${date}.${extension}`;
}

function todayFilename(): string {
  const d = new Date();
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`;
}
