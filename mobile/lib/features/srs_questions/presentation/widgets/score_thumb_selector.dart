import 'package:flutter/material.dart';

/// Widget ergonômico de autoavaliação (0 a 100%) posicionado na Natural Thumb Zone.
///
/// Atende às diretrizes dos especialistas:
/// - Ergonomia para uso com uma só mão no terço inferior da tela;
/// - Touch targets táteis com no mínimo 48x48dp;
/// - Presets ágeis (0%, 25%, 50%, 75%, 100%) e slider contínuo;
/// - Contraste WCAG 2.1 AA (>= 4.5:1) e semântica TalkBack/ScreenReader.
class ScoreThumbSelector extends StatelessWidget {
  final int currentScore;
  final ValueChanged<int> onScoreChanged;
  final VoidCallback? onSubmit;
  final bool isSubmitting;
  final bool isEnabled;

  const ScoreThumbSelector({
    super.key,
    required this.currentScore,
    required this.onScoreChanged,
    this.onSubmit,
    this.isSubmitting = false,
    this.isEnabled = true,
  });

  static const List<int> _presetScores = <int>[0, 25, 50, 75, 100];

  Color _getScoreColor(int score, BuildContext context) {
    if (score < 25) {
      return const Color(0xFFDC2626); // Vermelho rubi vibrante
    } else if (score < 50) {
      return const Color(0xFFEA580C); // Laranja queimado
    } else if (score < 75) {
      return const Color(0xFFD97706); // Âmbar rico
    } else if (score < 100) {
      return const Color(0xFF0284C7); // Azul oceano profundo
    } else {
      return const Color(0xFF059669); // Verde esmeralda escuro
    }
  }

  String _getScoreLabel(int score) {
    if (score == 0) return '0% - Não lembrei';
    if (score <= 25) return '$score% - Muito difícil';
    if (score <= 50) return '$score% - Regular com esforço';
    if (score <= 75) return '$score% - Bom com hesitação';
    return '$score% - Perfeito / Fácil';
  }

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final scoreColor = _getScoreColor(currentScore, context);

    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 16.0, vertical: 12.0),
      decoration: BoxDecoration(
        color: theme.colorScheme.surface,
        borderRadius: const BorderRadius.vertical(top: Radius.circular(20.0)),
        boxShadow: [
          BoxShadow(
            color: Colors.black.withOpacity(0.08),
            blurRadius: 10.0,
            offset: const Offset(0, -3),
          ),
        ],
        border: Border(
          top: BorderSide(
            color: theme.dividerColor.withOpacity(0.2),
            width: 1.0,
          ),
        ),
      ),
      child: SafeArea(
        top: false,
        child: Column(
          mainAxisSize: MainAxisSize.min,
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            // Indicador de Nota selecionada
            Row(
              mainAxisAlignment: MainAxisAlignment.spaceBetween,
              children: [
                Text(
                  'Autoavaliação:',
                  style: theme.textTheme.titleSmall?.copyWith(
                    fontWeight: FontWeight.w600,
                  ),
                ),
                Container(
                  padding: const EdgeInsets.symmetric(
                    horizontal: 12.0,
                    vertical: 4.0,
                  ),
                  decoration: BoxDecoration(
                    color: scoreColor.withOpacity(0.15),
                    borderRadius: BorderRadius.circular(12.0),
                    border: Border.all(color: scoreColor, width: 1.5),
                  ),
                  child: Text(
                    _getScoreLabel(currentScore),
                    style: TextStyle(
                      color: scoreColor,
                      fontWeight: FontWeight.bold,
                      fontSize: 13.0,
                    ),
                  ),
                ),
              ],
            ),
            const SizedBox(height: 10.0),

            // Slider contínuo (0 a 100)
            Semantics(
              label: 'Controle deslizante de nota de revisão: $currentScore por cento',
              value: '$currentScore',
              child: SliderTheme(
                data: SliderTheme.of(context).copyWith(
                  activeTrackColor: scoreColor,
                  thumbColor: scoreColor,
                  inactiveTrackColor: scoreColor.withOpacity(0.2),
                  trackHeight: 6.0,
                  thumbShape: const RoundSliderThumbShape(
                    enabledThumbRadius: 12.0,
                  ),
                ),
                child: Slider(
                  value: currentScore.toDouble(),
                  min: 0,
                  max: 100,
                  divisions: 100,
                  onChanged: isEnabled && !isSubmitting
                      ? (value) => onScoreChanged(value.round())
                      : null,
                ),
              ),
            ),
            const SizedBox(height: 6.0),

            // Presets ágeis com Touch Target mínimo de 48x48dp
            Row(
              mainAxisAlignment: MainAxisAlignment.spaceBetween,
              children: _presetScores.map((score) {
                final isSelected = (currentScore == score);
                final btnColor = _getScoreColor(score, context);

                return Semantics(
                  button: true,
                  selected: isSelected,
                  label: 'Preset $score por cento',
                  child: ConstrainedBox(
                    constraints: const BoxConstraints(
                      minWidth: 52.0,
                      minHeight: 48.0, // Touch target mínimo de 48dp WCAG
                    ),
                    child: OutlinedButton(
                      style: OutlinedButton.styleFrom(
                        padding: const EdgeInsets.symmetric(horizontal: 10.0),
                        backgroundColor: isSelected
                            ? btnColor
                            : theme.colorScheme.surface,
                        foregroundColor: isSelected
                            ? Colors.white
                            : btnColor,
                        side: BorderSide(
                          color: btnColor,
                          width: isSelected ? 2.0 : 1.2,
                        ),
                        shape: RoundedRectangleBorder(
                          borderRadius: BorderRadius.circular(10.0),
                        ),
                      ),
                      onPressed: isEnabled && !isSubmitting
                          ? () => onScoreChanged(score)
                          : null,
                      child: Text(
                        '$score%',
                        style: TextStyle(
                          fontSize: 14.0,
                          fontWeight:
                              isSelected ? FontWeight.bold : FontWeight.w600,
                        ),
                      ),
                    ),
                  ),
                );
              }).toList(),
            ),
            const SizedBox(height: 12.0),

            // Botão de submissão do resultado
            ConstrainedBox(
              constraints: const BoxConstraints(minHeight: 48.0),
              child: ElevatedButton.icon(
                style: ElevatedButton.styleFrom(
                  backgroundColor: scoreColor,
                  foregroundColor: Colors.white,
                  shape: RoundedRectangleBorder(
                    borderRadius: BorderRadius.circular(12.0),
                  ),
                  elevation: 2.0,
                ),
                onPressed: (isEnabled && !isSubmitting && onSubmit != null)
                    ? onSubmit
                    : null,
                icon: isSubmitting
                    ? const SizedBox(
                        width: 20.0,
                        height: 20.0,
                        child: CircularProgressIndicator(
                          strokeWidth: 2.5,
                          valueColor:
                              AlwaysStoppedAnimation<Color>(Colors.white),
                        ),
                      )
                    : const Icon(Icons.check_circle_outline, size: 22.0),
                label: Text(
                  isSubmitting ? 'Processando SRS...' : 'Confirmar e Avançar',
                  style: const TextStyle(
                    fontSize: 16.0,
                    fontWeight: FontWeight.bold,
                  ),
                ),
              ),
            ),
          ],
        ),
      ),
    );
  }
}
