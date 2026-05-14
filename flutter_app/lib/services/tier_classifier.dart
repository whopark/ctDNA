import '../data/gene_panels.dart';
import '../models/variant.dart';

/// AMP/ASCO/CAP somatic variant tier classification (Li et al., J Mol Diagn 2017).
/// Port of `assign_tier()` logic from `annotate_vcf.py`.
class TierClassifier {
  /// High-impact VEP consequences (truncating / canonical splice).
  static const Set<String> highImpactConsequences = {
    'stop_gained',
    'frameshift_variant',
    'splice_acceptor_variant',
    'splice_donor_variant',
    'start_lost',
    'transcript_ablation',
  };

  /// Moderate-impact consequences (missense, inframe indels).
  static const Set<String> moderateImpactConsequences = {
    'missense_variant',
    'inframe_insertion',
    'inframe_deletion',
    'protein_altering_variant',
  };

  /// Classify a variant into AMP/ASCO/CAP Tier 1-4.
  ///
  /// Inputs:
  ///   - [gene]: HUGO symbol (case-insensitive)
  ///   - [consequence]: VEP most_severe_consequence
  ///   - [clinSig]: ClinVar significance string (e.g., 'pathogenic')
  ///   - [maxPopAf]: maximum population allele frequency (0..1), or null
  static Tier classify({
    required String gene,
    required String? consequence,
    String? clinSig,
    double? maxPopAf,
  }) {
    final g = gene.toUpperCase();
    final cs = (clinSig ?? '').toLowerCase();
    final cq = (consequence ?? '').toLowerCase();
    final af = maxPopAf ?? 0.0;

    final isDriver = kTier12Genes.contains(g);
    final isTier3Gene = kTier3Genes.contains(g);

    final isHighImpact = highImpactConsequences.contains(cq);
    final isModerateImpact = moderateImpactConsequences.contains(cq);

    final isPathogenicClinVar =
        cs.contains('pathogenic') && !cs.contains('conflicting');
    final isBenignClinVar = cs.contains('benign');
    final isCommon = af > 0.01;

    // Tier 4: benign / common polymorphism
    if (isBenignClinVar || isCommon) return Tier.tier4;

    // Tier 1: known pathogenic in driver gene, rare
    if (isDriver && isPathogenicClinVar && af <= 0.01) {
      return Tier.tier1;
    }

    // Tier 2: high-impact or novel missense in driver gene, rare, not benign
    if (isDriver && (isHighImpact || isModerateImpact) && !isBenignClinVar) {
      return Tier.tier2;
    }

    // Tier 3: moderate/high impact in broader cancer gene
    if (isTier3Gene && (isHighImpact || isModerateImpact) && !isBenignClinVar) {
      return Tier.tier3;
    }

    // Default fallback
    return Tier.tier4;
  }

  /// Helper: whether a Tier 3 variant should appear in clinical reports.
  static bool isTier3Reportable(String gene) {
    return kActionableTier3Genes.contains(gene.toUpperCase());
  }
}
