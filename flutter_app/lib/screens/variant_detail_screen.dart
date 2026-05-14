import 'package:flutter/material.dart';
import 'package:flutter/services.dart';

import '../data/gene_panels.dart';
import '../models/variant.dart';
import '../widgets/tier_chip.dart';

class VariantDetailScreen extends StatelessWidget {
  final Variant variant;
  final String caseId;
  const VariantDetailScreen({
    super.key,
    required this.variant,
    required this.caseId,
  });

  @override
  Widget build(BuildContext context) {
    final (transcript, nuc) = variant.nucleotideChange;
    final (accession, prot) = variant.proteinChange;
    final therapy = kTherapyHints[variant.gene];
    final isDrugTarget = kDrugTargetGenes.contains(variant.gene);
    final isRisk = kRiskStratificationGenes.contains(variant.gene);
    final isDriver = kTier12Genes.contains(variant.gene);

    return Scaffold(
      appBar: AppBar(
        title: Text('${variant.gene} variant'),
        actions: [
          IconButton(
            icon: const Icon(Icons.open_in_new),
            tooltip: 'View on Ensembl',
            onPressed: () {
              ScaffoldMessenger.of(context).showSnackBar(
                SnackBar(
                  content: Text(
                    'External: https://grch37.ensembl.org/Homo_sapiens/Variation/Explore?v=${variant.rsid ?? variant.id}',
                  ),
                ),
              );
            },
          ),
        ],
      ),
      body: ListView(
        padding: const EdgeInsets.all(16),
        children: [
          Row(
            children: [
              Text(
                variant.gene,
                style: const TextStyle(
                  fontSize: 28,
                  fontWeight: FontWeight.bold,
                ),
              ),
              const SizedBox(width: 14),
              TierChip(tier: variant.tier),
            ],
          ),
          const SizedBox(height: 6),
          Text(
            variant.tier.description,
            style: TextStyle(color: Theme.of(context).hintColor),
          ),
          const SizedBox(height: 18),
          if (prot.isNotEmpty)
            _CopyField(label: 'Protein change', value: prot),
          if (nuc.isNotEmpty)
            _CopyField(label: 'Nucleotide change', value: nuc),
          _CopyField(
            label: 'Genomic position',
            value: 'chr${variant.chrom}:${variant.pos} ${variant.ref}>${variant.alt}',
          ),
          if (transcript.isNotEmpty)
            _CopyField(label: 'Transcript', value: transcript),
          if (accession.isNotEmpty)
            _CopyField(label: 'Protein accession', value: accession),
          const SizedBox(height: 10),
          _SectionCard(
            title: 'Allele frequency',
            children: [
              _Row('Sample VAF', '${variant.vafPct.toStringAsFixed(2)} %'),
              if (variant.ad != null && variant.dp != null)
                _Row('Depth (AD/DP)', '${variant.ad} / ${variant.dp}'),
              if (variant.maxPopAf != null)
                _Row('Max pop AF',
                    '${(variant.maxPopAf! * 100).toStringAsFixed(4)} %'),
            ],
          ),
          _SectionCard(
            title: 'Annotation',
            children: [
              if (variant.mostSevereConsequence != null)
                _Row(
                  'Consequence',
                  variant.mostSevereConsequence!.replaceAll('_', ' '),
                ),
              if (variant.clinSig != null && variant.clinSig!.isNotEmpty)
                _Row('ClinVar', variant.clinSig!.replaceAll('_', ' ')),
              if (variant.rsid != null && variant.rsid != 'NA')
                _Row('dbSNP', variant.rsid!),
              if (variant.uniprot != null && variant.uniprot != 'NA')
                _Row('UniProt', variant.uniprot!),
            ],
          ),
          _SectionCard(
            title: 'Gene panel classification',
            children: [
              _Badge(
                  active: isDriver,
                  label: 'Tier 1/2 lymphoma driver',
                  color: Colors.red),
              _Badge(
                  active: isDrugTarget,
                  label: 'Actionable drug target',
                  color: Colors.deepOrange),
              _Badge(
                  active: isRisk,
                  label: 'Risk stratification gene',
                  color: Colors.blueGrey),
              if (therapy != null) ...[
                const SizedBox(height: 6),
                Text(
                  'Targeted agents',
                  style: TextStyle(
                    color: Theme.of(context).hintColor,
                    fontSize: 12,
                  ),
                ),
                Text(therapy, style: const TextStyle(fontSize: 14)),
              ],
            ],
          ),
          _SectionCard(
            title: 'Case',
            children: [_Row('Case ID', caseId)],
          ),
          const SizedBox(height: 16),
          Card(
            color: Theme.of(context).colorScheme.surfaceContainerHighest,
            child: Padding(
              padding: const EdgeInsets.all(14),
              child: Row(
                children: [
                  const Icon(Icons.warning_amber_rounded,
                      color: Colors.orange, size: 22),
                  const SizedBox(width: 10),
                  Expanded(
                    child: Text(
                      'For research and educational use only — not a clinical diagnostic tool.',
                      style: TextStyle(
                        color: Theme.of(context).hintColor,
                        fontSize: 12,
                      ),
                    ),
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

class _CopyField extends StatelessWidget {
  final String label;
  final String value;
  const _CopyField({required this.label, required this.value});

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 4),
      child: Row(
        children: [
          SizedBox(
            width: 130,
            child: Text(
              label,
              style: TextStyle(
                color: Theme.of(context).hintColor,
                fontSize: 12,
              ),
            ),
          ),
          Expanded(
            child: SelectableText(
              value,
              style: const TextStyle(
                fontFamily: 'monospace',
                fontSize: 13,
              ),
            ),
          ),
          IconButton(
            icon: const Icon(Icons.copy, size: 16),
            visualDensity: VisualDensity.compact,
            tooltip: 'Copy',
            onPressed: () {
              Clipboard.setData(ClipboardData(text: value));
              ScaffoldMessenger.of(context).showSnackBar(
                SnackBar(
                  duration: const Duration(seconds: 1),
                  content: Text('Copied: $value'),
                ),
              );
            },
          ),
        ],
      ),
    );
  }
}

class _SectionCard extends StatelessWidget {
  final String title;
  final List<Widget> children;
  const _SectionCard({required this.title, required this.children});

  @override
  Widget build(BuildContext context) {
    return Card(
      margin: const EdgeInsets.symmetric(vertical: 8),
      child: Padding(
        padding: const EdgeInsets.all(14),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(
              title,
              style: const TextStyle(fontWeight: FontWeight.bold, fontSize: 14),
            ),
            const SizedBox(height: 6),
            ...children,
          ],
        ),
      ),
    );
  }
}

class _Row extends StatelessWidget {
  final String label;
  final String value;
  const _Row(this.label, this.value);

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 2),
      child: Row(
        children: [
          SizedBox(
            width: 130,
            child: Text(
              label,
              style: TextStyle(
                color: Theme.of(context).hintColor,
                fontSize: 12,
              ),
            ),
          ),
          Expanded(
            child: SelectableText(
              value,
              style: const TextStyle(fontSize: 13),
            ),
          ),
        ],
      ),
    );
  }
}

class _Badge extends StatelessWidget {
  final bool active;
  final String label;
  final Color color;
  const _Badge({
    required this.active,
    required this.label,
    required this.color,
  });

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 2),
      child: Row(
        children: [
          Icon(
            active ? Icons.check_circle : Icons.cancel_outlined,
            size: 16,
            color: active ? color : Theme.of(context).hintColor,
          ),
          const SizedBox(width: 6),
          Text(
            label,
            style: TextStyle(
              color: active ? color : Theme.of(context).hintColor,
              fontWeight: active ? FontWeight.w600 : FontWeight.normal,
              fontSize: 13,
            ),
          ),
        ],
      ),
    );
  }
}
