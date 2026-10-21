#!/usr/bin/env python3
"""Sanity / regression gate for the canonical dataset (B18; plan 11.3 control 5).

Run before every publish:

    python scripts/sanity_gate.py --current data/scraped_opportunities.json \\
        [--previous data/manifest.json] [--allow-init]

Checks (absolute, always):
  * current dataset is a non-empty JSON array
  * every ``deadline`` is '' (rolling/evergreen) or a real YYYY-MM-DD date
  * every ``type`` is in {Hackathon, Internship, Certification, Competition}
  * every ``link`` is a valid http(s) URL or ''
  * no duplicate ids (identity = ``id`` if present, else ``fingerprint``)
  * type histogram is non-degenerate (no single type > 98% of items)

Checks (relative, when a baseline is available):
  * total item count within +/-20% of the previous manifest's ``item_count``
  * per-source counts within +/-50%
  * per-source counts below ``MIN_SOURCE_BASELINE`` warn instead of error
  * sources marked ``blocked`` in the health report warn instead of error
    (a 403/429/Cloudflare block is a transport failure, not a regression)

Baseline resolution:
  1. ``--previous`` manifest (default ``data/manifest.json``) if it exists
  2. else the newest ``<dataset dir>/backups/scraped_*.json`` (full-file fallback)
  3. else, with ``--allow-init``: absolute checks only
  4. else: fail with a clear message

Exit codes: 0 = pass, 1 = fail.  This module is importable: tests drive
``run_gate()`` / ``main()`` directly.
"""
from __future__ import annotations

import argparse
import glob
import json
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
from urllib.parse import urlparse

VALID_TYPES = ("Hackathon", "Internship", "Certification", "Competition")
DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
TOTAL_TOLERANCE = 0.20
SOURCE_TOLERANCE = 0.50
# A percentage rule on a source this small is noise, not signal: a 2-item
# source dropping to 0 is "-100%" but says nothing about scrape health, and a
# 2-item source doubling is "+100%" for one extra item. Below this baseline we
# only warn. Real regressions in the big sources are unaffected.
MIN_SOURCE_BASELINE = 5
MAX_TYPE_SHARE = 0.98
DEFAULT_PREVIOUS = "data/manifest.json"
# Source-health report written by run_all.py each scrape. Maps a source *label*
# (e.g. "Topcoder") to its classified outcome. Used to distinguish a blocked
# source from a genuine data regression.
DEFAULT_HEALTH = "data/scraper_health.json"


def load_blocked_sources(health_path: Optional[str]) -> set:
    """Return the set of source *labels* marked ``blocked`` in the health file.

    run_all.py records health keyed by source label ("Devpost"), which is the
    same string the dataset uses as ``source``. Missing/unreadable file => empty
    set (the check simply does not apply; never a hard failure).
    """
    if not health_path:
        return set()
    path = Path(health_path)
    if not path.is_file():
        return set()
    data, err = load_json(path)
    if err is not None or not isinstance(data, dict):
        return set()
    sources = data.get("sources")
    if not isinstance(sources, dict):
        return set()
    blocked = set()
    for name, entry in sources.items():
        if not isinstance(entry, dict):
            continue
        label = entry.get("source") or name
        if entry.get("status") == "blocked":
            blocked.add(str(label))
    return blocked


# --------------------------------------------------------------------------- #
# helpers
# --------------------------------------------------------------------------- #
def is_real_date(value: Any) -> bool:
    """True for a real, round-trippable YYYY-MM-DD calendar date."""
    if not isinstance(value, str) or not DATE_RE.match(value):
        return False
    try:
        import datetime

        datetime.date.fromisoformat(value)
        return True
    except ValueError:
        return False


def is_http_url(value: Any) -> bool:
    if not isinstance(value, str) or not value:
        return False
    try:
        parsed = urlparse(value)
    except ValueError:
        return False
    return parsed.scheme in ("http", "https") and bool(parsed.netloc)


