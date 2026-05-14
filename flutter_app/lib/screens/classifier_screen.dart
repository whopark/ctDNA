import 'package:flutter/material.dart';

import '../models/variant.dart';
import '../services/tier_classifier.dart';
import '../widgets/tier_chip.dart';

/// Interactive AMP/ASCO/CAP tier classifier — enter gene + consequence + ClinVar + pop AF.
class ClassifierScreen extends StatefulWidget {
  const ClassifierScreen({super.key});

  @override
  State<ClassifierScreen> createState() => _ClassifierScreenState();
}

class _ClassifierScreenState extends State<ClassifierScreen> {
  final _geneCtrl = TextEditingController();
  String _consequence = 'missense_variant';
  String _clinSig = 'uncertain_significance';
  double _maxPopAfPct = 0.0;

  Tier? _result;

  static const _consequences = [
    'missense_variant',
    'stop_gained',
    'frameshift_variant',
    'splice_acceptor_variant',
    'splice_donor_variant',
    'start_lost',
    'transcript_ablation',
    'inframe_insertion',
    'inframe_deletion',
    'protein_altering_variant',
    'synonymous_variant',
    'intron_variant',
    'upstream_gene_variant',
    'downstream_gene_variant',
  ];

  static const _clinSigOptions = [
    'pathogenic',
    'likely_pathogenic',
    'uncertain_significance',
    'likely_benign',
    'benign',
    '(none)',
  ];

  void _classify() {
    final result = TierClassifier.classify(
      gene: _geneCtrl.text.trim().toUpperCase(),
      consequence: _consequence,
      clinSig: _clinSig == '(none)' ? null : _clinSig,
      maxPopAf: _maxPopAfPct / 100.0,
    );
    setState(() => _result = result);
  }

  @override
  void dispose() {
    _geneCtrl.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('Tier Classifier'),
      ),
      body: ListView(
        padding: const EdgeInsets.all(16),
        children: [
          Text(
            'AMP/ASCO/CAP somatic variant tier',
            style: Theme.of(context).textTheme.titleMedium,
          ),
          Text(
            'Enter variant attributes — the local classifier replicates '
            '`annotate_vcf.assign_tier()` from whopark/ctDNA.',
            style: TextStyle(color: Theme.of(context).hintColor),
          ),
          const SizedBox(height: 18),
          TextField(
            controller: _geneCtrl,
            textCapitalization: TextCapitalization.characters,
            decoration: const InputDecoration(
              labelText: 'Gene symbol (HUGO)',
              hintText: 'e.g. TP53, MYD88, EZH2',
              border: OutlineInputBorder(),
            ),
          ),
          const SizedBox(height: 14),
          DropdownButtonFormField<String>(
            value: _consequence,
            isExpanded: true,
            decoration: const InputDecoration(
              labelText: 'VEP most-severe consequence',
              border: OutlineInputBorder(),
            ),
            items: _consequences
                .map((c) =>
                    DropdownMenuItem(value: c, child: Text(c.replaceAll('_', ' '))))
                .toList(),
            onChanged: (v) => setState(() => _consequence = v ?? _consequence),
          ),
          const SizedBox(height: 14),
          DropdownButtonFormField<String>(
            value: _clinSig,
            isExpanded: true,
            decoration: const InputDecoration(
              labelText: 'ClinVar significance',
              border: OutlineInputBorder(),
            ),
            items: _clinSigOptions
                .map((c) =>
                    DropdownMenuItem(value: c, child: Text(c.replaceAll('_', ' '))))
                .toList(),
            onChanged: (v) => setState(() => _clinSig = v ?? _clinSig),
          ),
          const SizedBox(height: 18),
          Text(
            'Max population AF: ${_maxPopAfPct.toStringAsFixed(3)} %',
            style: const TextStyle(fontWeight: FontWeight.w600),
          ),
          Slider(
            min: 0,
            max: 5,
            divisions: 100,
            value: _maxPopAfPct,
            label: '${_maxPopAfPct.toStringAsFixed(2)} %',
            onChanged: (v) => setState(() => _maxPopAfPct = v),
          ),
          Text(
            'AMP rule: >1 % population AF ⇒ Tier 4 (benign / common).',
            style: TextStyle(
              color: Theme.of(context).hintColor,
              fontSize: 12,
            ),
          ),
          const SizedBox(height: 22),
          FilledButton.icon(
            icon: const Icon(Icons.science),
            label: const Text('Classify'),
            onPressed: _geneCtrl.text.trim().isEmpty ? null : _classify,
          ),
          const SizedBox(height: 24),
          if (_result != null)
            Card(
              child: Padding(
                padding: const EdgeInsets.all(16),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Row(
                      children: [
                        const Text(
                          'Result: ',
                          style: TextStyle(
                              fontSize: 16, fontWeight: FontWeight.bold),
                        ),
                        TierChip(tier: _result!),
                      ],
                    ),
                    const SizedBox(height: 8),
                    Text(
                      _result!.description,
                      style: const TextStyle(fontSize: 14),
                    ),
                    const Divider(height: 22),
                    _CriterionRow(
                      label: 'Driver gene (Tier 1/2 panel)',
                      ok: _result == Tier.tier1 || _result == Tier.tier2,
                    ),
                    _CriterionRow(
                      label: 'Broader cancer gene (Tier 3 panel)',
                      ok: _result == Tier.tier3,
                    ),
                    _CriterionRow(
                      label: 'Pop AF ≤ 1 %',
                      ok: _maxPopAfPct <= 1.0,
                    ),
                    _CriterionRow(
                      label: 'Not benign (ClinVar)',
                      ok: !_clinSig.contains('benign'),
                    ),
                  ],
                ),
              ),
            ),
          const SizedBox(height: 12),
          Card(
            child: Padding(
              padding: const EdgeInsets.all(14),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: const [
                  Text(
                    'Reference',
                    style: TextStyle(fontWeight: FontWeight.bold),
                  ),
                  SizedBox(height: 6),
                  Text(
                    'Li MM, Datto M, Duncavage EJ, et al. Standards and '
                    'Guidelines for the Interpretation and Reporting of '
                    'Sequence Variants in Cancer. J Mol Diagn. 2017;19(1):4–23.',
                    style: TextStyle(fontSize: 12, height: 1.4),
                  ),
                ],
              ),
            ),
          ),
        ],
      ),
    );
  }
}

class _CriterionRow extends StatelessWidget {
  final String label;
  final bool ok;
  const _CriterionRow({required this.label, required this.ok});

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 2),
      child: Row(
        children: [
          Icon(
            ok ? Icons.check_circle : Icons.cancel_outlined,
            size: 16,
            color: ok ? Colors.green : Theme.of(context).hintColor,
          ),
          const SizedBox(width: 8),
          Text(label, style: const TextStyle(fontSize: 13)),
        ],
      ),
    );
  }
}
