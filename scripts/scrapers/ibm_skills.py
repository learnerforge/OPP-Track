"""
IBM Skills Network scraper.
IBM offers cloud and AI certifications through Skills Network.
"""

from __future__ import annotations

import logging

import httpx

from scripts.scrapers.base import ScrapeItem, parse_deadline, clean_text, deduplicate_by_link

logger = logging.getLogger(__name__)

IBM_SKILLS_URL = "https://skills.network/learning"
IBM_BASE = "https://skills.network"

USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36"
)


def scrape_ibm_skills() -> list[ScrapeItem]:
    """Scrape IBM Skills Network courses and certifications."""
    items: list[ScrapeItem] = []
    logger.info("Fetching IBM Skills Network: %s", IBM_SKILLS_URL)

    try:
        resp = httpx.get(
            IBM_SKILLS_URL,
            timeout=30,
            follow_redirects=True,
            headers={"User-Agent": USER_AGENT},
        )
    except Exception as e:
        logger.error("IBM Skills request failed: %s", e)
        return items

    if resp.status_code != 200:
        logger.warning("IBM Skills returned %d", resp.status_code)
        return items

    from scrapling import Selector
    page = Selector(resp.text, url=IBM_SKILLS_URL)

    # IBM course cards
    cards = page.css(".course-card, .card, [class*='course'], article, [class*='learning']")
    seen_links = set()

    for card in cards:
        link_el = card.css("a[href*='/courses/'], a[href*='/learning/']")
        if not link_el:
            link_el = card.css("a")

        if not link_el:
            continue

        href = link_el[0].attrib.get("href", "")
        title_el = card.css("h2, h3, h4, .title, [class*='title']")
        title = clean_text(title_el[0].text) if title_el else clean_text(link_el[0].text)

        if not title or len(title) < 5:
            continue

        full_url = href if href.startswith("http") else f"{IBM_BASE}{href}"
        if full_url in seen_links:
            continue
        seen_links.add(full_url)

        tags = ["ibm", "cloud", "certification", "ai"]
        card_text = clean_text(card.text).lower()
        if "free" in card_text:
            tags.append("free")
        if "data science" in card_text:
            tags.append("data science")
        if "ai" in card_text or "artificial intelligence" in card_text:
            tags.append("ai")
        if "cybersecurity" in card_text:
            tags.append("cybersecurity")

        item = ScrapeItem(
            title=title,
            type="Certification",
            source="IBM Skills",
            link=full_url,
            deadline="",
            eligibility="Global participants",
            tags=tags,
            location="Online",
            notes="Source: IBM Skills Network.",
        )
        if not item.validate():
            items.append(item)

    # Add known IBM certifications
    known_certs = [
        ("IBM Data Science Professional Certificate", "https://www.ibm.com/training/certification/DS0101EN"),
        ("IBM AI Engineering Professional Certificate", "https://www.ibm.com/training/certification/AI0101EN"),
        ("IBM Cybersecurity Analyst Professional Certificate", "https://www.ibm.com/training/certification/CY0101EN"),
        ("IBM Cloud Computing Professional Certificate", "https://www.ibm.com/training/certification/CL0101EN"),
        ("IBM Data Analyst Professional Certificate", "https://www.ibm.com/training/certification/DA0101EN"),
        ("IBM Applied AI Professional Certificate", "https://www.ibm.com/training/certification/AAI0101EN"),
        ("IBM Full Stack Cloud Developer Professional Certificate", "https://www.ibm.com/training/certification/FS0101EN"),
    ]

    for title, link in known_certs:
        if link not in [item.link for item in items]:
            item = ScrapeItem(
                title=title,
                type="Certification",
                source="IBM Skills",
                link=link,
                deadline="",
                eligibility="Global participants",
                tags=["ibm", "cloud", "certification", "professional certificate"],
                location="Online",
                notes="Source: IBM Skills Network.",
            )
            if not item.validate():
                items.append(item)

    items = deduplicate_by_link(items)
    logger.info("IBM Skills: scraped %d items", len(items))
    return items


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    results = scrape_ibm_skills()
    print(f"IBM Skills: {len(results)} items")
    for item in results[:10]:
        print(f"  {item.title[:60]} | {item.type} | {item.link[:50]}")
