# ctDNA — Lymphoma ctDNA Variant Annotation Pipeline

Annotate lymphoma ctDNA panel VCF files using Ensembl VEP REST API (GRCh37) and classify somatic variants following AMP/ASCO/CAP tiering guidelines (Li et al., *J Mol Diagn*. 2017;19:4-23).

## Quick Start

### GUI (recommended)

```bash
pip install requests python-docx   # one-time dependencies
python ctdna_gui.py
```

### Command Line

```bash
# 1. Annotate VCF → full annotation CSV with tier assignments
python annotate_vcf.py sample.vcf

# 2. Generate tiered report CSV (Tier 1-3, actionable genes only)
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
  │     → Filters: VAF >= 1%, Tier 4 excluded, Tier 3 actionable only
  │
  ├─ reformat_tiers.py ──► {ID}_tiered_report.csv
  │     Filter Tier 1-3 (actionable Tier 3 only), format for clinical review
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

## AMP/ASCO/CAP Somatic Variant Tiering

| Tier | Classification | Criteria |
|------|---------------|----------|
| **Tier 1** | Strong clinical significance | Known pathogenic (ClinVar) in lymphoma driver gene, pop AF <= 1% |
| **Tier 2** | Potential clinical significance | High-impact or novel missense in driver gene, rare, not benign |
| **Tier 3** | Unknown clinical significance | Moderate/high impact in broader cancer gene, uncertain significance |
| **Tier 4** | Benign / likely benign | Common polymorphisms, benign ClinVar, non-driver genes (excluded from report) |

### Default Report Filters

| Filter | Default | Configurable |
|--------|---------|-------------|
| Minimum VAF | >= 1.0% | Yes (GUI spinbox, 0-100%) |
| Tier 4 | Excluded | Always excluded |
| Tier 3 | Actionable/risk-stratifying genes only | Yes (toggle + editable gene lists) |

## Gene Lists

### Tier 1/2 — Established Lymphoma Drivers (76 genes)

**DLBCL / B-cell lymphoma**: TP53, MYC, BCL2, BCL6, MYD88, CD79B, CD79A, CARD11, TNFAIP3, KMT2D, CREBBP, EZH2, EP300, ARID1A, NOTCH1, NOTCH2, PIM1, CCND1, CCND3, SOCS1, SGK1, TET2, GNA13, IRF4, FOXO1, MEF2B, PRDM1, NFKBIA, TCF3, ID3, STAT6, TNFRSF14, B2M, CIITA, CD58, FAS, BCL10, CD70, DTX1, UBE2A, SPEN, IRF8, BTG1, KLHL6, TBL1XR1

**Targeted therapy**: BTK, PLCG2, PI3KCA, PIK3CD, PIK3R1, PTEN, MTOR, ALK, JAK1, JAK2, STAT3, STAT5B, BRAF, KRAS, NRAS, MCL1

**Cell cycle / tumor suppressors**: CDKN2A, RB1, FBXW7, POT1, ATM

**Splicing / signaling**: SF3B1, BIRC3

**Other hematologic**: DNMT3A, IDH1, IDH2, NPM1, FLT3, BCOR, BCORL1, DDX3X

### Tier 3 — Broader Cancer-Associated (129 genes)

**Chromatin/epigenetic (30)**: KMT2D, CREBBP, EP300, EZH2, ARID1A, ARID1B, SMARCA4, SMARCB1, TET2, DNMT3A, IDH2, IDH1, SETD2, KDM6A, KDM5C, KMT2A, KMT2C, KMT2E, NSD2, NSD1, ASXL1, ASXL2, BCOR, BCORL1, CHD2, CHD4, ATRX, HIST1H1E, HIST1H1C, BCL7A

**DNA repair / cell cycle (35)**: TP53, ATM, ATR, CHEK1, CHEK2, BRCA1, BRCA2, PALB2, RAD51, RAD51C, RAD51D, FANCA, FANCD2, BLM, WRN, MSH2, MSH6, MLH1, PMS2, POLE, POLD1, PARP1, CDKN2A, CDKN2B, RB1, CCND1, CCND2, CCND3, CDK4, CDK6, E2F1, MYC, BCL2, PTEN, TP73

**RTK / signaling (41)**: EGFR, ERBB2, ERBB3, ERBB4, FGFR1, FGFR2, FGFR3, PDGFRA, PDGFRB, KIT, MET, FLT3, JAK1, JAK2, JAK3, STAT3, STAT5B, KRAS, NRAS, HRAS, BRAF, MAP2K1, MAP2K2, PIK3CA, PIK3CD, PIK3R1, AKT1, AKT2, AKT3, MTOR, SYK, LYN, BLK, BTK, PLCG2, CARD11, MYD88, IRAK4, TNFAIP3, NFKBIA, XPO1

**Splicing (24)**: SF3B1, SRSF2, U2AF1, U2AF2, ZRSR2, PRPF8, PRPF40B, SF1, RBM10, RBM15, RBM15B, DDX3X, DDX41, HNRNPK, HNRNPA1, HNRNPA2B1, SFPQ, FUBP1, WTAP, LUC7L2, PHF5A, TCERG1, EFTUD2

> Genes overlapping with Tier 1/2 are evaluated at Tier 1/2 first; only variants not meeting those criteria fall through to Tier 3.

### Tier 3 Reportable Whitelist (75 genes)

Only Tier 3 variants in actionable or risk-stratifying genes appear in clinical reports. Both lists are editable in the GUI.

**Actionable Drug Targets (54 genes)** — FDA-approved or late-stage clinical trial agents:

| Category | Genes | Example Agents |
|----------|-------|----------------|
| RTK / kinase | KIT, EGFR, ERBB2, ERBB3, FGFR1-3, PDGFRA, MET, FLT3 | imatinib, osimertinib, trastuzumab, erdafitinib, capmatinib, gilteritinib |
| JAK/STAT | JAK1, JAK2, JAK3 | ruxolitinib, fedratinib, tofacitinib |
| RAS/RAF/MEK | KRAS, NRAS, BRAF, MAP2K1, MAP2K2 | sotorasib, vemurafenib, trametinib |
| PI3K/AKT/mTOR | PIK3CA, PIK3CD, PIK3R1, AKT1, MTOR, PTEN | alpelisib, idelalisib, capivasertib, everolimus |
| BCR / NF-kB | BTK, PLCG2, CARD11, MYD88, IRAK4, SYK | ibrutinib, zanubrutinib, fostamatinib |
| Epigenetic | EZH2, IDH1, IDH2 | tazemetostat, ivosidenib, enasidenib |
| Cell cycle | CDK4, CDK6 | palbociclib, ribociclib, abemaciclib |
| DNA repair / PARP | BRCA1, BRCA2, PALB2, ATM, ATR, CHEK1, CHEK2, PARP1 | olaparib, niraparib, ceralasertib |
| MMR / IO | MSH2, MSH6, MLH1, PMS2 | pembrolizumab (MSI-H), dostarlimab |
| Splicing | SF3B1, SRSF2, DDX3X, DDX41 | H3B-8800 |
| Lymphoma-specific | XPO1, PIM1, BIRC3 | selinexor (XPOVIO), AZD1208 |

**Risk Stratification (21 genes)** — prognostic / diagnostic markers:

| Gene | Clinical Significance |
|------|----------------------|
| TP53 | Poor prognosis across cancers |
| MYC, BCL2 | Aggressive biology, double-hit marker |
| KMT2D, CREBBP, EP300, KMT2C | Epigenetic drivers, prognostic in FL/DLBCL |
| ARID1A | SWI/SNF, potential IO sensitivity marker |
| DNMT3A, TET2, ASXL1 | CHIP, prognostic in AML/MDS |
| SETD2, BCOR | Epigenetic, prognostic in hematologic malignancies |
| FBXW7 | Poor prognosis, Notch/mTOR pathway |
| CDKN2A, RB1, CCND1 | Cell cycle, prognostic |
| STAT3, STAT5B | JAK/STAT activation markers |
| TNFAIP3, NFKBIA | NF-kB pathway, ABC-DLBCL markers |

## GUI Application

Launch the Windows GUI with `python ctdna_gui.py`.

```
+------------------------------------------------------------+
|  ctDNA Annotation Pipeline — Lymphoma Panel                |
+------------------------------------------------------------+
|  [ Input Files ]                                           |
|    Browse VCF Files / Browse Folder / Clear All            |
|    ┌──────────────────────────────────────────┐             |
|    │ 01-JJH_10679562.vcf                      │             |
|    │ 02-OKW_10673102.vcf                      │             |
|    └──────────────────────────────────────────┘             |
|  [ Output Settings ]                                       |
|    Base Directory: C:/.../ctDNA/         [Browse...]        |
|    Batch Folder: [0224]     → C:/.../ctDNA/0224             |
|  [ Filter Configuration ]                                  |
|    Include Tiers: [x] Tier 1  [x] Tier 2  [x] Tier 3      |
|                                     Min VAF (%): [1.0]     |
|    [x] Tier 3: Report only genes in lists below  [Reset]   |
|    +-- Actionable Drug Targets ---+-- Risk Stratification -+|
|    | AKT1, ATM, ATR, BIRC3,      | ARID1A, ASXL1, BCL2,   ||
|    | BRAF, BRCA1, BRCA2, BTK,    | BCOR, CCND1, CDKN2A,   ||
|    | CDK4, CDK6, ...  (54 genes) | CREBBP, ...  (21 genes) ||
|    +------------------------------+------------------------+|
|  [ Patient Metadata (Optional) ]                           |
|    File: [dropdown]  Patient / Reg No / Specimen / Date    |
|  [ Pipeline Control ]                                      |
|    [Step 1: Annotate] [Step 2: Tier] [Step 3: DOCX]       |
|    [        Run Full Pipeline        ]       [Cancel]      |
|    Progress: [==============60%==============] File 2/4    |
|  [ Log | Tier Summary ]                                    |
|    > Querying VEP batch 2/3 (200 variants)...              |
|    > Done! 538/538 annotated                               |
|  [Open Output Folder]  [Open Latest Report]                |
+------------------------------------------------------------+
```

### GUI Features

| Feature | Description |
|---------|-------------|
| **Multi-file selection** | Browse individual VCFs or load all VCFs from a folder |
| **Batch folder naming** | Configurable output subfolder name (default: `MMDD` date) for organizing analysis runs |
| **Auto-metadata** | Patient name and registration number auto-parsed from filename (e.g. `01-JJH_10679562` → JJH / 10679562) |
| **Tier selection** | Checkboxes to include/exclude Tier 1, 2, or 3 from reports |
| **VAF threshold** | Adjustable minimum VAF% (spinbox, 0-100%, 0.5% step) |
| **Editable gene lists** | Two inline text areas for drug targets and risk stratification genes; add/remove genes freely |
| **Reset Defaults** | Restore original curated gene lists with one click |
| **Step-by-step or full pipeline** | Run individual steps or all 3 in sequence |
| **Threaded execution** | GUI stays responsive during VEP API calls; cancel anytime |
| **Real-time progress** | Per-batch VEP progress bar, file counter, color-coded log |
| **Tier Summary tab** | Treeview table showing per-case tier distribution |
| **Output actions** | Open output folder in Explorer, open latest .docx report directly |

### Pipeline Steps

| Button | Action | Input | Output |
|--------|--------|-------|--------|
| **Step 1: Annotate VCF** | Ensembl VEP REST API annotation + AMP/ASCO/CAP tiering | `.vcf` files | `{ID}_annotated.csv` |
| **Step 2: Tier Report** | Filter by tier/VAF/gene lists, format for clinical review | `_annotated.csv` | `{ID}_tiered_report.csv` |
| **Step 3: DOCX Report** | Populate KBB template with variants + interpretation | `_annotated.csv` + `_tiered_report.csv` | `{ID}_clinical_report.docx` |
| **Run Full Pipeline** | All 3 steps sequentially for each VCF | `.vcf` files | All outputs above |

---

## User Manual

### 1. Installation

```bash
# Clone the repository
git clone https://github.com/whopark/ctDNA.git
cd ctDNA

