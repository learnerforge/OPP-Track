import { STORAGE_KEY } from '../constants';
import type { Opportunity } from '../types/opportunity';

interface StorageResult {
  data: Opportunity[];
  isNew: boolean;
}

export class StorageError extends Error {
  constructor(message: string, public readonly operation: 'read' | 'write') {
    super(message);
    this.name = 'StorageError';
  }
}

function getStorage(): { get: (key: string) => string | null; set: (key: string, value: string) => void } | null {
  if (typeof window !== 'undefined' && window.storage && typeof window.storage.get === 'function') {
    return window.storage;
  }
  return null;
}

export function loadOpportunities(): StorageResult {
  const storage = getStorage();

  if (!storage) {
    return { data: [], isNew: true };
  }

  try {
    const raw = storage.get(STORAGE_KEY);
    if (raw === null || raw === undefined) {
      return { data: [], isNew: true };
    }
    const parsed = JSON.parse(raw) as Opportunity[];
    if (!Array.isArray(parsed)) {
      throw new Error('Stored data is not an array');
    }
    return { data: parsed, isNew: false };
  } catch (e) {
    throw new StorageError(
      `Failed to load opportunities: ${e instanceof Error ? e.message : 'Unknown error'}`,
      'read'
    );
  }
}

export function saveOpportunities(list: Opportunity[]): void {
  const storage = getStorage();

  if (!storage) {
    throw new StorageError('Storage API not available', 'write');
  }

  try {
    storage.set(STORAGE_KEY, JSON.stringify(list));
  } catch (e) {
    throw new StorageError(
      `Failed to save opportunities: ${e instanceof Error ? e.message : 'Unknown error'}`,
      'write'
    );
  }
}
