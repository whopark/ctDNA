#!/usr/bin/env python3
"""
Annotate a VCF file using Ensembl VEP REST API (GRCh37).
Produces a CSV with: chrom, pos, id, ref, alt, ad, dp, sample_af,
gene, most_severe_consequence, hgvsc, hgvsp, rsid, max_pop_af, clin_sig, uniprot, tier

Tiering follows AMP/ASCO/CAP somatic variant classification
(J Mol Diagn. 2017;19:4-23) adapted for lymphoma ctDNA panels.
"""

import csv
import json
import sys
import time
import requests

VEP_URL = "https://grch37.rest.ensembl.org/vep/homo_sapiens/region"
HEADERS = {"Content-Type": "application/json", "Accept": "application/json"}
BATCH_SIZE = 200  # Ensembl POST limit
RETRY_WAIT = 5
MAX_RETRIES = 5

OUT_FIELDS = [
    "chrom", "pos", "id", "ref", "alt", "ad", "dp", "sample_af",
    "gene", "most_severe_consequence", "hgvsc", "hgvsp",
    "rsid", "max_pop_af", "clin_sig", "uniprot", "tier",
]

# ---- Lymphoma driver / clinically relevant gene sets ----
# Tier 1/2 genes: established lymphoma drivers with strong/potential clinical significance
TIER1_2_GENES = {
    # DLBCL / aggressive B-cell lymphoma drivers
    "TP53", "MYC", "BCL2", "BCL6",
    "MYD88", "CD79B", "CD79A", "CARD11", "TNFAIP3",
    "KMT2D", "CREBBP", "EZH2", "EP300", "ARID1A",
    "NOTCH1", "NOTCH2", "PIM1", "CCND1", "CCND3",
    "SOCS1", "SGK1", "TET2", "GNA13", "IRF4",
    "FOXO1", "MEF2B", "PRDM1", "NFKBIA", "TCF3", "ID3",
    "STAT6", "TNFRSF14", "B2M", "CIITA", "CD58", "FAS",
    "BCL10", "CD70", "DTX1", "UBE2A", "SPEN",
    "IRF8", "BTG1", "KLHL6", "TBL1XR1",
    # Targeted therapy genes
    "BTK", "PLCG2", "PI3KCA", "PIK3CD", "PIK3R1", "PTEN", "MTOR",
    "ALK", "JAK1", "JAK2", "STAT3", "STAT5B",
    "BRAF", "KRAS", "NRAS", "MCL1",
    # Cell cycle / tumor suppressors
    "CDKN2A", "RB1", "FBXW7", "POT1", "ATM",
    # Splicing / signaling
    "SF3B1", "BIRC3",
    # Other hematologic malignancy drivers
    "DNMT3A", "IDH1", "IDH2", "NPM1", "FLT3",
    "BCOR", "BCORL1", "DDX3X",
}

# Tier 3 genes: broader cancer / lymphoma-associated genes with uncertain significance
TIER3_GENES = {
    # Chromatin / epigenetic
    "KMT2A", "KMT2C", "SETD2", "NSD2", "WHSC1",
    "ARID1B", "ARID2", "SMARCA4", "PBRM1",
    # DNA repair / cell cycle
    "ATR", "CHEK2", "BRCA1", "BRCA2", "CDK6",
    # RTK / signaling
    "EGFR", "ERBB2", "ERBB3", "MET", "RET", "ROS1", "KIT", "PDGFRA",
    # Splicing
    "U2AF1", "SRSF2", "ZRSR2",
    # Tumor suppressors / signaling
    "TSC1", "TSC2", "NF1", "NF2",
    # Transcription factors / lymphoid development
    "IKZF1", "PAX5", "EBF1", "RUNX1", "GATA3",
    # Other lymphoma-associated
    "XPO1", "MED12", "ITPKB", "NFKBIE",
    "TRAF3", "MAP3K14", "MALT1",
    "RHOA", "UBR5",
    "PCLO", "P2RY8", "ZFP36L1", "DUSP2",
    "HIST1H1E", "HIST1H1C", "HIST1H1B", "HIST1H1D",
}

# Consequence severity for tiering
HIGH_IMPACT = {
    "transcript_ablation", 
    "splice_acceptor_variant", 
    "splice_donor_variant",
    "stop_gained", 
    "frameshift_variant", 
    "stop_lost", 
   "start_lost",
}