# Install dependencies
pip install requests python-docx
```

**Requirements**: Python 3.8+, Windows 10/11 (GUI uses tkinter + `os.startfile`)

### Patient meta and interpretation files (SPEC-REPORT-001)

- `interpretations.yaml` — case-id to clinical interpretation text mapping. Resolution: exact case_id → prefix match → KB fallback → empty. Edit to add new cases without touching source.
- `{case_dir}/meta.json` — per-case patient/specimen/signatory metadata; auto-generated as a blank scaffold by the GUI when a new case folder is created. Contains PHI (patient_name, birth_date, reg_no, ordering_doctor) and is git-ignored by default.

Additional dependency: `pyyaml` (>=6.0). Install with:

```bash
pip install pyyaml
```

### 2. Running the GUI

```bash
python ctdna_gui.py
```

### 3. Loading VCF Files

1. Click **Browse VCF Files...** to select individual `.vcf` files, or **Browse Folder...** to load all VCFs from a directory.
2. Selected files appear in the file list. Use **Clear All** to reset.
3. VCF files must be GRCh37 reference with `AD` and `DP` fields in the INFO column.

### 4. Output Settings

| Field | Description | Default |
|-------|-------------|---------|
| **Base Directory** | Root folder for all pipeline outputs | Repository root |
| **Batch Folder** | Subfolder name for this analysis batch | Today's date (`MMDD`) |

The effective output path is `Base Directory / Batch Folder / {case_id}/`. The live preview below the fields shows the resolved path.

**Examples**:
- Base `C:\ctDNA` + Batch `0224` → outputs to `C:\ctDNA\0224\01-JJH_10679562\`
- Base `C:\ctDNA` + Batch `reanalysis` → outputs to `C:\ctDNA\reanalysis\01-JJH_10679562\`
- Leave Batch Folder empty → outputs directly to `C:\ctDNA\01-JJH_10679562\`

### 5. Filter Configuration

#### Tier Selection

Check or uncheck **Tier 1**, **Tier 2**, **Tier 3** to include or exclude each tier from the annotated CSV and tiered reports.

#### Minimum VAF (%)

Set the minimum variant allele frequency threshold. Variants below this VAF are excluded from all outputs.

| Setting | Effect |
|---------|--------|
| `1.0` (default) | Only variants with VAF >= 1% appear in reports |
| `0.5` | Include lower-frequency variants (higher sensitivity, more noise) |
| `5.0` | Only high-confidence variants |
| `0.0` | No VAF filter (include all) |

#### Tier 3 Gene Filter

When checked, **"Tier 3: Report only genes in lists below"** restricts Tier 3 variants to genes in the two editable lists:

**Actionable Drug Targets** (left panel):
- Genes with FDA-approved therapies or late-stage clinical trial agents
- Default: 54 genes (KIT, EGFR, BRCA1/2, BTK, EZH2, etc.)

**Risk Stratification** (right panel):
- Prognostic and diagnostic biomarkers relevant to lymphoma
- Default: 21 genes (TP53, MYC, BCL2, KMT2D, CREBBP, etc.)

**Editing gene lists**:
- Type directly into either text area to add or remove genes
- Genes can be separated by commas, spaces, or newlines
- Gene names are case-insensitive (auto-converted to uppercase)
- The gene count updates live as you edit
- Click **Reset Defaults** to restore the original curated lists

**When unchecked**: All Tier 3 genes in the 129-gene `TIER3_GENES` list appear in reports (no filtering).

### 6. Patient Metadata

1. Select a case from the **File** dropdown.
2. Fill in **Patient** name, **Reg No**, **Specimen** type, and **Test Date**.
3. Click **Save** to store metadata for that case.
4. Metadata is auto-populated from filenames when possible (e.g., `01-JJH_10679562` → Patient: JJH, Reg No: 10679562).
5. Metadata is used in Step 3 (DOCX report generation) to populate the clinical report header.

### 7. Running the Pipeline

#### Full Pipeline (recommended)

Click **Run Full Pipeline** to execute all three steps sequentially for every loaded VCF file:
1. VEP annotation + tier assignment → `_annotated.csv`
2. Tiered report generation → `_tiered_report.csv`
3. Clinical DOCX report → `_clinical_report.docx`

The pipeline header in the log shows the active filter settings (VAF threshold, tier selection, batch folder).

#### Step-by-Step

| Button | Prerequisite |
|--------|-------------|
| **Step 1: Annotate VCF** | VCF files loaded |
| **Step 2: Tier Report** | Step 1 completed (needs `_annotated.csv`) |
| **Step 3: DOCX Report** | Steps 1-2 completed (needs both CSVs) + `python-docx` installed |

#### Cancellation

Click **Cancel** at any time to stop the current pipeline run. The GUI will finish the current VEP batch and halt.

### 8. Viewing Results

**Log tab**: Real-time pipeline output with color-coded messages:
- Blue: pipeline headers and section markers
- Green: success messages
- Red: errors and warnings

**Tier Summary tab**: Table showing per-case results:

| Column | Description |
|--------|-------------|
| Case ID | VCF filename stem |
| Total | Total variants in VCF |
| Tier 1-4 | Count of variants per tier (all variants, pre-filter) |
| Status | Current pipeline status |

**Output actions**:
- **Open Output Folder**: Opens the batch output directory in Windows Explorer
- **Open Latest Report**: Opens the most recently generated `.docx` report (or `.csv` if no DOCX)

### 9. Command-Line Usage

For scripting or batch processing without the GUI:

```bash
# Annotate a single VCF
python annotate_vcf.py path/to/sample.vcf
# Output: path/to/sample_annotated.csv

