# ctDNA Lymphoma Variant Viewer (Flutter)

A cross-platform Flutter client that complements the
[whopark/ctDNA](https://github.com/whopark/ctDNA) lymphoma ctDNA annotation
pipeline. It provides a mobile/tablet/web UI for browsing annotated variant
calls, classifying somatic variants under AMP/ASCO/CAP guidelines (Li et al.,
*J Mol Diagn* 2017), and inspecting the curated lymphoma gene panels.

> Research / educational use only — **not a clinical diagnostic tool.**
> Do not upload real PHI.

## Features

- **Dashboard** — aggregate Tier distribution and top-mutated genes across all
  loaded cases (pie chart + bar plot via `fl_chart`).
- **Case browser** — list of patient cases with tier counts; tap into a case to
  see filtered variants (Tier / VAF threshold / gene & HGVS search).
- **Variant detail** — gene, HGVS.p / HGVS.c, genomic coords, VAF, depth,
  ClinVar significance, population AF, and gene-panel context (driver,
  drug target, risk-stratification) with example targeted agents.
- **Tier classifier** — interactive local re-implementation of
  `annotate_vcf.assign_tier()`. Enter a gene + VEP consequence + ClinVar
  significance + pop AF, get a Tier 1–4 call with rule trace.
- **Gene panels** — searchable lists for Tier 1/2 drivers, Tier 3 cancer genes,
  actionable drug targets (with example agents), and risk-stratification
  genes — ported from `annotate_vcf.py`.
- **CSV import** — load `{ID}_annotated.csv` files produced by the Python
  pipeline and persist them locally (SharedPreferences).
- **Sample data** — one-click synthetic cases for first-launch UX.

## Project layout

```
flutter_app/
├── lib/
│   ├── main.dart
│   ├── data/
│   │   ├── gene_panels.dart     # Tier 1/2, Tier 3, drug-target, risk gene sets
│   │   └── sample_data.dart     # Synthetic demo cases
│   ├── models/
│   │   ├── variant.dart         # Variant model (mirrors annotated CSV row)
│   │   └── case_record.dart
│   ├── services/
│   │   ├── tier_classifier.dart # AMP/ASCO/CAP tier rules (Dart port)
│   │   ├── csv_import.dart      # CSV → CaseRecord
│   │   └── case_repository.dart # SharedPreferences-backed store
│   ├── widgets/
│   │   ├── tier_chip.dart
│   │   └── variant_tile.dart
│   └── screens/
│       ├── home_screen.dart        # NavigationBar shell
│       ├── dashboard_screen.dart
│       ├── cases_screen.dart
│       ├── case_detail_screen.dart
│       ├── variant_detail_screen.dart
│       ├── classifier_screen.dart
│       └── gene_panel_screen.dart
└── pubspec.yaml
```

## Getting started

```bash
cd flutter_app
flutter pub get

# Web (Chrome / sandbox)
flutter run -d chrome
flutter build web --release

# Android
flutter run -d <device>
flutter build apk --release
```

Tested with Flutter 3.24.5 / Dart 3.5.4.

## Pipeline compatibility

The CSV importer expects the schema produced by `annotate_vcf.py`:

```
chrom,pos,id,ref,alt,ad,dp,sample_af,gene,most_severe_consequence,
hgvsc,hgvsp,rsid,max_pop_af,clin_sig,uniprot,tier
```

The Dart tier classifier mirrors the Python rules:

| Tier | Rule |
| ---- | ---- |
| Tier 1 | Driver gene + ClinVar pathogenic + pop AF ≤ 1 % |
| Tier 2 | Driver gene + high- or moderate-impact consequence, not benign |
| Tier 3 | Broader cancer gene + high- or moderate-impact, not benign |
| Tier 4 | Benign ClinVar or pop AF > 1 % (excluded from reports) |

## References

- Li MM, Datto M, Duncavage EJ, et al. *J Mol Diagn.* 2017;19(1):4–23.
- Chapuy B, et al. *Nat Med.* 2018;24(5):679–690.
- Schmitz R, et al. *N Engl J Med.* 2018;378(15):1396–1407.
