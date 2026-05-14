import 'variant.dart';

/// Patient case record — collection of variants + optional metadata.
class CaseRecord {
  final String id; // case id (e.g., "01-JJH_10679562")
  final String? patientName;
  final String? regNo;
  final String? specimenType;
  final String? testDate;
  final List<Variant> variants;

  CaseRecord({
    required this.id,
    this.patientName,
    this.regNo,
    this.specimenType,
    this.testDate,
    required this.variants,
  });

  /// Try to auto-parse "01-JJH_10679562" → patientName="JJH", regNo="10679562".
  factory CaseRecord.fromId(String id, List<Variant> variants) {
    String? name;
    String? reg;
    final m = RegExp(r'^\d+-([A-Za-z]+)_(\d+)').firstMatch(id);
    if (m != null) {
      name = m.group(1);
      reg = m.group(2);
    }
    return CaseRecord(
      id: id,
      patientName: name,
      regNo: reg,
      variants: variants,
    );
  }

  Map<Tier, int> tierCounts() {
    final m = {for (final t in Tier.values) t: 0};
    for (final v in variants) {
      m[v.tier] = (m[v.tier] ?? 0) + 1;
    }
    return m;
  }

  int get totalVariants => variants.length;
}
