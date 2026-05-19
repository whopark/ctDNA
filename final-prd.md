# ctDNA Annotation Pipeline — Final PRD

## 1. Product Overview

**ctDNA Annotation Pipeline**은 림프종(Lymphoma) ctDNA 패널 VCF 파일을 자동 분석하여
AMP/ASCO/CAP 가이드라인 기반 변이 분류(Tiering)와 임상 보고서(.docx)를 생성하는 Windows
데스크탑 애플리케이션이다.

- **Target Users**: 진단검사의학과 임상 유전체 분석 담당자
- **Delivery**: `ctDNA.exe` (22MB, Python 설치 불필요)
- **Reference Genome**: GRCh37 (hg19)
- **Classification Standard**: AMP/ASCO/CAP Somatic Variant Classification
  (Li et al., J Mol Diagn. 2017;19:4-23)

---

## 2. Architecture

```
VCF input (GRCh37, AD/DP in INFO)
  |
  v
annotate_vcf.py ── VEP REST API (grch37.rest.ensembl.org)
  |                  + ClinVar / pop AF / UniProt
  |                  + AMP/ASCO/CAP tier assignment
  v
{ID}_annotated.csv (17 columns, VAF >= 1%, Tier 1-3)
  |
  v
reformat_tiers.py ── HGVSc/p parsing, 7-column formatted CSV
  |
  v
{ID}_tiered_report.csv (Tier 1 > Tier 2 > Tier 3, VAF desc)
  |
  v
generate_clinical_reports.py ── template.docx + meta.json
  |                               + interpretations.yaml
  |                               + qc_stats + kb.json
  v
{ID}_clinical_report.docx (Korean-language clinical report)
  |
  v
kb_update.py ── harvest signed-out reports -> kb.json
                 (tier hints, therapeutic text, interpretation paragraphs)
```

### Delivery Modes

| Mode | Entry Point | Description |
|------|-------------|-------------|
| **Windows GUI** | `ctDNA.exe` or `python ctdna_gui.py` | tkinter 960x920 desktop app |
| **CLI** | `python annotate_vcf.py <file.vcf>` | headless single-VCF annotation |
| **Web (sandbox)** | `python web/server.py` | FastAPI + HTMX (Railway-deployable) |

---

## 3. Pipeline Modules

### 3.1 VEP Annotation (`annotate_vcf.py`, 609 lines)

- Ensembl VEP REST API (GRCh37) batch POST, 200 variants/request
- Retry with exponential backoff (5s base, max 5 retries)
- Extracts: gene, consequence, HGVSc, HGVSp, rsID, max pop AF, ClinVar, UniProt
- KB tier-hint promotion (from `kb.json`): past sign-out history can promote (never demote) tiers

### 3.2 Tiering Algorithm (`assign_tier`)

| Tier | Criteria |
|------|----------|
| **Tier 1** | TIER1_2 gene + ClinVar pathogenic (exact token match) + pop AF <= 1% |
| **Tier 2** | Driver gene + high-impact truncating, OR moderate + likely_pathogenic, OR moderate + rare (<0.1%) + not benign, OR splice + pathogenic signal |
| **Tier 3** | Cancer gene + moderate/high impact + not common + not benign; OR splice/pathogenic in low-impact |
| **Tier 4** | All remaining (excluded from report) |

**ClinVar tokenization**: `clin_sig` is split on `|`/`/` delimiters to prevent substring false matches
(e.g., `likely_pathogenic` is not matched as `pathogenic` for Tier 1).

### 3.3 Gene Lists

| List | Count | Purpose |
|------|-------|---------|
| `TIER1_2_GENES` | ~55 | Established lymphoma drivers + targeted therapy genes |
| `TIER3_GENES` | ~100+ | Broader cancer-associated genes (chromatin, DNA repair, RTK, splicing) |
| `DRUG_TARGET_GENES` | ~55 | FDA-approved or clinical trial agents |
| `RISK_STRATIFICATION_GENES` | ~20 | Prognostic/diagnostic markers |
| `ACTIONABLE_TIER3_GENES` | ~75 | Union of drug targets + risk stratification (Tier 3 report filter) |

### 3.4 Report Generation (`generate_clinical_reports.py`, 308 lines)

- Template: `template.docx` (176KB, Korean-language clinical report layout)
- Tables populated: patient info (T0), Tier 1/2 variants (T3), Tier 3 variants (T4),
  interpretation (T6), limitations + variant counts (T8), QC stats (T14), signatures (T15)
