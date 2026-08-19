"""
Test script to dump the DOM structure of Unstop competition cards (v3).
Targets a.item.opp_XXXXX elements which are the real competition listings.
"""

import sys
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

from scrapling import StealthyFetcher
import traceback

TARGET_URL = "https://unstop.com/competitions?oppstatus=open&usertype=students&domain=2"
USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36"


def safe_text(el):
    try:
        return (el.text or "").strip()
    except Exception:
        return ""


def safe_attrib(el, attr):
    try:
        return el.attrib.get(attr, "")
    except Exception:
        return ""


def deep_text(el):
    """Get all text including from children."""
    parts = []
    try:
        for desc in el.css("*"):
            t = safe_text(desc)
            if t:
                parts.append(t)
    except Exception:
        pass
    return " | ".join(parts)


def print_section(title):
    print()
    print("=" * 80)
    print(f"  {title}")
    print("=" * 80)


def main():
    print_section("FETCHING PAGE")
    print(f"URL: {TARGET_URL}")

    try:
        page = StealthyFetcher.fetch(
            TARGET_URL,
            headless=True,
            user_agent=USER_AGENT,
            network_idle=True,
            timeout=60000,
        )
        print(f"Status: {page.status}")
        print(f"HTML length: {len(page.html_content) if page.html_content else 0}")
    except Exception as e:
        print(f"FATAL: {e}")
        traceback.print_exc()
        return

    # --- Find all competition items (a elements with opp_ class) ---
    print_section("ALL COMPETITION ITEMS (a[class*='opp_'])")
    opp_items = page.css('a[class*="opp_"]')
    print(f"Found {len(opp_items)} competition items")

    for i, item in enumerate(opp_items[:25]):
        classes = safe_attrib(item, "class")
        href = safe_attrib(item, "href")
        h3 = item.css("h3")
        h3_text = safe_text(h3[0]) if h3 else ""
        h2 = item.css("h2")
        h2_text = safe_text(h2[0]) if h2 else ""
        title = h3_text or h2_text

        # Dates
        date_els = item.css('[class*="date"]')
        date_texts = [safe_text(d) for d in date_els if safe_text(d)]
        date_str = " | ".join(date_texts)

        # Counts
        count_els = item.css('[class*="count"]')
        count_texts = [safe_text(c) for c in count_els if safe_text(c)]
        count_str = " | ".join(count_texts)

        # Buttons / register
        btn_els = item.css('[class*="btn"]')
        btn_texts = [safe_text(b) for b in btn_els if safe_text(b)]
        btn_str = " | ".join(btn_texts)

        # All text
        all_text = deep_text(item)

        print(f"\n--- Item {i} ---")
        print(f"  Title: {title}")
        print(f"  Href: {href}")
        print(f"  Classes: {classes}")
        if date_str:
            print(f"  Dates: {date_str}")
        if count_str:
            print(f"  Counts: {count_str}")
        if btn_str:
            print(f"  Buttons: {btn_str}")
        print(f"  All text (condensed): {all_text[:250]}")

    # --- Detailed dump of first 3 competition items ---
    print_section("DETAILED STRUCTURE OF FIRST 3 COMPETITION ITEMS")

    for i, item in enumerate(opp_items[:3]):
        print(f"\n{'~' * 70}")
        print(f"COMPETITION ITEM {i + 1}")
        print(f"{'~' * 70}")

        href = safe_attrib(item, "href")
        print(f"HREF: {href}")

        # Print ALL descendants with structure
        children = item.css("*")
        print(f"Total descendants: {len(children)}")
        for j, child in enumerate(children):
            c_tag = child.tag if hasattr(child, "tag") else "?"
            c_class = safe_attrib(child, "class")
            c_text = safe_text(child)[:120]
            c_href = safe_attrib(child, "href")[:100]
            c_src = safe_attrib(child, "src")[:100]
            c_alt = safe_attrib(child, "alt")[:80]

            line_parts = [f"  [{j:2d}] <{c_tag}>"]
            if c_class:
                line_parts.append(f' class="{c_class}"')
            if c_href:
                line_parts.append(f' href="{c_href}"')
            if c_src:
                line_parts.append(f' src="{c_src}"')
            if c_alt:
                line_parts.append(f' alt="{c_alt}"')
            if c_text:
                line_parts.append(f' text="{c_text}"')
            print("".join(line_parts))

        # Raw HTML
        print(f"\nRaw HTML (first 4000 chars):")
        try:
            raw = str(item.html_content) if hasattr(item, "html_content") else str(item)
            print(raw[:4000])
        except Exception as e:
            print(f"  Error: {e}")

    # --- Parent containers ---
    print_section("PARENT CONTAINERS OF COMPETITION ITEMS")
    parent_selectors = [
        '[class*="listing"]',
        '[class*="Listing"]',
        '[class*="grid"]',
        '[class*="Grid"]',
        '[class*="results"]',
        '[class*="Results"]',
        'main',
        '[class*="content"]',
        'section',
        '[class*="opp"]',
        '[class*="search-result"]',
        'div[class*="col"]',
    ]
    for sel in parent_selectors:
        try:
            found = page.css(sel)
            if found:
                for f in found[:5]:
                    f_tag = f.tag if hasattr(f, "tag") else "?"
                    f_class = safe_attrib(f, "class")
                    inner_opps = f.css('a[class*="opp_"]')
                    if inner_opps:
                        print(f"\nSelector '{sel}' -> <{f_tag} class=\"{f_class}\">")
                        print(f"  Contains {len(inner_opps)} competition items")
        except Exception:
            pass

    # --- Dates section ---
    print_section("ELEMENTS WITH DATE/DEADLINE INFO (outside items)")
    date_els = page.css('[class*="date"]')
    print(f"Found {len(date_els)} elements with 'date' in class")
    for i, el in enumerate(date_els[:15]):
        tag = el.tag if hasattr(el, "tag") else "?"
        cls = safe_attrib(el, "class")
        text = safe_text(el)[:120]
        print(f"  [{i}] <{tag}> class=\"{cls}\" text=\"{text}\"")
        for child in el.css("*")[:5]:
            c_tag = child.tag if hasattr(child, "tag") else "?"
            c_cls = safe_attrib(child, "class")
            c_text = safe_text(child)[:80]
            if c_text:
                print(f"        <{c_tag}> class=\"{c_cls}\" text=\"{c_text}\"")

    # --- Count / participant / deadline info ---
    print_section("ELEMENTS WITH COUNT/PARTICIPANT/DEADLINE INFO")
    for pattern in ["count", "participant", "team", "member", "applied",
                     "registered", "deadline", "close", "registr"]:
        found = page.css(f'[class*="{pattern}"]')
        if found:
            print(f"\n[class*=\"{pattern}\"]: {len(found)} matches")
            for f in found[:3]:
                tag = f.tag if hasattr(f, "tag") else "?"
                cls = safe_attrib(f, "class")
                text = safe_text(f)[:100]
                print(f"  <{tag}> class=\"{cls}\" text=\"{text}\"")

    # --- Status labels ---
    print_section("STATUS/BADGE/TAG ELEMENTS")
    for pattern in ["status", "badge", "tag", "label", "type", "category"]:
        found = page.css(f'[class*="{pattern}"]')
        if found:
            unique_texts = set()
            for f in found[:20]:
                text = safe_text(f)[:60]
                if text:
                    unique_texts.add(text)
            if unique_texts:
                print(f"\n[class*=\"{pattern}\"]: {len(found)} matches, unique texts: {unique_texts}")

    print_section("DONE")


if __name__ == "__main__":
    main()
