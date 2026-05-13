"""
Phase 1.5 test scaffold — S2: Table 14 QC values computed from annotated CSV dp column.

All tests in RED state (FAIL) until qc_stats.py is implemented by Phase 2 executors.
"""
from __future__ import annotations

import csv
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

# ImportError expected here — module does not exist yet (RED state)
from qc_stats import compute_qc  # noqa: E402


def _write_annotated_csv(path, dp_values):
    """Helper: write a minimal annotated CSV with given dp values."""
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["chrom", "pos", "ref", "alt", "dp", "tier"])
        writer.writeheader()
        for dp in dp_values:
            writer.writerow({"chrom": "1", "pos": "100", "ref": "A", "alt": "T",
                             "dp": dp, "tier": "Tier 2"})


class TestComputeQcOracleS2:
    """S2: five dp values [50, 80, 120, 200, 300] produce exact metric values."""

    def test_mean_depth(self, tmp_path):
        csv_path = tmp_path / "sample_annotated.csv"
        _write_annotated_csv(str(csv_path), [50, 80, 120, 200, 300])
        result = compute_qc(str(csv_path))
        assert result["mean_depth"] == 150.0, (
            f"Expected mean_depth=150.0, got {result['mean_depth']}"
        )

    def test_median_depth(self, tmp_path):
        csv_path = tmp_path / "sample_annotated.csv"
        _write_annotated_csv(str(csv_path), [50, 80, 120, 200, 300])
        result = compute_qc(str(csv_path))
        assert result["median_depth"] == 120.0, (
            f"Expected median_depth=120.0, got {result['median_depth']}"
        )

    def test_pct_dp_ge_100x(self, tmp_path):
        """3 of 5 values (120, 200, 300) >= 100 → 60.0%."""
        csv_path = tmp_path / "sample_annotated.csv"
        _write_annotated_csv(str(csv_path), [50, 80, 120, 200, 300])
        result = compute_qc(str(csv_path))
        assert result["pct_dp_ge_100x"] == 60.0, (
            f"Expected pct_dp_ge_100x=60.0, got {result['pct_dp_ge_100x']}"
        )

    def test_total_variants(self, tmp_path):
        csv_path = tmp_path / "sample_annotated.csv"
        _write_annotated_csv(str(csv_path), [50, 80, 120, 200, 300])
        result = compute_qc(str(csv_path))
        assert result["total_variants"] == 5, (
            f"Expected total_variants=5, got {result['total_variants']}"
        )


class TestComputeQcEdgeCases:
    """Edge cases: empty input and rows with non-integer dp."""

    def test_empty_csv_returns_zeros_not_nan(self, tmp_path):
        """Empty annotated CSV must return 0.0 for all floats, not NaN."""
        csv_path = tmp_path / "empty_annotated.csv"
        _write_annotated_csv(str(csv_path), [])
        result = compute_qc(str(csv_path))
        assert result["mean_depth"] == 0.0, (
            f"Expected mean_depth=0.0 for empty input, got {result['mean_depth']}"
        )
        assert result["median_depth"] == 0.0, (
            f"Expected median_depth=0.0 for empty input, got {result['median_depth']}"
        )
        assert result["pct_dp_ge_100x"] == 0.0, (
            f"Expected pct_dp_ge_100x=0.0 for empty input, got {result['pct_dp_ge_100x']}"
        )
        assert result["total_variants"] == 0, (
            f"Expected total_variants=0 for empty input, got {result['total_variants']}"
        )
        # Confirm float values are not NaN
        import math
        assert not math.isnan(result["mean_depth"]), "mean_depth must not be NaN"
        assert not math.isnan(result["median_depth"]), "median_depth must not be NaN"
        assert not math.isnan(result["pct_dp_ge_100x"]), "pct_dp_ge_100x must not be NaN"

    def test_missing_dp_rows_are_skipped(self, tmp_path):
        """Rows with missing or non-integer dp are silently skipped; valid rows counted."""
        csv_path = tmp_path / "mixed_annotated.csv"
        with open(str(csv_path), "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=["chrom", "pos", "ref", "alt", "dp", "tier"])
            writer.writeheader()
            writer.writerow({"chrom": "1", "pos": "1", "ref": "A", "alt": "T",
                             "dp": "200", "tier": "Tier 1"})
            writer.writerow({"chrom": "1", "pos": "2", "ref": "A", "alt": "T",
                             "dp": "", "tier": "Tier 2"})   # missing dp
            writer.writerow({"chrom": "1", "pos": "3", "ref": "A", "alt": "T",
                             "dp": "N/A", "tier": "Tier 2"})  # non-integer dp
        result = compute_qc(str(csv_path))
        # Only the row with dp=200 is valid
        assert result["total_variants"] == 1, (
            f"Expected total_variants=1 after skipping bad rows, got {result['total_variants']}"
        )
        assert result["mean_depth"] == 200.0, (
            f"Expected mean_depth=200.0 from single valid row, got {result['mean_depth']}"
        )
