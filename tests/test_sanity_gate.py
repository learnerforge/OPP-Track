"""Tests for scripts/sanity_gate.py (milestone E2 — plan 11.3 control 5 / B18).

Stdlib ``unittest`` only (pytest is not installed and may not be added —
documented deviation from plan 4/B19, which suggested pytest).

Run:  python -m unittest discover -s tests -p "test_*.py"
"""
import importlib.util
import json
import sys
import tempfile
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = REPO_ROOT / "scripts" / "sanity_gate.py"

_spec = importlib.util.spec_from_file_location("sanity_gate", MODULE_PATH)
sanity_gate = importlib.util.module_from_spec(_spec)
sys.modules["sanity_gate"] = sanity_gate  # required so @dataclass resolves annotations
_spec.loader.exec_module(sanity_gate)

SOURCES = ("Alpha", "Beta", "Gamma", "Delta")
TYPES = ("Hackathon", "Internship", "Certification", "Competition")


def make_item(
    i,
    *,
    item_type=None,
    deadline="2026-12-01",
    link=None,
    source=None,
    fingerprint=None,
    item_id=None,
    title=None,
):
    """One contract-shaped opportunity (raw-scrape shape: fingerprint, no status)."""
    item = {
        "title": f"Opportunity {i}" if title is None else title,
        "type": TYPES[i % len(TYPES)] if item_type is None else item_type,
        "source": SOURCES[i % len(SOURCES)] if source is None else source,
        "link": f"https://example.com/o/{i}" if link is None else link,
        "deadline": deadline,
        "eligibility": "Open to all",
        "tags": ["tag"],
        "notes": "",
        "date_added": "2026-10-19",
        "fingerprint": f"fp{i:06d}" if fingerprint is None else fingerprint,
    }
    if item_id is not None:
        item["id"] = item_id
    return item


def make_items(n, **kwargs):
    return [make_item(i, **kwargs) for i in range(n)]


def per_source_counts(items):
    counts = {}
    for item in items:
        counts[item["source"]] = counts.get(item["source"], 0) + 1
    return counts