def item_label(item: Any, index: int) -> str:
    if isinstance(item, dict):
        for key in ("id", "fingerprint"):
            value = item.get(key)
            if isinstance(value, str) and value:
                return value
    return f"index {index}"


def load_json(path: Path) -> Tuple[Optional[Any], Optional[str]]:
    """Return (data, None) or (None, error message)."""
    try:
        raw = path.read_text(encoding="utf-8")
    except OSError as exc:
        return None, f"cannot read {path}: {exc}"
    try:
        return json.loads(raw), None
    except json.JSONDecodeError as exc:
        return None, f"invalid JSON in {path}: {exc}"


# --------------------------------------------------------------------------- #
# result type
# --------------------------------------------------------------------------- #
@dataclass
class GateResult:
    ok: bool
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    item_count: Optional[int] = None
    baseline_count: Optional[int] = None
    baseline_source: str = "none"
    current_path: str = ""


# --------------------------------------------------------------------------- #
# individual check groups
# --------------------------------------------------------------------------- #
def absolute_checks(items: List[Any]) -> Tuple[List[str], List[str]]:
    """Schema/degeneracy checks that need no baseline."""
    errors: List[str] = []
    warnings: List[str] = []

    if not items:
        errors.append("current dataset is empty (0 items) - a publish must never ship an empty catalog")
        return errors, warnings

    seen_ids: Dict[str, str] = {}
    type_counts: Dict[str, int] = {}

    for index, item in enumerate(items):
        if not isinstance(item, dict):
            errors.append(f"[index {index}] item is not an object")
            continue
        label = item_label(item, index)

        deadline = item.get("deadline")
        if not isinstance(deadline, str) or (deadline != "" and not is_real_date(deadline)):
            errors.append(
                f"[{label}] deadline {deadline!r} must be '' (rolling) or a real YYYY-MM-DD date"
            )

        item_type = item.get("type")
        if not isinstance(item_type, str) or item_type not in VALID_TYPES:
            errors.append(f"[{label}] invalid type {item_type!r} (expected {' | '.join(VALID_TYPES)})")
        type_counts[str(item_type)] = type_counts.get(str(item_type), 0) + 1

        link = item.get("link")
        if not isinstance(link, str) or (link != "" and not is_http_url(link)):
            errors.append(f"[{label}] link {link!r} is not a valid http(s) URL (use '' when absent)")

        identity = None
        for key in ("id", "fingerprint"):
            value = item.get(key)
            if isinstance(value, str) and value:
                identity = f"{key}:{value}"
                break
        if identity is None:
            errors.append(f"[{label}] missing identity: needs a non-empty 'id' or 'fingerprint'")
        elif identity in seen_ids:
            errors.append(f"[{label}] duplicate id {identity!r} (first seen at {seen_ids[identity]})")
        else:
            seen_ids[identity] = label

    total = len(items)
    top_type, top_n = max(type_counts.items(), key=lambda kv: kv[1])
    if total and top_n / total > MAX_TYPE_SHARE:
        errors.append(
            f"type histogram degenerate: {top_type!r} is {100 * top_n / total:.1f}% of {total} items "
            f"(max allowed {100 * MAX_TYPE_SHARE:.0f}%) - scraper likely collapsed to a single type"
        )

    return errors, warnings


