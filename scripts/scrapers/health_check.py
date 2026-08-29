"""Real-time health check for remaining scrapers (skipping detail-heavy ones)."""
import concurrent.futures
import json
import sys
import time
import logging

sys.path.insert(0, r"E:\GitHub Projects\OPP-Track")
from scripts.scrapers.run_all import SCRAPERS

logging.getLogger().setLevel(logging.CRITICAL)

SKIP = {
    "devfolio", "devpost", "hackerearth", "internshala",
    "unstop", "mlh", "hack2skill", "techgig", "hackindia",
    "swayam", "nptel", "coursera", "analytics_vidhya", "machinehack",
}

def run_one(pair):
    name, (label, func) = pair
    t0 = time.time()
    try:
        items = func()
        return label, len(items), round(time.time() - t0, 1), "OK" if items else "EMPTY"
    except Exception as e:
        return label, 0, round(time.time() - t0, 1), f"ERR: {str(e)[:60]}"

pairs = [(n, v) for n, v in SCRAPERS.items() if n not in SKIP]
print(f"Running {len(pairs)} scrapers (skipped {len(SKIP)} slow detail-fetchers)...\n")

results = []
with concurrent.futures.ThreadPoolExecutor(max_workers=8) as ex:
    for label, n, t, status in ex.map(run_one, pairs):
        results.append({"source": label, "items": n, "time_s": t, "status": status})
        print(f"{status:<12} {n:3d} items  {t:5.1f}s  {label}", flush=True)

total = sum(r["items"] for r in results)
errors = [r for r in results if r["status"].startswith("ERR")]
empties = [r for r in results if r["status"] == "EMPTY"]
print(f"\n=== TOTAL: {total} items | ERRORS: {len(errors)} | EMPTY: {len(empties)} | CHECKED: {len(results)} ===")
if errors:
    print("\n-- FAILED --")
    for r in errors:
        print(f"  {r['source']}: {r['status']}")
if empties:
    print("\n-- EMPTY (returned 0) --")
    for r in empties:
        print(f"  {r['source']}")

with open(r"E:\GitHub Projects\OPP-Track\data\scraper_health.json", "w", encoding="utf-8") as f:
    json.dump(results, f, indent=2, ensure_ascii=False)
print("\nSaved to data/scraper_health.json")