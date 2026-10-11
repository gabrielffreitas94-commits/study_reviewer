import 'package:flutter/material.dart';
import 'package:flutter/services.dart';

/// Área de digitação de resposta dissertativa com TextField expansível,
/// contador de caracteres, botão ergonômico de envio para IA e tratamento de erro de saldo/rede.
class QuestionTextInputArea extends StatefulWidget {
  final TextEditingController controller;
  final bool isEvaluating;
  final String? errorMessage;
  final VoidCallback onSubmit;
  final VoidCallback? onRevealManual;

  const QuestionTextInputArea({
    super.key,
    required this.controller,
    required this.isEvaluating,
    this.errorMessage,
    required this.onSubmit,
    this.onRevealManual,
  });

  @override
  State<QuestionTextInputArea> createState() => _QuestionTextInputAreaState();
}

class _QuestionTextInputAreaState extends State<QuestionTextInputArea>
    with SingleTickerProviderStateMixin {
  late AnimationController _shimmerController;

  @override
  void initState() {
    super.initState();
    _shimmerController = AnimationController(
      vsync: this,
      duration: const Duration(milliseconds: 1500),
    )..repeat(reverse: true);
  }

  @override
  void dispose() {
    _shimmerController.dispose();
    super.dispose();
  }

  bool get _isInsufficientTokens =>
      widget.errorMessage != null &&
      widget.errorMessage!.toLowerCase().contains('saldo');

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);

    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        // Banner de erro ou saldo insuficiente
        if (widget.errorMessage != null) ...[
          Container(
            margin: const EdgeInsets.only(bottom: 12.0),
            padding: const EdgeInsets.all(12.0),
            decoration: BoxDecoration(
              color: _isInsufficientTokens
                  ? const Color(0xFFFEF3C7) // Âmbar suave
                  : const Color(0xFFFEE2E2), // Vermelho suave
              borderRadius: BorderRadius.circular(12.0),
              border: Border.all(
                color: _isInsufficientTokens
                    ? const Color(0xFFF59E0B)
                    : const Color(0xFFEF4444),
                width: 1.2,
              ),
            ),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Row(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Icon(
                      _isInsufficientTokens
                          ? Icons.warning_amber_rounded
                          : Icons.error_outline,
                      color: _isInsufficientTokens
                          ? const Color(0xFFB45309)
                          : const Color(0xFFB91C1C),
                      size: 20.0,
                    ),
                    const SizedBox(width: 8.0),
                    Expanded(
                      child: Text(
                        widget.errorMessage!,
                        style: TextStyle(
                          color: _isInsufficientTokens
                              ? const Color(0xFF92400E)
                              : const Color(0xFF991B1B),
                          fontWeight: FontWeight.w500,
                          fontSize: 13.5,
                          height: 1.35,
                        ),
                      ),
                    ),
                  ],
                ),
                if (_isInsufficientTokens && widget.onRevealManual != null) ...[
                  const SizedBox(height: 8.0),
                  Align(
                    alignment: Alignment.centerRight,
                    child: TextButton.icon(
                      style: TextButton.styleFrom(
                        foregroundColor: const Color(0xFFB45309),
                        padding: const EdgeInsets.symmetric(horizontal: 8.0),
                      ),
                      onPressed: widget.onRevealManual,
                      icon: const Icon(Icons.visibility_outlined, size: 16.0),
                      label: const Text(
                        'Continuar no Modo Manual',
                        style: TextStyle(
                          fontWeight: FontWeight.bold,
                          fontSize: 13.0,
                        ),
                      ),
                    ),
                  ),
                ],
              ],
            ),
          ),
        ],

        // Campo de Texto Expansível Ergonômico
        Container(
          decoration: BoxDecoration(
            color: theme.colorScheme.surface,
            borderRadius: BorderRadius.circular(16.0),
            border: Border.all(
              color: widget.isEvaluating
                  ? const Color(0xFF6366F1)
                  : theme.dividerColor.withOpacity(0.35),
              width: widget.isEvaluating ? 1.8 : 1.2,
            ),
            boxShadow: [
              BoxShadow(
                color: Colors.black.withOpacity(0.03),
                blurRadius: 6.0,
                offset: const Offset(0, 2),
              ),
            ],
          ),
          child: Column(
            children: [
              TextField(
                controller: widget.controller,
                enabled: !widget.isEvaluating,
                minLines: 4,
                maxLines: 8,
                style: theme.textTheme.bodyMedium?.copyWith(
                  fontSize: 15.5,
                  height: 1.45,
                ),
                decoration: InputDecoration(
                  hintText:
                      'Digite sua resposta com suas próprias palavras para avaliação pela IA...',
                  hintStyle: TextStyle(
                    color: Colors.grey.shade400,
                    fontSize: 14.5,
                  ),
                  contentPadding: const EdgeInsets.all(16.0),
                  border: InputBorder.none,
                ),
              ),
              Padding(
                padding: const EdgeInsets.symmetric(
                  horizontal: 16.0,
                  vertical: 8.0,
                ),
                child: Row(
                  mainAxisAlignment: MainAxisAlignment.spaceBetween,
                  children: [
                    Text(
                      '~500 tokens de retenção',
                      style: TextStyle(
                        fontSize: 12.0,
                        color: Colors.grey.shade500,
                      ),
                    ),
                    ValueListenableBuilder<TextEditingValue>(
                      valueListenable: widget.controller,
                      builder: (context, value, child) {
                        return Text(
                          '${value.text.length} caracteres',
                          style: TextStyle(
                            fontSize: 12.0,
                            fontWeight: FontWeight.w500,
                            color: value.text.length >= 3
                                ? theme.colorScheme.primary
                                : Colors.grey.shade500,
                          ),
                        );
                      },
                    ),
                  ],
                ),
              ),
            ],
          ),
        ),

        const SizedBox(height: 14.0),

        // Indicador animado de avaliação em andamento ou botão de submissão
        if (widget.isEvaluating)
          FadeTransition(
            opacity: Tween<double>(begin: 0.6, end: 1.0)
                .animate(_shimmerController),
            child: Container(
              height: 52.0,
              padding: const EdgeInsets.symmetric(horizontal: 16.0),
              decoration: BoxDecoration(
                color: const Color(0xFF6366F1).withOpacity(0.12),
                borderRadius: BorderRadius.circular(14.0),
                border: Border.all(
                  color: const Color(0xFF6366F1).withOpacity(0.4),
                  width: 1.5,
                ),
              ),
              child: const Row(
                mainAxisAlignment: MainAxisAlignment.center,
                children: [
                  SizedBox(
                    width: 20.0,
                    height: 20.0,
                    child: CircularProgressIndicator(
                      strokeWidth: 2.5,
                      valueColor: AlwaysStoppedAnimation<Color>(
                        Color(0xFF6366F1),
                      ),
                    ),
                  ),
                  SizedBox(width: 12.0),
                  Text(
                    '✨ Avaliando com IA (RAG + Gemini)...',
                    style: TextStyle(
                      color: Color(0xFF4F46E5),
                      fontWeight: FontWeight.bold,
                      fontSize: 15.0,
                    ),
                  ),
                ],
              ),
            ),
          )
        else
          ConstrainedBox(
            constraints: const BoxConstraints(minHeight: 48.0), // Touch target >= 48dp
            child: ElevatedButton.icon(
              style: ElevatedButton.styleFrom(
                backgroundColor: const Color(0xFF4F46E5), // Indigo marcante
                foregroundColor: Colors.white,
                shape: RoundedRectangleBorder(
                  borderRadius: BorderRadius.circular(14.0),
                ),
                elevation: 2.0,
              ),
              onPressed: () {
                HapticFeedback.lightImpact();
                widget.onSubmit();
              },
              icon: const Icon(Icons.auto_awesome, size: 20.0),
              label: const Text(
                '✨ Avaliar com IA',
                style: TextStyle(
                  fontSize: 16.0,
                  fontWeight: FontWeight.bold,
                ),
              ),
            ),
          ),
      ],
    );
  }
}