- Tier 1/2: sorted by tier then VAF descending
- Tier 3: top 14 variants by VAF descending
- Therapeutic implications: KB-learned text preferred, hardcoded fallback dict

### 3.5 Knowledge Base (`kb.py` + `kb_update.py`)

Self-updating feedback loop:

```
signed-out .docx reports
  -> kb_update.py harvests therapeutic text, interpretation paragraphs, tier assignments
  -> kb.json stores:
       tier_hints      — promote variants in future runs
       therapeutics    — gene-level drug implication text (voting by frequency)
       interpretations — Korean interpretation paragraphs
       variant_evidence — per-variant tier history + VAF
  -> annotate_vcf.py / generate_clinical_reports.py consult KB at runtime
```

### 3.6 Output File Formats

**`_annotated.csv`** (17 columns):
```
chrom, pos, id, ref, alt, ad, dp, sample_af, gene, most_severe_consequence,
hgvsc, hgvsp, rsid, max_pop_af, clin_sig, uniprot, tier
```

**`_tiered_report.csv`** (7 columns):
```
ASCO/AMP Classification, Gene, Canonical name, Accession,
Nucleotide change, AA change, % VAF
```

**`_clinical_report.docx`**: Korean-language clinical report per `template.docx` layout.

---

## 4. GUI Features (`ctdna_gui.py`, 1,225 lines)

Window: 960 x 920 px, minimum 820 x 780 px
Title: "ctDNA Annotation Pipeline -- Lymphoma Panel"

| Section | Features |
|---------|----------|
| **Input Files** | Multi-select VCF browse (files or folder), scrollable listbox |
| **Output Settings** | Base directory + batch folder (auto MMDD date), live path preview |
| **Filter Config** | Tier checkboxes (1/2/3), min VAF% spinbox (default 1.0%), Tier 3 actionable-only toggle, editable gene lists with Reset Defaults |
| **Metadata** | Patient name, reg. number, specimen type, test date, interpretation (5 fields) |
| **Control** | Run Pipeline / Cancel buttons |
| **Log** | Scrolled text area (stderr + queue-based background thread output) |
| **KB Update** | "Update Knowledge Base" button |

Pipeline runs in background thread (`PipelineWorker`) with queue-based progress reporting.

---

## 5. Standalone Executable Build

### 5.1 Frozen Path Resolution (`frozen_path.py`)

```python
# PyInstaller bundles data in sys._MEIPASS (read-only temp dir)
# frozen_path.py provides:
#   is_frozen()       -> True if running as .exe
#   bundle_dir()      -> sys._MEIPASS or repo root
#   data_path(name)   -> bundled data file path (template.docx)
#   writable_kb_path() -> exe directory for kb.json (read/write)
```

### 5.2 Build Artifacts

| File | Purpose |
|------|---------|
| `ctdna.spec` | PyInstaller spec: single-file, no console, bundles template.docx + kb.json |
| `build.bat` | One-click build: `pip install` deps + `pyinstaller ctdna.spec` |
| `dist/ctDNA.exe` | 22MB standalone executable |

### 5.3 Build Command

```batch
build.bat
# or
python -m PyInstaller ctdna.spec
```

### 5.4 Runtime Behavior

- `template.docx`: bundled inside exe (read-only), resolved via `_find_template()` -> `data_path()`
- `kb.json`: copied from bundle to exe directory on first run (writable for KB updates)
- Hidden imports: `requests`, `docx`, `lxml`, `lxml.etree`, `lxml._elementpath`, all project modules
- Dependencies: `requests`, `python-docx`, `lxml` (transitive)

---

## 6. Patched Scripts for Frozen Compatibility

| File | Change |
|------|--------|
| `kb.py` | `DEFAULT_KB_PATH` uses `writable_kb_path()` when frozen |
| `generate_clinical_reports.py` | `_find_template()` checks `data_path("template.docx")` first when frozen |
| `ctdna_gui.py` | Bootstrap: copies bundled `kb.json` to exe dir on first run via `shutil.copy2` |

---

## 7. 0519 Batch Results (2026-05-19)

### 7.1 Summary

