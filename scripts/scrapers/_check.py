import json
data = json.load(open("data/scraped_opportunities.json", encoding="utf-8"))
sources = {}
for i in data:
    s = i["source"]
    sources[s] = sources.get(s, 0) + 1
print(f"Total items: {len(data)}")
print(f"Sources: {len(sources)}")
for s in sorted(sources):
    print(f"  {s}: {sources[s]}")
