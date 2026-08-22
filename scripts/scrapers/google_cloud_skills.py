"""
Google Cloud Certification scraper.
Google Cloud offers various cloud certifications and training resources.
The certification page at cloud.google.com/certification lists available certs.
"""

from __future__ import annotations

import logging

import httpx

from scripts.scrapers.base import ScrapeItem, parse_deadline, clean_text, deduplicate_by_link

logger = logging.getLogger(__name__)

GCP_CERT_URL = "https://cloud.google.com/certification"
GCP_BASE = "https://cloud.google.com"

USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36"
)


def scrape_google_cloud_skills() -> list[ScrapeItem]:
    """Scrape Google Cloud certifications."""
    items: list[ScrapeItem] = []
    logger.info("Fetching Google Cloud Certification: %s", GCP_CERT_URL)

    try:
        resp = httpx.get(
            GCP_CERT_URL,
            timeout=30,
            follow_redirects=True,
            headers={"User-Agent": USER_AGENT},
        )
    except Exception as e:
        logger.error("Google Cloud request failed: %s", e)
        return items

    if resp.status_code != 200:
        logger.warning("Google Cloud returned %d", resp.status_code)
        return items

    from scrapling import Selector
    page = Selector(resp.text, url=GCP_CERT_URL)

    # Google Cloud certification cards
    cards = page.css(".card, [class*='certification'], article, [class*='cert']")
    seen_links = set()

    for card in cards:
        link_el = card.css("a[href*='/certification/']")
        if not link_el:
            link_el = card.css("a")

        if not link_el:
            continue

        href = link_el[0].attrib.get("href", "")
        title_el = card.css("h2, h3, h4, .title, [class*='title']")
        title = clean_text(title_el[0].text) if title_el else clean_text(link_el[0].text)

        if not title or len(title) < 5:
            continue

        full_url = href if href.startswith("http") else f"{GCP_BASE}{href}"
        if full_url in seen_links:
            continue
        seen_links.add(full_url)

        tags = ["google cloud", "cloud", "certification"]
        card_text = clean_text(card.text).lower()
        if "data" in card_text:
            tags.append("data")
        if "machine learning" in card_text or "ml" in card_text:
            tags.append("machine learning")
        if "security" in card_text:
            tags.append("security")
        if "devops" in card_text:
            tags.append("devops")

        item = ScrapeItem(
            title=title,
            type="Certification",
            source="Google Cloud",
            link=full_url,
            deadline="",
            eligibility="Global participants",
            tags=tags,
            location="Online",
            notes="Source: Google Cloud Certification.",
        )
        if not item.validate():
            items.append(item)

    # Add known Google Cloud certifications
    known_certs = [
        ("Google Cloud Digital Leader", "https://cloud.google.com/certification/cloud-digital-leader"),
        ("Google Cloud Associate Cloud Engineer", "https://cloud.google.com/certification/cloud-engineer"),
        ("Google Cloud Professional Cloud Architect", "https://cloud.google.com/certification/cloud-architect"),
        ("Google Cloud Professional Data Engineer", "https://cloud.google.com/certification/data-engineer"),
        ("Google Cloud Professional Machine Learning Engineer", "https://cloud.google.com/certification/machine-learning-engineer"),
        ("Google Cloud Professional Cloud Security Engineer", "https://cloud.google.com/certification/security-engineer"),
        ("Google Cloud Professional Cloud DevOps Engineer", "https://cloud.google.com/certification/devops-engineer"),
        ("Google Cloud Professional Cloud Developer", "https://cloud.google.com/certification/cloud-developer"),
        ("Google Cloud Professional Network Engineer", "https://cloud.google.com/certification/network-engineer"),
        ("Google Cloud Professional Collaboration Engineer", "https://cloud.google.com/certification/collaboration-engineer"),
    ]

    for title, link in known_certs:
        if link not in [item.link for item in items]:
            item = ScrapeItem(
                title=title,
                type="Certification",
                source="Google Cloud",
                link=link,
                deadline="",
                eligibility="Global participants",
                tags=["google cloud", "cloud", "certification"],
                location="Online",
                notes="Source: Google Cloud Certification.",
            )
            if not item.validate():
                items.append(item)

    items = deduplicate_by_link(items)
    logger.info("Google Cloud: scraped %d certifications", len(items))
    return items


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    results = scrape_google_cloud_skills()
    print(f"Google Cloud: {len(results)} items")
    for item in results[:10]:
        print(f"  {item.title[:60]} | {item.type} | {item.link[:50]}")
