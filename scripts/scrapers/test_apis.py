"""Quick test script for API-based sources."""
import httpx
import json

def test_codeforces():
    resp = httpx.get("https://codeforces.com/api/contest.list", timeout=15)
    print(f"Codeforces API: {resp.status_code}")
    if resp.status_code == 200:
        data = resp.json()
        if data.get("status") == "OK":
            contests = [c for c in data["result"] if c.get("phase") == "BEFORE"][:3]
            for c in contests:
                print(f"  {c['name'][:50]} | phase={c['phase']}")
            return len(contests)
    return 0

def test_challenge_gov():
    resp = httpx.get("https://www.challenge.gov/api/challenges?page=1&page_size=5", timeout=15)
    print(f"Challenge.gov API: {resp.status_code}")
    if resp.status_code == 200:
        data = resp.json()
        challenges = data.get("challenges", data.get("results", []))[:3]
        for c in challenges:
            title = c.get("title", c.get("name", "?"))
            print(f"  {title[:50]}")
        return len(challenges)
    else:
        print(f"  Body: {resp.text[:200]}")
    return 0

def test_usajobs():
    headers = {
        "Host": "data.usajobs.gov",
        "User-Agent": "Mozilla/5.0",
        "Authorization-Key": "no-key"
    }
    resp = httpx.get(
        "https://data.usajobs.gov/api/search?ResultsPerPage=5&Keyword=internship&WhoMayApply=Students",
        headers=headers, timeout=15
    )
    print(f"USAJOBS API: {resp.status_code}")
    if resp.status_code == 200:
        data = resp.json()
        results = data.get("SearchResult", {}).get("SearchResultItems", [])[:3]
        for r in results:
            match = r.get("MatchedObjectDescriptor", {})
            print(f"  {match.get('PositionTitle', '?')[:50]} | {match.get('OrganizationName', '?')}")
        return len(results)
    else:
        print(f"  Body: {resp.text[:200]}")
    return 0

def test_kaggle():
    resp = httpx.get("https://www.kaggle.com/api/v1/competitions/list", timeout=15, follow_redirects=True)
    print(f"Kaggle API: {resp.status_code}")
    if resp.status_code == 200:
        try:
            data = resp.json()
            if isinstance(data, list):
                for c in data[:3]:
                    print(f"  {c.get('title', '?')[:50]} | reward={c.get('reward', '?')}")
                return len(data)
            else:
                print(f"  Non-list: {str(data)[:200]}")
        except Exception as e:
            print(f"  Parse error: {e}")
    else:
        print(f"  Body: {resp.text[:200]}")
    return 0

def test_unstop_api():
    resp = httpx.get(
        "https://unstop.com/api/public/opportunity/search-result",
        params={"page": 1, "per_page": 5, "type": "hackathon", "domain": "it"},
        timeout=15
    )
    print(f"Unstop API: {resp.status_code}")
    if resp.status_code == 200:
        data = resp.json()
        items = data.get("data", [])[:3]
        for item in items:
            print(f"  {item.get('title', '?')[:50]}")
        return len(items)
    else:
        print(f"  Body: {resp.text[:200]}")
    return 0

if __name__ == "__main__":
    results = {}
    results["codeforces"] = test_codeforces()
    results["challenge_gov"] = test_challenge_gov()
    results["usajobs"] = test_usajobs()
    results["kaggle"] = test_kaggle()
    results["unstop_api"] = test_unstop_api()
    print(f"\nResults: {results}")
