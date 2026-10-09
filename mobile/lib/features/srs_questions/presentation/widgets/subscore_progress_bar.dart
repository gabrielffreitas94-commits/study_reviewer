import 'package:flutter/material.dart';

/// Barra de progresso animada e acessível para exibição de métricas pedagógicas (subscores).
class SubscoreProgressBar extends StatelessWidget {
  final String label;
  final int score;
  final IconData? icon;

  const SubscoreProgressBar({
    super.key,
    required this.label,
    required this.score,
    this.icon,
  });

  Color _getScoreColor(int score) {
    if (score >= 80) {
      return const Color(0xFF059669); // Verde esmeralda
    } else if (score >= 60) {
      return const Color(0xFF0284C7); // Azul oceano
    } else if (score >= 40) {
      return const Color(0xFFD97706); // Âmbar
    } else {
      return const Color(0xFFDC2626); // Vermelho
    }
  }

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final clampedScore = score.clamp(0, 100);
    final color = _getScoreColor(clampedScore);

    return Semantics(
      label: '$label: $clampedScore por cento',
      child: Padding(
        padding: const EdgeInsets.symmetric(vertical: 4.0),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              mainAxisAlignment: MainAxisAlignment.spaceBetween,
              children: [
                Row(
                  children: [
                    if (icon != null) ...[
                      Icon(icon, size: 16.0, color: color),
                      const SizedBox(width: 6.0),
                    ],
                    Text(
                      label,
                      style: theme.textTheme.bodyMedium?.copyWith(
                        fontWeight: FontWeight.w600,
                      ),
                    ),
                  ],
                ),
                Text(
                  '$clampedScore%',
                  style: theme.textTheme.bodyMedium?.copyWith(
                    fontWeight: FontWeight.bold,
                    color: color,
                  ),
                ),
              ],
            ),
            const SizedBox(height: 6.0),
            ClipRRect(
              borderRadius: BorderRadius.circular(6.0),
              child: TweenAnimationBuilder<double>(
                duration: const Duration(milliseconds: 600),
                curve: Curves.easeOutCubic,
                tween: Tween<double>(begin: 0.0, end: clampedScore / 100.0),
                builder: (context, value, child) {
                  return LinearProgressIndicator(
                    value: value,
                    minHeight: 8.0,
                    backgroundColor: color.withOpacity(0.15),
                    valueColor: AlwaysStoppedAnimation<Color>(color),
                  );
                },
              ),
            ),
          ],
        ),
      ),
    );
  }
}
