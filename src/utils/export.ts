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

export function exportAsICS(opps: Opportunity[]): string {
  const activeOpps = opps.filter(o => o.deadline && o.status !== 'Completed');
  if (activeOpps.length === 0) return '';

  const lines: string[] = [
    'BEGIN:VCALENDAR',
    'VERSION:2.0',
    'PRODID:-//OppTrack//OppTrack//EN',
    'CALSCALE:GREGORIAN',
    'METHOD:PUBLISH',
  ];

  const now = icsStamp(new Date());

  for (const opp of activeOpps) {
    const dt = opp.deadline.replace(/-/g, '');
    lines.push('BEGIN:VEVENT');
    lines.push(`UID:${opp.id}@opptrack`);
    lines.push(`DTSTAMP:${now}`);
    lines.push(`DTSTART;VALUE=DATE:${dt}`);
    lines.push(`SUMMARY:${icsEscape(`${opp.title} (${opp.type})`)}`);
    if (opp.link) lines.push(`URL:${opp.link}`);
    const description = opp.notes
      ? `${opp.notes} — via ${opp.source || 'OppTrack'}`
      : `${opp.status} — via ${opp.source || 'OppTrack'}`;
    lines.push(`DESCRIPTION:${icsEscape(description)}`);
    lines.push('END:VEVENT');
  }

  lines.push('END:VCALENDAR');
  return lines.join('\r\n');
}

function icsStamp(date: Date): string {
  const pad = (n: number) => String(n).padStart(2, '0');
  return (
    `${date.getUTCFullYear()}${pad(date.getUTCMonth() + 1)}${pad(date.getUTCDate())}` +
    `T${pad(date.getUTCHours())}${pad(date.getUTCMinutes())}${pad(date.getUTCSeconds())}Z`
  );
}

function icsEscape(value: string): string {
  return value
    .replace(/\\/g, '\\\\')
    .replace(/;/g, '\\;')
    .replace(/,/g, '\\,')
    .replace(/\r?\n/g, '\\n');
}

function todayFilename(): string {
  const d = new Date();
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`;
}
