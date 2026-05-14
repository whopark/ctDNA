import 'dart:convert';

import 'package:file_picker/file_picker.dart';
import 'package:flutter/material.dart';

import '../data/sample_data.dart';
import '../models/case_record.dart';
import '../models/variant.dart';
import '../services/case_repository.dart';
import '../services/csv_import.dart';
import '../widgets/tier_chip.dart';
import 'case_detail_screen.dart';

class CasesScreen extends StatefulWidget {
  final CaseRepository repo;
  const CasesScreen({super.key, required this.repo});

  @override
  State<CasesScreen> createState() => _CasesScreenState();
}

class _CasesScreenState extends State<CasesScreen> {
  bool _busy = false;

  Future<void> _loadSamples() async {
    setState(() => _busy = true);
    for (final c in SampleData.seed()) {
      await widget.repo.add(c);
    }
    if (mounted) setState(() => _busy = false);
  }

  Future<void> _importCsv() async {
    setState(() => _busy = true);
    try {
      final result = await FilePicker.platform.pickFiles(
        type: FileType.custom,
        allowedExtensions: ['csv'],
        withData: true,
      );
      if (result == null || result.files.isEmpty) return;

      for (final f in result.files) {
        String text;
        if (f.bytes != null) {
          text = utf8.decode(f.bytes!, allowMalformed: true);
        } else {
          continue;
        }
        final name = f.name.replaceAll(RegExp(r'\.csv$', caseSensitive: false), '');
        final caseId = name.replaceAll(RegExp(r'_annotated$'), '');
        final c = CsvImportService.parse(caseId, text);
        await widget.repo.add(c);
      }

      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text('Imported ${result.files.length} file(s)')),
        );
      }
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text('Import failed: $e')),
        );
      }
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  Future<void> _confirmClear() async {
    final yes = await showDialog<bool>(
      context: context,
      builder: (_) => AlertDialog(
        title: const Text('Remove all cases?'),
        content: const Text(
            'This will clear all loaded cases from local storage. This action cannot be undone.'),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(context, false),
            child: const Text('Cancel'),
          ),
          FilledButton(
            onPressed: () => Navigator.pop(context, true),
            child: const Text('Clear'),
          ),
        ],
      ),
    );
    if (yes == true) {
      await widget.repo.clear();
    }
  }

  @override
  Widget build(BuildContext context) {
    final cases = widget.repo.cases;

    return Scaffold(
      appBar: AppBar(
        title: const Text('Cases'),
        actions: [
          PopupMenuButton<String>(
            onSelected: (v) {
              switch (v) {
                case 'sample':
                  _loadSamples();
                  break;
                case 'import':
                  _importCsv();
                  break;
                case 'clear':
                  _confirmClear();
                  break;
              }
            },
            itemBuilder: (_) => const [
              PopupMenuItem(
                value: 'sample',
                child: ListTile(
                  leading: Icon(Icons.auto_fix_high),
                  title: Text('Load sample cases'),
                  contentPadding: EdgeInsets.zero,
                ),
              ),
              PopupMenuItem(
                value: 'import',
                child: ListTile(
                  leading: Icon(Icons.upload_file),
                  title: Text('Import annotated CSV'),
                  contentPadding: EdgeInsets.zero,
                ),
              ),
              PopupMenuItem(
                value: 'clear',
                child: ListTile(
                  leading: Icon(Icons.delete_outline),
                  title: Text('Clear all'),
                  contentPadding: EdgeInsets.zero,
                ),
              ),
            ],
          ),
        ],
      ),
      body: _busy
          ? const Center(child: CircularProgressIndicator())
          : cases.isEmpty
              ? _EmptyView(onLoadSamples: _loadSamples, onImport: _importCsv)
              : ListView.builder(
                  padding: const EdgeInsets.symmetric(vertical: 8),
                  itemCount: cases.length,
                  itemBuilder: (_, i) => _CaseTile(
                    caseRecord: cases[i],
                    onTap: () {
                      Navigator.of(context).push(MaterialPageRoute(
                        builder: (_) => CaseDetailScreen(
                          caseId: cases[i].id,
                          repo: widget.repo,
                        ),
                      ));
                    },
                    onDelete: () => widget.repo.remove(cases[i].id),
                  ),
                ),
      floatingActionButton: FloatingActionButton.extended(
        onPressed: _importCsv,
        icon: const Icon(Icons.upload_file),
        label: const Text('Import CSV'),
      ),
    );
  }
}

