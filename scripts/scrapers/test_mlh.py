"""Extract MLH Inertia.js data - check upcomingEvents/pastEvents."""
import httpx
import json
import re

resp = httpx.get("https://www.mlh.com/seasons/2027/events/", timeout=15, follow_redirects=True)
html = resp.text

m = re.search(r'data-page="app"[^>]*>(.*?)</script>', html, re.DOTALL)
raw = m.group(1).strip()
data = json.loads(raw)
props = data.get("props", {})

upcoming = props.get("upcomingEvents", [])
past = props.get("pastEvents", [])
print(f"upcomingEvents: {len(upcoming)}")
print(f"pastEvents: {len(past)}")

if upcoming:
    first = upcoming[0]
    print(f"\nFirst upcoming event keys: {list(first.keys())}")
    print(json.dumps(first, indent=2, default=str)[:3000])
elif past:
    first = past[0]
    print(f"\nFirst past event keys: {list(first.keys())}")
    print(json.dumps(first, indent=2, default=str)[:3000])
