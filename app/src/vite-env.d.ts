/// <reference types="vite/client" />

/**
 * Environment variables exposed to the app bundle at build time.
 *
 * `VITE_EDITS_TOKEN` is the shared secret the write endpoint checks. Vite only
 * inlines variables prefixed `VITE_`, and inlined values are visible in the
 * bundle — which is acceptable here because the login gate already ships the
 * app openly and the endpoint independently fails closed when unset. It is
 * still set in Vercel rather than committed.
 */
interface ImportMetaEnv {
  readonly VITE_EDITS_TOKEN?: string;
}

interface ImportMeta {
  readonly env: ImportMetaEnv;
}
