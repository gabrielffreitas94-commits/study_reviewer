import 'package:study_reviewer_mobile/features/srs_questions/domain/entities/text_evaluation_result_entity.dart';

/// Modelo de dados para serialização e desserialização da avaliação dissertativa por IA.
class TextEvaluationResultModel extends TextEvaluationResultEntity {
  const TextEvaluationResultModel({
    required super.questionId,
    required super.score,
    required super.feedback,
    required super.coverageScore,
    required super.accuracyScore,
    required super.depthScore,
    required super.tokensConsumed,
    required super.remainingBalance,
    required super.ragGroundingApplied,
  });

  factory TextEvaluationResultModel.fromJson(Map<String, dynamic> json) {
    return TextEvaluationResultModel(
      questionId: (json['question_id'] ?? json['questionId'] ?? json['id'] ?? '').toString(),
      score: (json['score'] as num?)?.round() ?? 0,
      feedback: (json['feedback'] ?? '').toString(),
      coverageScore:
          ((json['coverage_score'] ?? json['coverageScore']) as num?)?.round() ?? 0,
      accuracyScore:
          ((json['accuracy_score'] ?? json['accuracyScore']) as num?)?.round() ?? 0,
      depthScore:
          ((json['depth_score'] ?? json['depthScore']) as num?)?.round() ?? 0,
      tokensConsumed:
          ((json['tokens_consumed'] ?? json['tokensConsumed']) as num?)?.round() ?? 0,
      remainingBalance:
          ((json['remaining_balance'] ?? json['remainingBalance']) as num?)?.round() ?? 0,
      ragGroundingApplied: json['rag_grounding_applied'] as bool? ??
          json['ragGroundingApplied'] as bool? ??
          false,
    );
  }

  Map<String, dynamic> toJson() {
    return <String, dynamic>{
      'question_id': questionId,
      'score': score,
      'feedback': feedback,
      'coverage_score': coverageScore,
      'accuracy_score': accuracyScore,
      'depth_score': depthScore,
      'tokens_consumed': tokensConsumed,
      'remaining_balance': remainingBalance,
      'rag_grounding_applied': ragGroundingApplied,
    };
  }

  TextEvaluationResultEntity toEntity() => this;
}
