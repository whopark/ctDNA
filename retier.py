"""
Re-tier existing `_annotated.csv` files in place by re-running `assign_tier`
on every row. Does NOT hit the Ensembl VEP REST API — uses only what is
already in the CSV (gene, most_severe_consequence, clin_sig, max_pop_af,
sample_af). Useful after a fix to `assign_tier()` that should propagate into
already-annotated case data without re-running Step 1.

Defaults to dry-run; pass `--apply` to write changes back.

Usage:
    python retier.py path/to/file_annotated.csv [more.csv ...]          # dry-run
    python retier.py path/to/file_annotated.csv --apply
    python retier.py 0325/03-PRG_*/*_annotated.csv --apply               # shell glob
"""

from __future__ import annotations

import argparse
import csv
import os
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

from annotate_vcf import assign_tier  # noqa: E402


def retier_file(path: Path, apply: bool) -> dict:
    """Re-tier one CSV. Returns a summary dict with per-file stats."""
    with path.open(encoding="utf-8", newline="") as fh:
        reader = csv.DictReader(fh)
        fieldnames = reader.fieldnames
        if not fieldnames or "tier" not in fieldnames:
            raise ValueError(f"{path}: missing 'tier' column; not a valid _annotated.csv")
        rows = list(reader)

    transitions: dict[tuple[str, str], int] = {}
    changed_rows: list[tuple] = []
    for r in rows:
        old = r.get("tier", "")
        new = assign_tier(r)
        transitions[(old, new)] = transitions.get((old, new), 0) + 1
        if old != new:
            changed_rows.append((
                r.get("chrom", ""), r.get("pos", ""), r.get("gene", ""),
                r.get("most_severe_consequence", ""), r.get("clin_sig", ""),
                old, new,
            ))
            r["tier"] = new

    applied = False
    if apply and changed_rows:
        tmp = path.with_suffix(path.suffix + ".tmp")
        with tmp.open("w", encoding="utf-8", newline="") as fh:
            writer = csv.DictWriter(fh, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(rows)
        os.replace(tmp, path)
        applied = True

    return {
        "path": path,
        "transitions": transitions,
        "changed_rows": changed_rows,
        "applied": applied,
    }


def _print_file_report(summary: dict) -> None:
    path = summary["path"]
    changed = summary["changed_rows"]
    if not changed:
        print(f"OK:  {path}  (no changes)")
        return
    action = "Applied" if summary["applied"] else "Would change"
    print(f"\n{action}: {path}  ({len(changed)} rows)")
    for chrom, pos, gene, csq, clin_sig, old, new in changed:
        print(f"  {chrom}:{pos}  {gene:10s}  {old} -> {new}  "
              f"clin_sig={clin_sig!r}  consequence={csq}")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Re-tier existing _annotated.csv files in place "
                    "without re-querying VEP."
    )
    parser.add_argument("paths", nargs="+", help="One or more *_annotated.csv files")
    parser.add_argument("--apply", action="store_true",
                        help="Write changes (default: dry-run preview only)")
    args = parser.parse_args(argv)

    total_changed = 0
    files_with_changes = 0
    for raw in args.paths:
        path = Path(raw)
        if not path.exists():
            print(f"SKIP {path}: not found", file=sys.stderr)
            continue
        try:
            summary = retier_file(path, apply=args.apply)
        except ValueError as e:
            print(f"SKIP {e}", file=sys.stderr)
            continue
        if summary["changed_rows"]:
            files_with_changes += 1
            total_changed += len(summary["changed_rows"])
        _print_file_report(summary)

    print()
    mode = "applied" if args.apply else "dry-run"
    print(f"Total: {total_changed} rows changed across {files_with_changes} file(s) [{mode}]")
    if not args.apply and total_changed:
        print("Re-run with --apply to write changes.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
