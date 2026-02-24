---
name: kbb-annotation
description: "Annotate lymphoma ctDNA panel VCF files using Ensembl VEP (GRCh37) with AMP/ASCO/CAP somatic variant tiering. Produces clinical-grade tiered reports. Use when the user says 'annotate VCF', 'annotate .vcf', 'run kbb annotation', 'tier variants', or provides a VCF file for lymphoma/ctDNA analysis."
allowed-tools: Read, Write, Edit, Bash, Glob, Grep
---

# KBB Annotation — Lymphoma ctDNA Variant Annotation & Tiering

> Annotate VCF files from lymphoma ctDNA panels via Ensembl VEP REST API (GRCh37), classify variants using AMP/ASCO/CAP somatic tiering, and produce clinical report CSVs.

## Overview

This skill runs a two-step pipeline:

1. **Annotate** (`annotate_vcf.py`): Parse VCF → query Ensembl VEP GRCh37 REST API in batches of 200 → produce full annotation CSV with gene, consequence, HGVS, rsID, population AF, ClinVar significance, UniProt, and AMP/ASCO/CAP tier
2. **Report** (`reformat_tiers.py`): Filter to Tier 1–3 → reformat into clinical report CSV

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
**DLBCL / B-cell lymphoma**: TP53, MYD88, CD79B, CD79A, EZH2, CREBBP, EP300, BCL2, BCL6, MYC, CARD11, TCF3, ID3, KMT2D, ARID1A, NOTCH1, NOTCH2, TNFAIP3, FOXO1, PRDM1, IRF4, SOCS1, STAT6, GNA13, MEF2B, TNFRSF14, B2M, CIITA, CD58, FAS

**Targeted therapy**: BTK, PI3KCA, PIK3CD, MTOR, ALK, JAK1, JAK2, STAT3, STAT5B, BRAF, KRAS, NRAS

**Hematologic drivers**: TET2, DNMT3A, IDH1, IDH2, NPM1, FLT3, BCOR, BCORL1, DDX3X, PIM1, SGK1

### Tier 3 Genes (Broader Cancer-Associated)
**Chromatin/epigenetic**: KMT2A, KMT2C, SETD2, NSD2, WHSC1, ARID1B, ARID2, SMARCA4, PBRM1

**DNA repair / cell cycle**: ATM, ATR, CHEK2, BRCA1, BRCA2, RB1, CDKN2A, CDK6

**RTK / signaling**: EGFR, ERBB2, ERBB3, MET, RET, ROS1, KIT, PDGFRA, FBXW7

**Splicing**: SF3B1, U2AF1, SRSF2, ZRSR2

**Other lymphoma-associated**: XPO1, MED12, POT1, ITPKB, NFKBIE, TRAF3, BIRC3, MAP3K14, MALT1, RHOA, TBL1XR1, UBR5, DTX1, PCLO, P2RY8, ZFP36L1, DUSP2, HIST1H1E, HIST1H1C, HIST1H1B, HIST1H1D, NF1, NF2, MTOR, TSC1, TSC2, IKZF1, PAX5, EBF1, RUNX1, GATA3

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
