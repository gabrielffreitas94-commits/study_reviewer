import 'package:flutter/material.dart';
import 'package:study_reviewer_mobile/features/srs_questions/domain/entities/text_evaluation_result_entity.dart';
import 'package:study_reviewer_mobile/features/srs_questions/presentation/widgets/subscore_progress_bar.dart';

/// Card de exibição do parecer avaliativo gerado pela Inteligência Artificial.
///
/// Exibe nota geral de domínio, barras de subscore (Cobertura, Precisão, Profundidade),
/// feedback pedagógico formatado, consumo de tokens e status de fundamentação RAG.
class EvaluationFeedbackCard extends StatelessWidget {
  final TextEvaluationResultEntity evaluation;
  final VoidCallback? onClear;

  const EvaluationFeedbackCard({
    super.key,
    required this.evaluation,
    this.onClear,
  });

  Color _getScoreBadgeColor(int score) {
    if (score >= 80) return const Color(0xFF059669);
    if (score >= 60) return const Color(0xFF0284C7);
    if (score >= 40) return const Color(0xFFD97706);
    return const Color(0xFFDC2626);
  }

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final scoreColor = _getScoreBadgeColor(evaluation.score);

    return Card(
      elevation: 2.0,
      margin: const EdgeInsets.symmetric(vertical: 8.0),
      shape: RoundedRectangleBorder(
        borderRadius: BorderRadius.circular(16.0),
        side: BorderSide(
          color: scoreColor.withOpacity(0.35),
          width: 1.5,
        ),
      ),
      child: Padding(
        padding: const EdgeInsets.all(16.0),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            // Cabeçalho da avaliação com Badge de Domínio
            Row(
              mainAxisAlignment: MainAxisAlignment.spaceBetween,
              children: [
                Row(
                  children: [
                    const Icon(
                      Icons.auto_awesome,
                      color: Color(0xFF6366F1),
                      size: 22.0,
                    ),
                    const SizedBox(width: 8.0),
                    Text(
                      'Avaliação da IA',
                      style: theme.textTheme.titleMedium?.copyWith(
                        fontWeight: FontWeight.bold,
                      ),
                    ),
                  ],
                ),
                Container(
                  padding: const EdgeInsets.symmetric(
                    horizontal: 12.0,
                    vertical: 5.0,
                  ),
                  decoration: BoxDecoration(
                    color: scoreColor.withOpacity(0.15),
                    borderRadius: BorderRadius.circular(12.0),
                    border: Border.all(color: scoreColor, width: 1.5),
                  ),
                  child: Text(
                    '${evaluation.score}% de Domínio',
                    style: TextStyle(
                      color: scoreColor,
                      fontWeight: FontWeight.bold,
                      fontSize: 14.0,
                    ),
                  ),
                ),
              ],
            ),
            const SizedBox(height: 16.0),

            // Grade de Subscores Analíticos
            Text(
              'Métricas Pedagógicas:',
              style: theme.textTheme.labelMedium?.copyWith(
                color: Colors.grey.shade600,
                fontWeight: FontWeight.w600,
              ),
            ),
            const SizedBox(height: 6.0),
            SubscoreProgressBar(
              label: 'Cobertura Conceitual',
              score: evaluation.coverageScore,
              icon: Icons.checklist_rtl,
            ),
            SubscoreProgressBar(
              label: 'Precisão Técnica',
              score: evaluation.accuracyScore,
              icon: Icons.verified_outlined,
            ),
            SubscoreProgressBar(
              label: 'Profundidade da Resposta',
              score: evaluation.depthScore,
              icon: Icons.psychology_outlined,
            ),

            const SizedBox(height: 14.0),

            // Feedback Pedagógico Estruturado
            Container(
              padding: const EdgeInsets.all(12.0),
              decoration: BoxDecoration(
                color: theme.colorScheme.surfaceVariant.withOpacity(0.4),
                borderRadius: BorderRadius.circular(12.0),
                border: Border.all(
                  color: theme.dividerColor.withOpacity(0.2),
                ),
              ),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Row(
                    children: [
                      Icon(
                        Icons.comment_outlined,
                        size: 16.0,
                        color: theme.colorScheme.primary,
                      ),
                      const SizedBox(width: 6.0),
                      Text(
                        'Orientação Pedagógica:',
                        style: theme.textTheme.bodySmall?.copyWith(
                          fontWeight: FontWeight.bold,
                          color: theme.colorScheme.primary,
                        ),
                      ),
                    ],
                  ),
                  const SizedBox(height: 6.0),
                  Text(
                    evaluation.feedback,
                    style: theme.textTheme.bodyMedium?.copyWith(
                      height: 1.45,
                    ),
                  ),
                ],
              ),
            ),

            const SizedBox(height: 12.0),

            // Rodapé com Metadados de Tokens e RAG Grounding
            Wrap(
              spacing: 8.0,
              runSpacing: 4.0,
              alignment: WrapAlignment.spaceBetween,
              crossWrap: WrapCrossAlignment.center,
              children: [
                Row(
                  mainAxisSize: MainAxisSize.min,
                  children: [
                    Icon(
                      Icons.token_outlined,
                      size: 14.0,
                      color: Colors.grey.shade600,
                    ),
                    const SizedBox(width: 4.0),
                    Text(
                      '${evaluation.tokensConsumed} tokens consumidos • Saldo: ${evaluation.remainingBalance}',
                      style: theme.textTheme.bodySmall?.copyWith(
                        color: Colors.grey.shade600,
                        fontSize: 11.5,
                      ),
                    ),
                  ],
                ),
                if (evaluation.ragGroundingApplied)
                  Container(
                    padding: const EdgeInsets.symmetric(
                      horizontal: 8.0,
                      vertical: 2.0,
                    ),
                    decoration: BoxDecoration(
                      color: const Color(0xFF10B981).withOpacity(0.12),
                      borderRadius: BorderRadius.circular(8.0),
                      border: Border.all(
                        color: const Color(0xFF10B981),
                        width: 1.0,
                      ),
                    ),
                    child: const Row(
                      mainAxisSize: MainAxisSize.min,
                      children: [
                        Icon(
                          Icons.verified,
                          size: 12.0,
                          color: Color(0xFF047857),
                        ),
                        SizedBox(width: 4.0),
                        Text(
                          'RAG Ativo',
                          style: TextStyle(
                            fontSize: 11.0,
                            fontWeight: FontWeight.bold,
                            color: Color(0xFF047857),
                          ),
                        ),
                      ],
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
