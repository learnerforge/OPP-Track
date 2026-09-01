"""
SIGNATE scraper.
Scrapes Japanese data science competitions from SIGNATE.
The /competitions page is a marketing landing page; the real competition
list is at user.competition.signate.jp/ja/competition/list/. Cards use
hashed Material-UI classes, so parsing is done on the raw HTML with regex.
Titles/notes are Japanese — that's fine.
"""

from __future__ import annotations

import logging
import re
from urllib.parse import urljoin

from scrapling.fetchers import StealthyFetcher

from scripts.scrapers.base import ScrapeItem, clean_text, deduplicate_by_link

logger = logging.getLogger(__name__)

SIGNATE_URL = "https://user.competition.signate.jp/ja/competition/list/"
SIGNATE_BASE = "https://user.competition.signate.jp"

FETCH_ARGS = {
    "headless": True,
    "disable_resources": True,
    "network_idle": True,
    "timeout": 45000,
}

# Card anchor regex — each competition card is: <a ... href=".../competition/detail/?competition=ID">
CARD_RE = re.compile(
    r'<a[^>]*href="([^"]*competition/detail/\?competition=[^"]+)"[^>]*>(.*?)</a>',
    re.DOTALL,
)
# Title lives in: <div class="MuiBox-root mui-w74nth">TITLE</div>
TITLE_RE = re.compile(r'class="MuiBox-root mui-w74nth"[^>]*>([^<]*)')
# Prize + status near the card footer (e.g. "1500万円" and "開催中")
CONTENT_RE = re.compile(r'<[^>]+>')
SKIP_TITLES = {"competition title"}


def scrape_signate() -> list[ScrapeItem]:
    """Scrape SIGNATE competitions."""
    items: list[ScrapeItem] = []
    logger.info("Fetching SIGNATE competitions: %s", SIGNATE_URL)

    try:
        page = StealthyFetcher.fetch(SIGNATE_URL, **FETCH_ARGS)
    except Exception as e:
        logger.error("SIGNATE fetch failed: %s", e)
        return items

    if page.status != 200:
        logger.warning("SIGNATE returned %d", page.status)
        return items

    body = page.body.decode("utf-8", "replace")
    seen_links = set()

    for match in CARD_RE.finditer(body):
        href, inner = match.groups()
        # Skip the featured/first banner cards that have no title div — require a title
        title_match = TITLE_RE.search(inner)
        if not title_match:
            continue
        title = clean_text(title_match.group(1))
        if not title or len(title) < 3 or title.lower() in SKIP_TITLES:
            continue

        full_url = href if href.startswith("http") else urljoin(SIGNATE_BASE, href)
        if full_url in seen_links:
            continue
        seen_links.add(full_url)

        # Prize: look for amounts ending in 万円/円/ドル within the card content
        inner_text = clean_text(CONTENT_RE.sub(" ", inner))
        prize_pool = ""
        prize_m = re.search(r'([\d,]+(?:\.\d+)?円|[\d,]+(?:\.\d+)?万円|US\$[\d,]+)', inner_text)
        if prize_m:
            prize_pool = prize_m.group(1)

        # Status: 開催中 (ongoing) => no deadline
        status = ""
        if "開催中" in inner_text:
            status = "開催中"

        tags = ["data science", "machine learning", "japan"]
        notes_parts = ["Source: SIGNATE."]
        if status:
            notes_parts.append(f"Status: {status}.")

        item = ScrapeItem(
            title=title,
            type="Competition",
            source="SIGNATE",
            link=full_url,
            deadline="",
            eligibility="Global participants",
            tags=tags,
            location="Online",
            prize_pool=prize_pool,
            notes=" ".join(notes_parts),
        )
        if not item.validate():
            items.append(item)

    items = deduplicate_by_link(items)
    logger.info("SIGNATE: scraped %d competitions", len(items))
    return items


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    results = scrape_signate()
    print(f"SIGNATE: {len(results)} items")
    for item in results[:10]:
        print(f"  {item.title} | {item.deadline} | {item.prize_pool} | {item.link}")
