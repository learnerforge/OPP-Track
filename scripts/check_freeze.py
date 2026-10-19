#!/usr/bin/env python3
"""Enforce the `src/` freeze — fullstack.md §14.1.

Rules
-----
* **Committed changes only** by default: the checked range is
  ``git diff --name-only <base>...<head> -- src/``. Uncommitted local work is
  NEVER flagged unless ``--worktree`` is passed (local checks).
* A changed path under ``src/`` is allowed only if
    1. it is ``src/lib/storage.ts`` — **Exception A**, written solely by
       ``scripts/regenerate_seeds.py`` (the generator writer), or
    2. it is matched by an **uncommented** entry in ``docs/FREEZE_ALLOWLIST.md``
       — **Exception B**, reserved for the E6 patch.
* Anything else is a violation: each one is printed with its reason and the
  script exits 1. A clean run prints the allowance summary and exits 0.

Base resolution: if ``--base`` (default ``origin/main``) does not resolve, the
script falls back through ``origin/main`` → ``origin/master`` → ``HEAD~1`` →
the git empty tree, warning about every substitution. ``origin/master`` is in
the chain because it is this repository's actual default branch.

Allowlist parsing (docs/FREEZE_ALLOWLIST.md): blank lines and lines whose first
non-space character is ``#`` are ignored. A remaining line is an active entry
only if, after stripping a single leading ``- `` list marker, it starts with
``src/`` or a glob prefix (``*`` / ``?``) — an exact path or a glob (``*`` =
any characters including ``/``; ``?`` = one character), matched case-sensitively
against the ``/``-separated git path. Everything else (prose, headings, table
rows, fenced markers) is ignored, so narrative text can never become an entry.

Exit codes: 0 = clean, 1 = freeze violation(s), 2 = usage / git error.

Usage:
    python scripts/check_freeze.py
    python scripts/check_freeze.py --base origin/master --head HEAD
    python scripts/check_freeze.py --worktree      # also check uncommitted work
"""

from __future__ import annotations

import argparse
import re
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]

EXCEPTION_A = "src/lib/storage.ts"
EXCEPTION_A_REASON = (
    "Exception A: generator-only file, sole writer scripts/regenerate_seeds.py "
    "(fullstack.md 14.1)"
)
DEFAULT_BASE = "origin/main"
DEFAULT_HEAD = "HEAD"
DEFAULT_ALLOWLIST = "docs/FREEZE_ALLOWLIST.md"
# Tried in order when the requested base does not resolve. origin/master is the
# repo's real default branch (the plan's origin/main does not exist yet).
FALLBACK_CHAIN = ("origin/main", "origin/master", "HEAD~1")
# git's well-known empty tree, used only if nothing in the chain resolves
# (e.g. a single-commit repository): every tracked src/ file is then "changed".
EMPTY_TREE_SHA = "4b825dc642cb6eb9a060e54bf8d69288fbee4904"


def _git(args: list[str], input_text: str | None = None) -> tuple[int, str, str]:
    """Run git in the repo root (no shell — safe for `^`, `~`, spaces)."""
    try:
        proc = subprocess.run(
            ["git", "-c", "core.quotepath=off", *args],
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            input=input_text,
        )
    except FileNotFoundError:
        print("check_freeze: git executable not found on PATH", file=sys.stderr)
        sys.exit(2)
    return proc.returncode, proc.stdout, proc.stderr


def _ref_is_commit(ref: str) -> bool:
    code, _, _ = _git(["rev-parse", "--verify", "--quiet", f"{ref}^{{commit}}"])
    return code == 0


def _short(ref: str) -> str:
    code, out, _ = _git(["rev-parse", "--short=8", ref])
    return out.strip() if code == 0 else ref


