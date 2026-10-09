import 'package:equatable/equatable.dart';

/// Entidade de domínio representando o resultado de avaliação dissertativa por IA.
class TextEvaluationResultEntity extends Equatable {
  final String questionId;
  final int score;
  final String feedback;
  final int coverageScore;
  final int accuracyScore;
  final int depthScore;
  final int tokensConsumed;
  final int remainingBalance;
  final bool ragGroundingApplied;

  const TextEvaluationResultEntity({
    required this.questionId,
    required this.score,
    required this.feedback,
    required this.coverageScore,
    required this.accuracyScore,
    required this.depthScore,
    required this.tokensConsumed,
    required this.remainingBalance,
    required this.ragGroundingApplied,
  });

  @override
  List<Object?> get props => [
        questionId,
        score,
        feedback,
        coverageScore,
        accuracyScore,
        depthScore,
        tokensConsumed,
        remainingBalance,
        ragGroundingApplied,
      ];
}
