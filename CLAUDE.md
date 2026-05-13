# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Repository Overview

Git repository (`main` branch) for the **ctDNA lymphoma panel annotation pipeline**. A Python pipeline that:

1. Annotates VCFs (GRCh37) through the Ensembl VEP REST API
2. Classifies each variant with AMP/ASCO/CAP somatic tiering (Li et al., *J Mol Diagn* 2017;19:4-23)
3. Emits a clinical report CSV plus a Korean-language DOCX report from a fixed template

There is no build system, no test suite, and no linter. README.md is the user-facing manual; this file is the architecture/orientation document.

## Commands

```bash
pip install requests python-docx       # requests is required; python-docx is needed only for Step 3

# Recommended entry point — GUI runs all 3 steps with editable filters
python ctdna_gui.py

# CLI, step by step
python annotate_vcf.py path/to/sample.vcf                  # Step 1 → {ID}_annotated.csv
python reformat_tiers.py path/to/sample_annotated.csv      # Step 2 → {ID}_tiered_report.csv
python generate_clinical_reports.py                        # Step 3 → {ID}_clinical_report.docx
                                                           #   (case metadata is hard-coded inside the
                                                           #    script — edit it before running, or use the GUI)
```

`python-docx` is imported lazily; the GUI and Step 3 also probe Windows-Store Python user site-packages paths so they keep working without an activated venv (see `_add_user_site_packages` in `ctdna_gui.py` and `generate_clinical_reports.py`).

## Architecture

### Three-stage pipeline

```
VCF (GRCh37, INFO contains AD + DP)
  │
  ├─ annotate_vcf.py     → {ID}_annotated.csv
  │     parse_vcf → build_vep_input → query_vep_batch (POST, 200/batch, retry+backoff)
  │     → extract_annotation → assign_tier  (Tier 1–4)
  │
  ├─ reformat_tiers.py   → {ID}_tiered_report.csv
  │     Filters to Tier 1–3, VAF ≥ 1%; Tier 3 limited to ACTIONABLE_TIER3_GENES
  │     Splits HGVSc/HGVSp into transcript/accession + change columns
  │
  └─ generate_clinical_reports.py → {ID}_clinical_report.docx
        Reuses ACTIONABLE_TIER3_GENES from annotate_vcf.py to filter Tier 3
        Locates template via _find_template() — prefers repo-root template.docx,
        falls back to 0325/template.docx, then parent dir
```

`ctdna_gui.py` is a tkinter front-end that imports the same helpers (`parse_vcf`, `build_vep_input`, `query_vep_batch`, `extract_annotation`, `assign_tier`, `generate_report`) and runs the three steps on a background thread, streaming progress through a queue.

### Tier assignment (in `annotate_vcf.py:assign_tier`)

| Tier | Criteria |
|------|----------|
| Tier 1 | ClinVar pathogenic/likely pathogenic in a `TIER1_2_GENES` gene, pop AF ≤ 1% |
| Tier 2 | High-impact or novel missense in a `TIER1_2_GENES` gene, rare, not ClinVar-benign |
| Tier 3 | Moderate/high impact in a `TIER3_GENES` gene, uncertain significance |
| Tier 4 | Common polymorphisms, benign ClinVar, or non-driver genes — **excluded from reports** |

### Gene-list constants — all editable in `annotate_vcf.py`

| Constant | Line | Role |
|----------|------|------|
| `TIER1_2_GENES` | 31 | Established lymphoma drivers — eligible for Tier 1/2 |
| `TIER3_GENES` | 58 | Broader cancer-associated pool — Tier 3 fall-through |
| `DRUG_TARGET_GENES` | ~100 | Tier 3 reportable subset — FDA-approved / late-trial targets |
| `RISK_STRATIFICATION_GENES` | 167 | Tier 3 reportable subset — prognostic markers |
| `ACTIONABLE_TIER3_GENES` | 192 | Auto-computed `DRUG_TARGET_GENES ∪ RISK_STRATIFICATION_GENES`; used by `reformat_tiers.py` and the DOCX generator |

