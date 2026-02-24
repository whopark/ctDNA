# ctDNA — Lymphoma ctDNA Variant Annotation Pipeline

Annotate lymphoma ctDNA panel VCF files using Ensembl VEP REST API (GRCh37) and classify somatic variants following AMP/ASCO/CAP tiering guidelines (Li et al., *J Mol Diagn*. 2017;19:4-23).

## Quick Start

```bash
pip install requests python-docx   # one-time dependencies

# 1. Annotate VCF → full annotation CSV with tier assignments
python annotate_vcf.py sample.vcf

# 2. Generate tiered report CSV (Tier 1-3 only)
python reformat_tiers.py sample_annotated.csv

# 3. Generate clinical .docx reports from template
python .claude/generate_docx_reports.py
```

## Pipeline Overview

```
VCF (GRCh37)
  │
  ├─ annotate_vcf.py ──► {ID}_annotated.csv
  │     Ensembl VEP REST API (batch POST, 200/request)
  │     → gene, consequence, HGVSc/p, rsID, pop AF, ClinVar, UniProt
  │     → AMP/ASCO/CAP somatic tier assignment
  │
  ├─ reformat_tiers.py ──► {ID}_tiered_report.csv
  │     Filter Tier 1-3, format for clinical review
  │
  └─ generate_docx_reports.py ──► {ID}_clinical_report.docx
        Populate KBB report template with variant tables,
        clinical interpretation, and therapeutic implications
```

## Input Requirements

- **Format**: VCFv4.2
- **Reference**: GRCh37 (hg19)
- **Required INFO fields**: `AD` (alt allele depth), `DP` (total depth)
- Designed for PiSeq lymphoma ctDNA panels but works with any VCF meeting the above criteria

## Output Files

| File | Description |
|------|-------------|
| `{ID}_annotated.csv` | Full annotation: chrom, pos, id, ref, alt, ad, dp, sample_af, gene, most_severe_consequence, hgvsc, hgvsp, rsid, max_pop_af, clin_sig, uniprot, tier |
| `{ID}_tiered_report.csv` | Tier 1-3 clinical report: ASCO/AMP Classification, Gene, Canonical name, Accession, Nucleotide change, AA change, %VAF |
| `{ID}_clinical_report.docx` | Formatted clinical report (Korean-language pathology report template) |
| `{ID}_clinical_report.md` | Markdown version of clinical report |

## AMP/ASCO/CAP Somatic Variant Tiering

| Tier | Classification | Criteria |
|------|---------------|----------|
| **Tier 1** | Strong clinical significance | Known pathogenic (ClinVar) in lymphoma driver gene, pop AF ≤ 1% |
| **Tier 2** | Potential clinical significance | High-impact or novel missense in driver gene, rare, not benign |
| **Tier 3** | Unknown clinical significance | Moderate/high impact in broader cancer gene, uncertain significance |
| **Tier 4** | Benign / likely benign | Common polymorphisms, benign ClinVar, non-driver genes (excluded from report) |

## Gene Lists

### Tier 1/2 — Established Lymphoma Drivers (58 genes)

**DLBCL / B-cell lymphoma**: TP53, MYC, BCL2, BCL6, MYD88, CD79B, CD79A, CARD11, TNFAIP3, KMT2D, CREBBP, EZH2, EP300, ARID1A, NOTCH1, NOTCH2, PIM1, CCND1, CCND3, SOCS1, SGK1, TET2, GNA13, IRF4, FOXO1, MEF2B, PRDM1, NFKBIA, TCF3, ID3, STAT6, TNFRSF14, B2M, CIITA, CD58, FAS, BCL10, CD70, DTX1, UBE2A, SPEN, IRF8, BTG1, KLHL6, TBL1XR1

**Targeted therapy**: BTK, PLCG2, PIK3CD, PIK3R1, PTEN, MTOR, JAK1, JAK2, STAT3, STAT5B, BRAF, KRAS, NRAS

**Other hematologic**: DNMT3A, IDH1, IDH2, NPM1, FLT3, BCOR, BCORL1, DDX3X, SF3B1, BIRC3, ATM, CDKN2A, RB1, FBXW7

### Tier 3 — Broader Cancer-Associated (70+ genes)

Chromatin/epigenetic, DNA repair, RTK/signaling, splicing, and other lymphoma-associated genes. Full list in `annotate_vcf.py`.

## Example Results (0224 batch)

| Case | Variants | Tier 1 | Tier 2 | Tier 3 | Key Findings |
|------|----------|--------|--------|--------|-------------|
| 01-JJH | 538 | 11 | 54 | 33 | EZH2 Y646, PTEN multi-hit, CREBBP, ARID1A — GCB-DLBCL (EZB) |
| 02-OKW | 443 | 3 | 23 | 33 | STAT3 activating, NOTCH2, DNMT3A+TET2 (CHIP) — GCB with mixed features |
| 03-OJS | 436 | 0 | 13 | 23 | BCL6, MEF2B dual, low burden — GCB-DLBCL |
| 04-PHJ | 410 | 0 | 17 | 28 | MEF2B dual, CREBBP, SPEN cluster, CIITA — GCB-DLBCL |

## Repository Structure

```
ctDNA/
├── annotate_vcf.py              # VEP annotation + tiering (main script)
├── reformat_tiers.py            # Generate tiered report CSV
├── .claude/
│   └── generate_docx_reports.py # Generate .docx clinical reports
├── 0224/                        # Patient case data (date-stamped)
│   ├── 01-JJH_10679562/
│   │   ├── *.vcf                # Input VCF
│   │   ├── *_annotated.csv      # Full VEP annotation
│   │   ├── *_tiered_report.csv  # Tier 1-3 clinical CSV
│   │   ├── *_clinical_report.docx  # Formatted clinical report
│   │   └── *_clinical_report.md    # Markdown clinical report
│   ├── 02-OKW_10673102/
│   ├── 03-OJS_23953884/
│   └── 04-PHJ_10680696/
├── .agents/skills/kbb-annotation/
│   ├── SKILL.md                 # Full skill documentation
│   ├── scripts/                 # Canonical script copies
│   └── reference/
│       └── report_template.docx # Clinical report template (Korean)
├── CLAUDE.md                    # Claude Code workspace instructions
└── skills-lock.json             # Installed skills manifest
```

## Dependencies

- **Python 3.8+**
- `requests` — Ensembl VEP REST API calls
- `python-docx` — Clinical report .docx generation

## References

- Li MM, Datto M, Duncavage EJ, et al. Standards and Guidelines for the Interpretation and Reporting of Sequence Variants in Cancer. *J Mol Diagn*. 2017;19(1):4-23.
- Chapuy B, Stewart C, Dunford AJ, et al. Molecular subtypes of diffuse large B cell lymphoma are associated with distinct pathogenic mechanisms and outcomes. *Nat Med*. 2018;24(5):679-690.
- Schmitz R, Wright GW, Huang DW, et al. Genetics and Pathogenesis of Diffuse Large B-Cell Lymphoma. *N Engl J Med*. 2018;378(15):1396-1407.
