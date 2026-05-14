import 'package:flutter/material.dart';

import '../models/variant.dart';
import 'tier_chip.dart';

/// Compact list tile representing a Variant.
class VariantTile extends StatelessWidget {
  final Variant variant;
  final VoidCallback? onTap;

  const VariantTile({super.key, required this.variant, this.onTap});

  @override
  Widget build(BuildContext context) {
    final (_, nuc) = variant.nucleotideChange;
    final (_, prot) = variant.proteinChange;
    final cs = (variant.clinSig ?? '').replaceAll('_', ' ');

    return Card(
      margin: const EdgeInsets.symmetric(horizontal: 12, vertical: 4),
      child: InkWell(
        onTap: onTap,
        borderRadius: BorderRadius.circular(8),
        child: Padding(
          padding: const EdgeInsets.all(12),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Row(
                children: [
                  Text(
                    variant.gene,
                    style: const TextStyle(
                      fontWeight: FontWeight.bold,
                      fontSize: 17,
                    ),
                  ),
                  const SizedBox(width: 10),
                  TierChip(tier: variant.tier, dense: true),
                  const Spacer(),
                  Text(
                    '${variant.vafPct.toStringAsFixed(2)}%',
                    style: const TextStyle(
                      fontWeight: FontWeight.w600,
                      fontFamily: 'monospace',
                    ),
                  ),
                ],
              ),
              const SizedBox(height: 6),
              if (prot.isNotEmpty)
                Text(
                  prot,
                  style: const TextStyle(
                    fontFamily: 'monospace',
                    fontSize: 13,
                  ),
                )
              else if (nuc.isNotEmpty)
                Text(
                  nuc,
                  style: const TextStyle(
                    fontFamily: 'monospace',
                    fontSize: 13,
                  ),
                ),
              const SizedBox(height: 4),
              Row(
                children: [
                  Text(
                    'chr${variant.chrom}:${variant.pos}',
                    style: TextStyle(
                      fontSize: 12,
                      color: Theme.of(context).hintColor,
                      fontFamily: 'monospace',
                    ),
                  ),
                  const SizedBox(width: 12),
                  if (cs.isNotEmpty)
                    Expanded(
                      child: Text(
                        cs,
                        style: TextStyle(
                          fontSize: 12,
                          color: Theme.of(context).hintColor,
                        ),
                        overflow: TextOverflow.ellipsis,
                      ),
                    ),
                ],
              ),
            ],
          ),
        ),
      ),
    );
  }
}
