"""Investigate MLH Inertia.js data structure and Challenge.gov API."""
import httpx
import json
from scrapling import Selector

def test_mlh_inertia():
    resp = httpx.get("https://www.mlh.com/seasons/2027/events/", timeout=15, follow_redirects=True)
    html = resp.text
    # Extract Inertia data-page JSON
    import re
    m = re.search(r'data-page="app"[^>]*>(.*?)</div>', html)
    if not m:
        print("No Inertia data found")
        return
    
    data = json.loads(m.group(1))
    props = data.get("props", {})
    events = props.get("events", props.get("data", []))
    print(f"MLH Inertia component: {data.get('component')}")
    print(f"Top-level props keys: {list(props.keys())[:15]}")
    print(f"Events count: {len(events)}")
    
    if events:
        first = events[0]
        print(f"\nFirst event keys: {list(first.keys())}")
        print(json.dumps(first, indent=2, default=str)[:1500])

def test_challenge_gov():
    # Try various API paths
    urls = [
        "https://www.challenge.gov/api/challenges",
        "https://www.challenge.gov/api/search",
        "https://api.challenge.gov/challenges",
        "https://www.challenge.gov/",
    ]
    for url in urls:
        try:
            resp = httpx.get(url, timeout=10, follow_redirects=True)
            print(f"  {url} -> {resp.status_code} {resp.url}")
            if resp.status_code == 200:
                ct = resp.headers.get("content-type", "")
                if "json" in ct:
                    data = resp.json()
                    print(f"    Keys: {list(data.keys())[:10]}")
                else:
                    print(f"    Content-Type: {ct}, length: {len(resp.text)}")
        except Exception as e:
            print(f"  {url} -> ERROR: {e}")

if __name__ == "__main__":
    print("=== MLH ===")
    test_mlh_inertia()
    print("\n=== Challenge.gov ===")
    test_challenge_gov()