MODERATE_IMPACT = {
    "inframe_insertion", 
    "inframe_deletion", 
    "missense_variant",
    "protein_altering_variant",
}

LOW_IMPACT = {
    "splice_region_variant", 
    "splice_donor_5th_base_variant",
    "splice_donor_region_variant", 
    "splice_polypyrimidine_tract_variant",
    "synonymous_variant", 
    "stop_retained_variant", 
    "start_retained_variant",
}

MODIFIER_IMPACT = {
    "3_prime_UTR_variant", 
    "5_prime_UTR_variant", 
    "intron_variant",
    "upstream_gene_variant", 
    "downstream_gene_variant",
    "non_coding_transcript_variant", 
    "non_coding_transcript_exon_variant",
    "intergenic_variant",
}


def assign_tier(row):
    """
    Assign AMP/ASCO/CAP tier for somatic variants in lymphoma ctDNA.

    Tier 1: Strong clinical significance — known pathogenic in cancer + driver gene
    Tier 2: Potential clinical significance — likely pathogenic / functional in driver gene
    Tier 3: Unknown clinical significance — variants in cancer genes without clear evidence
    Tier 4: Benign/likely benign — common polymorphisms or benign in non-driver genes
    """
    gene = row.get("gene", "NA")
    csq = row.get("most_severe_consequence", "NA")
    clin_sig = row.get("clin_sig", "NA")
    max_pop_af = row.get("max_pop_af", "NA")
    sample_af = float(row.get("sample_af", 0))

    # Parse population AF
    try:
        pop_af = float(max_pop_af) if max_pop_af != "NA" else None
    except (ValueError, TypeError):
        pop_af = None

    # Common germline polymorphism filter: pop AF > 1% → likely germline
    is_common = pop_af is not None and pop_af > 0.01

    # Parse ClinVar
    clin_lower = clin_sig.lower() if clin_sig != "NA" else ""
    has_pathogenic = "pathogenic" in clin_lower and "likely_benign" not in clin_lower
    has_likely_path = "likely_pathogenic" in clin_lower
    is_benign = clin_lower in ("benign", "likely_benign", "benign|likely_benign")
    has_any_pathogenic = "pathogenic" in clin_lower  # including mixed

    # Gene membership
    in_tier12 = gene in TIER1_2_GENES
    in_tier3 = gene in TIER3_GENES
    in_any_gene_list = in_tier12 or in_tier3

    # Consequence impact
    is_high = csq in HIGH_IMPACT
    is_moderate = csq in MODERATE_IMPACT
    is_low = csq in LOW_IMPACT
    is_modifier = csq in MODIFIER_IMPACT or csq == "NA"

    # ---- Tier 1: Strong clinical significance ----
    # Known pathogenic + established driver gene + not common polymorphism
    if in_tier12 and has_pathogenic and not is_common:
        return "Tier 1"

    # ---- Tier 2: Potential clinical significance ----
    # Case A: Driver gene + high impact (truncating) + not common
    if in_tier12 and is_high and not is_common:
        return "Tier 2"

    # Case B: Driver gene + moderate impact + likely pathogenic + not common
    if in_tier12 and is_moderate and has_likely_path and not is_common:
        return "Tier 2"

    # Case C: Driver gene + moderate impact + novel/rare (no pop AF or < 0.1%)
    if in_tier12 and is_moderate and (pop_af is None or pop_af < 0.001) and not is_benign:
        return "Tier 2"

    # Case D: Driver gene + splice region with clinical evidence
    if in_tier12 and "splice" in csq and has_any_pathogenic and not is_common:
        return "Tier 2"

    # ---- Tier 3: Unknown clinical significance ----
    # Very common polymorphisms (>5% pop AF) are Tier 4 regardless of ClinVar noise
    is_very_common = pop_af is not None and pop_af > 0.05

    # Case A: Any cancer gene + moderate/high impact + not common + no benign call
    if in_any_gene_list and (is_high or is_moderate) and not is_common and not is_benign:
        return "Tier 3"

    # Case B: Driver gene + low impact (splice region) + rare
    if in_any_gene_list and is_low and not is_common and not is_benign:
        if "splice" in csq or has_any_pathogenic:
            return "Tier 3"

    # Case C: Any cancer gene + moderate impact + common but has pathogenic signal
    #         (exclude very common polymorphisms — ClinVar noise)
    if in_any_gene_list and is_moderate and has_any_pathogenic and not is_very_common:
        return "Tier 3"

    # Case D: Tier3-only gene + high impact + not common
    if in_tier3 and is_high and not is_common:
        return "Tier 3"

    # ---- Tier 4: Benign / likely benign ----
    return "Tier 4"