| Case | VCF Variants | Tier 1 | Tier 2 | Tier 3 | Reportable | DOCX |
|------|-------------|--------|--------|--------|------------|------|
| 01-HTS | 2,830 | 2 | 195 | 46 | 243 | 199KB |
| 02-CKL | 420 | 0 | 7 | 18 | 25 | 174KB |
| 03-CBS | 389 | 0 | 10 | 15 | 25 | 175KB |
| 04-JYS | 393 | 1 | 7 | 19 | 26 | 174KB |
| 05-WYG | 2,170 | 5 | 173 | 46 | 224 | 196KB |

### 7.2 Notable Findings

- **01-HTS**: Tier 1 hits — CREBBP c.4471C>A p.Gln1491Lys (10.31% VAF),
  TP53 c.730G>A p.Gly244Ser (5.03% VAF). High-VAF Tier 2: TP53 p.Arg282Trp (84.07%),
  JAK1 p.Arg1041Trp (49.11%), MYC p.Leu164Val (44.86%), CD79B splice (43.55%).
- **05-WYG**: 5 Tier 1 variants, 173 Tier 2 — high-burden case.
- **02-CKL / 03-CBS / 04-JYS**: Low-burden cases (25-26 reportable), no or one Tier 1.
- **04-JYS**: Single Tier 1 variant detected.

### 7.3 Output Files per Case

```
0519/
  {ID}.vcf                    # Input
  {ID}_annotated.csv          # 17-col annotation (Tier 1-3, VAF >= 1%)
  {ID}_tiered_report.csv      # 7-col formatted report
  {ID}_clinical_report.docx   # Korean clinical report
```

---

## 8. Git History

| Commit | Description |
|--------|-------------|
| `1c4da22` | feat(build): standalone ctDNA.exe via PyInstaller |
| `8893c3c` | refactor(web): modernize FastAPI lifecycle |
| `e3553d6` | docs(repo): refresh CLAUDE.md, harden PHI gitignore |
| `efc7138` | chore(security): untrack PHI files from .claude/ |
| `3307db1` | feat(web): FastAPI + HTMX sandbox UI |
| `8ca4e0f` | fix(report): Table 14 unicode >= fix |
| `7881e2b` | feat(report): SPEC-REPORT-001 template.docx compliance |
| `8f6a395` | fix(tiering): ClinVar substring match bug (likely_pathogenic -> Tier 1) |
| `7676adb` | Fix DOCX report generation in GUI |
| `29fd927` | Add 0325 batch: 5 lymphoma ctDNA cases |
| `4cc21a6` | Update README with user manual and gene list docs |
| `105071f` | Add editable drug target and risk stratification gene lists |
| `9fe7fda` | Add GUI config: tier selection, VAF%, batch folder |
| `9b36362` | Filter Tier 3 to actionable/risk-stratifying genes only |
| `54ec746` | Filter reports to VAF >= 1%, exclude Tier 4 |
| `b39a03f` | Add Windows GUI for full pipeline |
| `d30971e` | Initial commit: lymphoma ctDNA variant annotation pipeline |

---

## 9. Dependencies

| Package | Version | Purpose |
|---------|---------|---------|
| `requests` | 2.33+ | VEP REST API calls |
| `python-docx` | 1.2+ | .docx report generation/reading |
| `lxml` | (transitive) | XML parsing for python-docx |
| `pyinstaller` | 6.20+ | Build-time only: standalone exe packaging |

Runtime: Python 3.11+ (bundled in exe, not required on target machine).

---

## 10. Security & PHI

- `meta.json` (patient name, reg_no, birth_date, ordering_doctor) is `.gitignore`d
- `*_clinical_report.docx`, `*.vcf`, `*_annotated.csv`, `*_tiered_report.csv` excluded from git
- GUI never overwrites operator-edited `meta.json` fields
- KB stores aggregated statistics only, no patient-level PHI

---

## 11. Known Limitations

1. **Internet required**: VEP REST API calls need network access
2. **GRCh37 only**: hg38 VCFs are not supported
3. **No batch parallelism**: VCF files are annotated sequentially (VEP rate limits)
4. **Tier 3 cap**: DOCX report shows top 14 Tier 3 variants by VAF
5. **meta.json manual entry**: Patient metadata must be filled in separately per case
6. **KB promotion only**: tier hints can upgrade but never downgrade tier assignments

---

## 12. Future Considerations

- GRCh38 support via VEP endpoint switch
- OncoKB / CIViC API integration for evidence-level annotations
- Batch-level summary report (cross-case statistics)
- Automated meta.json population from LIS/HIS interface
- Digital signature integration for final report sign-off
