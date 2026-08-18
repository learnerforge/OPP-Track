"""Quick test to inspect Devfolio page structure."""
import sys
sys.path.insert(0, r'E:\GitHub Projects\OPP-Track')
from scrapling.fetchers import Fetcher

page = Fetcher.get('https://devfolio.co/hackathons/open', impersonate='chrome')

print(f"Page status: {page.status}")
print(f"Page title: {page.css('title::text').get()}")
print()

# Look at all links that end with .devfolio.co
links = page.css('a[href$=".devfolio.co"]')
print(f"Found {len(links)} devfolio.co links")
for link in links[:30]:
    href = link.attrib.get('href', '')
    text = (link.text or '').strip()[:100]
    print(f"  href={href}")
    print(f"    text={text}")
print()

# Look at headings
for h in page.css('h1::text').getall()[:5]:
    print(f"H1: {h.strip()}")
for h in page.css('h2::text').getall()[:10]:
    print(f"H2: {h.strip()}")
for h in page.css('h3::text').getall()[:10]:
    print(f"H3: {h.strip()}")

print()
print("--- All text containing 'hackathon' ---")
for el in page.find_all(lambda e: e.text and 'hackathon' in e.text.lower()):
    tag = el.tag if hasattr(el, 'tag') else 'unknown'
    text = el.text.strip()[:120]
    print(f"  <{tag}>: {text}")
