"""
Console.dev scraper.
Console.dev is a developer-tools newsletter. Its /jobs page was removed (404).
The homepage features developer tools and beta releases. This scraper extracts
those featured tools as Certification items since they represent developer
tooling knowledge/skills relevant to the OPP-Track audience.
"""

from __future__ import annotations

import logging
import re

import httpx

from scripts.scrapers.base import ScrapeItem, clean_text, deduplicate_by_link

logger = logging.getLogger(__name__)

CONSOLE_URL = "https://console.dev"
CONSOLE_BASE = "https://console.dev"

USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36"
)


def scrape_console_dev() -> list[ScrapeItem]:
    """Scrape developer tools featured on console.dev homepage.

    The /jobs page no longer exists (404). The homepage features curated
    developer tools with reviews and beta releases. We extract those as
    Certification-type items for developer tooling awareness.
    """
    items: list[ScrapeItem] = []
    logger.info("Fetching Console.dev: %s", CONSOLE_URL)

    try:
        resp = httpx.get(
            CONSOLE_URL,
            timeout=30,
            follow_redirects=True,
            headers={"User-Agent": USER_AGENT},
        )
    except Exception as e:
        logger.error("Console.dev request failed: %s", e)
        return items

    if resp.status_code != 200:
        logger.warning("Console.dev returned %d", resp.status_code)
        return items

    from scrapling import Selector
    page = Selector(resp.text, url=CONSOLE_URL)

    # --- Section 1: "Interesting tools" (reviewed tools) ---
    # These are in <article> blocks under the "Interesting tools" section
    articles = page.css("article")
    for article in articles:
        name_el = article.css("h3 a")
        if not name_el:
            continue
        name = clean_text(name_el[0].text)
        href = name_el[0].attrib.get("href", "")
        if not name or not href:
            continue

        desc_el = article.css("p.text-sm")
        description = clean_text(desc_el[0].text) if desc_el else ""

        # Extract category from icon附近的 text
        category = "Developer Tools"
        cat_el = article.css("span.uppercase")
        if cat_el:
            category = clean_text(cat_el[0].text)

        full_url = href if href.startswith("http") else f"{CONSOLE_BASE}{href}"

        item = ScrapeItem(
            title=f"[Console.dev] {name}",
            type="Certification",
            source="Console.dev",
            link=full_url,
            deadline="",
            eligibility="Developers worldwide",
            tags=["developer tools", "software", category.lower().replace(" ", "_"), "newsletter"],
            location="Online",
            notes=f"Featured devtool: {description}" if description else "Featured developer tool on console.dev newsletter.",
        )
        if not item.validate():
            items.append(item)

    # --- Section 2: "Betas and previews" (new tools in beta) ---
    beta_section = page.css("section")
    for section in beta_section:
        header_el = section.css("h2")
        if not header_el:
            continue
        header_text = clean_text(header_el[0].text).lower()
        if "beta" not in header_text:
            continue

        beta_items = section.css("li")
        for li in beta_items:
            name_el = li.css("h3 a")
            if not name_el:
                continue
            name = clean_text(name_el[0].text)
            href = name_el[0].attrib.get("href", "")
            if not name or not href:
                continue

            desc_el = li.css("p.text-sm")
            description = clean_text(desc_el[0].text) if desc_el else ""

            category = "Developer Tools"
            cat_el = li.css("span.uppercase")
            if cat_el:
                category = clean_text(cat_el[0].text)

            full_url = href if href.startswith("http") else f"{CONSOLE_BASE}{href}"

            item = ScrapeItem(
                title=f"[Console.dev Beta] {name}",
                type="Certification",
                source="Console.dev",
                link=full_url,
                deadline="",
                eligibility="Developers worldwide",
                tags=["developer tools", "beta", "software", category.lower().replace(" ", "_"), "newsletter"],
                location="Online",
                notes=f"Beta/preview: {description}" if description else "Beta developer tool featured on console.dev.",
            )
            if not item.validate():
                items.append(item)

    items = deduplicate_by_link(items)
    logger.info("Console.dev: scraped %d items", len(items))
    return items


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    results = scrape_console_dev()
    print(f"Console.dev: {len(results)} items")
    for item in results[:5]:
        print(f"  {item.title[:60]} | {item.type} | {item.link[:50]}")
