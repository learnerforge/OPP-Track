import { build } from 'esbuild';
import { mkdtempSync, writeFileSync, rmSync, readFileSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { dirname, join } from 'node:path';
import { fileURLToPath, pathToFileURL } from 'node:url';

const __dirname = dirname(fileURLToPath(import.meta.url));
const repoRoot = join(__dirname, '..');

const VALID_STATUS = ['Not Started', 'Applied', 'In Progress', 'Rejected', 'Completed'];
const VALID_TYPES = ['Hackathon', 'Internship', 'Certification'];
const DATE_RE = /^\d{4}-\d{2}-\d{2}$/;
const CHECK_LINKS = process.argv.includes('--check-links');

function isRealDate(s) {
  if (!DATE_RE.test(s)) return false;
  const d = new Date(`${s}T00:00:00Z`);
  return !Number.isNaN(d.getTime()) && d.toISOString().slice(0, 10) === s;
}

async function loadSeeds() {
  const dir = mkdtempSync(join(tmpdir(), 'opptrack-validate-'));
  const outfile = join(dir, 'storage.mjs');
  try {
    await build({
      entryPoints: [join(repoRoot, 'src', 'lib', 'storage.ts')],
      bundle: true,
      format: 'esm',
      platform: 'browser',
      outfile,
      logLevel: 'silent',
    });
    const mod = await import(pathToFileURL(outfile).href);
    return { seeds: mod.SEED_DATA, version: mod.SEED_VERSION };
  } finally {
    rmSync(dir, { recursive: true, force: true });
  }
}

async function checkLink(url) {
  try {
    const controller = new AbortController();
    const timer = setTimeout(() => controller.abort(), 8000);
    const res = await fetch(url, { method: 'HEAD', redirect: 'follow', signal: controller.signal });
    clearTimeout(timer);
    if (res.ok) return { ok: true };
    const res2 = await fetch(url, { method: 'GET', redirect: 'follow', signal: controller.signal });
    clearTimeout(timer);
    return { ok: res2.ok, status: res2.status };
  } catch {
    return { ok: false };
  }
}

const { seeds, version } = await loadSeeds();

const errors = [];
const warnings = [];

const todayStr = new Date().toISOString().slice(0, 10);
const ids = new Set();
const titles = new Map();

for (const seed of seeds) {
  const id = seed?.id;
  if (!id) {
    errors.push(`entry at index ${seeds.indexOf(seed)} is missing id`);
    continue;
  }

  for (const field of ['title', 'type', 'source', 'link', 'deadline', 'eligibility', 'status', 'notes', 'date_added']) {
    if (typeof seed[field] !== 'string') {
      errors.push(`[${id}] field '${field}' is missing or not a string`);
    }
  }
  if (!Array.isArray(seed.tags) || seed.tags.some(t => typeof t !== 'string')) {
    errors.push(`[${id}] 'tags' must be an array of strings`);
  }

  if (ids.has(id)) errors.push(`[${id}] duplicate id`);
  ids.add(id);

  if (!/^seed_\d{3}$/.test(id)) errors.push(`[${id}] id does not match seed_NNN format`);

  const titleKey = (seed.title ?? '').toLowerCase();
  if (titles.has(titleKey)) errors.push(`[${id}] duplicate title with ${titles.get(titleKey)}`);
  titles.set(titleKey, id);

  if (!VALID_STATUS.includes(seed.status)) errors.push(`[${id}] invalid status '${seed.status}'`);
  if (!VALID_TYPES.includes(seed.type)) errors.push(`[${id}] invalid type '${seed.type}'`);

  if (!isRealDate(seed.deadline)) errors.push(`[${id}] deadline '${seed.deadline}' is not a valid YYYY-MM-DD date`);
  if (!isRealDate(seed.date_added)) errors.push(`[${id}] date_added '${seed.date_added}' is not a valid YYYY-MM-DD date`);

  if (!seed.link && seed.type !== 'Certification') {
    warnings.push(`[${id}] empty link (only acceptable for some Certification entries)`);
  }

  if (seed.deadline && isRealDate(seed.deadline) && seed.deadline < todayStr && seed.status === 'Not Started') {
    warnings.push(`[${id}] deadline ${seed.deadline} has passed but status is still 'Not Started' — likely stale / closed registration`);
  }
}

let brokenLinks = [];
if (CHECK_LINKS) {
  const targets = seeds.filter(s => s.link);
  const results = await Promise.all(targets.map(async s => ({ seed: s, result: await checkLink(s.link) })));
  brokenLinks = results.filter(r => !r.result.ok).map(r => `[${r.seed.id}] ${r.seed.link}`);
}

const byType = {};
const byStatus = {};
for (const s of seeds) {
  byType[s.type] = (byType[s.type] ?? 0) + 1;
  byStatus[s.status] = (byStatus[s.status] ?? 0) + 1;
}

console.log(`\n=== Seed data report ===`);
console.log(`SEED_VERSION: ${version}`);
console.log(`entries: ${seeds.length}`);
console.log(`by type:  ${JSON.stringify(byType)}`);
console.log(`by status: ${JSON.stringify(byStatus)}`);
console.log(`errors: ${errors.length}, warnings: ${warnings.length}${CHECK_LINKS ? `, broken links: ${brokenLinks.length}` : ''}`);

for (const w of warnings) console.log(`  WARN  ${w}`);
for (const e of errors) console.log(`  ERROR ${e}`);
for (const l of brokenLinks) console.log(`  DEAD  ${l}`);

if (!CHECK_LINKS) {
  console.log(`\nTip: run 'npm run validate:links' to HTTP-check every link (makes network calls).`);
}

process.exit(errors.length === 0 && (!CHECK_LINKS || brokenLinks.length === 0) ? 0 : 1);
