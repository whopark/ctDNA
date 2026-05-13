"""
End-to-end test for `retier.py`. Builds a tiny annotated CSV in a temp dir,
runs retier in dry-run and apply modes, and verifies the file is correctly
preserved or rewritten.

Run: `python tests/test_retier.py`
"""

from __future__ import annotations

import csv
import os
import shutil
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import retier  # noqa: E402


FIELDS = [
    "chrom", "pos", "id", "ref", "alt", "ad", "dp", "sample_af",
    "gene", "most_severe_consequence", "hgvsc", "hgvsp", "rsid",
    "max_pop_af", "clin_sig", "uniprot", "tier",
]


def make_row(**overrides) -> dict:
    """Build a complete annotated-CSV row with sane defaults."""
    base = {f: "NA" for f in FIELDS}
    base.update({
        "chrom": "1", "pos": "100", "id": ".", "ref": "A", "alt": "G",
        "ad": "20", "dp": "100", "sample_af": "0.2",
        "gene": "MYD88", "most_severe_consequence": "missense_variant",
        "hgvsc": "c.1A>G", "hgvsp": "p.M1V", "rsid": "rs1",
        "max_pop_af": "0.0", "clin_sig": "NA", "uniprot": "P1",
        "tier": "Tier 2",
    })
    base.update(overrides)
    return base


def write_csv(path: Path, rows: list[dict]) -> None:
    with path.open("w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=FIELDS)
        w.writeheader()
        w.writerows(rows)


def read_csv(path: Path) -> list[dict]:
    with path.open(encoding="utf-8", newline="") as fh:
        return list(csv.DictReader(fh))


def case_dry_run_preserves_file(tmp: Path) -> tuple[str, bool, str]:
    # Buggy-state row: pure likely_pathogenic mislabeled as Tier 1 by old logic.
    # After the fix, assign_tier() will return Tier 2, so retier should report a change.
    rows = [
        make_row(gene="KMT2D", most_severe_consequence="frameshift_variant",
                 clin_sig="likely_pathogenic", max_pop_af="0.0", tier="Tier 1"),
        make_row(gene="MYD88", most_severe_consequence="missense_variant",
                 clin_sig="pathogenic", max_pop_af="0.001", tier="Tier 1"),
    ]
    p = tmp / "sample_annotated.csv"
    write_csv(p, rows)
    before_mtime = p.stat().st_mtime_ns

    rc = retier.main([str(p)])  # dry-run by default
    after = read_csv(p)
    after_mtime = p.stat().st_mtime_ns

    if rc != 0:
        return "dry_run_preserves_file", False, f"exit code {rc}"
    if after[0]["tier"] != "Tier 1":
        return "dry_run_preserves_file", False, f"file was modified: tier={after[0]['tier']!r} (expected unchanged 'Tier 1')"
    if after_mtime != before_mtime:
        return "dry_run_preserves_file", False, "mtime changed despite dry-run"
    return "dry_run_preserves_file", True, "ok"


def case_apply_rewrites_file(tmp: Path) -> tuple[str, bool, str]:
    rows = [
        make_row(gene="KMT2D", most_severe_consequence="frameshift_variant",
                 clin_sig="likely_pathogenic", max_pop_af="0.0", tier="Tier 1"),
        make_row(gene="MYD88", most_severe_consequence="missense_variant",
                 clin_sig="pathogenic", max_pop_af="0.001", tier="Tier 1",
                 hgvsc="c.1234A>G", hgvsp="p.K412R", uniprot="Q99836"),
    ]
    p = tmp / "apply_annotated.csv"
    write_csv(p, rows)

    rc = retier.main([str(p), "--apply"])
    after = read_csv(p)

    if rc != 0:
        return "apply_rewrites_file", False, f"exit code {rc}"
    if after[0]["tier"] != "Tier 2":
        return "apply_rewrites_file", False, f"KMT2D row not rewritten: tier={after[0]['tier']!r}"
    if after[1]["tier"] != "Tier 1":
        return "apply_rewrites_file", False, f"MYD88 row should remain Tier 1, got {after[1]['tier']!r}"
    # Non-tier columns must be preserved verbatim.
    if after[1]["hgvsc"] != "c.1234A>G" or after[1]["uniprot"] != "Q99836":
        return "apply_rewrites_file", False, "non-tier columns lost during rewrite"
    if list(after[0].keys()) != FIELDS:
        return "apply_rewrites_file", False, f"column order changed: {list(after[0].keys())}"
    return "apply_rewrites_file", True, "ok"


def case_missing_tier_column_rejected(tmp: Path) -> tuple[str, bool, str]:
    # CSV without the required 'tier' column should be rejected, not crash.
    p = tmp / "bad_annotated.csv"
    with p.open("w", encoding="utf-8", newline="") as fh:
        fh.write("chrom,pos,gene\n1,100,MYD88\n")
    rc = retier.main([str(p)])
    if rc != 0:
        return "missing_tier_column_rejected", False, f"exit code {rc}"
    # File should be untouched.
    text = p.read_text(encoding="utf-8")
    if "tier" in text:
        return "missing_tier_column_rejected", False, "file was modified"
    return "missing_tier_column_rejected", True, "ok"


def case_missing_path_skipped(tmp: Path) -> tuple[str, bool, str]:
    rc = retier.main([str(tmp / "does_not_exist.csv")])
    if rc != 0:
        return "missing_path_skipped", False, f"exit code {rc}"
    return "missing_path_skipped", True, "ok"


def run() -> int:
    cases = [
        case_dry_run_preserves_file,
        case_apply_rewrites_file,
        case_missing_tier_column_rejected,
        case_missing_path_skipped,
    ]
    tmp = Path(tempfile.mkdtemp(prefix="retier_test_"))
    try:
        failures: list[str] = []
        for c in cases:
            name, ok, msg = c(tmp)
            status = "OK  " if ok else "FAIL"
            print(f"  {status}  {name}  ({msg})")
            if not ok:
                failures.append(name)
        print()
        if failures:
            print(f"{len(failures)} / {len(cases)} case(s) failed: {failures}")
            return 1
        print(f"All {len(cases)} cases passed.")
        return 0
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


if __name__ == "__main__":
    sys.exit(run())
