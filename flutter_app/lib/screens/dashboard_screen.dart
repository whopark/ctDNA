import 'package:fl_chart/fl_chart.dart';
import 'package:flutter/material.dart';

import '../models/case_record.dart';
import '../models/variant.dart';
import '../widgets/tier_chip.dart';

class DashboardScreen extends StatelessWidget {
  final List<CaseRecord> cases;
  const DashboardScreen({super.key, required this.cases});

  Map<Tier, int> _aggregateTiers() {
    final m = {for (final t in Tier.values) t: 0};
    for (final c in cases) {
      for (final v in c.variants) {
        m[v.tier] = (m[v.tier] ?? 0) + 1;
      }
    }
    return m;
  }

  Map<String, int> _topGenes({int limit = 8}) {
    final counts = <String, int>{};
    for (final c in cases) {
      for (final v in c.variants) {
        if (v.tier == Tier.tier4) continue;
        counts[v.gene] = (counts[v.gene] ?? 0) + 1;
      }
    }
    final sorted = counts.entries.toList()
      ..sort((a, b) => b.value.compareTo(a.value));
    return Map.fromEntries(sorted.take(limit));
  }

  @override
  Widget build(BuildContext context) {
    final tierCounts = _aggregateTiers();
    final topGenes = _topGenes();
    final totalVariants = tierCounts.values.fold<int>(0, (a, b) => a + b);

    return Scaffold(
      appBar: AppBar(
        title: const Text('ctDNA Lymphoma Viewer'),
        centerTitle: false,
      ),
      body: ListView(
        padding: const EdgeInsets.all(16),
        children: [
          _SummaryRow(
            cases: cases.length,
            variants: totalVariants,
            actionable: (tierCounts[Tier.tier1] ?? 0) +
                (tierCounts[Tier.tier2] ?? 0),
          ),
          const SizedBox(height: 20),
          _SectionHeader(
            title: 'Tier distribution',
            subtitle: 'AMP/ASCO/CAP somatic variant tiering',
          ),
          const SizedBox(height: 12),
          if (totalVariants == 0)
            _EmptyHint(
              icon: Icons.upload_file_outlined,
              text:
                  'No cases yet — open the Cases tab to load sample data or import an annotated CSV.',
            )
          else
            _TierPieCard(counts: tierCounts),
          const SizedBox(height: 20),
          _SectionHeader(
            title: 'Top mutated genes',
            subtitle: 'Tier 1–3 only',
          ),
          const SizedBox(height: 12),
          if (topGenes.isEmpty)
            const SizedBox.shrink()
          else
            _TopGenesCard(counts: topGenes),
          const SizedBox(height: 24),
          Card(
            child: Padding(
              padding: const EdgeInsets.all(16),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Row(
                    children: const [
                      Icon(Icons.info_outline, size: 18),
                      SizedBox(width: 8),
                      Text(
                        'About',
                        style: TextStyle(
                          fontWeight: FontWeight.bold,
                          fontSize: 15,
                        ),
                      ),
                    ],
                  ),
                  const SizedBox(height: 8),
                  Text(
                    'Flutter client based on the whopark/ctDNA lymphoma variant '
                    'annotation pipeline. Implements AMP/ASCO/CAP tiering '
                    '(Li et al., J Mol Diagn 2017) for lymphoma ctDNA panels. '
                    'Sandbox / education use only — not for diagnostic use.',
                    style: TextStyle(
                      color: Theme.of(context).hintColor,
                      height: 1.4,
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

class _SummaryRow extends StatelessWidget {
  final int cases;
  final int variants;
  final int actionable;
  const _SummaryRow({
    required this.cases,
    required this.variants,
    required this.actionable,
  });

  @override
  Widget build(BuildContext context) {
    return Row(
      children: [
        Expanded(
          child: _StatCard(
            icon: Icons.folder,
            label: 'Cases',
            value: '$cases',
            color: Colors.blueGrey,
          ),
        ),
        const SizedBox(width: 10),
        Expanded(
          child: _StatCard(
            icon: Icons.biotech,
            label: 'Variants',
            value: '$variants',
            color: Colors.indigo,
          ),
        ),
        const SizedBox(width: 10),
        Expanded(
          child: _StatCard(
            icon: Icons.local_hospital,
            label: 'Actionable',
            value: '$actionable',
            color: Colors.deepOrange,
          ),
        ),
      ],
    );
  }
}

class _StatCard extends StatelessWidget {
  final IconData icon;
  final String label;
  final String value;
  final Color color;
  const _StatCard({
    required this.icon,
    required this.label,
    required this.value,
    required this.color,
  });

  @override
  Widget build(BuildContext context) {
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(14),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Icon(icon, color: color, size: 22),
            const SizedBox(height: 8),
            Text(
              value,
              style: const TextStyle(
                fontSize: 22,
                fontWeight: FontWeight.bold,
              ),
            ),
            Text(
              label,
              style: TextStyle(
                color: Theme.of(context).hintColor,
                fontSize: 12,
              ),
            ),
          ],
        ),
      ),
    );
  }
}

class _SectionHeader extends StatelessWidget {
  final String title;
  final String subtitle;
  const _SectionHeader({required this.title, required this.subtitle});

  @override
  Widget build(BuildContext context) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(
          title,
          style: const TextStyle(fontSize: 17, fontWeight: FontWeight.bold),
        ),
        Text(
          subtitle,
          style: TextStyle(color: Theme.of(context).hintColor, fontSize: 12),
        ),
      ],
    );
  }
}

class _TierPieCard extends StatelessWidget {
  final Map<Tier, int> counts;
  const _TierPieCard({required this.counts});

  @override
  Widget build(BuildContext context) {
    final total = counts.values.fold<int>(0, (a, b) => a + b);
    final entries = counts.entries.where((e) => e.value > 0).toList();

    return Card(
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Row(
          children: [
            SizedBox(
              width: 130,
              height: 130,
              child: PieChart(
                PieChartData(
                  sectionsSpace: 2,
                  centerSpaceRadius: 32,
                  sections: entries.map((e) {
                    final pct = total == 0 ? 0.0 : (e.value / total * 100);
                    return PieChartSectionData(
                      color: TierChip.colorFor(e.key),
                      value: e.value.toDouble(),
                      title: '${pct.toStringAsFixed(0)}%',
                      titleStyle: const TextStyle(
                        color: Colors.white,
                        fontSize: 11,
                        fontWeight: FontWeight.bold,
                      ),
                      radius: 32,
                    );
                  }).toList(),
                ),
              ),
            ),
            const SizedBox(width: 20),
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: counts.entries.map((e) {
                  return Padding(
                    padding: const EdgeInsets.symmetric(vertical: 3),
                    child: Row(
                      children: [
                        TierChip(tier: e.key, dense: true),
                        const Spacer(),
                        Text(
                          '${e.value}',
                          style: const TextStyle(
                            fontWeight: FontWeight.w600,
                            fontFamily: 'monospace',
                          ),
                        ),
                      ],
                    ),
                  );
                }).toList(),
              ),
            ),
          ],
        ),
      ),
    );
  }
}

