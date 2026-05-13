"""
Reproduction + regression test for the `assign_tier` ClinVar substring bug.

Original bug (annotate_vcf.py:260, pre-fix):
    has_pathogenic = "pathogenic" in clin_lower and "likely_benign" not in clin_lower

Because Python's `in` is a substring match, `"pathogenic" in "likely_pathogenic"` is True.
A ClinVar value of `likely_pathogenic` therefore set `has_pathogenic = True` and the
Tier 1 branch at line 278 fired before the Tier 2 Case B branch at line 287 could
match it as a moderate-impact likely_pathogenic variant.

ClinVar uses `|` (and sometimes `/`) to separate multiple submitter opinions, e.g.
`likely_pathogenic|pathogenic|uncertain_significance`. The fix tokenizes on those
separators so the standalone `pathogenic` token is detected without false-positive
matches inside `likely_pathogenic`.

Run: `python tests/test_assign_tier_clin_sig.py`
"""

from __future__ import annotations

import os
import sys

# Make the repo root importable when running this file directly.
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from annotate_vcf import assign_tier  # noqa: E402


def row(gene: str, csq: str, clin_sig: str, max_pop_af: str = "0.0") -> dict:
    """Build the minimal row shape that assign_tier consumes."""
    return {
        "gene": gene,
        "most_severe_consequence": csq,
        "clin_sig": clin_sig,
        "max_pop_af": max_pop_af,
    }


# Each case is: (label, row, expected_tier).
# Gene choices: MYD88 and TP53 are in TIER1_2_GENES; ATR is in TIER3_GENES only.
CASES = [
    # --- regressions from real 0325 data: pure likely_pathogenic must NOT be Tier 1 ---
    (
        "pure likely_pathogenic, frameshift in driver gene -> Tier 2 (high impact)",
        row("KMT2D", "frameshift_variant", "likely_pathogenic", "0.0"),
        "Tier 2",
    ),
    (
        "pure likely_pathogenic, splice_acceptor in driver gene -> Tier 2",
        row("TCF3", "splice_acceptor_variant", "likely_pathogenic", "0.0"),
        "Tier 2",
    ),
    (
        "pure likely_pathogenic, missense in driver gene -> Tier 2 (Case B)",
        row("DDX3X", "missense_variant", "likely_pathogenic", "NA"),
        "Tier 2",
    ),
    (
        "likely_pathogenic|not_provided (no standalone pathogenic) -> Tier 2",
        row("CREBBP", "splice_acceptor_variant", "likely_pathogenic|not_provided", "NA"),
        "Tier 2",
    ),

    # --- legitimate Tier 1: any submitter said "pathogenic" as its own token ---
    (
        "plain pathogenic missense in driver gene -> Tier 1",
        row("MYD88", "missense_variant", "pathogenic", "0.001"),
        "Tier 1",
    ),
    (
        "multi-submitter likely_pathogenic|pathogenic|uncertain_significance -> Tier 1",
        row("MYD88", "missense_variant",
            "likely_pathogenic|pathogenic|uncertain_significance", "0.001"),
        "Tier 1",
    ),
    (
        "slash-separated pathogenic/likely_pathogenic -> Tier 1",
        row("TP53", "missense_variant",
            "pathogenic/likely_pathogenic", "NA"),
        "Tier 1",
    ),

    # --- benign / likely_benign must not be Tier 1 (existing guard) ---
    (
        "likely_benign missense -> Tier 4 (benign guard)",
        row("MYD88", "missense_variant", "likely_benign", "NA"),
        "Tier 4",
    ),

    # --- conflicting ClinVar interpretations must not promote to Tier 1 ---
    # ARID1A in 0325/03- and 0325/05- has this exact clin_sig with inframe_deletion;
    # original code routed it to Tier 3 via the `likely_benign not in clin_lower` guard.
    # Token-based fix must preserve this.
    (
        "conflicting benign|likely_benign|pathogenic|uncertain_significance "
        "inframe_deletion (ARID1A is in both TIER1_2_GENES and TIER3_GENES; "
        "the likely_benign token blocks has_pathogenic so the Tier 1 path "
        "is skipped, and the variant falls through to Tier 3 Case A) -> NOT Tier 1",
        row("ARID1A", "inframe_deletion",
            "benign|likely_benign|pathogenic|uncertain_significance", "0.0088"),
        "Tier 3",
    ),

    # --- common polymorphism filter still wins (>5% triggers is_very_common) ---
    (
        "pathogenic but pop_af > 5% -> Tier 4 (very common polymorphism)",
        row("MYD88", "missense_variant", "pathogenic", "0.10"),
        "Tier 4",
    ),
]


def run() -> int:
    failures: list[str] = []
    for label, r, expected in CASES:
        got = assign_tier(r)
        status = "OK  " if got == expected else "FAIL"
        print(f"  {status}  expected={expected:6s}  got={got:6s}  | {label}")
        if got != expected:
            failures.append(f"{label}: expected {expected}, got {got}")

    print()
    if failures:
        print(f"{len(failures)} / {len(CASES)} cases failed:")
        for f in failures:
            print(f"  - {f}")
        return 1
    print(f"All {len(CASES)} cases passed.")
    return 0


if __name__ == "__main__":
    sys.exit(run())