def regression_checks(
    current: List[Any],
    baseline_total: Optional[int],
    baseline_per_source: Optional[Dict[str, int]],
    blocked_sources: Optional[set] = None,
) -> Tuple[List[str], List[str]]:
    errors: List[str] = []
    warnings: List[str] = []
    blocked_sources = blocked_sources or set()

    current_total = len(current)

    if baseline_total is not None:
        lo = baseline_total * (1 - TOTAL_TOLERANCE)
        hi = baseline_total * (1 + TOTAL_TOLERANCE)
        if not (lo <= current_total <= hi):
            delta = 100 * (current_total - baseline_total) / baseline_total if baseline_total else 0.0
            errors.append(
                f"total count regressed: {baseline_total} -> {current_total} ({delta:+.0f}%) "
                f"outside +/-{100 * TOTAL_TOLERANCE:.0f}% (allowed {lo:.0f}..{hi:.0f})"
            )

    if baseline_per_source is not None:
        current_per_source: Dict[str, int] = {}
        for item in current:
            if isinstance(item, dict):
                source = item.get("source")
                if isinstance(source, str) and source:
                    current_per_source[source] = current_per_source.get(source, 0) + 1
        for source in sorted(baseline_per_source):
            prev = baseline_per_source[source]
            if prev <= 0:
                continue
            cur = current_per_source.get(source, 0)
            delta = 100 * (cur - prev) / prev
            # A blocked source is a transport failure, not a data regression.
            # Reporting "18 -> 0 (-100%)" for a 403 is a lie that sends the
            # reader looking for a broken parser. Warn instead of error so the
            # scheduled run does not fail on a site that simply refuses us.
            if source in blocked_sources:
                if cur != prev:
                    warnings.append(
                        f"source '{source}' BLOCKED (403/429/Cloudflare): {prev} -> {cur} items "
                        f"- transport failure, not a data regression; source skipped this run"
                    )
                continue
            if prev < MIN_SOURCE_BASELINE:
                # Too small for a percentage rule to mean anything.
                if cur != prev:
                    warnings.append(
                        f"source '{source}' changed: {prev} -> {cur} items ({delta:+.0f}%) "
                        f"- baseline below {MIN_SOURCE_BASELINE}, not treated as a regression"
                    )
                continue
            lo = prev * (1 - SOURCE_TOLERANCE)
            hi = prev * (1 + SOURCE_TOLERANCE)
            if not (lo <= cur <= hi):
                errors.append(
                    f"source '{source}' regressed: {prev} -> {cur} items ({delta:+.0f}%) "
                    f"outside +/-{100 * SOURCE_TOLERANCE:.0f}%"
                )
        for source in sorted(set(current_per_source) - set(baseline_per_source)):
            warnings.append(
                f"source '{source}' is new (no baseline): {current_per_source[source]} items"
            )

    return errors, warnings


# --------------------------------------------------------------------------- #
# baseline resolution
# --------------------------------------------------------------------------- #
def _per_source_from_items(items: List[Any]) -> Dict[str, int]:
    counts: Dict[str, int] = {}
    for item in items:
        if isinstance(item, dict):
            source = item.get("source")
            if isinstance(source, str) and source:
                counts[source] = counts.get(source, 0) + 1
    return counts


def resolve_baseline(
    current_path: Path, previous_path: Optional[str], allow_init: bool
) -> Tuple[Optional[int], Optional[Dict[str, int]], str, List[str], List[str]]:
    """Locate the comparison baseline.

    Returns (total, per_source, source_note, errors, warnings).
    """
    errors: List[str] = []
    warnings: List[str] = []

    previous = Path(previous_path) if previous_path else Path(DEFAULT_PREVIOUS)
    if previous.exists():
        data, err = load_json(previous)
        if err is not None:
            errors.append(f"previous manifest unusable: {err}")
            return None, None, str(previous), errors, warnings
        if not isinstance(data, dict) or not isinstance(data.get("item_count"), int):
            errors.append(
                f"previous manifest {previous} is malformed: needs an integer 'item_count' field"
            )
            return None, None, str(previous), errors, warnings
        per_source = data.get("per_source_counts")
        if isinstance(per_source, dict):
            per_source = {str(k): int(v) for k, v in per_source.items() if isinstance(v, int)}
        else:
            warnings.append(
                f"manifest {previous} has no 'per_source_counts' - per-source +/-50% check skipped"
            )
            per_source = None
        return int(data["item_count"]), per_source, f"manifest {previous}", errors, warnings

    # fallback: newest full-dataset backup next to the current dataset
    backups_dir = current_path.parent / "backups"
    candidates = sorted(glob.glob(str(backups_dir / "scraped_*.json")), reverse=True)
    for candidate in candidates:
        data, err = load_json(Path(candidate))
        if err is not None or not isinstance(data, list):
            warnings.append(f"skipping unreadable backup {candidate}: {err}")
            continue
        return len(data), _per_source_from_items(data), f"backup {candidate}", errors, warnings

    if allow_init:
        warnings.append(
            "no baseline found (no previous manifest, no backups) - --allow-init: "
            "running absolute checks only"
        )
        return None, None, "none (--allow-init)", errors, warnings

    errors.append(
        f"no baseline: {previous} does not exist and {backups_dir}/scraped_*.json is empty. "
        "Create the manifest, or pass --allow-init to run absolute checks only (first run)."
    )
    return None, None, "none", errors, warnings


