"""Comprehensive per-unit validation report for scraped_opportunities.json.

Checks every item against real-time data:
  1. Schema validity (run_all --validate equivalent)
  2. Live link check (HTTP status vs the live internet)
  3. Deadline freshness vs today
  4. Duplicate links / titles
  5. Field completeness (organizer, prize, location, notes)
Outputs a per-source table and an anomaly list.
"""

import json
import re
import sys
import urllib.request
import urllib.error
import concurrent.futures
from datetime import date, datetime
from collections import Counter, defaultdict

try:
    sys.stdout.reconfigure(encoding='utf-8')
    sys.stderr.reconfigure(encoding='utf-8')
except AttributeError:
    pass

DATA = 'data/scraped_opportunities.json'
TODAY = date(2026, 9, 12)
VALID_TYPES = ('Hackathon', 'Internship', 'Certification', 'Competition')


def main():
    with open(DATA, encoding='utf-8') as f:
        data = json.load(f)

    print(f'=== UNIT VALIDATION REPORT — {len(data)} items ===')
    print(f'(check date: {TODAY})\n')

    # 1) Schema check per unit
    schema_errors = []
    for it in data:
        errs = []
        if not it.get('title', '').strip():
            errs.append('empty title')
        if it.get('type') not in VALID_TYPES:
            errs.append(f'bad type {it.get("type")}')
        if not it.get('source', '').strip():
            errs.append('empty source')
        d = it.get('deadline', '')
        if d:
            try:
                datetime.strptime(d, '%Y-%m-%d')
            except ValueError:
                errs.append(f'bad deadline {d}')
        if not it.get('link', '').startswith(('http://', 'https://')):
            errs.append('bad link')
        if errs:
            schema_errors.append((it, errs))

    # 2) Live link check (all)
    def check(url):
        req = urllib.request.Request(url, method='GET',
                                     headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) OPPTrackValidator/1.0'})
        try:
            with urllib.request.urlopen(req, timeout=25) as r:
                r.read(1024)
                return (url, True, None)
        except urllib.error.HTTPError as e:
            return (url, e.code < 400, e.code)
        except Exception as ex:
            return (url, False, type(ex).__name__)

    link_results = {}
    with concurrent.futures.ThreadPoolExecutor(max_workers=25) as ex:
        futs = {ex.submit(check, it['link']): it for it in data}
        for fu in concurrent.futures.as_completed(futs):
            u, ok, info = fu.result()
            link_results[u] = (ok, info)

    # 3) Deadline freshness per unit
    def fresh(it):
        d = it.get('deadline', '')
        if not d:
            return 'none'
        try:
            dd = datetime.strptime(d, '%Y-%m-%d').date()
        except ValueError:
            return 'bad'
        return 'active' if dd >= TODAY else 'expired'

    # 4) Duplicates
    link_keys = Counter(it['link'].rstrip('/').lower() for it in data)
    title_keys = Counter(it['title'].strip().lower() for it in data)
    dup_links = {k: v for k, v in link_keys.items() if v > 1}
    dup_titles = {k: v for k, v in title_keys.items() if v > 1}

    # 5) Field completeness
    def completeness(it):
        score = 0
        for f in ('deadline', 'organizer', 'prize_pool', 'location', 'tags'):
            if it.get(f):
                score += 1
        return score

    # Per-source aggregation
    print('=== PER-SOURCE TABLE ===')
    print(f'{"SOURCE":24s} {"ITEMS":>5s} {"LIVE":>5s} {"BAD":>4s} {"ACTIVE":>7s} {"NONE":>5s} {"EXPIRED":>8s} {"FAIL":>5s}')
    per_source = defaultdict(list)
    for it in data:
        per_source[it['source']].append(it)

    total_live = 0
    total_bad_units = []
    for src in sorted(per_source):
        its = per_source[src]
        n = len(its)
        live = sum(1 for it in its if link_results[it['link']][0])
        bad = n - live
        st = Counter(fresh(it) for it in its)
        active, none, expired, bad_fmt = st['active'], st['none'], st['expired'], st['bad']
        n_fail = len([it for it in its if not (it.get('organizer','') and it.get('location','') and it.get('notes',''))])
        total_live += live
        if bad:
            for it in its:
                if not link_results[it['link']][0]:
                    total_bad_units.append((it, link_results[it['link']][1]))
        print(f'{src:24s} {n:5d} {live:5d} {bad:4d} {active:7d} {none:5d} {expired:8d} {n_fail:5d}')

    print()
    print('=== CROSS-CHECK SUMMARY ===')
    print(f'schema errors        : {len(schema_errors)}')
    print(f'links checked all    : {len(data)}')
    print(f'live links           : {total_live} ({100*total_live/len(data):.1f}%)')
    print(f'bad links            : {len(total_bad_units)}')
    print(f'units active deadline: {sum(1 for it in data if fresh(it)=="active")}')
    print(f'units no deadline    : {sum(1 for it in data if fresh(it)=="none")}')
    print(f'units expired        : {sum(1 for it in data if fresh(it)=="expired")}')
    print(f'duplicate links      : {sum(v-1 for v in dup_links.values())}')
    print(f'duplicate titles     : {len(dup_titles)}')

    print()
    print('=== ANOMALY LIST ===')
    if schema_errors:
        print('-- schema errors --')
        for it, errs in schema_errors[:15]:
            print(f'  {it["source"]}: {it["title"][:50]} -> {errs}')
    if total_bad_units:
        print(f'-- bad links ({len(total_bad_units)} @ 80 shown) --')
        dom = Counter((u.split('/')[2] if '://' in u else u) for u, _ in total_bad_units)
        print('  by domain:', dict(dom.most_common(12)))
        for it, info in total_bad_units[:80]:
            print(f'  [{info}] {it["source"]}: {it["title"][:45]} | {it["link"][:70]}')
    if dup_titles:
        print('-- duplicate titles --')
        for t, c in list(dup_titles.items())[:10]:
            print(f'  {c}x {t[:60]}')
    if not (schema_errors or total_bad_units or dup_titles):
        print('  none')


if __name__ == '__main__':
    main()