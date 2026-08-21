"""
Coursera scraper.
The requested /courseraplus/specializations path 404s, so this falls back to
the live Coursera Plus landing page and the course catalog browse page. Both
embed a normalized Apollo cache in `window.__APOLLO_STATE__` containing
ProductCard and Specialization entities — mapped as type="Certification".
"""

from __future__ import annotations

import json
import logging

import httpx

from scripts.scrapers.base import ScrapeItem

logger = logging.getLogger(__name__)

COURSERA_URLS = [
    "https://www.coursera.org/courseraplus/specializations",  # per spec (may 404)
    "https://www.coursera.org/courseraplus",
    "https://www.coursera.org/browse",
]

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36"
    ),
}

APOLLO_MARKER = "window.__APOLLO_STATE__ = "

PRODUCT_TYPE_LABELS = {
    "SPECIALIZATION": "Specialization",
    "PROFESSIONAL_CERTIFICATE": "Professional Certificate",
    "COURSE": "Course",
    "GUIDED_PROJECT": "Guided Project",
    "DEGREE": "Degree",
}


def _extract_apollo_state(html: str) -> dict | None:
    """Extract window.__APOLLO_STATE__ JSON via brace balancing (no regex fragility)."""
    idx = html.find(APOLLO_MARKER)
    if idx == -1:
        return None
    start = html.find("{", idx)
    if start == -1:
        return None

    depth = 0
    in_str = False
    escaped = False
    for pos in range(start, len(html)):
        ch = html[pos]
        if in_str:
            if escaped:
                escaped = False
            elif ch == "\\":
                escaped = True
            elif ch == '"':
                in_str = False
        else:
            if ch == '"':
                in_str = True
            elif ch == "{":
                depth += 1
            elif ch == "}":
                depth -= 1
                if depth == 0:
                    try:
                        return json.loads(html[start:pos + 1])
                    except json.JSONDecodeError as e:
                        logger.debug(f"  Apollo state JSON parse error: {e}")
                        return None
    return None


def _resolve_ref(state: dict, ref: dict) -> dict:
    """Resolve an Apollo {'__ref': 'Type:id'} pointer to its entity."""
    if not isinstance(ref, dict):
        return {}
    return state.get(ref.get("__ref", "")) or {}


def _format_duration(months) -> str:
    """Convert monthsToCompleteOverride into a human-readable duration."""
    if isinstance(months, (int, float)) and months > 0:
        months = int(months)
        return f"{months} Month" if months == 1 else f"{months} Months"
    return ""


def _map_product(card: dict, entity: dict, state: dict) -> ScrapeItem | None:
    """Map a Coursera ProductCard + canonical entity to a ScrapeItem."""
    title = (entity.get("name") or card.get("name") or "").strip()
    url_path = (entity.get("urlPath") or card.get("urlPath") or "").strip()
    if not title or not url_path:
        return None

    product_type = PRODUCT_TYPE_LABELS.get(
        card.get("marketingProductType", ""), card.get("marketingProductType", "")
    )

    # Partner/instructor organizations
    partners = []
    for ref in entity.get("partners") or []:
        partner = _resolve_ref(state, ref)
        name = (partner.get("name") or "").strip()
        if name:
            partners.append(name)

    attrs = card.get("productTypeAttributes") or {}
    rating = attrs.get("rating")
    review_count = attrs.get("reviewCount")
    course_count = entity.get("courseCount")

    notes_parts = []
    if product_type:
        notes_parts.append(product_type)
    if course_count:
        notes_parts.append(f"{course_count}-course series")
    if isinstance(rating, (int, float)) and rating > 0:
        notes_parts.append(f"Rating: {rating:.1f}")
    if isinstance(review_count, int) and review_count > 0:
        notes_parts.append(f"{review_count:,} reviews")
    notes_parts.append("Source: Coursera")

    tags = ["online learning", "certification"]
    if product_type and product_type.lower() not in ("course",):
        tags.append(product_type.lower().replace(" ", "-"))

    return ScrapeItem(
        title=title,
        type="Certification",
        source="Coursera",
        link=f"https://www.coursera.org{url_path}",
        deadline="",
        eligibility="Open to all",
        tags=tags,
        location="Online",
        organizer=", ".join(partners[:2]),
        duration=_format_duration(entity.get("monthsToCompleteOverride")),
        notes=". ".join(notes_parts),
    )


def scrape_coursera() -> list[ScrapeItem]:
    """Scrape Coursera specializations/courses from embedded Apollo state JSON."""
    items: list[ScrapeItem] = []

    for url in COURSERA_URLS:
        logger.info(f"Fetching Coursera: {url}")
        try:
            resp = httpx.get(url, timeout=30, follow_redirects=True, headers=HEADERS)
        except Exception as e:
            logger.error(f"Error fetching Coursera {url}: {e}")
            continue

        if resp.status_code != 200:
            logger.warning(f"Coursera returned status {resp.status_code} for {url}")
            continue

        state = _extract_apollo_state(resp.text)
        if not state:
            logger.warning(f"Coursera: could not extract __APOLLO_STATE__ from {url}")
            continue

        cards = {
            k: v for k, v in state.items()
            if k.startswith("ProductCard_ProductCard:") and isinstance(v, dict)
        }
        logger.info(f"Coursera: found {len(cards)} product cards on {url}")

        seen_paths: set[str] = set()
        for key, card in cards.items():
            entity = _resolve_ref(state, (card.get("productTypeAttributes") or {}).get("canonical") or {})
            if not entity:
                # Some cards embed the entity fields directly
                entity = card
            item = _map_product(card, entity, state)
            if not item:
                continue
            path_key = item.link.rstrip("/").lower()
            if path_key in seen_paths:
                continue
            errors = item.validate()
            if errors:
                logger.debug(f"  Skipping invalid item {item.title}: {errors}")
                continue
            seen_paths.add(path_key)
            items.append(item)
            logger.info(f"  Found: {item.title} | {item.organizer} | {item.duration}")

        if items:
            break  # first responsive URL is enough

    logger.info(f"Coursera: scraped {len(items)} certifications")
    return items


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    results = scrape_coursera()
    for item in results:
        print(f"  {item.title} | {item.organizer} | {item.duration} | {item.link}")
