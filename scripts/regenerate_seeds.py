"""
regenerate_seeds.py — Regenerates the full SEED_DATA array in src/lib/storage.ts from
the validated scraped data (data/scraped_opportunities.json).

Unlike merge_seeds.py (incremental append), this replaces the entire seed set with the
latest validated items so the storage always mirrors the freshest scrape.

Usage:
    python scripts/regenerate_seeds.py              # regenerate + bump SEED_VERSION
    python scripts/regenerate_seeds.py --dry-run    # print counts without writing
"""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
SCRAPED_FILE = PROJECT_ROOT / "data" / "scraped_opportunities.json"
STORAGE_FILE = PROJECT_ROOT / "src" / "lib" / "storage.ts"

START_MARKER = "export const SEED_DATA = ["
END_MARKER = "];  // END_SEED_DATA"
VERSION_RE = re.compile(r"export const SEED_VERSION = (\d+);")


def esc(value: str) -> str:
    return value.replace("\\", "\\\\").replace("'", "\\'")


def build_entry(item: dict, seed_id: int) -> str:
    tags = item.get("tags") or []
    tags_str = ", ".join(f"'{esc(str(t))}'" for t in tags) if tags else ""

    def opt(field: str, json_field: str | None = None) -> str:
        value = item.get(json_field or field, "")
        if not value:
            return ""
        return f"    {field}: '{esc(str(value))}',\n"

    lines = [
        "  {",
        f"    id: 'seed_{seed_id:03d}',",
        f"    title: '{esc(str(item['title']))}',",
        f"    type: '{esc(str(item['type']))}',",
        f"    source: '{esc(str(item['source']))}',",
        f"    link: '{esc(str(item['link']))}',",
        f"    deadline: '{esc(str(item.get('deadline', '')))}',",
        f"    eligibility: '{esc(str(item.get('eligibility', '')))}',",
        f"    tags: [{tags_str}],",
        "    status: 'Not Started',",
        f"    notes: '{esc(str(item.get('notes', '')))}',",
        f"    date_added: '{esc(str(item.get('date_added', '')))}',",
    ]
    for field in ("location", "prize_pool", "participants", "organizer", "duration"):
        opt_line = opt(field)
        if opt_line:
            lines.append(opt_line.rstrip("\n"))
    lines.append("  } as Opportunity,")
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(description="Regenerate full SEED_DATA in storage.ts")
    parser.add_argument("--dry-run", action="store_true", help="Only report what would change")
    args = parser.parse_args()

    items = json.loads(SCRAPED_FILE.read_text(encoding="utf-8"))
    content = STORAGE_FILE.read_text(encoding="utf-8")

    if START_MARKER not in content or END_MARKER not in content:
        raise SystemExit(f"Markers not found in {STORAGE_FILE}; aborting.")

    entries = [build_entry(item, i + 1) for i, item in enumerate(items)]
    new_block = f"{START_MARKER}\n" + "\n".join(entries) + f"\n{END_MARKER}"

    version_match = VERSION_RE.search(content)
    if not version_match:
        raise SystemExit("SEED_VERSION not found; aborting.")
    new_version = int(version_match.group(1)) + 1

    print(f"Items: {len(items)} -> {len(entries)} entries")
    print(f"SEED_VERSION: {version_match.group(1)} -> {new_version}")
    if args.dry_run:
        return

    content = content.replace(
        re.search(rf"{re.escape(START_MARKER)}.*?{re.escape(END_MARKER)}", content, re.S).group(0),
        new_block,
    )
    content = VERSION_RE.sub(f"export const SEED_VERSION = {new_version};", content, count=1)
    STORAGE_FILE.write_text(content, encoding="utf-8")
    print(f"Wrote {STORAGE_FILE}")


if __name__ == "__main__":
    main()