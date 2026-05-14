/// Variant model — mirrors the `_annotated.csv` row produced by `annotate_vcf.py`.
library;

enum Tier {
  tier1('Tier 1', 'Strong clinical significance'),
  tier2('Tier 2', 'Potential clinical significance'),
  tier3('Tier 3', 'Unknown clinical significance'),
  tier4('Tier 4', 'Benign / likely benign');

  final String label;
  final String description;
  const Tier(this.label, this.description);

  static Tier? fromLabel(String? raw) {
    if (raw == null) return null;
    final t = raw.trim();
    for (final v in Tier.values) {
      if (v.label.toLowerCase() == t.toLowerCase()) return v;
    }
    return null;
  }
}

class Variant {
  final String chrom;
  final int pos;
  final String id;
  final String ref;
  final String alt;
  final int? ad;
  final int? dp;
  final double sampleAf; // 0..1
  final String gene;
  final String? mostSevereConsequence;
  final String? hgvsc;
  final String? hgvsp;
  final String? rsid;
  final double? maxPopAf;
  final String? clinSig;
  final String? uniprot;
  final Tier tier;

  Variant({
    required this.chrom,
    required this.pos,
    required this.id,
    required this.ref,
    required this.alt,
    this.ad,
    this.dp,
    required this.sampleAf,
    required this.gene,
    this.mostSevereConsequence,
    this.hgvsc,
    this.hgvsp,
    this.rsid,
    this.maxPopAf,
    this.clinSig,
    this.uniprot,
    required this.tier,
  });

  /// VAF as percentage (0..100).
  double get vafPct => sampleAf * 100;

  /// Split "ENST00000398117.1:c.205_206insGG" → ("ENST...", "c....").
  (String, String) get nucleotideChange {
    final v = hgvsc;
    if (v == null || v.isEmpty || v == 'NA') return ('', '');
    final idx = v.indexOf(':');
    if (idx < 0) return ('', v);
    return (v.substring(0, idx), v.substring(idx + 1));
  }

  (String, String) get proteinChange {
    final v = hgvsp;
    if (v == null || v.isEmpty || v == 'NA') return ('', '');
    final idx = v.indexOf(':');
    if (idx < 0) return ('', v);
    return (v.substring(0, idx), v.substring(idx + 1));
  }

  factory Variant.fromCsvRow(Map<String, String> row) {
    double? parseDouble(String? s) {
      if (s == null || s.isEmpty || s == 'NA') return null;
      return double.tryParse(s);
    }

    int? parseInt(String? s) {
      if (s == null || s.isEmpty || s == 'NA') return null;
      return int.tryParse(s);
    }

    return Variant(
      chrom: row['chrom'] ?? '',
      pos: parseInt(row['pos']) ?? 0,
      id: row['id'] ?? '',
      ref: row['ref'] ?? '',
      alt: row['alt'] ?? '',
      ad: parseInt(row['ad']),
      dp: parseInt(row['dp']),
      sampleAf: parseDouble(row['sample_af']) ?? 0.0,
      gene: (row['gene'] ?? '').toUpperCase(),
      mostSevereConsequence: row['most_severe_consequence'],
      hgvsc: row['hgvsc'],
      hgvsp: row['hgvsp'],
      rsid: row['rsid'],
      maxPopAf: parseDouble(row['max_pop_af']),
      clinSig: row['clin_sig'],
      uniprot: row['uniprot'],
      tier: Tier.fromLabel(row['tier']) ?? Tier.tier4,
    );
  }

  Map<String, dynamic> toJson() => {
        'chrom': chrom,
        'pos': pos,
        'id': id,
        'ref': ref,
        'alt': alt,
        'ad': ad,
        'dp': dp,
        'sample_af': sampleAf,
        'gene': gene,
        'most_severe_consequence': mostSevereConsequence,
        'hgvsc': hgvsc,
        'hgvsp': hgvsp,
        'rsid': rsid,
        'max_pop_af': maxPopAf,
        'clin_sig': clinSig,
        'uniprot': uniprot,
        'tier': tier.label,
      };
}
