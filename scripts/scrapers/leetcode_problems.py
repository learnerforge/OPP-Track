"""
LeetCode problems scraper.
LeetCode hosts coding problems and daily challenges via REST + GraphQL APIs.
"""

from __future__ import annotations

import logging

import httpx

from scripts.scrapers.base import ScrapeItem, clean_text, deduplicate_by_link

logger = logging.getLogger(__name__)

LEETCODE_GQL = "https://leetcode.com/graphql"
LEETCODE_PROBLEMS_API = "https://leetcode.com/api/problems/all/"

USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36"
)

HEADERS = {
    "User-Agent": USER_AGENT,
    "Content-Type": "application/json",
    "Referer": "https://leetcode.com/problemset/",
}

CHALLENGE_QUERY = """query { activeDailyCodingChallengeQuestion { date link question { title titleSlug difficulty topicTags { name } } } }"""

DIFFICULTY_MAP = {1: "Easy", 2: "Medium", 3: "Hard"}


def scrape_leetcode_problems() -> list[ScrapeItem]:
    """Scrape LeetCode problems and daily challenge."""
    items: list[ScrapeItem] = []
    logger.info("Fetching LeetCode problems")

    # 1. Daily challenge via GraphQL
    try:
        resp = httpx.post(
            LEETCODE_GQL,
            json={"query": CHALLENGE_QUERY},
            timeout=30,
            headers=HEADERS,
        )
        if resp.status_code == 200:
            data = resp.json()
            challenge = data.get("data", {}).get("activeDailyCodingChallengeQuestion", {})
            if challenge:
                question = challenge.get("question", {})
                title = question.get("title", "")
                slug = question.get("titleSlug", "")
                difficulty = question.get("difficulty", "")
                tags = [t["name"].lower() for t in question.get("topicTags", [])]
                date = challenge.get("date", "")

                if title:
                    item = ScrapeItem(
                        title=f"[LeetCode Daily] {title} ({difficulty})",
                        type="Competition",
                        source="LeetCode",
                        link=f"https://leetcode.com{challenge.get('link', '')}",
                        deadline=date,
                        eligibility="Global participants",
                        tags=["leetcode", "daily challenge", "algorithms"] + tags[:5],
                        location="Online",
                        notes=f"LeetCode Daily Coding Challenge. Difficulty: {difficulty}. Source: leetcode.com.",
                    )
                    if not item.validate():
                        items.append(item)
    except Exception as e:
        logger.error("LeetCode daily challenge request failed: %s", e)

    # 2. Problems via REST API (GraphQL problemsetQuestionList is unreliable)
    try:
        resp = httpx.get(
            LEETCODE_PROBLEMS_API,
            timeout=30,
            headers=HEADERS,
        )
        if resp.status_code == 200:
            data = resp.json()
            pairs = data.get("stat_status_pairs", [])
            seen = set()
            capped = 0
            for p in pairs:
                stat = p.get("stat", {})
                title = stat.get("question__title", "")
                slug = stat.get("question__title_slug", "")
                diff_level = p.get("difficulty", {}).get("level", 0)
                difficulty = DIFFICULTY_MAP.get(diff_level, "")
                if not title or slug in seen:
                    continue
                seen.add(slug)
                # Keep the problem set bounded and useful — the daily challenge
                # already covers the "current" problem, and every problem ever
                # is not useful opportunity data. Cap to the 100 most recent.
                if capped >= 100:
                    break
                capped += 1

                item = ScrapeItem(
                    title=f"[LeetCode] {title} ({difficulty})",
                    type="Competition",
                    source="LeetCode",
                    link=f"https://leetcode.com/problems/{slug}/",
                    deadline="",
                    eligibility="Global participants",
                    tags=["leetcode", "problems", "algorithms", difficulty.lower()] if difficulty else ["leetcode", "problems", "algorithms"],
                    location="Online",
                    notes=f"LeetCode problem. Difficulty: {difficulty}. Source: leetcode.com.",
                )
                if not item.validate():
                    items.append(item)
            logger.info("LeetCode REST API returned %d problems (%d unique)", len(pairs), len(seen))
        else:
            logger.warning("LeetCode REST API returned %d", resp.status_code)
    except Exception as e:
        logger.error("LeetCode problems request failed: %s", e)

    items = deduplicate_by_link(items)
    logger.info("LeetCode: scraped %d items", len(items))
    return items


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    results = scrape_leetcode_problems()
    print(f"LeetCode: {len(results)} items")
    for item in results[:10]:
        print(f"  {item.title[:60]} | {item.type} | {item.link[:50]}")