The GUI exposes `DRUG_TARGET_GENES` and `RISK_STRATIFICATION_GENES` as editable text panels with a Reset Defaults button. Changes apply to the next pipeline run.

### Canonical vs. convenience copies

- `.agents/skills/kbb-annotation/scripts/annotate_vcf.py` and `reformat_tiers.py` are the canonical skill copies. Both root-level scripts have **diverged** from their skill copies (verify with `diff -q annotate_vcf.py .agents/skills/kbb-annotation/scripts/annotate_vcf.py`) — when editing, decide whether the change should live in both or only at the root.
- `generate_clinical_reports.py` lives at the repo root (and a divergent copy in `0325/`). There is also an older `.claude/generate_docx_reports.py` left over from earlier work — do not treat it as canonical.
- The DOCX template is `template.docx` at repo root (or `0325/template.docx`); the older `.agents/skills/kbb-annotation/reference/report_template.docx` is the original skill reference.

## Output layout (batch folders)

GUI output path is `{Base Directory}/{Batch Folder}/{case_id}/`, with Batch Folder defaulting to today's `MMDD`. Existing batches `0224/` and `0325/` follow this layout — each case folder contains `{ID}_annotated.csv`, `{ID}_tiered_report.csv`, and `{ID}_clinical_report.docx`.

Case IDs typically encode `{NN}-{INITIALS}_{REG_NO}` (e.g. `01-JJH_10679562`). The GUI parses initials and registration number from this pattern to pre-fill patient metadata.

## Conventions

- VEP requests are batched at 200 variants per POST with `RETRY_WAIT=5s` and `MAX_RETRIES=5` (see top of `annotate_vcf.py`).
- Generated reports use **Korean-language headers** — preserve them when editing the DOCX template or report-generation code.
- Patient/clinical data lives only on the local filesystem; do not commit case VCFs or reports beyond what is already tracked.
- Shell is PowerShell on Windows 10 — use PowerShell syntax (`$env:VAR`, `;` between commands) when not invoking via the Bash tool.

## Notes

- Plans and design documents go in `docs/plans/`.
- `skills-lock.json` tracks installed skills under `.agents/skills/` (sourced from `davila7/claude-code-templates`); the project's own skill is `kbb-annotation`.


<!-- AUTOPUS:BEGIN -->
# Autopus-ADK Harness

> 이 섹션은 Autopus-ADK에 의해 자동 생성됩니다. 수동으로 편집하지 마세요.

- **프로젝트**: ctDNA
- **모드**: full
- **플랫폼**: claude-code, codex

## 설치된 구성 요소

- Rules: .claude/rules/autopus/
- Skills: .claude/skills/autopus/
- Commands: .claude/skills/auto/SKILL.md
- Agents: .claude/agents/autopus/

## Language Policy

IMPORTANT: Follow these language settings strictly for all work in this project.

- **Code comments**: Write all code comments, docstrings, and inline documentation in English (en)
- **Commit messages**: Write all git commit messages in English (en)
- **AI responses**: Respond to the user in English (en)

## Core Guidelines

### Subagent Delegation

IMPORTANT: Use subagents for complex tasks that modify 3+ files, span multiple domains, or exceed 200 lines of new code. Define clear scope, provide full context, review output before integrating.

### File Size Limit

IMPORTANT: No source code file may exceed 300 lines. Target under 200 lines. Split by type, concern, or layer when approaching the limit. Excluded: generated files (*_generated.go, *.pb.go), documentation (*.md), and config files (*.yaml, *.json).

### Code Review

During review, verify:
- No file exceeds 300 lines (REQUIRED)
- Complex changes use subagent delegation (SUGGESTED)
- See .claude/rules/autopus/ for detailed guidelines

<!-- AUTOPUS:END -->