def parse_vcf(path):
    """Parse VCF, return list of variant dicts."""
    variants = []
    warned_missing = False
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line.startswith("#"):
                continue
            parts = line.split("\t")
            chrom, pos, vid, ref, alt = parts[0], int(parts[1]), parts[2], parts[3], parts[4]
            info = {}
            for token in parts[7].split(";"):
                if "=" in token:
                    k, v = token.split("=", 1)
                    info[k] = v
            ad_raw = info.get("AD")
            dp_raw = info.get("DP")
            if (ad_raw is None or dp_raw is None) and not warned_missing:
                missing = [f for f in ("AD", "DP") if f not in info]
                print(f"  WARN: INFO field missing {', '.join(missing)} "
                      f"(first seen at {chrom}:{pos}). "
                      f"Expected AD and DP in INFO column.", file=sys.stderr)
                warned_missing = True
            ad = int(ad_raw) if ad_raw is not None else 0
            dp = int(dp_raw) if dp_raw is not None else 1
            sample_af = round(ad / dp, 6) if dp > 0 else 0.0
            variants.append({
                "chrom": str(chrom),
                "pos": pos,
                "id": vid,
                "ref": ref,
                "alt": alt,
                "ad": ad,
                "dp": dp,
                "sample_af": sample_af,
            })
    return variants


def build_vep_input(variant):
    """Build VEP region notation: chr start end allele_string strand."""
    chrom = variant["chrom"]
    pos = variant["pos"]
    ref = variant["ref"]
    alt = variant["alt"]

    if len(ref) == 1 and len(alt) == 1:
        # SNV
        return f"{chrom} {pos} {pos} {ref}/{alt} 1"
    elif len(ref) > len(alt):
        # Deletion
        deleted = ref[len(alt):]
        start = pos + len(alt)
        end = start + len(deleted) - 1
        return f"{chrom} {start} {end} {deleted}/- 1"
    elif len(alt) > len(ref):
        # Insertion: VEP wants start = base after anchor, end = start - 1
        inserted = alt[len(ref):]
        start = pos + len(ref)
        end = start - 1
        return f"{chrom} {start} {end} -/{inserted} 1"
    else:
        # MNV (same length, >1)
        end = pos + len(ref) - 1
        return f"{chrom} {pos} {end} {ref}/{alt} 1"


def query_vep_batch(vep_inputs):
    """POST a batch of VEP region strings, return list of result dicts."""
    payload = json.dumps({
        "variants": vep_inputs,
        "variant_class": True,
        "hgvs": True,
        "uniprot": True,
        "protein": True,
        "domains": True,
        "canonical": True,
        "pick": True,  # pick single most severe per allele
        "frequency": True,
    })
    for attempt in range(MAX_RETRIES):
        try:
            resp = requests.post(VEP_URL, headers=HEADERS, data=payload, timeout=120)
            if resp.status_code == 200:
                return resp.json()
            elif resp.status_code == 429:
                wait = int(resp.headers.get("Retry-After", RETRY_WAIT))
                print(f"  Rate limited, waiting {wait}s...", file=sys.stderr)
                time.sleep(wait)
            else:
                print(f"  VEP HTTP {resp.status_code}: {resp.text[:200]}", file=sys.stderr)
                time.sleep(RETRY_WAIT)
        except requests.exceptions.RequestException as e:
            print(f"  Request error: {e}", file=sys.stderr)
            time.sleep(RETRY_WAIT)
    print(f"  WARN: Failed batch after {MAX_RETRIES} retries", file=sys.stderr)
    return []


