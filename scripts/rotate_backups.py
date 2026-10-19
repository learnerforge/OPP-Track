#!/usr/bin/env python3
"""Rotate timestamped backups of the canonical dataset (fullstack.md E1).

Protection controls #8 (backups) and #9 (bounded growth), contract §11.2.

Exact CLI contract (also called by scripts/publish_dataset.py):

    python scripts/rotate_backups.py --file data/scraped_opportunities.json \
        --dir data/backups --keep-daily 7 --keep-weekly 8 [--dry-run]

Behaviour:
  * copies --file to <dir>/scraped_YYYYMMDD_HHMMSS.json (UTC), written
    atomically (temp file -> fsync -> os.replace); the canonical file is
    READ-ONLY here and is never modified;
  * retention: keeps the newest backup of each of the last --keep-daily
    distinct calendar days (UTC) and the newest backup of each of the last
    --keep-weekly distinct ISO weeks; deletes the rest;
  * --dry-run prints the plan and changes nothing;
  * exit 0 on success, exit 1 with a human-readable message on error;
  * stdlib only; idempotent (a second run in the same second/minute simply
    overwrites the same timestamped copy).

Files in --dir whose names do not match the backup pattern are never
touched.
"""

from __future__ import annotations

import argparse
import os
import re
import shutil
import sys
import tempfile
from datetime import datetime, timezone

PREFIX = "[rotate_backups]"
BACKUP_NAME_RE = re.compile(r"^scraped_(\d{8})_(\d{6})\.json$")


class _Parser(argparse.ArgumentParser):
    """ArgumentParser that exits with code 1 (our error code) on bad args."""

    def error(self, message: str):  # noqa: D102
        self.print_usage(sys.stderr)
        print(f"{PREFIX} error: {message}", file=sys.stderr)
        raise SystemExit(1)


def log(message: str) -> None:
    print(f"{PREFIX} {message}", flush=True)


def err(message: str) -> None:
    print(f"{PREFIX} error: {message}", file=sys.stderr, flush=True)


def parse_backup_time(name: str) -> datetime | None:
    """UTC datetime encoded in a backup filename, or None if not parseable."""
    match = BACKUP_NAME_RE.match(name)
    if not match:
        return None
    try:
        stamp = datetime.strptime(
            f"{match.group(1)}_{match.group(2)}", "%Y%m%d_%H%M%S"
        )
    except ValueError:
        return None
    return stamp.replace(tzinfo=timezone.utc)


def atomic_copy(src: str, dest: str) -> None:
    """Copy src -> dest atomically: temp file, fsync, os.replace."""
    dest_dir = os.path.dirname(os.path.abspath(dest)) or "."
    fd, tmp_path = tempfile.mkstemp(
        prefix=".rotate_tmp_", suffix=".json", dir=dest_dir
    )
    os.close(fd)
    try:
        shutil.copyfile(src, tmp_path)
        if os.path.getsize(tmp_path) != os.path.getsize(src):
            raise OSError("size mismatch after copy")
        with open(tmp_path, "r+b") as handle:
            os.fsync(handle.fileno())
        os.replace(tmp_path, dest)
    except BaseException:
        try:
            os.unlink(tmp_path)
        except OSError:
            pass
        raise


def list_backups(backup_dir: str) -> tuple[list[tuple[str, datetime]], list[str]]:
    """Return ([(name, utc_datetime), ...], [unrecognized_name, ...])."""
    entries: list[tuple[str, datetime]] = []
    unrecognized: list[str] = []
    names = sorted(os.listdir(backup_dir)) if os.path.isdir(backup_dir) else []
    for name in names:
        when = parse_backup_time(name)
        if when is None:
            unrecognized.append(name)
        else:
            entries.append((name, when))
    return entries, unrecognized


