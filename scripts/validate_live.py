import json
import sys
import urllib.request
import urllib.error
import concurrent.futures
from datetime import date, datetime
from collections import Counter

with open('data/scraped_opportunities.json', encoding='utf-8') as f:
    data = json.load(f)

today = date(2026, 9, 12)

def parse_deadline(s):
    if not s or s in ('TBD', 'Rolling', 'rolling', 'Unknown', 'None', ''):
        return None
    s = s.strip()
    for fmt in ('%Y-%m-%d', '%d %B %Y', '%B %d, %Y', '%b %d, %Y', '%d-%m-%Y'):
        try:
            return datetime.strptime(s, fmt).date()
        except ValueError:
            continue
    return None

print('=== DEADLINE FRESHNESS ===')
expired = 0
no_deadline = 0
deadline_items = []
for it in data:
    d = parse_deadline(it.get('deadline', ''))
    if d is None:
        no_deadline += 1
    elif d < today:
        expired += 1
    deadline_items.append((it, d))
print('total items       :', len(data))
print('no deadline (TBD) :', no_deadline)
print('expired (d<today) :', expired)
print('active            :', sum(1 for _, d in deadline_items if d and d >= today))

print()
print('=== EXPIRED SAMPLE (first 20) ===')
for it, d in deadline_items:
    if d and d < today:
        print(f'  [{d}] {it["title"][:60]} | {it["source"]}')
        if sum(1 for _ in range(1)) >= 20:
            pass
expired_list = [(it, d) for it, d in deadline_items if d and d < today]
for it, d in expired_list[:20]:
    print(f'  [{d}] {it["title"][:60]} | {it["source"]}')
print('... total expired:', len(expired_list))

print()
print('=== LIVE LINK CHECK (sample 120) ===')
links = [it['link'] for it in data]
sample = links[:120]

def check(url):
    req = urllib.request.Request(url, method='HEAD', headers={'User-Agent': 'Mozilla/5.0 (compatible; OppTrackValidator/1.0)'})
    try:
        with urllib.request.urlopen(req, timeout=20) as r:
            return (url, r.status, None)
    except urllib.error.HTTPError as e:
        return (url, e.code, None)
    except Exception as e:
        return (url, None, type(e).__name__)

results = []
with concurrent.futures.ThreadPoolExecutor(max_workers=20) as ex:
    for r in ex.map(check, sample):
        results.append(r)

ok = sum(1 for _, s, e in results if s and s < 400)
bad = [(u, s, e) for u, s, e in results if not (s and s < 400)]
print('checked :', len(results))
print('live    :', ok)
print('bad     :', len(bad))
for u, s, e in bad[:30]:
    print(f'  [{s or e}] {u[:90]}')