import { useState, useEffect, useRef, useCallback } from 'react';
import type { Opportunity } from '../types/opportunity';
import {
  exportAsJSON,
  exportAsCSV,
  exportAsICS,
  downloadFile,
  copyToClipboard,
  getExportFilename,
} from '../utils';

interface ExportButtonProps {
  opportunities: Opportunity[];
}

type ExportFormat = 'json' | 'csv' | 'ics';
type ExportAction = 'download' | 'clipboard';

export function ExportButton({ opportunities }: ExportButtonProps) {
  const [open, setOpen] = useState(false);
  const [copied, setCopied] = useState(false);
  const menuRef = useRef<HTMLDivElement>(null);

  const close = useCallback(() => setOpen(false), []);

  useEffect(() => {
    if (!open) return;
    function handleKey(e: KeyboardEvent) {
      if (e.key === 'Escape') close();
    }
    document.addEventListener('keydown', handleKey);
    return () => document.removeEventListener('keydown', handleKey);
  }, [open, close]);

  async function handleExport(format: ExportFormat, action: ExportAction) {
    const content =
      format === 'json'
        ? exportAsJSON(opportunities)
        : format === 'csv'
          ? exportAsCSV(opportunities)
          : exportAsICS(opportunities);

    if (!content && format === 'ics') {
      close();
      return;
    }

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

    setOpen(false);
  }

  return (
    <div className="relative">
      <button
        onClick={() => setOpen(!open)}
        aria-haspopup="true"
        aria-expanded={open}
        aria-label="Export opportunities"
        className="text-xs bg-white border border-gray-200 text-gray-600 px-3 py-2 rounded-md hover:bg-gray-50 transition-colors font-medium min-h-[40px]"
      >
        📥 Export
      </button>

      {open && (
        <>
          <div
            className="fixed inset-0 z-40"
            onClick={close}
            aria-hidden="true"
          />
          <div
            ref={menuRef}
            role="menu"
            aria-label="Export options"
            className="absolute right-0 mt-1 bg-white border border-gray-200 rounded-lg shadow-lg z-50 py-1 w-52 animate-fade-in"
          >
            <div className="px-3 py-1.5 text-xs text-gray-400 font-medium uppercase tracking-wide">
              Download
            </div>
            <button
              role="menuitem"
              onClick={() => handleExport('json', 'download')}
              className="w-full text-left px-3 py-2 text-sm text-gray-700 hover:bg-gray-50 transition-colors"
            >
              📄 JSON file
            </button>
            <button
              role="menuitem"
              onClick={() => handleExport('csv', 'download')}
              className="w-full text-left px-3 py-2 text-sm text-gray-700 hover:bg-gray-50 transition-colors"
            >
              📊 CSV file
            </button>
            <button
              role="menuitem"
              onClick={() => handleExport('ics', 'download')}
              className="w-full text-left px-3 py-2 text-sm text-gray-700 hover:bg-gray-50 transition-colors"
            >
              📅 Calendar (.ics)
            </button>
            <div className="border-t border-gray-100 my-1" />
            <div className="px-3 py-1.5 text-xs text-gray-400 font-medium uppercase tracking-wide">
              Copy to Clipboard
            </div>
            <button
              role="menuitem"
              onClick={() => handleExport('json', 'clipboard')}
              className="w-full text-left px-3 py-2 text-sm text-gray-700 hover:bg-gray-50 transition-colors"
            >
              {copied ? '✅ Copied!' : '📋 JSON'}
            </button>
            <button
              role="menuitem"
              onClick={() => handleExport('csv', 'clipboard')}
              className="w-full text-left px-3 py-2 text-sm text-gray-700 hover:bg-gray-50 transition-colors"
            >
              {copied ? '✅ Copied!' : '📋 CSV'}
            </button>
          </div>
        </>
      )}
    </div>
  );
}
