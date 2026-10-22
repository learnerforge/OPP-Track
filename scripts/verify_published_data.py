#!/usr/bin/env python3
"""Verify that the manifest identifies the exact catalog bytes being served.

This is intentionally read-only and stdlib-only so it can run in CI before a
deployment. It checks the canonical dataset, the manifest's digest/name, the
public manifest, and the immutable public snapshot.
"""

from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
CANONICAL = ROOT / "data" / "scraped_opportunities.json"
MANIFEST = ROOT / "data" / "manifest.json"
PUBLIC = ROOT / "public" / "data"
PUBLIC_MANIFEST = PUBLIC / "manifest.json"


def fail(message: str) -> int:
    print(f"DATA INTEGRITY: FAIL - {message}", file=sys.stderr)
    return 1


def load_manifest(path: Path) -> dict[str, object] | None:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        print(f"DATA INTEGRITY: FAIL - cannot read {path}: {exc}", file=sys.stderr)
        return None
    if not isinstance(data, dict):
        print(f"DATA INTEGRITY: FAIL - {path} must contain an object", file=sys.stderr)
        return None
    return data


def main() -> int:
    try:
        raw = CANONICAL.read_bytes()
        items = json.loads(raw)
    except (OSError, json.JSONDecodeError) as exc:
        return fail(f"cannot read canonical dataset: {exc}")
    if not isinstance(items, list):
        return fail("canonical dataset must be a JSON array")

    manifest = load_manifest(MANIFEST)
    public_manifest = load_manifest(PUBLIC_MANIFEST)
    if manifest is None or public_manifest is None:
        return 1

    digest = hashlib.sha256(raw).hexdigest()
    expected_file = f"opportunities.{digest[:8]}.json"
    if manifest.get("sha256") != digest:
        return fail("data/manifest.json sha256 does not match canonical dataset")
    if manifest.get("published_sha8") != digest[:8]:
        return fail("data/manifest.json published_sha8 does not match canonical dataset")
    if manifest.get("published_file") != expected_file:
        return fail("data/manifest.json published_file does not match canonical dataset")
    if manifest.get("item_count") != len(items):
        return fail("data/manifest.json item_count does not match canonical dataset")
    if public_manifest != manifest:
        return fail("public/data/manifest.json differs from data/manifest.json")

    published = PUBLIC / expected_file
    try:
        public_raw = published.read_bytes()
    except OSError as exc:
        return fail(f"published asset missing: {exc}")
    if public_raw != raw:
        return fail("published asset is not byte-identical to canonical dataset")

    print(f"DATA INTEGRITY: PASS - {len(items)} items, sha256 {digest}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
