import json
import urllib.request
import urllib.error
import concurrent.futures
from datetime import date, datetime
from collections import Counter

with open('data/scraped_opportunities.json', encoding='utf-8') as f:
    data = json.load(f)

today = date(2026, 9, 12)
print('=== LIVE LINK CHECK: ALL', len(data), 'ITEMS ===')

def check(url):
    req = urllib.request.Request(url, method='GET', headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) OppTrackValidator/1.0'})
    try:
        with urllib.request.urlopen(req, timeout=25) as r:
            body = r.read(4096)
            return (url, r.status, None)
    except urllib.error.HTTPError as e:
        return (url, e.code, None)
    except Exception as e:
        return (url, None, type(e).__name__)

results = []
with concurrent.futures.ThreadPoolExecutor(max_workers=25) as ex:
    futs = {ex.submit(check, it['link']): it for it in data}
    for fu in concurrent.futures.as_completed(futs):
        it = futs[fu]
        try:
            results.append((fu.result(), it))
        except Exception as e:
            results.append((('ERR', None, 'submit'), it))

bad = [(r, it) for r, it in results if not (r[1] and r[1] < 400)]
print('total checked :', len(results))
print('live (2xx/3xx):', len(results) - len(bad))
print('bad           :', len(bad))
print()
print('--- bad by domain ---')
dom = Counter()
for (u, s, e), it in bad:
    dom[u.split('/')[2] if '://' in u else u] += 1
for d, c in dom.most_common(20):
    print(f'  {c:>4}  {d}')
print()
print('--- bad sample (first 40) ---')
for (u, s, e), it in bad[:40]:
    print(f'  [{s or e}] {u[:95]}  <- {it["source"]}')
done = len(results)
print()
print('done', done)