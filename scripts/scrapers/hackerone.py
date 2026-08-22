"""
HackerOne scraper.
HackerOne has a public GraphQL endpoint for hacktivity data.
The hacktivity page at hackerone.com/hacktivity/overview shows disclosed reports.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone

import httpx

from scripts.scrapers.base import ScrapeItem, parse_deadline, clean_text, deduplicate_by_link

logger = logging.getLogger(__name__)

HACKERONE_HACKTIVITY_URL = "https://hackerone.com/hacktivity/overview"
HACKERONE_BASE = "https://hackerone.com"

USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36"
)

HACKTIVITY_QUERY = """
query HacktivityQuery($after: String) {
  hacktivity_items(
    first: 25
    after: $after
    orderBy: LATEST_DISCLOSABLE_ACTIVITY_AT
    where: { report: { disclosed_at: { _is_null: false } } }
  ) {
    totalCount
    pageInfo {
      hasNextPage
      endCursor
    }
    edges {
      node {
        ... on HackerPublished {
          report {
            _id
            title
            disclosed_at
            severity {
              rating
            }
            bounties {
              total_awarded_amount
            }
          }
          team {
            handle
            name
          }
        }
        ... on Disclosed {
          report {
            _id
            title
            disclosed_at
            severity {
              rating
            }
            bounties {
              total_awarded_amount
            }
          }
          team {
            handle
            name
          }
        }
      }
    }
  }
}
"""


def scrape_hackerone() -> list[ScrapeItem]:
    """Scrape HackerOne hacktivity via GraphQL."""
    items: list[ScrapeItem] = []
    logger.info("Fetching HackerOne hacktivity")

    try:
        resp = httpx.post(
            f"{HACKERONE_BASE}/graphql",
            json={
                "query": HACKTIVITY_QUERY,
                "variables": {"after": None},
            },
            timeout=30,
            follow_redirects=True,
            headers={
                "User-Agent": USER_AGENT,
                "Content-Type": "application/json",
                "Accept": "application/json",
            },
        )
    except Exception as e:
        logger.error("HackerOne GraphQL request failed: %s", e)
        return items

    if resp.status_code != 200:
        logger.warning("HackerOne GraphQL returned %d", resp.status_code)
        return items

    try:
        data = resp.json()
    except Exception:
        logger.warning("HackerOne returned non-JSON")
        return items

    hacktivity = data.get("data", {}).get("hacktivity_items", {})
    edges = hacktivity.get("edges", [])

    for edge in edges:
        node = edge.get("node", {})

        # Get report info from either HackerPublished or Disclosed
        report = node.get("report", {})
        team = node.get("team", {})

        if not report:
            continue

        title = report.get("title", "").strip()
        if not title:
            continue

        report_id = report.get("_id", "")
        disclosed_at = report.get("disclosed_at", "")
        severity = report.get("severity", {}).get("rating", "")
        bounties = report.get("bounties", [])
        total_bounty = sum(b.get("total_awarded_amount", 0) for b in bounties if b) if bounties else 0

        team_handle = team.get("handle", "")
        team_name = team.get("name", team_handle)

        report_url = f"{HACKERONE_BASE}/reports/{report_id}" if report_id else ""

        deadline = ""
        if disclosed_at:
            try:
                dt = datetime.fromisoformat(disclosed_at.replace("Z", "+00:00"))
                deadline = dt.strftime("%Y-%m-%d")
            except (ValueError, TypeError):
                pass

        tags = ["bug bounty", "security", "hackerone"]
        if severity:
            tags.append(severity.lower())

        prize_pool = f"${total_bounty:,}" if total_bounty else ""

        notes_parts = ["Source: HackerOne Hacktivity."]
        if team_name:
            notes_parts.append(f"Program: {team_name}.")
        if severity:
            notes_parts.append(f"Severity: {severity}.")

        item = ScrapeItem(
            title=f"[HackerOne] {title}",
            type="Competition",
            source="HackerOne",
            link=report_url,
            deadline=deadline,
            eligibility="Security researchers",
            tags=tags,
            location="Online",
            prize_pool=prize_pool,
            notes=" ".join(notes_parts),
        )
        if not item.validate():
            items.append(item)

    items = deduplicate_by_link(items)
    logger.info("HackerOne: scraped %d reports", len(items))
    return items


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    results = scrape_hackerone()
    print(f"HackerOne: {len(results)} items")
    for item in results[:10]:
        print(f"  {item.title[:60]} | {item.type} | {item.deadline} | {item.link[:50]}")