def resolve_base(requested: str) -> tuple[str, bool, list[str]]:
    """Return (base, base_is_commit, warnings); falls back through the chain."""
    warnings: list[str] = []
    candidates: list[str] = []
    for cand in (requested,) + FALLBACK_CHAIN:
        if cand and cand not in candidates:
            candidates.append(cand)
    for cand in candidates:
        if _ref_is_commit(cand):
            if cand != requested:
                warnings.append(
                    f"base {requested!r} does not resolve; using {cand!r} instead"
                )
            return cand, True, warnings
    warnings.append(
        f"neither {requested!r} nor any fallback ref resolves; "
        "comparing against the git empty tree (most conservative)"
    )
    code, out, _ = _git(["mktree"], input_text="")
    sha = out.strip() if code == 0 and out.strip() else EMPTY_TREE_SHA
    return sha, False, warnings


def _clean_paths(output: str) -> list[str]:
    seen: list[str] = []
    for line in output.splitlines():
        p = line.strip().replace("\\", "/")
        if p.startswith("src/") and p not in seen:
            seen.append(p)
    return seen


def committed_paths(base: str, head: str, base_is_commit: bool) -> tuple[list[str], list[str]]:
    """Paths changed under src/ in the committed range base..head."""
    warnings: list[str] = []
    if base_is_commit:
        code, out, err = _git(["diff", "--name-only", f"{base}...{head}", "--", "src/"])
        if code == 0:
            return _clean_paths(out), warnings
        warnings.append(
            f"three-dot diff {base}...{head} failed "
            f"({(err or '').strip() or f'exit {code}'}); retrying as a two-dot diff"
        )
    code, out, err = _git(["diff", "--name-only", base, head, "--", "src/"])
    if code != 0:
        print(
            f"check_freeze: git diff {base} {head} -- src/ failed:\n{(err or '').strip()}",
            file=sys.stderr,
        )
        sys.exit(2)
    return _clean_paths(out), warnings


def worktree_paths(head: str) -> list[str]:
    """Uncommitted (staged + unstaged + untracked) changes under src/."""
    code, out, err = _git(["diff", "--name-only", head, "--", "src/"])
    if code != 0:
        print(f"check_freeze: git diff {head} -- src/ failed:\n{(err or '').strip()}",
              file=sys.stderr)
        sys.exit(2)
    paths = _clean_paths(out)
    code, out, _ = _git(["ls-files", "--others", "--exclude-standard", "--", "src/"])
    if code == 0:
        for p in _clean_paths(out):
            if p not in paths:
                paths.append(p)
    return paths


def parse_allowlist(path: Path) -> tuple[list[tuple[int, str]], str | None]:
    """Return ([(lineno, pattern)], note).

    Active entries are uncommented lines that, after stripping one leading
    ``- `` list marker, start with ``src/`` or a glob prefix (``*`` / ``?``).
    Prose, headings, table rows and fences are ignored — narrative in the
    Markdown file can never silently become an allowance.
    """
    if not path.is_file():
        return [], (
            f"allowlist {path.name} not found at {path} - "
            "Exception B is unavailable, the freeze is strict"
        )
    entries: list[tuple[int, str]] = []
    text = path.read_text(encoding="utf-8-sig")
    for lineno, raw in enumerate(text.splitlines(), start=1):
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("- "):
            line = line[2:].strip()
            if not line or line.startswith("#"):
                continue
        if not line.startswith(("src/", "*", "?")):
            continue  # prose / heading / fence marker — not an entry
        entries.append((lineno, line))
    return entries, None


def _compile(pattern: str) -> re.Pattern[str]:
    """Case-sensitive glob → regex. `*` = any chars (incl. `/`), `?` = one char."""
    regex = "".join(
        ".*" if ch == "*" else "." if ch == "?" else re.escape(ch)
        for ch in pattern.replace("\\", "/")
    )
    return re.compile(f"^{regex}$")


