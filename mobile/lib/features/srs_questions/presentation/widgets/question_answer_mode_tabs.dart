import 'package:flutter/material.dart';
import 'package:flutter/services.dart';

/// Seletor de abas/modos para formulação de resposta na pergunta aberta.
///
/// Modos suportados:
/// - 0: ✍️ Digitar Resposta (com auxílio de avaliação por IA)
/// - 1: 💡 Apenas Gabarito (Active Recall Manual sem consumo de tokens)
class QuestionAnswerModeTabs extends StatelessWidget {
  final int activeMode;
  final ValueChanged<int> onModeChanged;
  final bool isEnabled;

  const QuestionAnswerModeTabs({
    super.key,
    required this.activeMode,
    required this.onModeChanged,
    this.isEnabled = true,
  });

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);

    return Container(
      margin: const EdgeInsets.symmetric(vertical: 8.0),
      padding: const EdgeInsets.all(4.0),
      decoration: BoxDecoration(
        color: theme.colorScheme.surfaceVariant.withOpacity(0.5),
        borderRadius: BorderRadius.circular(14.0),
        border: Border.all(color: theme.dividerColor.withOpacity(0.2)),
      ),
      child: Row(
        children: [
          Expanded(
            child: _buildTabButton(
              context: context,
              title: '✍️ Digitar Resposta',
              mode: 0,
              isSelected: activeMode == 0,
            ),
          ),
          const SizedBox(width: 4.0),
          Expanded(
            child: _buildTabButton(
              context: context,
              title: '💡 Apenas Gabarito',
              mode: 1,
              isSelected: activeMode == 1,
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildTabButton({
    required BuildContext context,
    required String title,
    required int mode,
    required bool isSelected,
  }) {
    final theme = Theme.of(context);

    return ConstrainedBox(
      constraints: const BoxConstraints(minHeight: 48.0), // Touch target >= 48dp
      child: InkWell(
        borderRadius: BorderRadius.circular(10.0),
        onTap: isEnabled
            ? () {
                if (activeMode != mode) {
                  HapticFeedback.lightImpact();
                  onModeChanged(mode);
                }
              }
            : null,
        child: Container(
          alignment: Alignment.center,
          padding: const EdgeInsets.symmetric(horizontal: 12.0, vertical: 10.0),
          decoration: BoxDecoration(
            color: isSelected ? theme.colorScheme.primary : Colors.transparent,
            borderRadius: BorderRadius.circular(10.0),
            boxShadow: isSelected
                ? [
                    BoxShadow(
                      color: theme.colorScheme.primary.withOpacity(0.3),
                      blurRadius: 6.0,
                      offset: const Offset(0, 2),
                    ),
                  ]
                : null,
          ),
          child: Text(
            title,
            style: TextStyle(
              fontSize: 14.0,
              fontWeight: isSelected ? FontWeight.bold : FontWeight.w600,
              color: isSelected
                  ? theme.colorScheme.onPrimary
                  : theme.textTheme.bodyMedium?.color?.withOpacity(0.75),
            ),
            textAlign: TextAlign.center,
          ),
        ),
      ),
    );
  }
}
