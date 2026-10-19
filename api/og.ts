import { CACHE, fail, requireGet } from './_lib/respond.ts';
import type { ApiRequest, ApiResponse } from './_lib/types.ts';
import { OPPORTUNITY_TYPES, ParamError } from './_lib/validate.ts';

/**
 * GET /api/og — dynamic Open-Graph image (§11.4, F11).
 * Renders an SVG card via stdlib string templating; user text is XML-escaped.
 * NOTE: many social crawlers (Facebook, LinkedIn) do not render SVG OG images —
 * documented limitation in docs/API.md.
 */

function escapeXml(s: string): string {
  return s
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&apos;');
}

/** Wrap text into at most `maxLines` lines of ~`perLine` chars. */
function wrap(text: string, perLine: number, maxLines: number): string[] {
  const words = text.split(/\s+/).filter(Boolean);
  const lines: string[] = [];
  let cur = '';
  for (const w of words) {
    const candidate = cur ? `${cur} ${w}` : w;
    if (candidate.length > perLine && cur) {
      lines.push(cur);
      cur = w;
      if (lines.length === maxLines) break;
    } else {
      cur = candidate;
    }
  }
  if (lines.length < maxLines && cur) lines.push(cur);
  if (lines.length === maxLines && words.join(' ').length > lines.join(' ').length) {
    lines[maxLines - 1] = `${lines[maxLines - 1].slice(0, perLine - 1)}…`;
  }
  return lines;
}

const TYPE_COLORS: Record<string, string> = {
  Hackathon: '#22d3ee',
  Internship: '#a78bfa',
  Certification: '#fbbf24',
  Competition: '#f472b6',
};

export default function handler(req: ApiRequest, res: ApiResponse): unknown {
  if (!requireGet(req, res)) return;
  try {
    const q = req.query ?? {};
    const first = (k: string): string | undefined => {
      const v = q[k];
      const s = Array.isArray(v) ? v[0] : v;
      const t = typeof s === 'string' ? s.trim() : '';
      return t === '' ? undefined : t;
    };

    const rawTitle = first('title') ?? 'OPP-Track';
    if (rawTitle.length > 300) throw new ParamError('title must be 300 characters or fewer.');
    const rawType = first('type');
    if (rawType !== undefined && !(OPPORTUNITY_TYPES as readonly string[]).includes(rawType)) {
      throw new ParamError(`type must be one of: ${OPPORTUNITY_TYPES.join(', ')}.`);
    }
    const source = first('source');
    const deadline = first('deadline');

    const accent = rawType ? TYPE_COLORS[rawType] : '#38bdf8';
    const titleLines = wrap(rawTitle, 26, 3);
    const titleSvg = titleLines
      .map((line, i) => `<text x="80" y="${270 + i * 76}" font-size="64" font-weight="700" fill="#f8fafc">${escapeXml(line)}</text>`)
      .join('\n  ');

    const metaParts = [rawType, source, deadline && `Deadline ${deadline}`].filter(Boolean) as string[];
    const meta = metaParts.length ? metaParts.join('  ·  ') : 'Complete opportunities catalog';

    const svg = `<svg xmlns="http://www.w3.org/2000/svg" width="1200" height="630" viewBox="0 0 1200 630">
  <rect width="1200" height="630" fill="#0b1120"/>
  <rect x="0" y="0" width="1200" height="10" fill="${escapeXml(accent)}"/>
  <text x="80" y="120" font-size="32" font-weight="600" fill="${escapeXml(accent)}" letter-spacing="4">OPP-TRACK</text>
  ${titleSvg}
  <text x="80" y="540" font-size="28" fill="#94a3b8">${escapeXml(meta)}</text>
</svg>`;

    res.status(200);
    res.setHeader('Content-Type', 'image/svg+xml; charset=utf-8');
    res.setHeader('Cache-Control', CACHE.og);
    res.send(svg);
  } catch (err) {
    if (err instanceof ParamError) {
      fail(res, 400, err.code, err.message);
      return;
    }
    fail(res, 500, 'internal_error', 'Unexpected error.');
  }
}
