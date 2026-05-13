"""Pipeline driver — calls existing annotate/reformat/report functions in-process.

Designed for the FastAPI sandbox: every step writes into the session root,
and progress is streamed line-by-line to a log file the UI can poll via HTMX.
"""
from __future__ import annotations

import csv
import os
import sys
import time
from pathlib import Path

# Make the repo root importable when running as `uvicorn web.app:app`
_REPO_ROOT = Path(__file__).resolve().parent.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from annotate_vcf import (  # noqa: E402
    ACTIONABLE_TIER3_GENES,
    BATCH_SIZE,
    OUT_FIELDS,
    assign_tier,
    build_vep_input,
    extract_annotation,
    parse_vcf,
    query_vep_batch,
)
from reformat_tiers import parse_hgvsc, parse_hgvsp  # noqa: E402
from generate_clinical_reports import generate_report  # noqa: E402

MIN_VAF = 0.01
TIER_ORDER = {"Tier 1": 0, "Tier 2": 1, "Tier 3": 2}
TIERED_FIELDS = [
    "ASCO/AMP Classification",
    "Gene",
    "Canonical name",
    "Accession",
    "Nucleotide change",
    "AA change",
    "% VAF",
]


def run_annotation(vcf_path: Path, out_csv: Path, log) -> dict:
    """Step 1: VEP annotation + tier assignment. Returns tier counts."""
    log(f"Parsing VCF: {vcf_path.name}")
    variants = parse_vcf(str(vcf_path))
    log(f"Found {len(variants)} variants")
    if not variants:
        raise ValueError("No variants found in VCF — check format and INFO AD/DP fields")

    vep_inputs = [build_vep_input(v) for v in variants]
    n_batches = (len(vep_inputs) + BATCH_SIZE - 1) // BATCH_SIZE
    all_results: list = []
    for i in range(0, len(vep_inputs), BATCH_SIZE):
        batch_num = i // BATCH_SIZE + 1
        batch = vep_inputs[i:i + BATCH_SIZE]
        log(f"VEP batch {batch_num}/{n_batches} ({len(batch)} variants)")
        all_results.extend(query_vep_batch(batch))
        if batch_num < n_batches:
            time.sleep(1)

    result_by_input = {
        r.get("input", "").strip(): r for r in all_results if r.get("input")
    }

    tier_counts = {"Tier 1": 0, "Tier 2": 0, "Tier 3": 0, "Tier 4": 0}
    written = 0
    with out_csv.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=OUT_FIELDS)
        writer.writeheader()
        for v, vep_inp in zip(variants, vep_inputs):
            row = {k: v[k] for k in ["chrom", "pos", "id", "ref", "alt", "ad", "dp", "sample_af"]}
            res = result_by_input.get(vep_inp)
            if res:
                row.update(extract_annotation(res))
            else:
                row.update({k: "NA" for k in [
                    "gene", "most_severe_consequence", "hgvsc", "hgvsp",
                    "rsid", "max_pop_af", "clin_sig", "uniprot",
                ]})
            row["tier"] = assign_tier(row)
            tier_counts[row["tier"]] += 1
            try:
                vaf = float(row["sample_af"])
            except (TypeError, ValueError):
                continue
            if vaf < MIN_VAF or row["tier"] == "Tier 4":
                continue
            if row["tier"] == "Tier 3" and row.get("gene", "NA") not in ACTIONABLE_TIER3_GENES:
                continue
            writer.writerow(row)
            written += 1

    log(f"Annotation done — {written} reportable rows written")
    return {"tier_counts": tier_counts, "reportable": written, "total": len(variants)}


def run_tiering(annotated_csv: Path, out_csv: Path, log) -> int:
    """Step 2: filter to Tier 1-3 + parse HGVS, sort by tier and VAF."""
    log("Reformatting tiered report")
    with annotated_csv.open(encoding="utf-8") as fin:
        rows = list(csv.DictReader(fin))

    keep = []
    for r in rows:
        if r["tier"] not in TIER_ORDER:
            continue
        try:
            vaf = float(r["sample_af"])
        except (TypeError, ValueError):
            continue
        if vaf < MIN_VAF:
            continue
        if r["tier"] == "Tier 3" and r["gene"] not in ACTIONABLE_TIER3_GENES:
            continue
        keep.append(r)
    keep.sort(key=lambda r: (TIER_ORDER[r["tier"]], -float(r["sample_af"])))

    with out_csv.open("w", newline="", encoding="utf-8") as fout:
        writer = csv.DictWriter(fout, fieldnames=TIERED_FIELDS)
        writer.writeheader()
        for r in keep:
            transcript, nuc = parse_hgvsc(r["hgvsc"])
            accession, aa = parse_hgvsp(r["hgvsp"])
            writer.writerow({
                "ASCO/AMP Classification": r["tier"],
                "Gene": r["gene"],
                "Canonical name": transcript,
                "Accession": accession,
                "Nucleotide change": nuc,
                "AA change": aa,
                "% VAF": f"{float(r['sample_af']) * 100:.2f}%",
            })
    log(f"Tiered report: {len(keep)} variants")
    return len(keep)


def run_report(case_id: str, tiered_csv: Path, annotated_csv: Path, out_docx: Path, log) -> None:
    """Step 3: render DOCX from template using meta.json in the same dir."""
    log("Generating DOCX clinical report")
    generate_report(
        case_id=case_id,
        tiered_csv=str(tiered_csv),
        annotated_csv=str(annotated_csv),
        output_path=str(out_docx),
    )
    log(f"DOCX written: {out_docx.name}")


def read_tiered_rows(tiered_csv: Path) -> list[dict]:
    if not tiered_csv.exists():
        return []
    with tiered_csv.open(encoding="utf-8") as f:
        return list(csv.DictReader(f))
