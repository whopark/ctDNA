"""QC statistics computation from annotated CSV dp column.

Replaces the simpler read_annotated_csv in generate_clinical_reports.py
which only returned tier_counts. Now also yields depth statistics so
that Table 14 can be populated per SPEC-REPORT-001 REQ-1.
"""

from __future__ import annotations

import csv
import statistics
from pathlib import Path

TIER_KEYS = ("Tier 1", "Tier 2", "Tier 3", "Tier 4")


# @AX:NOTE [AUTO] dp column is the source of truth for Table 14 depth stats; non-integer
# @AX:NOTE [AUTO] or missing dp rows are skipped from depth stats, total_variants, AND tier_counts.
def compute_qc(annotated_csv: str | Path) -> dict:
    """Read the annotated CSV and compute depth + tier statistics.

    Only rows with a valid integer dp value are counted. Rows with a
    missing or non-integer dp field are silently skipped from depth
    statistics, total_variants, AND tier_counts — the entire row is
    excluded from all metrics, not just depth. This keeps all four
    return fields consistent on the same filtered row set.

    Returns:
      {
        "mean_depth": float,           # 0.0 on empty / no valid rows
        "median_depth": float,         # 0.0 on empty
        "pct_dp_ge_100x": float,       # 0.0 on empty; rounded to 1 decimal
        "total_variants": int,         # count of rows with valid integer dp
        "tier_counts": {"Tier 1": int, ...},  # only rows with valid integer dp
      }
    """
    depths: list[int] = []
    tier_counts = {k: 0 for k in TIER_KEYS}

    path = Path(annotated_csv)
    if not path.exists():
        return _empty_result()

    with open(path, encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            dp_raw = row.get("dp", "").strip()
            if not dp_raw:
                continue  # skip rows with missing dp
            try:
                dp_val = int(dp_raw)
            except ValueError:
                continue  # skip rows with non-integer dp
            # Only count rows with valid integer dp
            depths.append(dp_val)
            tier = row.get("tier", "Tier 4")
            if tier in tier_counts:
                tier_counts[tier] += 1
            else:
                tier_counts["Tier 4"] += 1

    if not depths:
        return {
            "mean_depth": 0.0,
            "median_depth": 0.0,
            "pct_dp_ge_100x": 0.0,
            "total_variants": 0,
            "tier_counts": tier_counts,
        }

    mean = round(statistics.mean(depths), 1)
    median = round(statistics.median(depths), 1)
    ge100 = sum(1 for d in depths if d >= 100)
    pct = round((ge100 / len(depths)) * 100.0, 1)
    return {
        "mean_depth": mean,
        "median_depth": median,
        "pct_dp_ge_100x": pct,
        "total_variants": len(depths),
        "tier_counts": tier_counts,
    }


def _empty_result() -> dict:
    """Return a zero-valued result for missing or unreadable input."""
    return {
        "mean_depth": 0.0,
        "median_depth": 0.0,
        "pct_dp_ge_100x": 0.0,
        "total_variants": 0,
        "tier_counts": {k: 0 for k in TIER_KEYS},
    }
