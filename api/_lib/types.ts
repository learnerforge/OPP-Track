/**
 * Minimal request/response typings for the read-only API routes.
 * Deliberately independent of `@vercel/node` so `api/` typechecks
 * standalone (see api/tsconfig.json) with only `@types/node` installed.
 */

export type QueryValue = string | string[] | undefined;

export interface ApiRequest {
  method?: string;
  query?: Record<string, QueryValue>;
  url?: string;
  /**
   * Parsed JSON body. The Vercel Node runtime populates this for requests with
   * `Content-Type: application/json`; the read-only GET routes never look at
   * it, so it stays optional and unused outside the write endpoint.
   */
  body?: unknown;
  headers?: Record<string, string | string[] | undefined>;
}

export interface ApiResponse {
  status(code: number): unknown;
  json(body: unknown): unknown;
  setHeader(name: string, value: string): unknown;
  send(body: string): unknown;
}

/** The subset of an opportunity record the API reads (src/types/opportunity.ts). */
export interface OpportunityRecord {
  id?: string;
  fingerprint?: string;
  title: string;
  type: string;
  source: string;
  link: string;
  deadline: string;
  eligibility: string;
  tags: string[];
  status?: string;
  notes: string;
  date_added: string;
  location?: string;
  prize_pool?: string;
  participants?: string;
  organizer?: string;
  duration?: string;
  quality_score?: number;
  [key: string]: unknown;
}

export type RouteHandler = (req: ApiRequest, res: ApiResponse) => unknown;
