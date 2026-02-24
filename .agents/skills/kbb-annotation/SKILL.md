---
name: kbb-annotation
description: "Annotate lymphoma ctDNA panel VCF files using Ensembl VEP (GRCh37) 
with AMP/ASCO/CAP somatic variant tiering. 
Produces clinical-grade tiered reports. 
Use when the user says
-  'annotate VCF', 
- 'annotate .vcf', 
- 'run kbb annotation', 
- 'tier variants', or 
- provides a VCF file for lymphoma/ctDNA analysis."
allowed-tools: Read, Write, Edit, Bash, Glob, Grep
---

# KBB Annotation — Lymphoma ctDNA Variant Annotation & Tiering

> Annotate VCF files from lymphoma ctDNA panels via
-  Ensembl VEP REST API (GRCh37), 
- classify variants using AMP/ASCO/CAP somatic tiering, and 
- produce clinical report CSVs as well as docx using template from reference/report_template.docx

## Overview

This skill runs a two-step pipeline:

1. **Annotate** (`annotate_vcf.py`): Parse VCF → query Ensembl VEP GRCh37 REST API in batches of 200 → produce full annotation CSV with gene, consequence, HGVS, rsID, population AF, ClinVar significance, UniProt, and AMP/ASCO/CAP tier
2. **Report** (`reformat_tiers.py`): 
- Filter to Tier 1–3 → reformat into clinical report CSV
- generate summary report from reference/report_template.docx

## Output Format

### Full annotation CSV (`{ID}_annotated.csv`)
`chrom, pos, id, ref, alt, ad, dp, sample_af, gene, most_severe_consequence, hgvsc, hgvsp, rsid, max_pop_af, clin_sig, uniprot, tier`

### Tiered report CSV (`{ID}_tiered_report.csv`)
`ASCO/AMP Classification | Gene | Canonical name | Accession | Nucleotide change | AA change | % VAF`

- **Canonical name** = Ensembl transcript ID (e.g., ENST00000269305.4)
- **Accession** = Ensembl protein ID (e.g., ENSP00000269305.4)
- **Nucleotide change** = HGVS coding (e.g., c.743G>A)
- **AA change** = HGVS protein (e.g., p.Arg248Gln)
- Sorted by tier (1→2→3), then descending VAF within each tier
- Tier 4 (benign/likely benign) excluded from report

## Tiering Logic (AMP/ASCO/CAP)

Reference: Li et al., J Mol Diagn. 2017;19:4-23

### Tier 1 — Strong Clinical Significance
- Known pathogenic (ClinVar) in established lymphoma driver gene
- Not a common polymorphism (population AF ≤ 1%)

### Tier 2 — Potential Clinical Significance
- Driver gene + high-impact consequence (frameshift, stop gained, splice donor/acceptor) + rare
- Driver gene + missense + likely pathogenic + rare
- Driver gene + missense + novel/very rare (pop AF < 0.1%) + not benign
- Driver gene + splice variant + any ClinVar pathogenic signal + rare

### Tier 3 — Unknown Clinical Significance
- Any cancer gene + moderate/high impact + not common + not benign
- Any cancer gene + splice variant + rare + not benign
- Any cancer gene + missense + has pathogenic ClinVar signal + pop AF ≤ 5%
- Broader cancer gene + high impact + rare

### Tier 4 — Benign / Likely Benign
- Common germline polymorphisms (pop AF > 1%)
- Benign ClinVar classification
- Non-driver gene variants
- Low-impact / modifier consequences in non-relevant genes

## Gene Lists

### Tier 1/2 Genes (Established Lymphoma Drivers)
**DLBCL / B-cell lymphoma**: 
TP53, MYC, BCL2, BCL6, MYD88, CD79B, CARD11, TNFAIP3, KMT2D, CREBBP, EZH2, EP300, 
ARID1A, NOTCH1, NOTCH2, PIM1, CCND1, CCND3, BTK, PLCG2, SF3B1, ATM, BIRC3, 
SOCS1, SGK1, TET2, GNA13, IRF4, FOXO1, MEF2B, PRDM1, NFKBIA

	
BTK, PLCG2, BCL2, EZH2, PIK3CD, MTOR, XPO1, MYD88, CD79B, CARD11, NOTCH1, 
NOTCH2, TP53, IDH2, SYK, IRAK4, MALT1, TNFAIP3, CCND1, CD19

**Hematologic drivers**: 
TP53, MYD88, CD79B, CD79A, EZH2, CREBBP, EP300, KMT2D, ARID1A, TET2, DNMT3A, 
IDH2, IDH1, SF3B1, SRSF2, U2AF1, ATM, BIRC3, NOTCH1, NOTCH2, CARD11, 
TNFAIP3, PIM1, PRDM1, IRF4, GNA13, FOXO1, MEF2B, CCND1, CCND3, BCL2, 
BCL6, MYC, STAT3, STAT6, SOCS1, NFKBIA, RHOA, IKZF1, IKZF3