def extract_annotation(vep_result):
    """Extract fields from a single VEP result dict."""
    ann = {
        "gene": "NA",
        "most_severe_consequence": "NA",
        "hgvsc": "NA",
        "hgvsp": "NA",
        "rsid": "NA",
        "max_pop_af": "NA",
        "clin_sig": "NA",
        "uniprot": "NA",
    }

    ann["most_severe_consequence"] = vep_result.get("most_severe_consequence", "NA")

    # rsID
    colocated = vep_result.get("colocated_variants", [])
    rs_ids = [c["id"] for c in colocated if c.get("id", "").startswith("rs")]
    if rs_ids:
        ann["rsid"] = rs_ids[0]

    # max population AF from colocated
    max_af = None
    for cv in colocated:
        for key in ("gnomad_af", "minor_allele_freq", "af"):
            val = cv.get(key)
            if val is not None:
                if max_af is None or val > max_af:
                    max_af = val
        # Also check population-specific frequencies
        freqs = cv.get("frequencies", {})
        for allele_freqs in freqs.values():
            if isinstance(allele_freqs, dict):
                for pop_af in allele_freqs.values():
                    if isinstance(pop_af, (int, float)):
                        if max_af is None or pop_af > max_af:
                            max_af = pop_af
    if max_af is not None:
        ann["max_pop_af"] = round(max_af, 4)

    # ClinVar significance from colocated
    clin_sigs = []
    for cv in colocated:
        cs = cv.get("clin_sig", [])
        if isinstance(cs, list):
            clin_sigs.extend(cs)
        elif isinstance(cs, str):
            clin_sigs.append(cs)
    if clin_sigs:
        ann["clin_sig"] = "|".join(sorted(set(clin_sigs)))

    # Transcript-level from picked consequence
    tcs = vep_result.get("transcript_consequences", [])

    # prefer canonical / picked
    picked = [t for t in tcs if t.get("pick") == 1 or t.get("canonical") == 1]
    tc = picked[0] if picked else (tcs[0] if tcs else None)
    if tc:
        ann["gene"] = tc.get("gene_symbol", tc.get("gene_id", "NA"))
        ann["hgvsc"] = tc.get("hgvsc", "NA")
        ann["hgvsp"] = tc.get("hgvsp", "NA")
        # UniProt
        swissprot = tc.get("swissprot", [])
        if swissprot:
            ann["uniprot"] = swissprot[0] if isinstance(swissprot, list) else str(swissprot)

    return ann


def main():
    vcf_path = sys.argv[1] if len(sys.argv) > 1 else "data/01.vcf"
    out_path = vcf_path.rsplit(".", 1)[0] + "_annotated.csv"

    print(f"Parsing {vcf_path}...", file=sys.stderr)
    variants = parse_vcf(vcf_path)
    print(f"Found {len(variants)} variants", file=sys.stderr)

    # Build VEP inputs and maintain mapping
    vep_inputs = []
    for v in variants:
        vep_inputs.append(build_vep_input(v))

    # Query in batches
    all_results = []
    n_batches = (len(vep_inputs) + BATCH_SIZE - 1) // BATCH_SIZE
    for i in range(0, len(vep_inputs), BATCH_SIZE):
        batch = vep_inputs[i:i + BATCH_SIZE]
        batch_num = i // BATCH_SIZE + 1
        print(f"Querying VEP batch {batch_num}/{n_batches} ({len(batch)} variants)...", file=sys.stderr)
        results = query_vep_batch(batch)
        all_results.extend(results)
        if batch_num < n_batches:
            time.sleep(1)  # be polite to Ensembl

    # Index results by input string for matching
    result_by_input = {}
    for r in all_results:
        inp = r.get("input", "").strip()
        if inp:
            result_by_input[inp] = r

    # Write output with tiering
    matched = 0
    tier_counts = {"Tier 1": 0, "Tier 2": 0, "Tier 3": 0, "Tier 4": 0}
    with open(out_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=OUT_FIELDS)
        writer.writeheader()
        for v, vep_inp in zip(variants, vep_inputs):
            row = {k: v[k] for k in ["chrom", "pos", "id", "ref", "alt", "ad", "dp", "sample_af"]}
            result = result_by_input.get(vep_inp)
            if result:
                ann = extract_annotation(result)
                matched += 1
            else:
                ann = {k: "NA" for k in ["gene", "most_severe_consequence", "hgvsc", "hgvsp",
                                          "rsid", "max_pop_af", "clin_sig", "uniprot"]}
            row.update(ann)
            row["tier"] = assign_tier(row)
            tier_counts[row["tier"]] += 1
            writer.writerow(row)

    print(f"\nDone! {matched}/{len(variants)} variants annotated.", file=sys.stderr)
    print(f"Output: {out_path}", file=sys.stderr)
    print(f"\nTier distribution:", file=sys.stderr)
    for tier in ("Tier 1", "Tier 2", "Tier 3", "Tier 4"):
        print(f"  {tier}: {tier_counts[tier]}", file=sys.stderr)


if __name__ == "__main__":
    main()