class _TopGenesCard extends StatelessWidget {
  final Map<String, int> counts;
  const _TopGenesCard({required this.counts});

  @override
  Widget build(BuildContext context) {
    final maxV = counts.values.isEmpty
        ? 1
        : counts.values.reduce((a, b) => a > b ? a : b);

    return Card(
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          children: counts.entries.map((e) {
            final frac = e.value / maxV;
            return Padding(
              padding: const EdgeInsets.symmetric(vertical: 6),
              child: Row(
                children: [
                  SizedBox(
                    width: 70,
                    child: Text(
                      e.key,
                      style: const TextStyle(
                        fontWeight: FontWeight.w600,
                        fontFamily: 'monospace',
                      ),
                    ),
                  ),
                  Expanded(
                    child: ClipRRect(
                      borderRadius: BorderRadius.circular(4),
                      child: LinearProgressIndicator(
                        value: frac,
                        minHeight: 14,
                        backgroundColor:
                            Theme.of(context).dividerColor.withOpacity(0.2),
                        valueColor: AlwaysStoppedAnimation(
                          Theme.of(context).colorScheme.primary,
                        ),
                      ),
                    ),
                  ),
                  const SizedBox(width: 10),
                  SizedBox(
                    width: 30,
                    child: Text(
                      '${e.value}',
                      textAlign: TextAlign.right,
                      style: const TextStyle(fontFamily: 'monospace'),
                    ),
                  ),
                ],
              ),
            );
          }).toList(),
        ),
      ),
    );
  }
}

class _EmptyHint extends StatelessWidget {
  final IconData icon;
  final String text;
  const _EmptyHint({required this.icon, required this.text});

  @override
  Widget build(BuildContext context) {
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(20),
        child: Row(
          children: [
            Icon(icon, size: 28, color: Theme.of(context).hintColor),
            const SizedBox(width: 14),
            Expanded(
              child: Text(
                text,
                style: TextStyle(color: Theme.of(context).hintColor),
              ),
            ),
          ],
        ),
      ),
    );
  }
}