### Tier 3 Genes (Broader Cancer-Associated)
**Chromatin/epigenetic**: 
KMT2D, CREBBP, EP300, EZH2, ARID1A, ARID1B, SMARCA4, SMARCB1, TET2, DNMT3A, 
IDH2, IDH1, SETD2, KDM6A, KDM5C, KMT2A, KMT2C, KMT2E, NSD2, NSD1, ASXL1, 
ASXL2, BCOR, BCORL1, CHD2, CHD4, ATRX, HIST1H1E, HIST1H1C, BCL7A

**DNA repair / cell cycle**: 
TP53, ATM, ATR, CHEK1, CHEK2, BRCA1, BRCA2, PALB2, RAD51, RAD51C, RAD51D, 
FANCA, FANCD2, BLM, WRN, MSH2, MSH6, MLH1, PMS2, POLE, POLD1, PARP1, 
CDKN2A, CDKN2B, RB1, CCND1, CCND2, CCND3, CDK4, CDK6, E2F1, MYC, BCL2, PTEN, TP73

**RTK / signaling**: 
EGFR, ERBB2, ERBB3, ERBB4, FGFR1, FGFR2, FGFR3, PDGFRA, PDGFRB, KIT, MET, FLT3, 
JAK1, JAK2, JAK3, STAT3, STAT5B, KRAS, NRAS, HRAS, BRAF, MAP2K1, MAP2K2, 
PIK3CA, PIK3CD, PIK3R1, AKT1, AKT2, AKT3, MTOR, SYK, LYN, BLK, BTK, PLCG2, 
CARD11, MYD88, IRAK4, TNFAIP3, NFKBIA

**Splicing**: 
SF3B1, SRSF2, U2AF1, U2AF2, ZRSR2, PRPF8, PRPF40B, SF1, RBM10, RBM15, RBM15B, 
DDX3X, DDX41, HNRNPK, HNRNPA1, HNRNPA2B1, SFPQ, FUBP1, WTAP, LUC7L2, PHF5A, 
TCERG1, EFTUD2, SMARCA4, BCOR, BCORL1

**Other lymphoma-associated**:
B2M, CIITA, CD58, FAS, CD70, TNFRSF14, GNA13, P2RY8, S1PR2, POU2AF1, ETV6, TBL1XR1, BTG1, BTG2, 
KLHL6, ZFP36L1, ZFP36L2, HIST1H1E, HIST1H1C, IRF8, REL, NFKBIE, TRAF3, BCL10, MALT1, SPEN, DTX1,
 UBE2A, RHOA, VAV1, STAT5B, CCR4, PLCG1, PRKCB, XPO1

## How to Run

### Prerequisites
```bash
pip install requests
```

### Single VCF
```bash
python annotate_vcf.py data/01.vcf
python reformat_tiers.py data/01_annotated.csv
```

### Batch (multiple VCFs)
Run annotation in parallel (each takes ~1–2 min depending on variant count):
```bash
python annotate_vcf.py data/01.vcf &
python annotate_vcf.py data/02.vcf &
python annotate_vcf.py data/03.vcf &
wait
python reformat_tiers.py data/01_annotated.csv
python reformat_tiers.py data/02_annotated.csv
python reformat_tiers.py data/03_annotated.csv
```

### Expected Input
- VCFv4.2 files, GRCh37 reference
- INFO field must contain `AD` (alt depth) and `DP` (total depth)
- Designed for PiSeq lymphoma ctDNA panels but works with any VCF meeting above criteria

### Expected Output
For input `data/XX.vcf`:
- `data/XX_annotated.csv` — full annotation with all 583+ variants and tier column
- `data/XX_tiered_report.csv` — Tier 1–3 clinical report in ASCO/AMP format

## VEP API Details
- Endpoint: `https://grch37.rest.ensembl.org/vep/homo_sapiens/region` (POST)
- Batch size: 200 variants per request
- Retry: up to 5 attempts with backoff on rate limiting (HTTP 429)
- Annotations requested: `hgvs`, `uniprot`, `protein`, `domains`, `canonical`, `pick`, `frequency`
- Variant types handled: SNV, deletion, insertion, MNV

## Modifying Gene Lists

To add genes to the tiering, edit the `TIER1_2_GENES` or `TIER3_GENES` sets in `annotate_vcf.py`. Tier 1/2 genes receive stricter (higher) tier assignments; Tier 3 genes receive Tier 3 for variants of uncertain significance.
