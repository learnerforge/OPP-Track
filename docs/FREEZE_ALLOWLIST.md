# `src/` freeze allowlist — Exception B

This file is read by [`scripts/check_freeze.py`](../scripts/check_freeze.py),
which runs in `.github/workflows/verify.yml` on every push and pull request.
It is the **only** way a change to `src/` other than the generator-written
`src/lib/storage.ts` can pass CI. The freeze itself is defined in
`fullstack.md` §14.1; the E6 patch that will use this file is §14.8 item 3.

## How the checker parses this file

- Blank lines and lines whose first non-space character is `#` are **ignored**
  (comments — inactive).
- A missing file means **zero** Exception B entries: the freeze is strict.
- A remaining line is an **active entry** only if, after stripping one leading
  `- ` list marker, it *starts with* `src/` or a glob prefix (`*` / `?`): an
  exact path or a glob, compared case-sensitively against the `/`-separated
  path git reports.
  - `*` matches any characters, including `/`
  - `?` matches exactly one character
  - entries are written as bare paths — no backticks, no list prose after them
- Everything else — prose, headings, table rows, fence markers — is ignored,
  so narrative in this file can never silently become an allowance. Keep any
  illustrative `src/...` paths in prose backticked or on `#` comment lines.

The checker's default mode inspects **committed ranges only**
(`git diff base...head -- src/`); it never flags uncommitted local work unless
you explicitly pass `--worktree`.

## Exception A — not in this file (built into the checker)

`src/lib/storage.ts` may change, but **only** as a write of
`scripts/regenerate_seeds.py` (the sole generator writer, §14.3). The checker
allows that path unconditionally; `verify.yml` additionally runs `typecheck`,
`npm test` (23 tests import the real bundled module) and the build, so a
malformed generator write still cannot merge. Do not add it below.

## Exception B — the E6 patch (§11.10 / §14.8 item 3)

Today this file contains **no active entries**: the freeze is strict. The
planned E6 patch (F1/F2 fixes + stage-2 runtime fetch) is staged below as
commented-out pending lines. **Uncomment exactly the paths the E6 patch touches
when it lands, and remove them again once E6 merges**, so the freeze returns to
strict (the E6 acceptance criterion in §11.10).

```text
# PENDING E6: src/utils/date.ts            (F1: evergreen/rolling deadline presentation, kills "NaN days left")
# PENDING E6: src/utils/validation.ts      (F1/F2: validation guard around empty deadlines)
# PENDING E6: src/hooks/useReminders.ts     (F2: reminder guard, stops the notification storm)
# PENDING E6: src/lib/api.ts               (stage-2 runtime fetch: manifest-first loader, §11.5)
# PENDING E6: src/hooks/useOpportunities.ts (wires the ladder + cache into the data hook)
```

Note the fenced block above: entries inside a code fence are still parsed as
lines — keep them commented until E6 actually ships. If E6 ends up touching a
different file set, adjust the list to match reality rather than widening it to
`src/**`.

## Active entries

```text
(none — strict freeze, E5)
```

## Retiring entries

An entry that has served its milestone must be deleted, not left behind:
`verify.yml` treats this file like any other reviewed change, and an entry that
lingers silently lifts the freeze for that path forever. When in doubt, leave
the line commented and let CI fail loudly instead.
