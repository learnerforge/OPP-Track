"""
publish_dataset.py — the single publish command (E3, fullstack.md §11.4/§11.6/§14.4).

One command = validate -> sanity gate -> manifest -> atomic writes -> published
asset -> backup rotation -> publish report. Sole writer of data/manifest.json,
data/reports/publish-*.md and public/data/* (§14.3).

Usage:
    python scripts/publish_dataset.py                 # full guarded publish
    python scripts/publish_dataset.py --with-seeds    # + regenerate the bundled
                                                      #   SEED_DATA snapshot (CI)
    python scripts/publish_dataset.py --skip-validator  # bypass node validator
    python scripts/publish_dataset.py --skip-gate        # bypass sanity gate

Exit codes:
    0  published, OR no changes (idempotent skip)
    1  validation / sanity-gate failure (nothing was published), or a required
       tool (validator, gate) missing while its skip flag was NOT passed
    2  publish artifacts were written but a post-publish step (backup
       rotation) failed — see the report

Idempotence: if the canonical file's sha256 equals the previous manifest's,
prints "no changes — publish skipped (sha256 <sha8>)" and writes NOTHING.

Stdlib only. Every write is atomic: temp file in the destination directory,
flush + fsync, then os.replace (control #3, §11.3).
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import subprocess
import sys
import tempfile
import time
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = PROJECT_ROOT / "data"
CANONICAL_FILE = DATA_DIR / "scraped_opportunities.json"
MANIFEST_FILE = DATA_DIR / "manifest.json"
REPORTS_DIR = DATA_DIR / "reports"
BACKUPS_DIR = DATA_DIR / "backups"
PUBLIC_DATA_DIR = PROJECT_ROOT / "public" / "data"
VALIDATOR = PROJECT_ROOT / "scripts" / "validate-data.mjs"
SANITY_GATE = PROJECT_ROOT / "scripts" / "sanity_gate.py"
ROTATE_BACKUPS = PROJECT_ROOT / "scripts" / "rotate_backups.py"
REGENERATE_SEEDS = PROJECT_ROOT / "scripts" / "regenerate_seeds.py"
STORAGE_TS = PROJECT_ROOT / "src" / "lib" / "storage.ts"

SCHEMA_VERSION = 1
SEED_VERSION_RE = re.compile(r"export const SEED_VERSION = (\d+);")
VALIDATOR_VERSION_RE = re.compile(r"VALIDATOR_VERSION\s*=\s*['\"]([^'\"]+)['\"]")


# --------------------------------------------------------------------------- helpers


def now_utc() -> datetime:
    return datetime.now(timezone.utc)


def iso_utc(ts: datetime) -> str:
    return ts.strftime("%Y-%m-%dT%H:%M:%SZ")


def atomic_write_bytes(path: Path, payload: bytes) -> None:
    """Temp file in the same directory -> flush -> fsync -> os.replace (§11.3 #3)."""
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_name = tempfile.mkstemp(dir=str(path.parent), prefix=f".{path.name}.", suffix=".tmp")
    try:
        with os.fdopen(fd, "wb") as fh:
            fh.write(payload)
            fh.flush()
            os.fsync(fh.fileno())
        os.replace(tmp_name, str(path))
    except BaseException:
        try:
            os.unlink(tmp_name)
        except OSError:
            pass
        raise


def atomic_write_text(path: Path, text: str) -> None:
    atomic_write_bytes(path, text.encode("utf-8"))


def run_step(cmd: list[str], label: str) -> subprocess.CompletedProcess:
    print(f"[publish] {label}: {' '.join(cmd)}")
    proc = subprocess.run(cmd, cwd=str(PROJECT_ROOT), capture_output=True, text=True, encoding="utf-8", errors="replace")
    tail = (proc.stdout or "").strip().splitlines()[-6:]
    for line in tail:
        print(f"    {line}")
    if proc.returncode != 0 and proc.stderr:
        for line in proc.stderr.strip().splitlines()[-8:]:
            print(f"    ERR {line}")
    return proc


def read_seed_version() -> str | None:
    """Parse SEED_VERSION from src/lib/storage.ts WITHOUT editing it (read-only)."""
    try:
        m = SEED_VERSION_RE.search(STORAGE_TS.read_text(encoding="utf-8"))
        return m.group(1) if m else None
    except OSError:
        return None


def read_validator_version() -> str:
    """Prefer an explicit VALIDATOR_VERSION constant; else content-hash the validator."""
    try:
        src = VALIDATOR.read_text(encoding="utf-8")
    except OSError:
        return "unknown"
    m = VALIDATOR_VERSION_RE.search(src)
    if m:
        return m.group(1)
    return "sha256:" + hashlib.sha256(src.encode("utf-8")).hexdigest()[:8]


def git_head() -> str:
    """Best-effort HEAD commit for provenance; never fatal."""
    try:
        proc = subprocess.run(
            ["git", "rev-parse", "HEAD"], cwd=str(PROJECT_ROOT),
            capture_output=True, text=True, encoding="utf-8", errors="replace",
        )
        if proc.returncode == 0:
            return proc.stdout.strip()
    except OSError:
        pass
    return "unknown"


def item_key(item: dict) -> str:
    """Stable identity: explicit id if present, else the fingerprint hash (B6/B24)."""
    return str(item.get("id") or item.get("fingerprint") or "")


def find_previous_items(prev_manifest: dict | None) -> tuple[list[dict] | None, str]:
    """Previous dataset for the id-level diff: published asset first, then newest backup."""
    if not prev_manifest:
        return None, "none (no previous manifest — initial publish)"
    sha8 = prev_manifest.get("published_sha8", "")
    published = prev_manifest.get("published_file", "")
    if published:
        asset = PUBLIC_DATA_DIR / published
        if asset.is_file():
            try:
                return json.loads(asset.read_text(encoding="utf-8")), f"public/data/{published}"
            except (OSError, json.JSONDecodeError):
                pass
    if sha8:
        asset = PUBLIC_DATA_DIR / f"opportunities.{sha8}.json"
        if asset.is_file():
            try:
                return json.loads(asset.read_text(encoding="utf-8")), f"public/data/{asset.name}"
            except (OSError, json.JSONDecodeError):
                pass
    if BACKUPS_DIR.is_dir():
        backups = sorted(BACKUPS_DIR.glob("*.json"), key=lambda p: p.stat().st_mtime, reverse=True)
        for b in backups:
            try:
                return json.loads(b.read_text(encoding="utf-8")), f"data/backups/{b.name}"
            except (OSError, json.JSONDecodeError):
                continue
    return None, "none (previous dataset not found on disk)"


def build_report(
    ts: datetime,
    validation: str,
    gate: str,
    items: list[dict],
    manifest: dict,
    prev_manifest: dict | None,
    prev_items: list[dict] | None,
    prev_source: str,
    rotation: str,
    seeds: str,
) -> str:
    type_hist = manifest["type_histogram"]
    src_counts = manifest["per_source_counts"]

    lines = [
        f"# Publish report — {iso_utc(ts)}",
        "",
        "## Gates",
        "",
        f"- **Validation** (`node scripts/validate-data.mjs data/scraped_opportunities.json`): {validation}",
        f"- **Sanity gate** (`python scripts/sanity_gate.py --current data/scraped_opportunities.json "
        f"--previous data/manifest.json --allow-init`): {gate}",
        "",
        "## Dataset",
        "",
        f"- items: **{manifest['item_count']}**",
        f"- rolling (deadline == ''): **{manifest['rolling_count']}**",
        f"- sha256: `{manifest['sha256']}`",
        f"- published: `public/data/{manifest['published_file']}` (sha8 `{manifest['published_sha8']}`, byte-identical)",
        f"- seed_version: {manifest['seed_version']}  ·  validator_version: {manifest['validator_version']}",
        f"- git_commit: `{manifest['git_commit']}`  ·  duration_s: {manifest['duration_s']}",
        "",
        "### Per type",
        "",
        "| type | count |",
        "|---|---|",
    ]
    for t in sorted(type_hist):
        lines.append(f"| {t} | {type_hist[t]} |")
    lines += ["", "### Per source", "", "| source | count |", "|---|---|"]
    for s in sorted(src_counts, key=lambda k: (-src_counts[k], k)):
        lines.append(f"| {s} | {src_counts[s]} |")

    lines += ["", "## Diff vs previous publish", "", f"Previous dataset: {prev_source}"]
    if prev_items is None:
        lines.append("")
        lines.append("_No previous dataset available — id-level diff skipped (initial publish)._")
    else:
        old_by_key = {item_key(i): i for i in prev_items}
        new_by_key = {item_key(i): i for i in items}
        added = sorted(k for k in new_by_key if k not in old_by_key)
        removed = sorted(k for k in old_by_key if k not in new_by_key)
        changed = sorted(
            k for k in (set(old_by_key) & set(new_by_key))
            if json.dumps(old_by_key[k], sort_keys=True, ensure_ascii=False)
            != json.dumps(new_by_key[k], sort_keys=True, ensure_ascii=False)
        )

        def titles(keys: list[str], mapping: dict[str, dict]) -> list[str]:
            out = []
            for k in keys[:40]:
                it = mapping.get(k, {})
                out.append(f"  - `{k}` {it.get('title', '?')} ({it.get('source', '?')})")
            if len(keys) > 40:
                out.append(f"  - … and {len(keys) - 40} more")
            return out

        lines += [
            "",
            f"- previous total: {len(prev_items)} → new total: {len(items)} (delta {len(items) - len(prev_items):+d})",
            f"- **added: {len(added)}**",
            *titles(added, new_by_key),
            f"- **removed: {len(removed)}**",
            *titles(removed, old_by_key),
            f"- **changed: {len(changed)}**",
            *titles(changed, new_by_key),
        ]
        if prev_manifest and isinstance(prev_manifest.get("per_source_counts"), dict):
            prev_src = prev_manifest["per_source_counts"]
            keys = sorted(set(prev_src) | set(src_counts))
            deltas = [(s, src_counts.get(s, 0) - prev_src.get(s, 0)) for s in keys]
            deltas = [d for d in deltas if d[1] != 0]
            lines += ["", "### Per-source deltas", "", "| source | Δ |", "|---|---|"]
            for s, d in sorted(deltas, key=lambda x: (-abs(x[1]), x[0])):
                lines.append(f"| {s} | {d:+d} |")
            if not deltas:
                lines.append("| — | 0 (no per-source change) |")

    lines += [
        "",
        "## Post-publish",
        "",
        f"- backup rotation: {rotation}",
        f"- bundled snapshot regeneration: {seeds}",
        "",
        "Sole writer: `scripts/publish_dataset.py` (§14.3). Canonical bytes are copied "
        "byte-identically to `public/data/` under the immutable `opportunities.<sha8>.json` name (control #12).",
        "",
    ]
    return "\n".join(lines)


# --------------------------------------------------------------------------- main


def main() -> int:
    parser = argparse.ArgumentParser(description="Publish the dataset: validate -> gate -> manifest -> assets -> report")
    parser.add_argument("--with-seeds", action="store_true",
                        help="also run scripts/regenerate_seeds.py to refresh the bundled snapshot (CI)")
    parser.add_argument("--skip-validator", action="store_true",
                        help="bypass the node validator (development only)")
    parser.add_argument("--skip-gate", action="store_true",
                        help="bypass the sanity/regression gate (development only)")
    args = parser.parse_args()

    t0 = time.perf_counter()
    ts = now_utc()

    # --- 0. read the canonical dataset ------------------------------------
    if not CANONICAL_FILE.is_file():
        print(f"[publish] ERROR: canonical dataset not found: {CANONICAL_FILE}", file=sys.stderr)
        return 1
    raw = CANONICAL_FILE.read_bytes()
    try:
        items = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        print(f"[publish] ERROR: canonical dataset is not valid JSON: {exc}", file=sys.stderr)
        return 1
    if not isinstance(items, list):
        print("[publish] ERROR: canonical dataset must be a JSON array (§11.2)", file=sys.stderr)
        return 1

    # --- a. validate-before-publish (control #4) --------------------------
    if args.skip_validator:
        validation_result = "SKIPPED (--skip-validator)"
        print("[publish] WARNING: validation SKIPPED via --skip-validator — do not use in CI")
    else:
        if not VALIDATOR.is_file():
            print(f"[publish] ERROR: validator not found: {VALIDATOR}", file=sys.stderr)
            print("[publish] Nothing was published. (Pass --skip-validator to bypass during development.)", file=sys.stderr)
            return 1
        proc = run_step(["node", str(VALIDATOR), str(CANONICAL_FILE)], "validate")
        if proc.returncode != 0:
            validation_result = "FAILED"
            print("[publish] ERROR: validation failed — nothing published (exit 1)", file=sys.stderr)
            return 1
        validation_result = "PASSED"

    # --- b. sanity/regression gate (control #5) ---------------------------
    if args.skip_gate:
        gate_result = "SKIPPED (--skip-gate)"
        print("[publish] WARNING: sanity gate SKIPPED via --skip-gate — do not use in CI")
    else:
        if not SANITY_GATE.is_file():
            print(f"[publish] ERROR: sanity gate not found: {SANITY_GATE}", file=sys.stderr)
            print("[publish] Nothing was published. It is being written by a companion agent — "
                  "re-run when it lands, or pass --skip-gate to bypass during development.", file=sys.stderr)
            return 1
        proc = run_step(
            [sys.executable, str(SANITY_GATE),
             "--current", str(CANONICAL_FILE),
             "--previous", str(MANIFEST_FILE),
             "--allow-init"],
            "sanity gate",
        )
        if proc.returncode != 0:
            gate_result = "FAILED"
            print("[publish] ERROR: sanity gate failed — nothing published (exit 1)", file=sys.stderr)
            return 1
        gate_result = "PASSED"

    # --- c. sha256 of the exact canonical bytes + idempotence check -------
    sha256 = hashlib.sha256(raw).hexdigest()
    sha8 = sha256[:8]

    prev_manifest: dict | None = None
    if MANIFEST_FILE.is_file():
        try:
            prev_manifest = json.loads(MANIFEST_FILE.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            prev_manifest = None

    if prev_manifest and prev_manifest.get("sha256") == sha256:
        print(f"no changes — publish skipped (sha256 {sha8})")
        return 0

    type_hist = dict(sorted(Counter(str(i.get("type", "")) for i in items).items()))
    src_counts = dict(sorted(Counter(str(i.get("source", "")) for i in items).items()))
    rolling = sum(1 for i in items if i.get("deadline", "") == "")

    manifest = {
        "schema_version": SCHEMA_VERSION,
        "generated_at": iso_utc(ts),
        "item_count": len(items),
        "type_histogram": type_hist,
        "per_source_counts": src_counts,
        "rolling_count": rolling,
        "sha256": sha256,
        "published_sha8": sha8,
        "published_file": f"opportunities.{sha8}.json",
        "git_commit": git_head(),
        "duration_s": round(time.perf_counter() - t0, 3),
        "seed_version": read_seed_version(),
        "validator_version": read_validator_version(),
    }

    # --- d. atomic writes: manifest + published asset + public manifest ---
    manifest_bytes = (json.dumps(manifest, indent=2, ensure_ascii=False) + "\n").encode("utf-8")
    atomic_write_bytes(MANIFEST_FILE, manifest_bytes)
    atomic_write_bytes(PUBLIC_DATA_DIR / manifest["published_file"], raw)   # byte-identical (control #12)
    atomic_write_bytes(PUBLIC_DATA_DIR / "manifest.json", manifest_bytes)
    print(f"[publish] wrote data/manifest.json (sha256 {sha8}, {manifest['item_count']} items)")
    print(f"[publish] wrote public/data/{manifest['published_file']} + public/data/manifest.json")

    # --- f. backup rotation (invokes companion #1's rotator, never reimpl) -
    if ROTATE_BACKUPS.is_file():
        proc = run_step(
            [sys.executable, str(ROTATE_BACKUPS),
             "--file", str(CANONICAL_FILE),
             "--dir", str(BACKUPS_DIR),
             "--keep-daily", "7",
             "--keep-weekly", "8"],
            "rotate backups",
        )
        rotation_result = "PASSED" if proc.returncode == 0 else f"FAILED (exit {proc.returncode})"
        rotation_failed = proc.returncode != 0
    else:
        rotation_result = "SKIPPED — scripts/rotate_backups.py not found (companion #1 owns it)"
        rotation_failed = False
        print("[publish] WARNING: backup rotation skipped — scripts/rotate_backups.py not present yet")

    # --- g. optional bundled-snapshot regeneration (never in dev waves) ---
    if args.with_seeds:
        if REGENERATE_SEEDS.is_file():
            proc = run_step([sys.executable, str(REGENERATE_SEEDS)], "regenerate seeds")
            seeds_result = "PASSED" if proc.returncode == 0 else f"FAILED (exit {proc.returncode})"
        else:
            seeds_result = "SKIPPED — scripts/regenerate_seeds.py not found"
    else:
        seeds_result = "not requested (run with --with-seeds)"

    # --- e. publish report (§11.2 / /api/report/latest) -------------------
    prev_items, prev_source = find_previous_items(prev_manifest)
    report = build_report(ts, validation_result, gate_result, items, manifest,
                          prev_manifest, prev_items, prev_source, rotation_result, seeds_result)
    stamp = ts.strftime("%Y%m%d-%H%M%S")
    report_path = REPORTS_DIR / f"publish-{stamp}.md"
    atomic_write_text(report_path, report)
    print(f"[publish] wrote data/reports/{report_path.name}")

    print(f"[publish] done in {round(time.perf_counter() - t0, 2)}s — sha256 {sha8}, "
          f"{manifest['item_count']} items, {len(src_counts)} sources, {rolling} rolling")
    if rotation_failed:
        print("[publish] ERROR: publish succeeded but backup rotation failed — see report", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
