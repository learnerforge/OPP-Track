import json

with open('data/scraped_opportunities.json') as f:
    items = json.load(f)

print('=== Devfolio items WITHOUT tags ===')
for i in items:
    if i['source'] == 'Devfolio' and not i.get('tags'):
        print(f'  {i["title"][:60]:60s} | {i["link"]}')

print()
print('=== Devfolio items WITHOUT organizer ===')
for i in items:
    if i['source'] == 'Devfolio' and not i.get('organizer'):
        print(f'  {i["title"][:60]:60s} | {i["link"]}')

print()
print('=== Devfolio items WITHOUT prize_pool ===')
for i in items:
    if i['source'] == 'Devfolio' and not i.get('prize_pool'):
        print(f'  {i["title"][:60]:60s}')

print()
print('=== Devpost items WITHOUT deadline ===')
for i in items:
    if i['source'] == 'Devpost' and not i.get('deadline'):
        print(f'  {i["title"][:60]:60s} | {i["link"]}')

print()
print('=== HackerEarth ALL ===')
for i in items:
    if i['source'] == 'HackerEarth':
        print(f'  {i["title"][:60]:60s} | deadline={i.get("deadline","")} | duration={i.get("duration","")} | prize={i.get("prize_pool","")} | tags={i.get("tags",[])}')

print()
print('=== Unstop items WITHOUT prize_pool (first 15) ===')
count = 0
for i in items:
    if i['source'] == 'Unstop' and not i.get('prize_pool'):
        print(f'  {i["title"][:60]:60s} | participants={i.get("participants","")}')
        count += 1
        if count >= 15: break

print()
print('=== Sample Unstop item to see full structure ===')
for i in items:
    if i['source'] == 'Unstop' and not i.get('prize_pool'):
        print(json.dumps(i, indent=2, ensure_ascii=False))
        break

print()
print('=== Sample Devfolio item without tags ===')
for i in items:
    if i['source'] == 'Devfolio' and not i.get('tags'):
        print(json.dumps(i, indent=2, ensure_ascii=False))
        break

print()
print('=== Sample Devpost item without deadline ===')
for i in items:
    if i['source'] == 'Devpost' and not i.get('deadline'):
        print(json.dumps(i, indent=2, ensure_ascii=False))
        break