# --------------------------------------------------------------------------- #
# public API
# --------------------------------------------------------------------------- #
def run_gate(
    current_path: str,
    previous_path: Optional[str] = DEFAULT_PREVIOUS,
    allow_init: bool = False,
    health_path: Optional[str] = DEFAULT_HEALTH,
) -> GateResult:
    """Run every check against ``current_path``. Never writes to any file."""
    current = Path(current_path)

    data, err = load_json(current)
    if err is not None:
        return GateResult(ok=False, errors=[err], current_path=str(current))
    if not isinstance(data, list):
        return GateResult(
            ok=False,
            errors=[f"{current} must contain a plain JSON array of opportunity objects"],
            current_path=str(current),
        )

    abs_errors, abs_warnings = absolute_checks(data)
    base_total, base_per_source, base_note, base_errors, base_warnings = resolve_baseline(
        current, previous_path, allow_init
    )
    blocked_sources = load_blocked_sources(health_path)
    reg_errors, reg_warnings = regression_checks(
        data, base_total, base_per_source, blocked_sources=blocked_sources
    )

    errors = abs_errors + base_errors + reg_errors
    warnings = abs_warnings + base_warnings + reg_warnings
    return GateResult(
        ok=not errors,
        errors=errors,
        warnings=warnings,
        item_count=len(data),
        baseline_count=base_total,
        baseline_source=base_note,
        current_path=str(current),
    )


def format_report(result: GateResult) -> str:
    lines = ["=== Sanity / regression gate ==="]
    baseline = (
        f"{result.baseline_source} ({result.baseline_count} items)"
        if result.baseline_count is not None
        else result.baseline_source
    )
    lines.append(f"current:  {result.current_path} ({result.item_count} items)")
    lines.append(f"baseline: {baseline}")
    if result.errors:
        lines.append(f"FAIL - {len(result.errors)} problem(s):")
        lines.extend(f"  ERROR  {e}" for e in result.errors)
    if result.warnings:
        lines.append(f"{len(result.warnings)} warning(s):")
        lines.extend(f"  WARN   {w}" for w in result.warnings)
    lines.append(f"RESULT: {'FAIL' if not result.ok else 'PASS'}")
    return "\n".join(lines)


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        description="Sanity/regression gate for the canonical dataset (run before every publish)."
    )
    parser.add_argument("--current", required=True, help="dataset JSON to check")
    parser.add_argument(
        "--previous",
        default=DEFAULT_PREVIOUS,
        help=f"previous manifest with item_count/per_source_counts (default: {DEFAULT_PREVIOUS})",
    )
    parser.add_argument(
        "--allow-init",
        action="store_true",
        help="first run: if no baseline exists, run only the absolute checks",
    )
    parser.add_argument(
        "--health",
        default=DEFAULT_HEALTH,
        help=f"source-health report written by run_all.py (default: {DEFAULT_HEALTH}); "
        "sources marked 'blocked' are reported as transport failures, not regressions",
    )
    args = parser.parse_args(argv)

    result = run_gate(
        args.current,
        previous_path=args.previous,
        allow_init=args.allow_init,
        health_path=args.health,
    )
    print(format_report(result))
    return 0 if result.ok else 1


if __name__ == "__main__":
    sys.exit(main())