def select_kept(
    entries: list[tuple[str, datetime]], keep_daily: int, keep_weekly: int
) -> dict[str, str]:
    """Newest backup per calendar day (last N distinct days) and per ISO week
    (last N distinct weeks). Returns {name: reason}."""
    newest_per_day: dict = {}
    newest_per_week: dict = {}
    for name, when in sorted(entries, key=lambda item: item[1], reverse=True):
        newest_per_day.setdefault(when.date(), name)
        iso = when.isocalendar()
        newest_per_week.setdefault((iso[0], iso[1]), name)

    kept: dict[str, str] = {}
    for day in sorted(newest_per_day, reverse=True)[:keep_daily]:
        kept[newest_per_day[day]] = f"daily {day.isoformat()}"
    for week in sorted(newest_per_week, reverse=True)[:keep_weekly]:
        kept.setdefault(newest_per_week[week], f"weekly ISO {week[0]}-W{week[1]:02d}")
    return kept


def build_parser() -> _Parser:
    parser = _Parser(
        prog="rotate_backups.py",
        description=(
            "Rotate timestamped backups of the canonical dataset "
            "(newest per day x --keep-daily, newest per ISO week x --keep-weekly)."
        ),
    )
    parser.add_argument("--file", required=True, help="canonical file to back up (read-only)")
    parser.add_argument("--dir", required=True, help="backup directory")
    parser.add_argument("--keep-daily", type=int, default=7, help="distinct days to keep (default 7)")
    parser.add_argument("--keep-weekly", type=int, default=8, help="distinct ISO weeks to keep (default 8)")
    parser.add_argument("--dry-run", action="store_true", help="print the plan; change nothing")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)

    if args.keep_daily < 0 or args.keep_weekly < 0:
        err("--keep-daily and --keep-weekly must be >= 0")
        return 1
    if not os.path.isfile(args.file):
        err(f"source file not found: {args.file}")
        return 1

    src = args.file
    backup_dir = args.dir
    src_size = os.path.getsize(src)
    now = datetime.now(timezone.utc)
    new_name = f"scraped_{now.strftime('%Y%m%d_%H%M%S')}.json"
    new_path = os.path.join(backup_dir, new_name)

    if os.path.abspath(src) == os.path.abspath(new_path):
        err("refusing to back up a file onto itself")
        return 1

    try:
        entries, unrecognized = list_backups(backup_dir)
    except OSError as exc:
        err(f"cannot list {backup_dir}: {exc}")
        return 1

    existing_names = {name for name, _ in entries}
    if new_name not in existing_names:
        entries.append((new_name, now))  # the copy this run creates/reuses

    kept = select_kept(entries, args.keep_daily, args.keep_weekly)
    deletions = sorted(
        (name for name, _ in entries if name not in kept), reverse=True
    )

    if args.dry_run:
        log("DRY RUN — nothing will be written or deleted")
        log(f"source: {src} ({src_size} bytes)")
        verb = "would reuse" if new_name in existing_names else "would write"
        log(f"{verb}: {new_path}")
        for name in sorted(kept):
            log(f"would keep:    {name} ({kept[name]})")
        for name in deletions:
            log(f"would delete:  {name} (superseded)")
        for name in unrecognized:
            log(f"would skip:    {name} (name does not match backup pattern)")
        log(f"plan: {len(kept)} kept, {len(deletions)} deleted, "
            f"{len(unrecognized)} skipped")
        return 0

    # --- real run ---------------------------------------------------------
    try:
        os.makedirs(backup_dir, exist_ok=True)
        atomic_copy(src, new_path)
    except OSError as exc:
        err(f"failed to write {new_path}: {exc}")
        return 1
    verb = "reused" if new_name in existing_names else "wrote"
    log(f"{verb}: {new_path} ({src_size} bytes, atomic)")

    for name in sorted(kept):
        log(f"keep:    {name} ({kept[name]})")

    failed: list[str] = []
    for name in deletions:
        try:
            os.remove(os.path.join(backup_dir, name))
            log(f"delete:  {name} (superseded)")
        except FileNotFoundError:
            continue
        except OSError as exc:
            failed.append(f"{name}: {exc}")
    for name in unrecognized:
        log(f"skip:    {name} (name does not match backup pattern)")

    if failed:
        for line in failed:
            err(f"could not delete {line}")
        return 1

    log(f"done: {len(kept)} kept, {len(deletions)} deleted")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        err("interrupted")
        sys.exit(1)
