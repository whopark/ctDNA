import 'package:flutter/material.dart';

import '../models/case_record.dart';
import '../models/variant.dart';
import '../services/case_repository.dart';
import '../widgets/tier_chip.dart';
import '../widgets/variant_tile.dart';
import 'variant_detail_screen.dart';

class CaseDetailScreen extends StatefulWidget {
  final String caseId;
  final CaseRepository repo;
  const CaseDetailScreen({
    super.key,
    required this.caseId,
    required this.repo,
  });

  @override
  State<CaseDetailScreen> createState() => _CaseDetailScreenState();
}

class _CaseDetailScreenState extends State<CaseDetailScreen> {
  final Set<Tier> _activeTiers = {Tier.tier1, Tier.tier2, Tier.tier3};
  double _minVafPct = 1.0;
  String _query = '';

  @override
  Widget build(BuildContext context) {
    final c = widget.repo.byId(widget.caseId);
    if (c == null) {
      return Scaffold(
        appBar: AppBar(title: Text(widget.caseId)),
        body: const Center(child: Text('Case not found')),
      );
    }

    final filtered = c.variants.where((v) {
      if (!_activeTiers.contains(v.tier)) return false;
      if (v.vafPct < _minVafPct) return false;
      if (_query.isNotEmpty) {
        final q = _query.toUpperCase();
        if (!v.gene.toUpperCase().contains(q) &&
            !(v.hgvsp?.toUpperCase().contains(q) ?? false) &&
            !(v.hgvsc?.toUpperCase().contains(q) ?? false)) {
          return false;
        }
      }
      return true;
    }).toList()
      ..sort((a, b) {
        final ta = a.tier.index.compareTo(b.tier.index);
        if (ta != 0) return ta;
        return b.sampleAf.compareTo(a.sampleAf);
      });

    return Scaffold(
      appBar: AppBar(
        title: Text(c.id, overflow: TextOverflow.ellipsis),
        bottom: PreferredSize(
          preferredSize: const Size.fromHeight(120),
          child: _FilterBar(
            activeTiers: _activeTiers,
            minVafPct: _minVafPct,
            onTierToggle: (t) => setState(() {
              if (_activeTiers.contains(t)) {
                _activeTiers.remove(t);
              } else {
                _activeTiers.add(t);
              }
            }),
            onMinVafChanged: (v) => setState(() => _minVafPct = v),
            onSearch: (q) => setState(() => _query = q),
          ),
        ),
      ),
      body: Column(
        children: [
          _MetaCard(caseRecord: c),
          Padding(
            padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 4),
            child: Row(
              children: [
                Text(
                  '${filtered.length} variant${filtered.length == 1 ? '' : 's'} shown',
                  style: TextStyle(
                    color: Theme.of(context).hintColor,
                    fontSize: 12,
                  ),
                ),
                const Spacer(),
                Text(
                  'sorted: tier ↑, VAF ↓',
                  style: TextStyle(
                    color: Theme.of(context).hintColor,
                    fontSize: 11,
                  ),
                ),
              ],
            ),
          ),
          Expanded(
            child: filtered.isEmpty
                ? Center(
                    child: Padding(
                      padding: const EdgeInsets.all(24),
                      child: Text(
                        'No variants match the current filters.',
                        textAlign: TextAlign.center,
                        style: TextStyle(color: Theme.of(context).hintColor),
                      ),
                    ),
                  )
                : ListView.builder(
                    padding: const EdgeInsets.only(bottom: 16),
                    itemCount: filtered.length,
                    itemBuilder: (_, i) => VariantTile(
                      variant: filtered[i],
                      onTap: () {
                        Navigator.of(context).push(MaterialPageRoute(
                          builder: (_) => VariantDetailScreen(
                            variant: filtered[i],
                            caseId: c.id,
                          ),
                        ));
                      },
                    ),
                  ),
          ),
        ],
      ),
    );
  }
}

class _MetaCard extends StatelessWidget {
  final CaseRecord caseRecord;
  const _MetaCard({required this.caseRecord});

  @override
  Widget build(BuildContext context) {
    final counts = caseRecord.tierCounts();
    return Card(
      margin: const EdgeInsets.all(12),
      child: Padding(
        padding: const EdgeInsets.all(14),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                Icon(Icons.person_outline,
                    color: Theme.of(context).hintColor, size: 18),
                const SizedBox(width: 6),
                Text(
                  caseRecord.patientName ?? '(unknown patient)',
                  style: const TextStyle(fontWeight: FontWeight.w600),
                ),
                if (caseRecord.regNo != null) ...[
                  const SizedBox(width: 10),
                  Text(
                    '#${caseRecord.regNo}',
                    style: TextStyle(
                      color: Theme.of(context).hintColor,
                      fontSize: 13,
                    ),
                  ),
                ],
              ],
            ),
            const SizedBox(height: 10),
            Wrap(
              spacing: 8,
              runSpacing: 6,
              children: [
                for (final t in Tier.values)
                  if ((counts[t] ?? 0) > 0)
                    Container(
                      padding: const EdgeInsets.symmetric(
                          horizontal: 8, vertical: 3),
                      decoration: BoxDecoration(
                        color: TierChip.colorFor(t).withOpacity(0.12),
                        borderRadius: BorderRadius.circular(10),
                      ),
                      child: Text(
                        '${t.label}: ${counts[t]}',
                        style: TextStyle(
                          color: TierChip.colorFor(t),
                          fontSize: 11,
                          fontWeight: FontWeight.w600,
                        ),
                      ),
                    ),
              ],
            ),
          ],
        ),
      ),
    );
  }
}

class _FilterBar extends StatelessWidget {
  final Set<Tier> activeTiers;
  final double minVafPct;
  final ValueChanged<Tier> onTierToggle;
  final ValueChanged<double> onMinVafChanged;
  final ValueChanged<String> onSearch;

  const _FilterBar({
    required this.activeTiers,
    required this.minVafPct,
    required this.onTierToggle,
    required this.onMinVafChanged,
    required this.onSearch,
  });

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.fromLTRB(12, 0, 12, 8),
      child: Column(
        children: [
          SizedBox(
            height: 40,
            child: TextField(
              decoration: InputDecoration(
                hintText: 'Search gene / HGVS…',
                prefixIcon: const Icon(Icons.search, size: 18),
                isDense: true,
                border: OutlineInputBorder(
                  borderRadius: BorderRadius.circular(8),
                ),
              ),
              onChanged: onSearch,
            ),
          ),
          const SizedBox(height: 6),
          Row(
            children: [
              for (final t in Tier.values)
                Padding(
                  padding: const EdgeInsets.only(right: 6),
                  child: FilterChip(
                    label: Text(t.label),
                    selected: activeTiers.contains(t),
                    onSelected: (_) => onTierToggle(t),
                    selectedColor:
                        TierChip.colorFor(t).withOpacity(0.25),
                    showCheckmark: false,
                  ),
                ),
              const Spacer(),
              Text('VAF≥', style: TextStyle(color: Theme.of(context).hintColor)),
              SizedBox(
                width: 110,
                child: Slider(
                  min: 0,
                  max: 10,
                  divisions: 20,
                  value: minVafPct,
                  label: '${minVafPct.toStringAsFixed(1)}%',
                  onChanged: onMinVafChanged,
                ),
              ),
              SizedBox(
                width: 40,
                child: Text(
                  '${minVafPct.toStringAsFixed(1)}%',
                  textAlign: TextAlign.right,
                  style: const TextStyle(fontFamily: 'monospace'),
                ),
              ),
            ],
          ),
        ],
      ),
    );
  }
}
