# Changelog

All notable changes to the ctDNA pipeline are documented here.

The format is based on [Keep a Changelog](https://keepachangelog.com/).

## [Unreleased]

### SPEC-REPORT-001 — 0325/template.docx 완전 준수 (2026-05-14)

**Added**

- `case_meta.py` — per-case `meta.json` loader + scaffold writer; fail-soft contract (missing/malformed → empty + warning, never raises)
- `qc_stats.py` — `compute_qc()` reads `dp` column from annotated CSV and returns mean/median depth, `pct_dp_ge_100x`, `total_variants`, `tier_counts`
- `interpretations_loader.py` — 4-step interpretation resolver (yaml exact → yaml longest-prefix → KB → empty)
- `report_tables.py` — Table 0 12-cell mapping + Table 14 QC + Table 15 signature DOCX helpers
- `interpretations.yaml` — externalized clinical interpretation text seeded from previous `INTERPRETATIONS` dict
- `tests/test_qc_stats.py`, `tests/test_case_meta.py`, `tests/test_interpretations.py`, `tests/test_report_table15.py` — 31 unit + integration tests covering acceptance scenarios S1–S8
- `.gitignore` rules for `**/meta.json` (PHI) plus downstream artifacts (`*_clinical_report.docx`, `*_annotated.csv`, `*_tiered_report.csv`, `*.vcf`)
- README section documenting `interpretations.yaml`, `meta.json`, and the new `pyyaml`/`pytest` dependencies

**Changed**

- `generate_clinical_reports.py` refactored: 432 → 296 lines. Removed inline `CASES` and `INTERPRETATIONS` dicts and the duplicate `read_annotated_csv`. Now wires in `case_meta`, `qc_stats`, `interpretations_loader`, and `report_tables`. Table 0 populates all 12 cells per the explicit spec.md mapping (fixes prior R0c5/R3c3 wrong-key bindings and R2c5/R3c5 mis-sourced report dates). Table 14 QC and Table 15 signatures now filled. Tier 1/2 sorted by VAF desc within tier groups; Tier 3 cap reduced from 20 → 14 to match template row capacity. `_find_template()` accepts an explicit `template_path` argument with priority: explicit → `./template.docx` → `./0325/template.docx`.
- `ctdna_gui.py` `run_docx_report()` — removed legacy `gdr.CASES`/`gdr.INTERPRETATIONS` writes (AttributeError after refactor). Added `write_meta_scaffold` hook + `_prefill_meta_from_gui` helper to preserve GUI metadata input UX by merging legacy 5 keys (patient/reg_no/specimen/test_date) into `meta.json` without clobbering operator edits.

**Removed**

- `0325/generate_clinical_reports.py` — stale divergent copy (older 349-line variant lacking KB integration and Windows site-packages handling). Canonical entry is root `generate_clinical_reports.py`.

**Security**

- `meta.json` files (PHI containers) git-ignored by default; downstream PHI-embedding artifacts also excluded going forward. Pre-existing committed PHI under `0224/` and `0325/` is out-of-scope (separate cleanup needed).

**Quality**

- 31/31 tests pass. Coverage 87% across new modules (case_meta 79%, qc_stats 91%, interpretations_loader 85%, report_tables 95%).
- Multi-provider SPEC review: PASS after 1 revision iteration. Code review (TRUST 5): APPROVE after 2 RALF iterations. Security audit: PASS, 0 critical/high findings.
- 14 `@AX` annotations added (12 NOTE, 2 WARN) across modified files.

**Ref**: `.autopus/specs/SPEC-REPORT-001/`
