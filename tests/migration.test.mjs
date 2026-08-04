import { build } from 'esbuild';
import { mkdtempSync, rmSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { dirname, join } from 'node:path';
import { fileURLToPath, pathToFileURL } from 'node:url';

const __dirname = dirname(fileURLToPath(import.meta.url));
const repoRoot = join(__dirname, '..');

const dir = mkdtempSync(join(tmpdir(), 'opptrack-test-'));
const outfile = join(dir, 'storage.mjs');
await build({
  entryPoints: [join(repoRoot, 'src', 'lib', 'storage.ts')],
  bundle: true,
  format: 'esm',
  platform: 'browser',
  outfile,
  logLevel: 'silent',
});
const { loadOpportunities, saveOpportunities, SEED_DATA, SEED_VERSION } = await import(pathToFileURL(outfile).href);
rmSync(dir, { recursive: true, force: true });

const seedIds = new Set(SEED_DATA.map(s => s.id));
const seedCount = SEED_DATA.length;
const canonical = id => SEED_DATA.find(s => s.id === id);

function makeStorage(initial) {
  const map = new Map(initial instanceof Map ? initial.entries() : Object.entries(initial || {}));
  return {
    get: (k) => (map.has(k) ? map.get(k) : null),
    set: (k, v) => map.set(k, v),
    dump: () => map,
  };
}

let failures = 0;
let checks = 0;
function check(label, cond) {
  checks++;
  console.log(`${cond ? 'PASS' : 'FAIL'} - ${label}`);
  if (!cond) failures++;
}

const oldSnapshot = [
  {
    id: 'seed_001',
    title: 'Smart India Hackathon 2026',
    type: 'Hackathon',
    source: 'TCOE India',
    link: 'https://sih.gov.in',
    deadline: '2026-07-31',
    eligibility: 'old',
    tags: ['AI/ML'],
    status: 'Not Started',
    notes: 'old deadline version',
    date_added: '2026-07-29',
  },
  {
    id: 'seed_010',
    title: 'User edited seed',
    type: 'Hackathon',
    source: 'x',
    link: 'https://x',
    deadline: '2026-12-01',
    eligibility: '',
    tags: [],
    status: 'Applied',
    notes: 'user changed this to Applied - must stay',
    date_added: '2026-07-29',
  },
  {
    id: 'opp_123_user',
    title: 'My own opportunity',
    type: 'Internship',
    source: 'me',
    link: 'https://mine',
    deadline: '2026-10-01',
    eligibility: '',
    tags: [],
    status: 'In Progress',
    notes: '',
    date_added: '2026-07-30',
  },
];

// --- Test 1: old snapshot (no version key) gets merged + refreshed ---
const s1 = makeStorage({});
globalThis.window = { storage: s1 };
s1.set('opportunities-list', JSON.stringify(oldSnapshot));

const r1 = loadOpportunities();
check('migrated snapshot returns isNew true', r1.isNew === true);
check('old + all new seeds + user opp present', r1.data.length === 3 + (seedCount - 2));
check('seed_001 refreshed to canonical', r1.data.find(o => o.id === 'seed_001').deadline === canonical('seed_001').deadline);
check('seed_001 notes refreshed to canonical', r1.data.find(o => o.id === 'seed_001').notes === canonical('seed_001').notes);
check('Applied seed_010 preserved untouched', r1.data.find(o => o.id === 'seed_010').status === 'Applied' && r1.data.find(o => o.id === 'seed_010').notes === 'user changed this to Applied - must stay');
check('user opp preserved', r1.data.find(o => o.id === 'opp_123_user').status === 'In Progress');
check('last seed in SEED_DATA included', r1.data.some(o => o.id === SEED_DATA[SEED_DATA.length - 1].id));
check('kept canonical seed_199 (Gemini XPRIZE) included', r1.data.some(o => o.id === 'seed_199'));
check('version key written', s1.dump().get('opptrack-seed-version') === String(SEED_VERSION));
check('no duplicate seed_001', r1.data.filter(o => o.id === 'seed_001').length === 1);

// --- Test 2: reload with current version -> no re-migration ---
const s1b = makeStorage(s1.dump());
globalThis.window = { storage: s1b };
const r1b = loadOpportunities();
check('second load returns stored data unchanged', r1b.data.length === r1.data.length && r1b.isNew === false);

// --- Test 3: fresh user gets full seed list ---
const s2 = makeStorage({});
globalThis.window = { storage: s2 };
const r2 = loadOpportunities();
check('fresh user gets all seeds', r2.data.length === seedCount && r2.isNew === true);
check('fresh user version written', s2.dump().get('opptrack-seed-version') === String(SEED_VERSION));

// --- Test 4: older user with orphan seeds gets them dropped ---
const orphans = ['seed_016', 'seed_020', 'seed_040', 'seed_046', 'seed_052', 'seed_189'];
const v3Snapshot = [
  ...oldSnapshot,
  ...orphans.map((id, i) => ({
    id,
    title: `stale duplicate ${i}`,
    type: 'Hackathon',
    source: 'x',
    link: 'https://x',
    deadline: '2026-08-08',
    eligibility: '',
    tags: [],
    status: 'Not Started',
    notes: 'stale duplicate, must be dropped',
    date_added: '2026-07-29',
  })),
  {
    id: 'seed_199',
    title: 'Gemini XPRIZE (canonical, keep)',
    type: 'Hackathon',
    source: 'Devpost',
    link: 'https://xprize.devpost.com/',
    deadline: '2026-08-17',
    eligibility: '',
    tags: [],
    status: 'Applied',
    notes: 'user engaged with this canonical seed - keep as-is',
    date_added: '2026-08-01',
  },
];
const s4 = makeStorage({
  'opportunities-list': JSON.stringify(v3Snapshot),
  'opptrack-seed-version': '3',
});
globalThis.window = { storage: s4 };
const r4 = loadOpportunities();
for (const orphan of orphans) {
  if (seedIds.has(orphan)) continue;
  check(`orphan ${orphan} dropped`, !r4.data.some(o => o.id === orphan));
}
check('canonical engaged seed_199 preserved with user status', r4.data.find(o => o.id === 'seed_199').status === 'Applied' && r4.data.find(o => o.id === 'seed_199').notes === 'user engaged with this canonical seed - keep as-is');
check('user opp preserved after dedup', r4.data.some(o => o.id === 'opp_123_user'));
check('version bumped after dedup', s4.dump().get('opptrack-seed-version') === String(SEED_VERSION));
check('deduped list is complete (4 kept + rest added)', r4.data.length === 4 + (seedCount - 3));

// --- Test 5: saveOpportunities bumps version ---
const s5 = makeStorage({
  'opportunities-list': JSON.stringify([oldSnapshot[2]]),
  'opptrack-seed-version': '0',
});
globalThis.window = { storage: s5 };
saveOpportunities(JSON.parse(s5.dump().get('opportunities-list')));
check('save writes current version', s5.dump().get('opptrack-seed-version') === String(SEED_VERSION));

// --- Test 6: version bump refreshes Not Started seeds, preserves edited ones ---
const v4Snapshot = [
  { ...oldSnapshot[0], id: 'seed_037', title: '.hack \'26', status: 'Not Started', notes: 'old', tags: ['IEEE'] },
  { ...oldSnapshot[0], id: 'seed_038', title: 'NexHack 2.0 @ IIT Madras', status: 'Not Started', notes: 'old', tags: ['IIT'] },
  { ...oldSnapshot[0], id: 'seed_105', title: 'TechHub Africa 2026', status: 'Not Started', notes: 'old', tags: [] },
  { ...oldSnapshot[1], id: 'seed_024', title: 'Amazon SDE Intern 2027', status: 'Applied', notes: 'user edited me - keep' },
];
const s6 = makeStorage({
  'opportunities-list': JSON.stringify(v4Snapshot),
  'opptrack-seed-version': '4',
});
globalThis.window = { storage: s6 };
const r6 = loadOpportunities();
for (const id of ['seed_037', 'seed_038', 'seed_105']) {
  const got = r6.data.find(o => o.id === id);
  check(`${id} refreshed to canonical`, got.eligibility === canonical(id).eligibility && got.notes === canonical(id).notes);
}
check('user-edited Applied seed_024 kept its status+notes', r6.data.find(o => o.id === 'seed_024').status === 'Applied' && r6.data.find(o => o.id === 'seed_024').notes === 'user edited me - keep');
check('version bumped after v4 snapshot', s6.dump().get('opptrack-seed-version') === String(SEED_VERSION));

console.log(failures === 0 ? `\nALL ${checks} TESTS PASSED` : `\n${failures}/${checks} TEST(S) FAILED`);
process.exit(failures === 0 ? 0 : 1);
