import 'package:csv/csv.dart';

import '../models/case_record.dart';
import '../models/variant.dart';

/// Parse an annotated CSV (output of `annotate_vcf.py`) into a CaseRecord.
class CsvImportService {
  /// Parse a full CSV string. The CSV must contain at minimum:
  ///   chrom,pos,id,ref,alt,ad,dp,sample_af,gene,most_severe_consequence,
  ///   hgvsc,hgvsp,rsid,max_pop_af,clin_sig,uniprot,tier
  static CaseRecord parse(String caseId, String csvText) {
    // Allow CR/LF or LF line endings.
    final rows = const CsvToListConverter(eol: '\n', shouldParseNumbers: false)
        .convert(csvText.replaceAll('\r\n', '\n').replaceAll('\r', '\n'));

    if (rows.isEmpty) {
      return CaseRecord.fromId(caseId, []);
    }

    final header = rows.first.map((e) => e.toString().trim()).toList();
    final variants = <Variant>[];
    for (var i = 1; i < rows.length; i++) {
      final cells = rows[i];
      if (cells.length == 1 && cells.first.toString().trim().isEmpty) continue;
      final row = <String, String>{};
      for (var j = 0; j < header.length && j < cells.length; j++) {
        row[header[j]] = cells[j].toString();
      }
      try {
        variants.add(Variant.fromCsvRow(row));
      } catch (_) {
        // skip malformed
      }
    }

    return CaseRecord.fromId(caseId, variants);
  }
}
