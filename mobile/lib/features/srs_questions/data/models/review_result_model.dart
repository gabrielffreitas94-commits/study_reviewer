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

    final dynamic rawPrev = json['previous_level'] ?? json['level_before'];
    final int prevLevel = (rawPrev is num) ? rawPrev.toInt() : 0;

    final dynamic rawNew = json['new_level'] ?? json['level_after'];
    final int newLevel = (rawNew is num) ? rawNew.toInt() : 0;

    final bool isPromoted = (json['is_promoted'] is bool)
        ? (json['is_promoted'] as bool)
        : (newLevel > prevLevel);
    final bool isDemoted = (json['is_regressed'] is bool)
        ? (json['is_regressed'] as bool)
        : ((json['is_demoted'] is bool)
            ? (json['is_demoted'] as bool)
            : (newLevel < prevLevel));
    final bool isMaintained = (json['is_maintained'] is bool)
        ? (json['is_maintained'] as bool)
        : (!isPromoted && !isDemoted);

    final dynamic rawScore = json['score'];
    final int scoreVal = (rawScore is num) ? rawScore.toInt() : submittedScore;

    final dynamic rawInterval = json['interval_days'];
    final int intervalVal = (rawInterval is num) ? rawInterval.toInt() : 1;

    return ReviewResultModel(
      questionId: (json['question_id'] ?? json['id'] ?? '').toString(),
      score: scoreVal,
      levelBefore: prevLevel,
      levelAfter: newLevel,
      nextReviewDate: parsedDate,
      isPromoted: isPromoted,
      isDemoted: isDemoted,
      isMaintained: isMaintained,
      intervalDays: intervalVal,
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
