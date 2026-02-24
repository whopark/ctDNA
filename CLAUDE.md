# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Workspace Overview

This is a general-purpose Claude Code workspace on Windows 10 (not a git repository). It serves as a working directory for:
1. **Clinical genomics analysis** — VCF-based lymphoma ctDNA variant interpretation pipelines (VEP + COSMIC + ClinVar, OncoKB, CIVIC, MyCancerGenome + AMP/ASCO/CAP guideline)
2. **Computational drug discovery** — e.g., PHB2 inhibitor pipeline design (`docs/plans/`)
3. **New project scaffolding** — via installed Claude Code skills

No build, test, or lint commands exist. When creating a new project here, initialize a git repo and update this file with project-specific commands.

## Pipeline: KBB Annotation (`kbb-annotation` skill)

Annotates lymphoma ctDNA panel VCFs via Ensembl VEP REST API (GRCh37) and classifies variants using AMP/ASCO/CAP somatic tiering (Li et al., J Mol Diagn. 2017;19:4-23). Full tiering logic documented in `.agents/skills/kbb-annotation/SKILL.md`.

### Input Requirements
- VCFv4.2 files, **GRCh37 reference genome**
- INFO field must contain `AD` (alt allele depth) and `DP` (total depth)
- Designed for PiSeq lymphoma ctDNA panels but works with any VCF meeting above criteria

### Usage
```bash
pip install requests  # one-time dependency
python annotate_vcf.py data/XX.vcf
python reformat_tiers.py data/XX_annotated.csv
```
Root-level scripts are convenience copies of `.agents/skills/kbb-annotation/scripts/`.

### Outputs
- `{ID}_annotated.csv` — full annotation (chrom, pos, id, ref, alt, ad, dp, sample_af, gene, most_severe_consequence, hgvsc, hgvsp, rsid, max_pop_af, clin_sig, uniprot, tier)
- `{ID}_tiered_report.csv` — Tier 1–3 only, formatted as: `ASCO/AMP Classification | Gene | Canonical name | Accession | Nucleotide change | AA change | % VAF`

### Tiering Summary
- **Tier 1**: Known pathogenic (ClinVar) in lymphoma driver gene, rare (pop AF ≤ 1%)
- **Tier 2**: High-impact or novel missense in driver gene, rare, not benign
- **Tier 3**: Moderate/high impact in broader cancer gene, uncertain significance
- **Tier 4**: Common polymorphisms, benign, non-driver genes (excluded from report)

Gene lists and tiering thresholds are editable in `annotate_vcf.py` (`TIER1_2_GENES`, `TIER3_GENES`). VEP batches at 200 variants per request with retry/backoff.

## Data Directory (`data/`)

Patient case folders (`01/`–`05/`) follow this pipeline output structure:

- **Input**: `{ID}.vcf` (source VCF)
- **Annotation**: `{ID}_all_annotations.csv` (VEP + ClinVar + COSMIC + UniProt), `{ID}_vep_cosmic_clinvar_acmg.csv`
- **Filtering**: `{ID}_strict_somatic_like.csv`, `{ID}_skipped_variants.csv`, `{ID}_diagnostic_shortlist.csv`
- **Subtyping**: `{ID}_subtype_matrix.json` (GCB/ABC scoring)
- **Knowledge base**: `{ID}_kb_input_normalized_*.csv`, `{ID}_kb_summary_raw_*.csv`, `{ID}_kb_summary_strict_*.csv`
- **Reports**: `{ID}_clinical_draft_report.md`, `{ID}_clinical_report_strict_*.md`, `{ID}_therapeutic_recommendation_*.md`

CSV columns in `all_annotations.csv`: `chrom, pos, id, ref, alt, ad, dp, sample_af, gene, most_severe_consequence, hgvsc, hgvsp, rsid, max_pop_af, clin_sig, uniprot`

Reports use Korean-language headers and tiered variant classification (Tier 1/2/3 + Drug response).

## Installed Skills

Skills in `.agents/skills/` are tracked via `skills-lock.json` (sourced from `davila7/claude-code-templates`):

- **Clinical genomics**: `kbb-annotation`
- **App building**: `app-builder`, `backend-dev-guidelines`
- **AI/ML**: `pytorch-lightning`, `huggingface-accelerate`, `knowledge-distillation`, `dspy`, `ml-paper-writing`
- **Agent orchestration**: `agent-management`, `crewai-multi-agent`, `parallel-agents`
- **Research & memory**: `perplexity`, `context7-auto-research`, `memory-search`, `conversation-memory`
- **Planning & design**: `brainstorming`, `planning`, `prompt-engineer`, `prompt-library`, `mermaid-diagrams`, `research-engineer`
- **Meta**: `claude-code-guide`, `context-window-management`

Bioinformatics slash commands (`/biomni`, `/biopython`, `/bioservices`, `/clinvar-database`, `/ensembl-database`, `/pubmed-database`, etc.) are available as system-level skills — see the slash command menu for the full list.

## Notes

- Plans and design documents go in `docs/plans/`.
- Python dependency: only `requests` is required (for VEP API calls).
