import 'dart:async';
import 'dart:convert';

import 'package:shared_preferences/shared_preferences.dart';

import '../models/case_record.dart';
import '../models/variant.dart';

/// In-memory + SharedPreferences-backed store for cases.
class CaseRepository {
  static const _key = 'ctdna_cases_v1';

  final List<CaseRecord> _cases = [];
  final StreamController<List<CaseRecord>> _ctrl =
      StreamController.broadcast();

  List<CaseRecord> get cases => List.unmodifiable(_cases);
  Stream<List<CaseRecord>> get stream => _ctrl.stream;

  Future<void> load() async {
    final prefs = await SharedPreferences.getInstance();
    final raw = prefs.getString(_key);
    _cases.clear();
    if (raw != null && raw.isNotEmpty) {
      try {
        final list = json.decode(raw) as List<dynamic>;
        for (final c in list) {
          _cases.add(_fromJson(c as Map<String, dynamic>));
        }
      } catch (_) {
        // ignore corrupt cache
      }
    }
    _emit();
  }

  Future<void> _persist() async {
    final prefs = await SharedPreferences.getInstance();
    await prefs.setString(
      _key,
      json.encode(_cases.map(_toJson).toList()),
    );
  }

  void _emit() => _ctrl.add(cases);

  Future<void> add(CaseRecord c) async {
    _cases.removeWhere((x) => x.id == c.id);
    _cases.add(c);
    await _persist();
    _emit();
  }

  Future<void> remove(String id) async {
    _cases.removeWhere((x) => x.id == id);
    await _persist();
    _emit();
  }

  Future<void> clear() async {
    _cases.clear();
    await _persist();
    _emit();
  }

  CaseRecord? byId(String id) {
    for (final c in _cases) {
      if (c.id == id) return c;
    }
    return null;
  }

  // ---- (de)serialization ----
  Map<String, dynamic> _toJson(CaseRecord c) => {
        'id': c.id,
        'patient_name': c.patientName,
        'reg_no': c.regNo,
        'specimen_type': c.specimenType,
        'test_date': c.testDate,
        'variants': c.variants.map((v) => v.toJson()).toList(),
      };

  CaseRecord _fromJson(Map<String, dynamic> m) {
    final variants = (m['variants'] as List<dynamic>? ?? [])
        .map((v) => _variantFromJson(v as Map<String, dynamic>))
        .toList();
    return CaseRecord(
      id: m['id'] as String,
      patientName: m['patient_name'] as String?,
      regNo: m['reg_no'] as String?,
      specimenType: m['specimen_type'] as String?,
      testDate: m['test_date'] as String?,
      variants: variants,
    );
  }

  Variant _variantFromJson(Map<String, dynamic> m) => Variant(
        chrom: m['chrom'] ?? '',
        pos: m['pos'] ?? 0,
        id: m['id'] ?? '',
        ref: m['ref'] ?? '',
        alt: m['alt'] ?? '',
        ad: m['ad'],
        dp: m['dp'],
        sampleAf: (m['sample_af'] as num?)?.toDouble() ?? 0.0,
        gene: m['gene'] ?? '',
        mostSevereConsequence: m['most_severe_consequence'],
        hgvsc: m['hgvsc'],
        hgvsp: m['hgvsp'],
        rsid: m['rsid'],
        maxPopAf: (m['max_pop_af'] as num?)?.toDouble(),
        clinSig: m['clin_sig'],
        uniprot: m['uniprot'],
        tier: Tier.fromLabel(m['tier'] as String?) ?? Tier.tier4,
      );

  void dispose() => _ctrl.close();
}