# Generate tiered report
python reformat_tiers.py path/to/sample_annotated.csv
# Output: path/to/sample_tiered_report.csv

# Generate DOCX reports (edit case metadata in script)
python .claude/generate_docx_reports.py
```

Command-line scripts use the same default filters (VAF >= 1%, Tier 4 excluded, Tier 3 actionable only). To change filter settings, edit the constants in `annotate_vcf.py`:
- `DRUG_TARGET_GENES` — actionable drug target whitelist
- `RISK_STRATIFICATION_GENES` — prognostic marker whitelist
- `ACTIONABLE_TIER3_GENES` — combined set (auto-computed as union)

### 10. Customizing Gene Lists

#### In the GUI

Edit the gene text areas directly in the Filter Configuration section. Changes take effect on the next pipeline run.

#### In the source code

Edit `annotate_vcf.py`:

```python
# Tier 1/2 driver genes — add/remove for your panel
TIER1_2_GENES = { "TP53", "MYC", ... }

# Tier 3 broader gene list — all cancer-associated genes to evaluate
TIER3_GENES = { "KMT2A", "KMT2C", ... }

# Drug targets — genes with therapeutic agents
DRUG_TARGET_GENES = { "KIT", "EGFR", ... }

# Risk stratification — prognostic markers
RISK_STRATIFICATION_GENES = { "TP53", "MYC", ... }
```

---

## Repository Structure

```
ctDNA/
├── ctdna_gui.py                 # Windows GUI application (tkinter)
├── annotate_vcf.py              # VEP annotation + tiering (main script)
├── reformat_tiers.py            # Generate tiered report CSV
├── .claude/
│   └── generate_docx_reports.py # Generate .docx clinical reports
├── {MMDD}/                      # Patient case data (batch folder)
│   ├── {case_id}/
│   │   ├── *.vcf                # Input VCF
│   │   ├── *_annotated.csv      # Full VEP annotation + tiers
│   │   ├── *_tiered_report.csv  # Tier 1-3 clinical report CSV
│   │   └── *_clinical_report.docx  # Formatted clinical report
│   └── .../
├── .agents/skills/kbb-annotation/
│   ├── SKILL.md                 # Full skill documentation
│   ├── scripts/                 # Canonical script copies
│   └── reference/
│       └── report_template.docx # Clinical report template (Korean)
├── CLAUDE.md                    # Claude Code workspace instructions
├── README.md                    # This file
└── skills-lock.json             # Installed skills manifest
```

## Dependencies

- **Python 3.8+**
- `requests` — Ensembl VEP REST API calls
- `python-docx` — Clinical report .docx generation (optional, for Step 3)
- `tkinter` — GUI (included with standard Python on Windows)

## References

- Li MM, Datto M, Duncavage EJ, et al. Standards and Guidelines for the Interpretation and Reporting of Sequence Variants in Cancer. *J Mol Diagn*. 2017;19(1):4-23.
- Chapuy B, Stewart C, Dunford AJ, et al. Molecular subtypes of diffuse large B cell lymphoma are associated with distinct pathogenic mechanisms and outcomes. *Nat Med*. 2018;24(5):679-690.
- Schmitz R, Wright GW, Huang DW, et al. Genetics and Pathogenesis of Diffuse Large B-Cell Lymphoma. *N Engl J Med*. 2018;378(15):1396-1407.
