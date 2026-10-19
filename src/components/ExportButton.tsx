import { useState } from 'react';
import type { Opportunity } from '../types/opportunity';
import {
  exportAsJSON,
  exportAsCSV,
  exportAsICS,
  downloadFile,
  copyToClipboard,
  getExportFilename,
} from '../utils';
import { Button } from './ui/button';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from './ui/dropdown-menu';

interface ExportButtonProps {
  opportunities: Opportunity[];
}

type ExportFormat = 'json' | 'csv' | 'ics';
type ExportAction = 'download' | 'clipboard';

export function ExportButton({ opportunities }: ExportButtonProps) {
  const [copied, setCopied] = useState(false);

  async function handleExport(format: ExportFormat, action: ExportAction) {
    const content =
      format === 'json'
        ? exportAsJSON(opportunities)
        : format === 'csv'
          ? exportAsCSV(opportunities)
          : exportAsICS(opportunities);

    if (!content && format === 'ics') return;

    if (action === 'download') {
      const filename = getExportFilename(format);
      const mime =
        format === 'json'
          ? 'application/json'
          : format === 'csv'
            ? 'text/csv'
            : 'text/calendar';
      downloadFile(content, filename, mime);
    } else {
      const ok = await copyToClipboard(content);
      if (ok) {
        setCopied(true);
        setTimeout(() => setCopied(false), 2000);
      }
    }
  }

  return (
    <DropdownMenu>
      <DropdownMenuTrigger asChild>
        <Button
          size="sm"
          variant="outline"
          aria-label="Export opportunities"
          className="h-8 gap-1.5 font-mono text-xs"
        >
          <svg
            className="h-3.5 w-3.5"
            fill="none"
            viewBox="0 0 24 24"
            stroke="currentColor"
            strokeWidth={2}
            aria-hidden="true"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              d="M12 3v12m0 0 4-4m-4 4-4-4M4 17v2a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2v-2"
            />
          </svg>
          Export
        </Button>
      </DropdownMenuTrigger>
      <DropdownMenuContent align="end" className="w-52">
        <DropdownMenuLabel className="kicker text-inherit">
          download
        </DropdownMenuLabel>
        <DropdownMenuItem onClick={() => handleExport('json', 'download')}>
          JSON file
        </DropdownMenuItem>
        <DropdownMenuItem onClick={() => handleExport('csv', 'download')}>
          CSV file
        </DropdownMenuItem>
        <DropdownMenuItem onClick={() => handleExport('ics', 'download')}>
          Calendar (.ics)
        </DropdownMenuItem>
        <DropdownMenuSeparator />
        <DropdownMenuLabel className="kicker text-inherit">
          copy to clipboard
        </DropdownMenuLabel>
        <DropdownMenuItem
          onClick={() => handleExport('json', 'clipboard')}
          aria-live="polite"
        >
          {copied ? '✓ Copied!' : 'JSON'}
        </DropdownMenuItem>
        <DropdownMenuItem
          onClick={() => handleExport('csv', 'clipboard')}
          aria-live="polite"
        >
          {copied ? '✓ Copied!' : 'CSV'}
        </DropdownMenuItem>
      </DropdownMenuContent>
    </DropdownMenu>
  );
}
