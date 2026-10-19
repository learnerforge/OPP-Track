#!/usr/bin/env node
// scripts/validate-data.mjs — contract validator for the canonical dataset.
//
// Usage:
//   node scripts/validate-data.mjs [path] [--check-links]
//
//   path           JSON file to validate (default: data/scraped_opportunities.json)
//   --check-links  additionally HTTP-check every non-empty link (network calls)
//
// Rules implement the §11.2 data contract:
//   - title   : required, non-empty string
//   - type    : Hackathon | Internship | Certification | Competition
//   - link    : valid http(s) URL or '' (empty = link intentionally absent; never fabricated)
//   - deadline: '' (rolling/evergreen — valid, never an error) or a real YYYY-MM-DD date
//   - source/eligibility/notes/date_added/tags : contract fields, must exist with the right type
//   - identity: at least one of `id` / `fingerprint`; duplicates are errors.
//     `id` and `status` are OPTIONAL: raw scrape output has neither (regenerate_seeds.py
//     injects them when building the bundled snapshot) — checks for them only run when
//     the field is present, and no fixed id pattern is enforced (B2 rule 1).
//
// Exit codes: 0 = pass (warnings allowed), 1 = fail.

import { readFileSync } from 'node:fs';
import { dirname, join, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';

const __dirname = dirname(fileURLToPath(import.meta.url));
const repoRoot = join(__dirname, '..');

const DEFAULT_DATASET = join(repoRoot, 'data', 'scraped_opportunities.json');
const VALID_TYPES = ['Hackathon', 'Internship', 'Certification', 'Competition'];
const VALID_STATUS = ['Not Started', 'Applied', 'In Progress', 'Rejected', 'Completed'];
const REQUIRED_STRING_FIELDS = ['title', 'type', 'source', 'link', 'deadline', 'eligibility', 'notes', 'date_added'];
const DATE_RE = /^\d{4}-\d{2}-\d{2}$/;
const MAX_REPORTED = 200;

const argv = process.argv.slice(2);
const CHECK_LINKS = argv.includes('--check-links');
const pathArg = argv.find((a) => !a.startsWith('--'));
const dataPath = pathArg ? resolve(process.cwd(), pathArg) : DEFAULT_DATASET;

function isRealDate(s) {
  if (typeof s !== 'string' || !DATE_RE.test(s)) return false;
  const d = new Date(`${s}T00:00:00Z`);
  return !Number.isNaN(d.getTime()) && d.toISOString().slice(0, 10) === s;
}

function isHttpUrl(s) {
  try {
    const u = new URL(s);
    return u.protocol === 'http:' || u.protocol === 'https:';
  } catch {
    return false;
  }
}

function labelOf(item, index) {
  if (item && typeof item === 'object') {
    if (typeof item.id === 'string' && item.id) return item.id;
    if (typeof item.fingerprint === 'string' && item.fingerprint) return item.fingerprint;
  }
  return `index ${index}`;
}

function validateItems(items) {
  const errors = [];
  const warnings = [];
  const todayStr = new Date().toISOString().slice(0, 10);

  const ids = new Set();
  const fingerprints = new Set();
  const titleMap = new Map(); // lowercase title -> { label, link }
  const byType = {};
  let rolling = 0;

  items.forEach((item, index) => {
    if (item === null || typeof item !== 'object' || Array.isArray(item)) {
      errors.push(`[index ${index}] item is not an object`);
      return;
    }
    const label = labelOf(item, index);

    for (const field of REQUIRED_STRING_FIELDS) {
      if (typeof item[field] !== 'string') {
        errors.push(`[${label}] field '${field}' is missing or not a string`);
      }
    }
    if (!Array.isArray(item.tags) || item.tags.some((t) => typeof t !== 'string')) {
      errors.push(`[${label}] 'tags' must be an array of strings`);
    }

    // title: required, non-empty
    if (typeof item.title === 'string' && item.title.trim() === '') {
      errors.push(`[${label}] title is empty`);
    }

    // type: closed enum (B2 rule 3 — 'Competition' is part of the Opportunity union)
    if (typeof item.type === 'string' && !VALID_TYPES.includes(item.type)) {
      errors.push(`[${label}] invalid type '${item.type}' (expected ${VALID_TYPES.join(' | ')})`);
    }
    byType[item.type] = (byType[item.type] ?? 0) + 1;

    // deadline: '' means rolling/evergreen — VALID, never "Invalid date" (B2 rule 2)
    if (typeof item.deadline === 'string') {
      if (item.deadline === '') {
        rolling += 1;
      } else if (!isRealDate(item.deadline)) {
        errors.push(`[${label}] deadline '${item.deadline}' must be '' (rolling) or a real YYYY-MM-DD date`);
      }
    }

    if (typeof item.date_added === 'string' && item.date_added !== '' && !isRealDate(item.date_added)) {
      errors.push(`[${label}] date_added '${item.date_added}' is not a valid YYYY-MM-DD date`);
    }

    // link: valid http(s) URL or '' (B11 — never fabricated)
    if (typeof item.link === 'string' && item.link !== '' && !isHttpUrl(item.link)) {
      errors.push(`[${label}] link '${item.link}' is not a valid http(s) URL (use '' when absent)`);
    }

    // identity: at least one of id / fingerprint; each must be unique.
    // No fixed id pattern (B2 rule 1 — '^seed_\d{3}$' rejected seed_1000..seed_2577).
    const hasId = typeof item.id === 'string' && item.id !== '';
    const hasFp = typeof item.fingerprint === 'string' && item.fingerprint !== '';
    if (!hasId && !hasFp) {
      errors.push(`[${label}] missing identity: needs a non-empty 'id' or 'fingerprint'`);
    }
    if (typeof item.id === 'string' && item.id !== '') {
      if (ids.has(item.id)) errors.push(`[${label}] duplicate id`);
      ids.add(item.id);
    }
    if (typeof item.fingerprint === 'string' && item.fingerprint !== '') {
      if (fingerprints.has(item.fingerprint)) errors.push(`[${label}] duplicate fingerprint`);
      fingerprints.add(item.fingerprint);
    }

    // status: user state injected at seed-generation time — checked only when present
    if ('status' in item && !VALID_STATUS.includes(item.status)) {
      errors.push(`[${label}] invalid status '${item.status}'`);
    }

    // duplicate title: error only when the link matches too (B13 — title alone is insufficient)
    if (typeof item.title === 'string' && item.title.trim() !== '') {
      const key = item.title.toLowerCase();
      const prev = titleMap.get(key);
      if (prev) {
        if (prev.link === item.link) {
          errors.push(`[${label}] duplicate entry: same title and link as ${prev.label}`);
        } else {
          warnings.push(`[${label}] duplicate title '${item.title}' with ${prev.label} (different link — kept, B13)`);
        }
      } else {
        titleMap.set(key, { label, link: item.link });
      }
    }

    // stale-data hint (warning only, and only when status is present)
    if (
      typeof item.status === 'string' &&
      typeof item.deadline === 'string' &&
      isRealDate(item.deadline) &&
      item.deadline < todayStr &&
      item.status === 'Not Started'
    ) {
      warnings.push(`[${label}] deadline ${item.deadline} has passed but status is still 'Not Started' — likely stale`);
    }
  });

  return { errors, warnings, byType, rolling };
}

async function checkLinks(items) {
  const targets = items.filter((it) => it && typeof it === 'object' && typeof it.link === 'string' && it.link !== '');
  const results = await Promise.all(
    targets.map(async (item) => {
      try {
        const controller = new AbortController();
        const timer = setTimeout(() => controller.abort(), 8000);
        const res = await fetch(item.link, { method: 'HEAD', redirect: 'follow', signal: controller.signal });
        clearTimeout(timer);
        if (res.ok) return null;
        const controller2 = new AbortController();
        const timer2 = setTimeout(() => controller2.abort(), 8000);
        const res2 = await fetch(item.link, { method: 'GET', redirect: 'follow', signal: controller2.signal });
        clearTimeout(timer2);
        return res2.ok ? null : `${labelOf(item, -1)} ${item.link} (status ${res2.status})`;
      } catch {
        return `${labelOf(item, -1)} ${item.link} (unreachable)`;
      }
    }),
  );
  return results.filter(Boolean);
}

function printList(tag, lines) {
  const shown = lines.slice(0, MAX_REPORTED);
  for (const l of shown) console.log(`  ${tag}  ${l}`);
  if (lines.length > shown.length) console.log(`  ... and ${lines.length - shown.length} more ${tag.toLowerCase()}s (showing first ${MAX_REPORTED})`);
}

async function main() {
  let raw;
  try {
    raw = readFileSync(dataPath, 'utf8');
  } catch (err) {
    console.error(`\n=== Dataset validation report ===\nfile: ${dataPath}`);
    console.error(`RESULT: FAIL — cannot read file: ${err.message}`);
    process.exit(1);
  }

  let data;
  try {
    data = JSON.parse(raw);
  } catch (err) {
    console.error(`\n=== Dataset validation report ===\nfile: ${dataPath}`);
    console.error(`RESULT: FAIL — invalid JSON: ${err.message}`);
    process.exit(1);
  }

  const errors = [];
  const warnings = [];

  if (!Array.isArray(data)) {
    console.error(`\n=== Dataset validation report ===\nfile: ${dataPath}`);
    console.error('RESULT: FAIL — top level must be a plain JSON array of opportunity objects (§11.2)');
    process.exit(1);
  }
  if (data.length === 0) {
    errors.push('dataset is an empty array — refusing to pass an empty catalog');
  }

  const { errors: itemErrors, warnings: itemWarnings, byType, rolling } = validateItems(data);
  errors.push(...itemErrors);
  warnings.push(...itemWarnings);

  let brokenLinks = [];
  if (CHECK_LINKS && errors.length === 0) {
    brokenLinks = await checkLinks(data);
  }

  const sources = new Set(data.filter((i) => i && typeof i === 'object' && typeof i.source === 'string').map((i) => i.source));

  console.log(`\n=== Dataset validation report ===`);
  console.log(`file:    ${dataPath}`);
  console.log(`entries: ${data.length}`);
  console.log(`by type: ${JSON.stringify(byType)}`);
  console.log(`sources: ${sources.size} | rolling (deadline ''): ${rolling} | dated: ${data.length - rolling}`);
  console.log(`errors: ${errors.length}, warnings: ${warnings.length}${CHECK_LINKS ? `, dead links: ${brokenLinks.length}` : ''}`);

  printList('WARN', warnings);
  printList('ERROR', errors);
  if (brokenLinks.length) printList('DEAD', brokenLinks);

  const failed = errors.length > 0 || (CHECK_LINKS && brokenLinks.length > 0);
  console.log(`\nRESULT: ${failed ? 'FAIL' : 'PASS'}`);
  if (!CHECK_LINKS && !failed) {
    console.log(`Tip: 'npm run validate:links' additionally HTTP-checks every link (makes network calls).`);
  }
  process.exit(failed ? 1 : 0);
}

await main();
