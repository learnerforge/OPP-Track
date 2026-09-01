"""
Immunefi scraper.
Scrapes Web3 bug bounty programs from immunefi.com/bug-bounty/.
Each program card links to /bug-bounty/{protocol}/information/ with the
protocol name as its text. Programs are always-open bug bounties.
"""

from __future__ import annotations

import logging

from scrapling.fetchers import StealthyFetcher

from scripts.scrapers.base import ScrapeItem, clean_text, deduplicate_by_link

logger = logging.getLogger(__name__)

IMMUNEFI_URL = "https://immunefi.com/bug-bounty/"
IMMUNEFI_BASE = "https://immunefi.com"

FETCH_ARGS = {
    "headless": True,
    "disable_resources": True,
    "network_idle": True,
    "timeout": 45000,
}

# Navigation labels that are not actual protocols
SKIP_TITLES = {"explore bounties", "bounties", "bug bounty program", "view bounty"}


def scrape_immunefi() -> list[ScrapeItem]:
    """Scrape Immunefi Web3 bug bounty programs."""
    items: list[ScrapeItem] = []
    logger.info("Fetching Immunefi bug bounties: %s", IMMUNEFI_URL)

    try:
        page = StealthyFetcher.fetch(IMMUNEFI_URL, **FETCH_ARGS)
    except Exception as e:
        logger.error("Immunefi fetch failed: %s", e)
        return items

    if page.status != 200:
        logger.warning("Immunefi returned %d", page.status)
        return items

    links = page.css("a[href*='/bug-bounty/']")
    seen_links = set()

    for link_el in links:
        href = link_el.attrib.get("href", "")
        # Only direct detail pages: /bug-bounty/{protocol}/information/
        if not href.endswith("/information/") or "/bug-bounty//" in href:
            continue

        title = clean_text(link_el.get_all_text())
        if not title or len(title) < 2 or title.lower() in SKIP_TITLES:
            continue
        # Collapse newlines and drop trailing metadata like "Triaged by Immunefi"
        title = " ".join(title.split())
        for suffix in ("Triaged by Immunefi", "Triaged by "):
            if suffix.lower() in title.lower():
                idx = title.lower().find(suffix.lower())
                title = title[:idx].strip()
                break
        if not title:
            continue

        full_url = href if href.startswith("http") else f"{IMMUNEFI_BASE}{href}"
        if full_url in seen_links:
            continue
        seen_links.add(full_url)

        item = ScrapeItem(
            title=f"[Immunefi] {title}",
            type="Competition",
            source="Immunefi",
            link=full_url,
            deadline="",
            eligibility="Security researchers (Web3 focus)",
            tags=["bug bounty", "security", "web3", "blockchain", "immunefi"],
            location="Online",
            notes="Source: Immunefi. Always-open Web3 bug bounty program.",
        )
        if not item.validate():
            items.append(item)

    items = deduplicate_by_link(items)
    logger.info("Immunefi: scraped %d bounties", len(items))
    return items


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    results = scrape_immunefi()
    print(f"Immunefi: {len(results)} items")
    for item in results[:10]:
        print(f"  {item.title} | {item.link}")
