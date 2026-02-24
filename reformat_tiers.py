#!/usr/bin/env python3
"""
Reformat annotated VCF CSV into clinical report format (Tier 1-3 only).
Output: ASCO/AMP Classification | Gene | Canonical name | Accession | Nucleotide change | AA change | % VAF
"""
import csv
import sys


def parse_hgvsc(hgvsc):
    """Split 'ENST00000398117.1:c.205_206insGG' into transcript and c. change."""
    if not hgvsc or hgvsc == "NA":
        return "", ""
    if ":" in hgvsc:
        transcript, change = hgvsc.split(":", 1)
        return transcript, change
    return "", hgvsc


def parse_hgvsp(hgvsp):
    """Split 'ENSP00000381185.1:p.Thr69ArgfsTer28' into accession and p. change."""
    if not hgvsp or hgvsp == "NA":
        return "", ""
    if ":" in hgvsp:
        accession, change = hgvsp.split(":", 1)
        return accession, change
    return "", hgvsp


def main():
    in_path = sys.argv[1] if len(sys.argv) > 1 else "data/01_annotated.csv"
    out_path = in_path.rsplit("_annotated", 1)[0] + "_tiered_report.csv"

    out_fields = [
        "ASCO/AMP Classification",
        "Gene",
        "Canonical name",
        "Accession",
        "Nucleotide change",
        "AA change",
        "% VAF",
    ]

    with open(in_path, encoding="utf-8") as fin:
        reader = csv.DictReader(fin)
        rows = list(reader)

    # Filter to Tier 1-3 with VAF >= 1%, sort by tier then descending VAF
    MIN_VAF = 0.01  # 1% VAF threshold
    tier_order = {"Tier 1": 0, "Tier 2": 1, "Tier 3": 2}
    reportable = [r for r in rows
                  if r["tier"] in tier_order
                  and float(r["sample_af"]) >= MIN_VAF]
    reportable.sort(key=lambda r: (tier_order[r["tier"]], -float(r["sample_af"])))

    with open(out_path, "w", newline="", encoding="utf-8") as fout:
        writer = csv.DictWriter(fout, fieldnames=out_fields)
        writer.writeheader()
        for r in reportable:
            transcript, nuc_change = parse_hgvsc(r["hgvsc"])
            accession, aa_change = parse_hgvsp(r["hgvsp"])
            vaf_pct = f"{float(r['sample_af']) * 100:.2f}%"
            writer.writerow({
                "ASCO/AMP Classification": r["tier"],
                "Gene": r["gene"],
                "Canonical name": transcript,
                "Accession": accession,
                "Nucleotide change": nuc_change,
                "AA change": aa_change,
                "% VAF": vaf_pct,
            })

    # Print summary
    counts = {}
    for r in reportable:
        counts[r["tier"]] = counts.get(r["tier"], 0) + 1

    print(f"Output: {out_path}", file=sys.stderr)
    print(f"Total reportable variants: {len(reportable)}", file=sys.stderr)
    for tier in ("Tier 1", "Tier 2", "Tier 3"):
        print(f"  {tier}: {counts.get(tier, 0)}", file=sys.stderr)


if __name__ == "__main__":
    main()