class SanityGateTest(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory(prefix="opp-track-gate-")
        self.addCleanup(tmp.cleanup)
        self.tmp = Path(tmp.name)
        self.data_dir = self.tmp / "data"
        self.data_dir.mkdir()
        self.current = self.data_dir / "scraped_opportunities.json"
        self.previous = self.data_dir / "manifest.json"

    # -- helpers ---------------------------------------------------------- #
    def write_current(self, items):
        self.current.write_text(json.dumps(items), encoding="utf-8")
        return self.current

    def write_manifest(self, items=None, item_count=None, per_source=None):
        payload = {}
        if item_count is not None:
            payload["item_count"] = item_count
        elif items is not None:
            payload["item_count"] = len(items)
        if per_source is not None:
            payload["per_source_counts"] = per_source
        elif items is not None:
            payload["per_source_counts"] = per_source_counts(items)
        self.previous.write_text(json.dumps(payload), encoding="utf-8")
        return self.previous

    def gate(self, allow_init=False, previous=None):
        return sanity_gate.run_gate(
            str(self.current),
            previous_path=str(previous if previous is not None else self.previous),
            allow_init=allow_init,
        )

    def cli(self, *extra):
        args = ["--current", str(self.current), "--previous", str(self.previous)]
        return sanity_gate.main(list(args) + list(extra))

    # -- absolute checks --------------------------------------------------- #
    def test_sane_data_passes(self):
        items = make_items(40)
        items[0]["deadline"] = ""  # rolling/evergreen is valid
        items[1]["link"] = ""  # absent link is valid (never fabricated)
        self.write_current(items)
        self.write_manifest(items)

        result = self.gate()
        self.assertTrue(result.ok, msg=result.errors)
        self.assertEqual(result.item_count, 40)
        self.assertEqual(result.baseline_count, 40)
        self.assertEqual(self.cli(), 0)

    def test_empty_file_rejected(self):
        self.write_current([])
        result = self.gate(allow_init=True)
        self.assertFalse(result.ok)
        self.assertTrue(any("empty" in e for e in result.errors), msg=result.errors)
        self.assertEqual(self.cli("--allow-init"), 1)

    def test_unknown_type_rejected(self):
        items = make_items(40)
        items[7]["type"] = "Scholarship"
        self.write_current(items)
        self.write_manifest(items)

        result = self.gate()
        self.assertFalse(result.ok)
        self.assertTrue(any("invalid type 'Scholarship'" in e for e in result.errors), msg=result.errors)

    def test_malformed_deadline_rejected(self):
        items = make_items(40)
        items[3]["deadline"] = "soon"  # neither '' nor YYYY-MM-DD
        items[9]["deadline"] = "2026-13-45"  # ISO-shaped but not a real date
        self.write_current(items)
        self.write_manifest(items)

        result = self.gate()
        self.assertFalse(result.ok)
        deadline_errors = [e for e in result.errors if "deadline" in e]
        self.assertEqual(len(deadline_errors), 2, msg=result.errors)

    def test_junk_link_rejected(self):
        items = make_items(40)
        items[5]["link"] = "not-a-url-at-all"
        self.write_current(items)
        self.write_manifest(items)

        result = self.gate()
        self.assertFalse(result.ok)
        self.assertTrue(any("not a valid http(s) URL" in e for e in result.errors), msg=result.errors)

    def test_duplicate_ids_rejected(self):
        # identity via fingerprint (raw scrape shape)
        items = make_items(40)
        items[12]["fingerprint"] = items[4]["fingerprint"]
        self.write_current(items)
        self.write_manifest(items)
        result = self.gate()
        self.assertFalse(result.ok)
        self.assertTrue(any("duplicate id" in e for e in result.errors), msg=result.errors)

        # identity via id (seed shape)
        items = make_items(40)
        for i, item in enumerate(items):
            item["id"] = f"seed_{i:04d}"
        items[20]["id"] = items[10]["id"]
        self.write_current(items)
        self.write_manifest(items)
        result = self.gate()
        self.assertFalse(result.ok)
        self.assertTrue(any("duplicate id" in e for e in result.errors), msg=result.errors)

    def test_degenerate_type_histogram_rejected(self):
        items = make_items(50, item_type="Internship")  # 100% one type
        self.write_current(items)
        result = self.gate(allow_init=True)
        self.assertFalse(result.ok)
        self.assertTrue(any("degenerate" in e for e in result.errors), msg=result.errors)

    # -- baseline / regression checks -------------------------------------- #
    def test_60_percent_collapse_rejected(self):
        baseline = make_items(100)
        self.write_manifest(baseline)  # item_count=100, 25 per source
        self.write_current(make_items(40))  # 40 items = -60%, 10 per source = -60%

        result = self.gate()
        self.assertFalse(result.ok)
        self.assertTrue(any("total count regressed" in e for e in result.errors), msg=result.errors)
        self.assertTrue(any("regressed" in e and "source" in e for e in result.errors), msg=result.errors)
        self.assertEqual(self.cli(), 1)

    def test_within_tolerance_passes(self):
        baseline = make_items(100)
        self.write_manifest(baseline)
        self.write_current(make_items(85))  # -15% total, sources -15%: inside both tolerances
        result = self.gate()
        self.assertTrue(result.ok, msg=result.errors)

    def test_no_baseline_fails_without_allow_init(self):
        self.write_current(make_items(40))
        # no manifest, no backups/
        result = self.gate(allow_init=False)
        self.assertFalse(result.ok)
        self.assertTrue(any("--allow-init" in e for e in result.errors), msg=result.errors)

    def test_allow_init_runs_absolute_checks_only(self):
        items = make_items(40)
        self.write_current(items)
        # no manifest, no backups/ -> absolute checks only
        result = self.gate(allow_init=True)
        self.assertTrue(result.ok, msg=result.errors)
        self.assertIsNone(result.baseline_count)
        self.assertEqual(self.cli("--allow-init"), 0)

        # ...but absolute failures still fail the gate under --allow-init
        items[0]["type"] = "Fellowship"
        self.write_current(items)
        result = self.gate(allow_init=True)
        self.assertFalse(result.ok)

    def test_backup_fallback_baseline(self):
        backup_dir = self.data_dir / "backups"
        backup_dir.mkdir()
        baseline = make_items(100)
        (backup_dir / "scraped_20260101_000000.json").write_text(
            json.dumps(baseline), encoding="utf-8"
        )
        # no manifest -> falls back to newest backup
        self.write_current(make_items(40))  # -60% vs backup
        result = self.gate()
        self.assertFalse(result.ok)
        self.assertIn("backup", result.baseline_source)
        self.assertEqual(result.baseline_count, 100)
        self.assertTrue(any("total count regressed" in e for e in result.errors), msg=result.errors)

        self.write_current(make_items(100))
        result = self.gate()
        self.assertTrue(result.ok, msg=result.errors)

    # -- integrity ---------------------------------------------------------- #
    def test_gate_reads_but_never_writes(self):
        items = make_items(40)
        self.write_current(items)
        self.write_manifest(items)
        backups_dir = self.data_dir / "backups"
        backups_dir.mkdir()
        backup = backups_dir / "scraped_20260101_000000.json"
        backup.write_text(json.dumps(make_items(100)), encoding="utf-8")

        watched = [self.current, self.previous, backup]
        before = [(p.read_bytes(), p.stat().st_mtime_ns) for p in watched]

        result = self.gate()
        self.assertTrue(result.ok, msg=result.errors)

        after = [(p.read_bytes(), p.stat().st_mtime_ns) for p in watched]
        self.assertEqual(before, after, "the gate must never modify the files it reads")


if __name__ == "__main__":
    unittest.main()