def classify(paths: list[str], entries: list[tuple[int, str]],
             allowlist_label: str = DEFAULT_ALLOWLIST) -> tuple[list[tuple[str, str]], list[tuple[str, str]]]:
    """Split changed paths into (allowed, violations) with human reasons."""
    compiled = [(ln, pat, _compile(pat)) for ln, pat in entries]
    allowed: list[tuple[str, str]] = []
    violations: list[tuple[str, str]] = []
    for p in paths:
        if p == EXCEPTION_A:
            allowed.append((p, EXCEPTION_A_REASON))
            continue
        hit = next(((ln, pat) for ln, pat, rx in compiled if rx.fullmatch(p)), None)
        if hit is not None:
            allowed.append(
                (p, f"Exception B: matched allowlist line {hit[0]} (entry {hit[1]!r})")
            )
        else:
            violations.append(
                (
                    p,
                    f"changed under src/ but is neither {EXCEPTION_A} (Exception A) "
                    f"nor matched by any uncommented entry in {allowlist_label} "
                    "(Exception B)",
                )
            )
    return allowed, violations


def main(argv: list[str] | None = None) -> int:
    # Keep output readable when stdout is a pipe (CI logs); printed literals
    # are plain ASCII anyway so a non-UTF-8 reader can never be confused.
    for stream in (sys.stdout, sys.stderr):
        reconf = getattr(stream, "reconfigure", None)
        if reconf is not None:
            try:
                reconf(encoding="utf-8", errors="replace")
            except Exception:
                pass

    parser = argparse.ArgumentParser(
        description="Enforce the src/ freeze (fullstack.md 14.1). "
        "Committed range only unless --worktree is given."
    )
    parser.add_argument("--base", default=DEFAULT_BASE,
                        help=f"base ref of the checked range (default: {DEFAULT_BASE})")
    parser.add_argument("--head", default=DEFAULT_HEAD,
                        help=f"head ref of the checked range (default: {DEFAULT_HEAD})")
    parser.add_argument("--allowlist", default=DEFAULT_ALLOWLIST,
                        help="allowlist file (default: docs/FREEZE_ALLOWLIST.md); "
                             "relative paths are repo-root relative")
    parser.add_argument("--worktree", action="store_true",
                        help="ALSO check uncommitted changes in the working tree "
                             "(off by default so local work is never flagged)")
    args = parser.parse_args(argv)

    allowlist_path = Path(args.allowlist)
    if not allowlist_path.is_absolute():
        allowlist_path = REPO_ROOT / allowlist_path

    if not _ref_is_commit(args.head):
        print(f"check_freeze: --head {args.head!r} does not resolve to a commit",
              file=sys.stderr)
        return 2

    base, base_is_commit, warnings = resolve_base(args.base)
    paths, range_warnings = committed_paths(base, args.head, base_is_commit)
    warnings.extend(range_warnings)
    committed = list(paths)

    if args.worktree:
        for p in worktree_paths(args.head):
            if p not in committed:
                committed.append(p)

    entries, allowlist_note = parse_allowlist(allowlist_path)
    if allowlist_note:
        warnings.append(allowlist_note)

    allowed, violations = classify(committed, entries, args.allowlist)

    for w in warnings:
        print(f"check_freeze: warning: {w}")

    if violations:
        print(f"FREEZE VIOLATION - {len(violations)} path(s) changed under src/ "
              "without an exception (fullstack.md 14.1):")
        for path, reason in violations:
            print(f"  {path}")
            print(f"    reason: {reason}")
        print("Either revert the change, route it through the generator "
              "(scripts/regenerate_seeds.py), or add/uncomment an entry in "
              "docs/FREEZE_ALLOWLIST.md and justify it in review.")
        return 1

    print("src/ freeze check PASSED (fullstack.md 14.1)")
    base_desc = _short(base) if base_is_commit else "empty tree"
    print(f"  base:  {args.base if base == args.base else base} ({base_desc})")
    print(f"  head:  {args.head} ({_short(args.head)})")
    print(f"  committed src/ changes in range: {len(committed)}")
    print("  worktree check: "
          + ("ON (uncommitted changes included)" if args.worktree
             else "off (committed range only)"))
    print(f"  active allowlist entries: {len(entries)} in {args.allowlist}")
    if allowed:
        print("  allowances used in this range:")
        for path, reason in allowed:
            print(f"    {path} - {reason}")
    else:
        print("  allowances used in this range: none needed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
