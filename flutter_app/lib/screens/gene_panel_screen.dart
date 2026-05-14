import 'package:flutter/material.dart';

import '../data/gene_panels.dart';

class GenePanelScreen extends StatelessWidget {
  const GenePanelScreen({super.key});

  @override
  Widget build(BuildContext context) {
    return DefaultTabController(
      length: 4,
      child: Scaffold(
        appBar: AppBar(
          title: const Text('Gene Panels'),
          bottom: const TabBar(
            isScrollable: true,
            tabs: [
              Tab(text: 'Tier 1/2'),
              Tab(text: 'Tier 3'),
              Tab(text: 'Drug targets'),
              Tab(text: 'Risk'),
            ],
          ),
        ),
        body: TabBarView(
          children: [
            _GeneListView(
              title: 'Tier 1/2 lymphoma drivers',
              subtitle:
                  'Established lymphoma drivers with strong/potential clinical significance',
              genes: kTier12Genes.toList()..sort(),
            ),
            _GeneListView(
              title: 'Tier 3 broader cancer genes',
              subtitle:
                  'Genes evaluated at Tier 3 when Tier 1/2 criteria are not met',
              genes: kTier3Genes.toList()..sort(),
            ),
            _GeneListView(
              title: 'Actionable drug targets',
              subtitle:
                  'FDA-approved or late-stage clinical trial agents available',
              genes: kDrugTargetGenes.toList()..sort(),
              therapy: kTherapyHints,
            ),
            _GeneListView(
              title: 'Risk stratification genes',
              subtitle: 'Prognostic / diagnostic markers in lymphoma',
              genes: kRiskStratificationGenes.toList()..sort(),
            ),
          ],
        ),
      ),
    );
  }
}

class _GeneListView extends StatefulWidget {
  final String title;
  final String subtitle;
  final List<String> genes;
  final Map<String, String>? therapy;

  const _GeneListView({
    required this.title,
    required this.subtitle,
    required this.genes,
    this.therapy,
  });

  @override
  State<_GeneListView> createState() => _GeneListViewState();
}

class _GeneListViewState extends State<_GeneListView> {
  String _query = '';

  @override
  Widget build(BuildContext context) {
    final filtered = widget.genes
        .where((g) => g.toUpperCase().contains(_query.toUpperCase()))
        .toList();

    return Column(
      children: [
        Padding(
          padding: const EdgeInsets.fromLTRB(16, 12, 16, 4),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Row(
                children: [
                  Expanded(
                    child: Text(
                      widget.title,
                      style: const TextStyle(
                        fontSize: 16,
                        fontWeight: FontWeight.bold,
                      ),
                    ),
                  ),
                  Chip(
                    label: Text('${widget.genes.length}'),
                    visualDensity: VisualDensity.compact,
                  ),
                ],
              ),
              Text(
                widget.subtitle,
                style: TextStyle(
                  color: Theme.of(context).hintColor,
                  fontSize: 12,
                ),
              ),
            ],
          ),
        ),
        Padding(
          padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
          child: TextField(
            decoration: InputDecoration(
              hintText: 'Filter genes…',
              prefixIcon: const Icon(Icons.search, size: 18),
              isDense: true,
              border: OutlineInputBorder(
                borderRadius: BorderRadius.circular(8),
              ),
            ),
            onChanged: (v) => setState(() => _query = v),
          ),
        ),
        Expanded(
          child: widget.therapy != null
              ? ListView.separated(
                  itemCount: filtered.length,
                  separatorBuilder: (_, __) => const Divider(height: 1),
                  itemBuilder: (_, i) {
                    final g = filtered[i];
                    final t = widget.therapy?[g];
                    return ListTile(
                      dense: true,
                      title: Text(
                        g,
                        style: const TextStyle(
                          fontWeight: FontWeight.w600,
                          fontFamily: 'monospace',
                        ),
                      ),
                      subtitle: t == null
                          ? null
                          : Text(
                              t,
                              style: const TextStyle(fontSize: 12),
                            ),
                    );
                  },
                )
              : Padding(
                  padding: const EdgeInsets.symmetric(horizontal: 12),
                  child: SingleChildScrollView(
                    child: Wrap(
                      spacing: 6,
                      runSpacing: 6,
                      children: filtered.map((g) {
                        return Container(
                          padding: const EdgeInsets.symmetric(
                              horizontal: 10, vertical: 6),
                          decoration: BoxDecoration(
                            color: Theme.of(context)
                                .colorScheme
                                .primaryContainer,
                            borderRadius: BorderRadius.circular(14),
                          ),
                          child: Text(
                            g,
                            style: const TextStyle(
                              fontFamily: 'monospace',
                              fontSize: 12,
                              fontWeight: FontWeight.w600,
                            ),
                          ),
                        );
                      }).toList(),
                    ),
                  ),
                ),
        ),
      ],
    );
  }
}
