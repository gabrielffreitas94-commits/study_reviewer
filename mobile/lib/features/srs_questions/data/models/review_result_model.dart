import 'package:study_reviewer_mobile/features/srs_questions/domain/entities/review_result_entity.dart';

/// Modelo de dados para desserialização do resultado do cálculo de repetição espaçada.
class ReviewResultModel extends ReviewResultEntity {
  const ReviewResultModel({
    required super.questionId,
    required super.score,
    required super.levelBefore,
    required super.levelAfter,
    required super.nextReviewDate,
    required super.isPromoted,
    required super.isDemoted,
    required super.isMaintained,
    super.intervalDays = 1,
  });

  factory ReviewResultModel.fromJson(
    Map<String, dynamic> json, {
    int submittedScore = 0,
  }) {
    final rawDate = json['next_review_date']?.toString() ??
        DateTime.now().toIso8601String();
    final parsedDate = DateTime.tryParse(rawDate) ?? DateTime.now();

    final prevLevel = (json['previous_level'] ?? json['level_before'] as num?)
            ?.toInt() ??
        0;
    final newLevel = (json['new_level'] ?? json['level_after'] as num?)
            ?.toInt() ??
        0;

    final isPromoted = (json['is_promoted'] as bool?) ?? (newLevel > prevLevel);
    final isDemoted = (json['is_regressed'] as bool?) ??
        (json['is_demoted'] as bool?) ??
        (newLevel < prevLevel);
    final isMaintained = (json['is_maintained'] as bool?) ??
        (!isPromoted && !isDemoted);

    final scoreVal = (json['score'] as num?)?.toInt() ?? submittedScore;

    return ReviewResultModel(
      questionId: (json['question_id'] ?? json['id'] ?? '').toString(),
      score: scoreVal,
      levelBefore: prevLevel,
      levelAfter: newLevel,
      nextReviewDate: parsedDate,
      isPromoted: isPromoted,
      isDemoted: isDemoted,
      isMaintained: isMaintained,
      intervalDays: (json['interval_days'] as num?)?.toInt() ?? 1,
    );
  }

  Map<String, dynamic> toJson() {
    return <String, dynamic>{
      'question_id': questionId,
      'score': score,
      'previous_level': levelBefore,
      'new_level': levelAfter,
      'next_review_date': nextReviewDate.toIso8601String().split('T').first,
      'is_promoted': isPromoted,
      'is_regressed': isDemoted,
      'is_maintained': isMaintained,
      'interval_days': intervalDays,
    };
  }

  ReviewResultEntity toEntity() => this;
}
