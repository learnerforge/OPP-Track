"""
Turing scraper.
Turing.com connects remote developers with top US companies.
The /jobs page is JS-rendered and does not expose individual job listings.
We parse the sitemap for /jobs/<slug> individual job role pages, then extract
role data from the __NEXT_DATA__ embedded JSON.
"""

from __future__ import annotations

import json
import logging
import re

import httpx

from scripts.scrapers.base import ScrapeItem, clean_text, deduplicate_by_link

logger = logging.getLogger(__name__)

TURING_SITEMAP = "https://www.turing.com/sitemap.xml"

USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36"
)

HEADERS = {"User-Agent": USER_AGENT}


def _get_job_urls(limit: int = 50) -> list[str]:
    """Parse Turing sitemap for /jobs/<slug> URLs."""
    try:
        resp = httpx.get(TURING_SITEMAP, timeout=20, follow_redirects=True, headers=HEADERS)
        if resp.status_code != 200:
            logger.warning("Turing sitemap returned %d", resp.status_code)
            return []
        urls = re.findall(r"<loc>(.*?)</loc>", resp.text)
        job_urls = [
            u for u in urls
            if re.match(r"https://www\.turing\.com/jobs/[a-z0-9-]+$", u)
        ]
        logger.info("Turing sitemap: %d job URLs, using %d", len(job_urls), min(limit, len(job_urls)))
        return job_urls[:limit]
    except Exception as e:
        logger.error("Turing sitemap fetch failed: %s", e)
        return []


def _extract_job_data(html: str) -> dict | None:
    """Extract job role data from __NEXT_DATA__."""
    nd_match = re.search(r'<script id="__NEXT_DATA__"[^>]*>(.*?)</script>', html)
    if not nd_match:
        return None
    try:
        nd = json.loads(nd_match.group(1))
        page = nd.get("props", {}).get("pageProps", {}).get("page", {})
        return page.get("data", {})
    except (json.JSONDecodeError, KeyError):
        return None


def scrape_turing() -> list[ScrapeItem]:
    """Scrape Turing remote developer job roles from sitemap + individual pages."""
    items: list[ScrapeItem] = []
    logger.info("Fetching Turing job URLs from sitemap")

    job_urls = _get_job_urls(limit=50)
    if not job_urls:
        logger.warning("No Turing job URLs from sitemap")
        return items

    for url in job_urls:
        try:
            resp = httpx.get(url, timeout=20, follow_redirects=True, headers=HEADERS)
            if resp.status_code != 200:
                continue

            data = _extract_job_data(resp.text)
            if not data:
                continue

            name = clean_text(data.get("name", ""))
            j_title = clean_text(data.get("j_title", ""))
            meta_title = clean_text(data.get("meta_title", ""))
            j_skills = clean_text(data.get("j_required_skills", ""))
            j_experience = data.get("j_experience_months", 0)
            meta_desc = clean_text(data.get("meta_description", ""))

            title = j_title or meta_title or name
            if not title:
                # Fallback: derive from slug
                slug = url.rstrip("/").split("/")[-1]
                title = slug.replace("-", " ").title()

            notes_parts = ["Remote developer role. Source: turing.com."]
            if j_skills:
                notes_parts.append(f"Skills: {j_skills}.")
            if j_experience:
                notes_parts.append(f"Experience: ~{j_experience} months.")
            if meta_desc:
                notes_parts.append(meta_desc[:150])

            tags = ["remote", "developer", "turing", "full-time"]
            title_lower = title.lower()
            for skill in ["python", "react", "java", "node", "flutter", "devops", "data", "angular", "php", "ruby", "typescript", "kubernetes", "docker", "aws", "gcp"]:
                if skill in title_lower:
                    tags.append(skill)

            item = ScrapeItem(
                title=f"[Turing] {title}",
                type="Internship",
                source="Turing",
                link=url,
                deadline="",
                eligibility="Remote developers worldwide",
                tags=tags,
                location="Remote",
                organizer="Turing",
                notes=" ".join(notes_parts),
            )
            if not item.validate():
                items.append(item)
        except Exception as e:
            logger.debug("Turing job page fetch failed for %s: %s", url, e)

    items = deduplicate_by_link(items)
    logger.info("Turing: scraped %d items", len(items))
    return items


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    results = scrape_turing()
    print(f"Turing: {len(results)} items")
    for item in results[:10]:
        print(f"  {item.title[:60]} | {item.type} | {item.link[:60]}")
