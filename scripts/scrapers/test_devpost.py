"""
Test script to dump the DOM structure of Devpost hackathon cards.
Uses Scrapling's StealthyFetcher to render the page and inspect the HTML.
"""

from __future__ import annotations

import sys
import io
import logging
from scrapling.fetchers import StealthyFetcher

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

URL = "https://devpost.com/hackathons?status[]=upcoming"


def css1(parent, selector: str):
    """Return the first matching element or None."""
    results = parent.css(selector)
    return results[0] if results else None


def main() -> None:
    logger.info(f"Fetching {URL} ...")
    try:
        page = StealthyFetcher.fetch(
            URL,
            headless=True,
            disable_resources=False,
            network_idle=True,
            timeout=60000,
        )
    except Exception as e:
        logger.error(f"Fetch failed: {e}")
        sys.exit(1)

    print(f"\n{'=' * 80}")
    print(f"HTTP status: {page.status}")
    title_el = css1(page, "title")
    print(f"Page title:  {title_el.text if title_el else '(none)'}")
    print(f"{'=' * 80}\n")

    # --- Top-level page structure -------------------------------------------------
    print("=" * 80)
    print("TOP-LEVEL PAGE STRUCTURE")
    print("=" * 80)
    body = css1(page, "body")
    if body:
        children = body.css(":scope > *")
        for i, child in enumerate(children[:30]):
            tag = child.tag
            cls = child.attrib.get("class", "")
            id_ = child.attrib.get("id", "")
            child_count = len(child.css("*"))
            print(f"  [{i}] <{tag}> class=\"{cls}\" id=\"{id_}\"  ({child_count} descendants)")
    print()

    # --- Try various selectors that Devpost cards might use -----------------------
    selectors_to_try = [
        ".hackathon-tile",
        "[class*='hackathon']",
        ".directory-listing .small-12",
        ".small-12.columns",
        "[data-role='hackathon-tile']",
        ".hackathon-container",
        ".card",
        ".tile",
        "li.hackathon",
        ".list_content .item",
        ".browse-listings .column",
        ".content-column",
        "section.section",
        ".row .column",
    ]

    cards = []
    used_selector = ""
    for sel in selectors_to_try:
        try:
            found = page.css(sel)
        except Exception:
            found = []
        if found:
            print(f"Selector '{sel}' matched {len(found)} elements")
            if len(found) > 2 and not cards:
                cards = found
                used_selector = sel

    print()

    # --- Broader search: anything that looks like a card --------------------------
    if not cards:
        print("No known selector matched. Searching for common patterns...\n")
        # Look for repeated sibling elements with links to /hackathons/
        all_links = page.css('a[href*="/hackathons/"]')
        print(f"Found {len(all_links)} links to /hackathons/*")
        for lnk in all_links[:10]:
            href = lnk.attrib.get("href", "")
            txt = (lnk.text or "")[:80]
            parent_tag = lnk.parent.tag if lnk.parent else "?"
            parent_cls = lnk.parent.attrib.get("class", "") if lnk.parent else ""
            print(f"  <a href=\"{href}\"> {txt!r}  (parent: <{parent_tag}> class=\"{parent_cls}\")")
        print()

    # --- Dump first 3 cards in detail ---------------------------------------------
    if cards:
        print(f"Using selector: {used_selector}")
        print("=" * 80)
        print(f"DETAILED CARD DUMP (first 3 of {len(cards)})")
        print("=" * 80)
        for idx, card in enumerate(cards[:3]):
            print(f"\n{'-' * 80}")
            print(f"CARD {idx + 1}")
            print(f"{'-' * 80}")
            tag = card.tag
            cls = card.attrib.get("class", "")
            id_ = card.attrib.get("id", "")
            print(f"  Tag:       <{tag}>")
            print(f"  Class:     {cls}")
            print(f"  Id:        {id_}")
            print(f"  Outer HTML (first 3000 chars):")
            try:
                outer = card.prettify() if hasattr(card, "prettify") else str(card)
            except Exception:
                outer = str(card)
            for line in outer[:3000].split("\n"):
                print(f"    {line}")
            if len(outer) > 3000:
                print(f"    ... ({len(outer) - 3000} more chars)")

            # Extract structured info
            print(f"\n  --- Extracted info ---")
            # Title
            for title_sel in ["h3", "h2", "h4", ".title", "[class*='title']", "a"]:
                els = card.css(title_sel)
                for el in els[:2]:
                    t = (el.text or "").strip()
                    if t:
                        print(f"  Title ({title_sel}):    {t!r}")
                        break
                else:
                    continue
                break

            # Link
            a_els = card.css("a[href]")
            for a in a_els:
                href = a.attrib.get("href", "")
                if "/hackathons/" in href:
                    print(f"  Link:      {href}")
                    break

            # Date / deadline text
            for el in card.css("*"):
                txt = (el.text or "").strip()
                if any(w in txt.lower() for w in ["deadline", "due", "ends", "registration"]):
                    print(f"  Deadline text: {txt!r}")
                    break
            # Also look for time elements
            for time_el in card.css("time"):
                print(f"  <time>:    datetime={time_el.attrib.get('datetime', '')}  text={time_el.text!r}")

            # Participants
            for el in card.css("*"):
                txt = (el.text or "").strip().lower()
                if "participant" in txt or "member" in txt or "registrant" in txt:
                    print(f"  Participants: {el.text!r}")
                    break

            # All text content
            all_text = " ".join(
                (e.text or "").strip()
                for e in card.css("*")
                if (e.text or "").strip()
            )
            print(f"\n  Full card text (collapsed):")
            print(f"    {all_text[:500]}")
    else:
        print("Could not find card-like elements. Dumping raw page text snippet...")
        body_text = (body.text if body else "") or ""
        print(body_text[:5000])

    print(f"\n{'=' * 80}")
    print("DONE")
    print(f"{'=' * 80}")


if __name__ == "__main__":
    main()
