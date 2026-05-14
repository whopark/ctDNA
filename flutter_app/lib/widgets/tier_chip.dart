import 'package:flutter/material.dart';

import '../models/variant.dart';

/// Color-coded chip showing a variant tier.
class TierChip extends StatelessWidget {
  final Tier tier;
  final bool dense;

  const TierChip({super.key, required this.tier, this.dense = false});

  static Color colorFor(Tier t) {
    switch (t) {
      case Tier.tier1:
        return const Color(0xFFD32F2F); // red
      case Tier.tier2:
        return const Color(0xFFF57C00); // orange
      case Tier.tier3:
        return const Color(0xFF1976D2); // blue
      case Tier.tier4:
        return const Color(0xFF616161); // grey
    }
  }

  @override
  Widget build(BuildContext context) {
    final c = colorFor(tier);
    return Container(
      padding: EdgeInsets.symmetric(
        horizontal: dense ? 8 : 10,
        vertical: dense ? 2 : 4,
      ),
      decoration: BoxDecoration(
        color: c.withOpacity(0.12),
        border: Border.all(color: c, width: 1),
        borderRadius: BorderRadius.circular(12),
      ),
      child: Text(
        tier.label,
        style: TextStyle(
          color: c,
          fontWeight: FontWeight.w600,
          fontSize: dense ? 11 : 13,
        ),
      ),
    );
  }
}