class _CaseTile extends StatelessWidget {
  final CaseRecord caseRecord;
  final VoidCallback onTap;
  final VoidCallback onDelete;

  const _CaseTile({
    required this.caseRecord,
    required this.onTap,
    required this.onDelete,
  });

  @override
  Widget build(BuildContext context) {
    final counts = caseRecord.tierCounts();
    return Card(
      margin: const EdgeInsets.symmetric(horizontal: 12, vertical: 4),
      child: InkWell(
        onTap: onTap,
        borderRadius: BorderRadius.circular(8),
        child: Padding(
          padding: const EdgeInsets.all(14),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Row(
                children: [
                  Expanded(
                    child: Text(
                      caseRecord.id,
                      style: const TextStyle(
                        fontWeight: FontWeight.bold,
                        fontSize: 16,
                      ),
                    ),
                  ),
                  IconButton(
                    icon: const Icon(Icons.delete_outline, size: 20),
                    tooltip: 'Remove case',
                    onPressed: onDelete,
                  ),
                ],
              ),
              if (caseRecord.patientName != null ||
                  caseRecord.regNo != null) ...[
                const SizedBox(height: 4),
                Text(
                  [
                    if (caseRecord.patientName != null)
                      caseRecord.patientName!,
                    if (caseRecord.regNo != null) '#${caseRecord.regNo!}',
                  ].join(' · '),
                  style:
                      TextStyle(color: Theme.of(context).hintColor, fontSize: 13),
                ),
              ],
              const SizedBox(height: 10),
              Wrap(
                spacing: 6,
                runSpacing: 6,
                children: [
                  for (final t in Tier.values)
                    if ((counts[t] ?? 0) > 0)
                      _TierCountChip(tier: t, count: counts[t]!),
                  if (caseRecord.totalVariants == 0)
                    Text(
                      'No variants',
                      style: TextStyle(color: Theme.of(context).hintColor),
                    ),
                ],
              ),
              const SizedBox(height: 6),
              Text(
                '${caseRecord.totalVariants} variants',
                style: TextStyle(
                  color: Theme.of(context).hintColor,
                  fontSize: 12,
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }
}

class _TierCountChip extends StatelessWidget {
  final Tier tier;
  final int count;
  const _TierCountChip({required this.tier, required this.count});

  @override
  Widget build(BuildContext context) {
    final c = TierChip.colorFor(tier);
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 3),
      decoration: BoxDecoration(
        color: c.withOpacity(0.12),
        border: Border.all(color: c.withOpacity(0.5)),
        borderRadius: BorderRadius.circular(10),
      ),
      child: Text(
        '${tier.label}: $count',
        style: TextStyle(
          color: c,
          fontSize: 11,
          fontWeight: FontWeight.w600,
        ),
      ),
    );
  }
}

class _EmptyView extends StatelessWidget {
  final VoidCallback onLoadSamples;
  final VoidCallback onImport;
  const _EmptyView({required this.onLoadSamples, required this.onImport});

  @override
  Widget build(BuildContext context) {
    return Center(
      child: Padding(
        padding: const EdgeInsets.all(28),
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            Icon(Icons.science_outlined,
                size: 60, color: Theme.of(context).hintColor),
            const SizedBox(height: 16),
            const Text(
              'No cases loaded',
              style: TextStyle(fontSize: 18, fontWeight: FontWeight.bold),
            ),
            const SizedBox(height: 8),
            Text(
              'Load sample cases for a demo, or import an annotated CSV '
              'produced by annotate_vcf.py.',
              textAlign: TextAlign.center,
              style: TextStyle(color: Theme.of(context).hintColor),
            ),
            const SizedBox(height: 20),
            Wrap(
              spacing: 10,
              children: [
                FilledButton.icon(
                  icon: const Icon(Icons.auto_fix_high),
                  label: const Text('Load samples'),
                  onPressed: onLoadSamples,
                ),
                OutlinedButton.icon(
                  icon: const Icon(Icons.upload_file),
                  label: const Text('Import CSV'),
                  onPressed: onImport,
                ),
              ],
            ),
          ],
        ),
      ),
    );
  }
}
