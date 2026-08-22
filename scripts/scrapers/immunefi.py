"""
Immunefi scraper.
Immunefi is a leading Web3 bug bounty platform.
The bounties page at immunefi.com/bounties lists active bug bounty programs.
"""

from __future__ import annotations

import logging

import httpx

from scripts.scrapers.base import ScrapeItem, parse_deadline, clean_text, deduplicate_by_link

logger = logging.getLogger(__name__)

IMMUNEFI_URL = "https://immunefi.com/bounties/"
IMMUNEFI_BASE = "https://immunefi.com"

USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36"
)


def scrape_immunefi() -> list[ScrapeItem]:
    """Scrape Immunefi bug bounty programs."""
    items: list[ScrapeItem] = []
    logger.info("Fetching Immunefi bounties: %s", IMMUNEFI_URL)

    try:
        resp = httpx.get(
            IMMUNEFI_URL,
            timeout=30,
            follow_redirects=True,
            headers={"User-Agent": USER_AGENT},
        )
    except Exception as e:
        logger.error("Immunefi request failed: %s", e)
        return items

    if resp.status_code != 200:
        logger.warning("Immunefi returned %d", resp.status_code)
        return items

    from scrapling import Selector
    page = Selector(resp.text, url=IMMUNEFI_URL)

    # Immunefi bounty cards
    cards = page.css(".bounty-card, .card, [class*='bounty'], article")
    seen_links = set()

    for card in cards:
        link_el = card.css("a[href*='/bounties/']")
        if not link_el:
            link_el = card.css("a")

        if not link_el:
            continue

        href = link_el[0].attrib.get("href", "")
        title_el = card.css("h2, h3, h4, .title, [class*='title'], .bounty-name")
        title = clean_text(title_el[0].text) if title_el else clean_text(link_el[0].text)

        if not title or len(title) < 3:
            continue

        full_url = href if href.startswith("http") else f"{IMMUNEFI_BASE}{href}"
        if full_url in seen_links:
            continue
        seen_links.add(full_url)

        # Try to find max bounty
        bounty_el = card.css("[class*='max'], [class*='bounty'], [class*='reward']")
        prize_pool = clean_text(bounty_el[0].text) if bounty_el else ""

        # Try to find protocol type
        type_el = card.css("[class*='type'], [class*='tag'], .badge")
        protocol_type = clean_text(type_el[0].text) if type_el else ""

        tags = ["bug bounty", "security", "web3", "blockchain", "immunefi"]
        if protocol_type:
            tags.append(protocol_type.lower())

        notes_parts = ["Source: Immunefi."]
        if protocol_type:
            notes_parts.append(f"Type: {protocol_type}.")

        item = ScrapeItem(
            title=f"[Immunefi] {title}",
            type="Competition",
            source="Immunefi",
            link=full_url,
            deadline="",
            eligibility="Security researchers (Web3 focus)",
            tags=tags,
            location="Online",
            prize_pool=prize_pool,
            notes=" ".join(notes_parts),
        )
        if not item.validate():
            items.append(item)

    # Fallback: parse bounty links
    if not items:
        links = page.css("a[href*='/bounties/']")
        for link_el in links:
            href = link_el.attrib.get("href", "")
            title = clean_text(link_el.text)
            if not title or len(title) < 3:
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
                notes="Source: Immunefi.",
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
        print(f"  {item.title[:60]} | {item.type} | {item.link[:50]}")
