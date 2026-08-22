"""
AWS Training and Certification scraper.
AWS offers cloud certifications and free training resources.
The training page at aws.amazon.com/training lists learning paths.
"""

from __future__ import annotations

import logging
import re

import httpx

from scripts.scrapers.base import ScrapeItem, parse_deadline, clean_text, deduplicate_by_link

logger = logging.getLogger(__name__)

AWS_TRAINING_URL = "https://aws.amazon.com/training/"
AWS_CERT_URL = "https://aws.amazon.com/certification/"
AWS_BASE = "https://aws.amazon.com"

USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36"
)


def scrape_aws_training() -> list[ScrapeItem]:
    """Scrape AWS training and certification programs."""
    items: list[ScrapeItem] = []
    logger.info("Fetching AWS Training: %s", AWS_TRAINING_URL)

    for url in [AWS_CERT_URL, AWS_TRAINING_URL]:
        try:
            resp = httpx.get(
                url,
                timeout=30,
                follow_redirects=True,
                headers={"User-Agent": USER_AGENT},
            )
        except Exception as e:
            logger.error("AWS request failed for %s: %s", url, e)
            continue

        if resp.status_code != 200:
            logger.warning("AWS returned %d for %s", resp.status_code, url)
            continue

        from scrapling import Selector
        page = Selector(resp.text, url=url)

        # AWS certification/training cards
        cards = page.css(".card, [class*='certification'], [class*='training'], article, [class*='path']")
        seen_links = set()

        for card in cards:
            link_el = card.css("a[href*='/training/'], a[href*='/certification/']")
            if not link_el:
                link_el = card.css("a")

            if not link_el:
                continue

            href = link_el[0].attrib.get("href", "")
            title_el = card.css("h2, h3, h4, .title, [class*='title']")
            title = clean_text(title_el[0].text) if title_el else clean_text(link_el[0].text)

            if not title or len(title) < 5:
                continue

            full_url = href if href.startswith("http") else f"{AWS_BASE}{href}"
            if full_url in seen_links:
                continue
            seen_links.add(full_url)

            tags = ["cloud", "aws", "certification"]
            card_text = clean_text(card.text).lower()
            if "free" in card_text:
                tags.append("free")
            if "training" in card_text:
                tags.append("training")

            item = ScrapeItem(
                title=title,
                type="Certification",
                source="AWS Training",
                link=full_url,
                deadline="",
                eligibility="Global participants",
                tags=tags,
                location="Online",
                notes="Source: AWS Training and Certification.",
            )
            if not item.validate():
                items.append(item)

    # Add known AWS certifications as static entries
    known_certs = [
        ("AWS Cloud Practitioner", "https://aws.amazon.com/certification/certified-cloud-practitioner/"),
        ("AWS Solutions Architect - Associate", "https://aws.amazon.com/certification/certified-solutions-architect-associate/"),
        ("AWS Developer - Associate", "https://aws.amazon.com/certification/certified-developer-associate/"),
        ("AWS SysOps Administrator - Associate", "https://aws.amazon.com/certification/certified-sysops-administrator-associate/"),
        ("AWS Solutions Architect - Professional", "https://aws.amazon.com/certification/certified-solutions-architect-professional/"),
        ("AWS DevOps Engineer - Professional", "https://aws.amazon.com/certification/certified-devops-engineer-professional/"),
        ("AWS Machine Learning - Specialty", "https://aws.amazon.com/certification/certified-machine-learning-specialty/"),
        ("AWS Data Analytics - Specialty", "https://aws.amazon.com/certification/certified-data-analytics-specialty/"),
        ("AWS Security - Specialty", "https://aws.amazon.com/certification/certified-security-specialty/"),
        ("AWS Database - Specialty", "https://aws.amazon.com/certification/certified-database-specialty/"),
    ]

    for title, link in known_certs:
        if link not in [item.link for item in items]:
            item = ScrapeItem(
                title=title,
                type="Certification",
                source="AWS Training",
                link=link,
                deadline="",
                eligibility="Global participants",
                tags=["cloud", "aws", "certification"],
                location="Online",
                notes="Source: AWS Training and Certification.",
            )
            if not item.validate():
                items.append(item)

    items = deduplicate_by_link(items)
    logger.info("AWS Training: scraped %d items", len(items))
    return items


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    results = scrape_aws_training()
    print(f"AWS Training: {len(results)} items")
    for item in results[:10]:
        print(f"  {item.title[:60]} | {item.type} | {item.link[:50]}")
