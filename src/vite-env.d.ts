interface ArtifactStorage {
  get(key: string): string | null;
  set(key: string, value: string): void;
  delete(key: string): void;
  list(): string[];
}

interface Window {
  storage?: ArtifactStorage;
}
