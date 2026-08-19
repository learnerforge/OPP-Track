"""
HackerEarth challenges page DOM structure explorer - Final.
Deep-dives into the actual challenge card structure found in the grid.
"""

from __future__ import annotations

import traceback
from scrapling.fetchers import StealthyFetcher


def css1(el, selector: str):
    results = el.css(selector)
    return results[0] if results else None


def run() -> None:
    url = "https://www.hackerearth.com/challenges/"
    print(f"Fetching {url} ...\n")

    try:
        page = StealthyFetcher.fetch(
            url,
            headless=True,
            timeout=60000,
        )

        print(f"Status: {page.status}")
        print(f"URL: {page.url}")
        title_el = css1(page, "title")
        print(f"Title: {title_el.text if title_el else 'N/A'}")

        # ── Find the main grid container ──────────────────────────────
        print("\n" + "=" * 80)
        print("GRID CONTAINER")
        print("=" * 80)
        grid = css1(page, 'div[class*="grid"][class*="grid-cols"]')
        if grid:
            cls = grid.attrib.get("class", "")
            children = list(grid.children)
            print(f"Grid class: {cls}")
            print(f"Direct children count: {len(children)}")
            for i, child in enumerate(children):
                tag = getattr(child, "tag", "?")
                cls_c = child.attrib.get("class", "")[:80]
                print(f"  [{i}] <{tag}> class=\"{cls_c}\"")

        # ── Find challenge card wrappers (group relative w-full block) ──
        print("\n" + "=" * 80)
        print("CHALLENGE CARD WRAPPERS (div.group.relative.w-full.block)")
        print("=" * 80)
        cards = page.css('div.group.relative.w-full.block')
        print(f"Found {len(cards)} challenge cards\n")

        for i, card in enumerate(cards):
            print(f"{'='*60}")
            print(f"CARD {i + 1}")
            print(f"{'='*60}")

            # Full HTML
            try:
                card_html = card.html_content
            except Exception:
                card_html = card.prettify()
            print(f"\n--- Full HTML ({len(card_html)} chars) ---")
            print(card_html[:5000])
            print()

            # Extract specific fields
            print("--- Field Extraction ---")

            # Title (h3)
            h3 = css1(card, "h3")
            title = h3.text.strip() if h3 and h3.text else ""
            print(f"  Title (h3): {title!r}")

            # Company/organizer
            company = ""
            # The company is typically in a div after h3 within px-4 py-4 grid gap-2
            info_div = css1(card, 'div[class*="px-4"][class*="py-4"]')
            if info_div:
                divs = info_div.css("div")
                for d in divs:
                    text = (d.text or "").strip()
                    if text and text != title and len(text) < 60:
                        # Check if it's not a nested element that's already a title
                        child_tags = [getattr(c, "tag", "?") for c in d.children]
                        if not child_tags:  # leaf node
                            company = text
                            break
            print(f"  Company: {company!r}")

            # Status badge
            status = ""
            # Look for badge-like elements
            for sel in ['[class*="badge"]', '[class*="status"]', '[class*="bg-"]']:
                badges = card.css(sel)
                for b in badges:
                    text = (b.text or "").strip()
                    if text and len(text) < 30:
                        status = text
                        break
                if status:
                    break
            # Fallback: look for known status text
            full_text = card.get_all_text() if hasattr(card, "get_all_text") else (card.text or "")
            for known in ["Live", "Upcoming", "Registration Open", "Ended", "Completed"]:
                if known in full_text:
                    status = known
                    break
            print(f"  Status: {status!r}")

            # Participants
            participants = ""
            for known_pattern in ["K", "k"]:
                import re
                match = re.search(r'(\d+(?:\.\d+)?K?)\s*(?:participant|team|member|registr)', full_text, re.I)
                if match:
                    participants = match.group(1)
                    break
            # Fallback: look for numbers near participant-related text
            if not participants:
                # In the text, after the status, there's a number
                nums = re.findall(r'(\d+(?:\.\d+)?K?)', full_text)
                # Filter out small numbers that could be dates, etc.
                for n in nums:
                    if n not in ("0", "2", "3") or "K" in n or len(n) > 1:
                        participants = n
                        break
            print(f"  Participants: {participants!r}")

            # Link
            link = ""
            a = css1(card, "a[href]")
            if a:
                href = a.attrib.get("href", "")
                if not href.startswith("http"):
                    href = f"https://www.hackerearth.com{href}"
                link = href
            print(f"  Link: {link!r}")

            # Image
            img = css1(card, "img[src]")
            img_src = img.attrib.get("src", "") if img else ""
            print(f"  Image: {img_src[:120]!r}")

            # Full text dump
            print(f"  Full card text: {full_text.strip()[:300]!r}")

            # All child elements tree
            print(f"\n  --- Child Element Tree ---")
            for child in card.css("*"):
                tag = getattr(child, "tag", "?")
                cls = child.attrib.get("class", "")
                text = (child.text or "").strip()[:80]
                href = child.attrib.get("href", "")
                src = child.attrib.get("src", "")
                alt = child.attrib.get("alt", "")
                line = f"    <{tag}>"
                if cls:
                    line += f" class=\"{cls[:100]}\""
                if href:
                    line += f" href=\"{href}\""
                if src:
                    line += f" src=\"{src[:80]}\""
                if alt:
                    line += f" alt=\"{alt}\""
                if text:
                    line += f"  text=\"{text}\""
                print(line)

            print()

        # ── Sidebar card (Host your own hackathon) ────────────────────
        print("=" * 80)
        print("SIDEBAR / PROMO SECTION")
        print("=" * 80)
        sidebar = css1(page, 'div[class*="hidden"][class*="xl:flex"][class*="flex-col"][class*="gap-3"]')
        if sidebar:
            print(sidebar.html_content[:2000])

        # ── Filter buttons ────────────────────────────────────────────
        print("\n" + "=" * 80)
        print("FILTER / TAB BUTTONS")
        print("=" * 80)
        buttons = page.css("button")
        for b in buttons:
            text = (b.text or "").strip()
            if text and len(text) < 50 and text not in ("Theme", "Submit Feedback"):
                cls = b.attrib.get("class", "")
                print(f"  <button> text=\"{text}\" class=\"{cls[:80]}\"")

        # ── Status tabs (Upcoming, Live, etc.) ────────────────────────
        print("\n" + "=" * 80)
        print("STATUS TABS / PILLS")
        print("=" * 80)
        tabs = page.css('[class*="tab"], [role="tab"], [class*="pill"]')
        for t in tabs:
            text = (t.text or "").strip()
            cls = t.attrib.get("class", "")
            print(f"  text=\"{text}\" class=\"{cls[:100]}\"")

        # Check for "Status: Upcoming" / "Status: Live" pills
        status_divs = page.css('div[class*="flex"][class*="gap-2"]')
        for d in status_divs:
            text = (d.get_all_text() if hasattr(d, "get_all_text") else (d.text or "")).strip()
            if "Status:" in text or "Upcoming" in text or "Live" in text:
                print(f"\n  Status filter area: {text!r}")
                break

    except Exception as e:
        print(f"ERROR: {e}")
        traceback.print_exc()


if __name__ == "__main__":
    run()
