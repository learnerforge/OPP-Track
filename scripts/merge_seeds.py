"""
merge_seeds.py — Reads scraped_opportunities.json and generates SEED_DATA entries.

This script:
1. Reads scraped data from data/scraped_opportunities.json
2. Reads existing SEED_DATA from src/lib/storage.ts
3. Deduplicates against existing entries
4. Generates new seed entries with proper IDs
5. Outputs new entries to data/new_seed_entries.json (manual review before merging)

Usage:
    python scripts/merge_seeds.py                    # Generate new entries
    python scripts/merge_seeds.py --auto             # Auto-merge into storage.ts
    python scripts/merge_seeds.py --preview          # Preview only, no file output
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
SCRAPED_FILE = PROJECT_ROOT / "data" / "scraped_opportunities.json"
STORAGE_FILE = PROJECT_ROOT / "src" / "lib" / "storage.ts"
OUTPUT_FILE = PROJECT_ROOT / "data" / "new_seed_entries.json"


def extract_existing_titles(storage_path: Path) -> set[str]:
    """Extract existing seed titles from storage.ts to avoid duplicates."""
    if not storage_path.exists():
        return set()

    content = storage_path.read_text(encoding="utf-8")
    # Match title: 'Some Title' patterns in SEED_DATA
    titles = set()
    for match in re.finditer(r"title:\s*['\"](.+?)['\"]", content):
        titles.add(match.group(1).lower().strip())
    return titles


def extract_existing_links(storage_path: Path) -> set[str]:
    """Extract existing seed links from storage.ts to avoid duplicates."""
    if not storage_path.exists():
        return set()

    content = storage_path.read_text(encoding="utf-8")
    links = set()
    for match in re.finditer(r"link:\s*['\"](.+?)['\"]", content):
        links.add(match.group(1).strip())
    return links


def get_next_seed_id(storage_path: Path) -> int:
    """Find the next available seed ID number."""
    if not storage_path.exists():
        return 1

    content = storage_path.read_text(encoding="utf-8")
    ids = []
    for match in re.finditer(r"id:\s*['\"]seed_(\d+)['\"]", content):
        ids.append(int(match.group(1)))

    return max(ids) + 1 if ids else 1


def generate_seed_entry(item: dict, seed_id: int) -> str:
    """Generate a TypeScript SEED_DATA entry string."""
    id_str = f"seed_{seed_id:03d}"
    title = item["title"].replace("'", "\\'")
    opp_type = item["type"]
    source = item["source"].replace("'", "\\'")
    link = item["link"].replace("'", "\\'")
    deadline = item.get("deadline", "")
    eligibility = item.get("eligibility", "").replace("'", "\\'")
    tags = item.get("tags", [])
    notes = item.get("notes", "").replace("'", "\\'")
    date_added = item.get("date_added", "2026-08-18")
    location = item.get("location", "").replace("'", "\\'")
    prize_pool = item.get("prize_pool", "").replace("'", "\\'")
    participants = item.get("participants", "")
    organizer = item.get("organizer", "").replace("'", "\\'")

    tags_str = ", ".join(f"'{t}'" for t in tags) if tags else ""
    participants_str = f"'{participants}'" if participants else ""
    location_str = f"'{location}'" if location else ""
    prize_pool_str = f"'{prize_pool}'" if prize_pool else ""
    organizer_str = f"'{organizer}'" if organizer else ""

    return f"""  {{
    id: '{id_str}',
    title: '{title}',
    type: '{opp_type}',
    source: '{source}',
    link: '{link}',
    deadline: '{deadline}',
    eligibility: '{eligibility}',
    tags: [{tags_str}],
    status: 'Not Started',
    notes: '{notes}',
    date_added: '{date_added}',
    location: {location_str},
    prize_pool: {prize_pool_str},
    participants: {participants_str},
    organizer: {organizer_str},
  }},"""


def main():
    parser = argparse.ArgumentParser(description="Merge scraped data into SEED_DATA")
    parser.add_argument("--auto", action="store_true", help="Auto-merge into storage.ts")
    parser.add_argument("--preview", action="store_true", help="Preview only")
    parser.add_argument("--scraped", type=str, default=str(SCRAPED_FILE))
    parser.add_argument("--output", type=str, default=str(OUTPUT_FILE))
    args = parser.parse_args()

    scraped_path = Path(args.scraped)
    output_path = Path(args.output)

    # Load scraped data
    if not scraped_path.exists():
        print(f"Error: {scraped_path} not found. Run scrapers first.")
        sys.exit(1)

    with open(scraped_path, "r", encoding="utf-8") as f:
        scraped_data = json.load(f)

    print(f"Loaded {len(scraped_data)} scraped items")

    # Get existing data to deduplicate
    existing_titles = extract_existing_titles(STORAGE_FILE)
    existing_links = extract_existing_links(STORAGE_FILE)
    next_id = get_next_seed_id(STORAGE_FILE)

    print(f"Existing seeds: {len(existing_titles)} titles, {len(existing_links)} links")
    print(f"Next seed ID: {next_id}")

    # Filter out duplicates
    new_items = []
    skipped = 0
    for item in scraped_data:
        title_lower = item["title"].lower().strip()
        link = item.get("link", "")

        # Skip if title already exists
        if title_lower in existing_titles:
            skipped += 1
            continue

        # Skip if link already exists
        if link and link in existing_links:
            skipped += 1
            continue

        new_items.append(item)

    print(f"New items: {len(new_items)} (skipped {skipped} duplicates)")

    if args.preview:
        print("\n--- Preview ---")
        for item in new_items:
            print(f"  {item['title']} | {item['type']} | {item.get('deadline', 'N/A')}")
        return

    # Generate entries
    entries = []
    for i, item in enumerate(new_items):
        entry = generate_seed_entry(item, next_id + i)
        entries.append(entry)

    # Save to file
    output_path.parent.mkdir(parents=True, exist_ok=True)

    if args.auto:
        # Append directly to storage.ts
        if STORAGE_FILE.exists():
            content = STORAGE_FILE.read_text(encoding="utf-8")
            # Find the end of SEED_DATA array
            insert_marker = "];  // END_SEED_DATA"
            if insert_marker in content:
                new_entries = "\n".join(entries)
                content = content.replace(insert_marker, f"{new_entries}\n{insert_marker}")
                STORAGE_FILE.write_text(content, encoding="utf-8")
                print(f"\nAppended {len(entries)} entries to {STORAGE_FILE}")
            else:
                # Try to find the closing bracket of SEED_DATA
                print(f"\nCould not find insertion marker. Saving to {output_path}")
                with open(output_path, "w", encoding="utf-8") as f:
                    json.dump(new_items, f, indent=2, ensure_ascii=False)
                print(f"Saved {len(new_items)} new items to {output_path}")
    else:
        # Save to JSON for manual review
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(new_items, f, indent=2, ensure_ascii=False)
        print(f"\nSaved {len(new_items)} new items to {output_path}")

        # Also save the TypeScript entries
        ts_path = output_path.with_suffix(".ts")
        with open(ts_path, "w", encoding="utf-8") as f:
            f.write("// Auto-generated SEED_DATA entries from scrapers\n")
            f.write("// Review these entries before adding to storage.ts\n\n")
            f.write("export const NEW_SEED_ENTRIES = [\n")
            for entry in entries:
                f.write(entry + "\n")
            f.write("];\n")
        print(f"Saved TypeScript entries to {ts_path}")

    # Summary by source
    by_source: dict[str, int] = {}
    for item in new_items:
        src = item["source"]
        by_source[src] = by_source.get(src, 0) + 1

    if by_source:
        print("\nBy source:")
        for src, count in sorted(by_source.items()):
            print(f"  {src}: {count}")


if __name__ == "__main__":
    main()
