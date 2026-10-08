import 'package:study_reviewer_mobile/features/performance/domain/entities/user_statistics_entity.dart';

/// Modelo de dados para mapear as estatísticas consolidadas da API de desempenho.
class UserStatisticsModel extends UserStatisticsEntity {
  const UserStatisticsModel({
    required super.retentionRate,
    required super.matureQuestionsCount,
    required super.totalReviewsCount,
    required super.activeDaysCount,
    required super.srsDistribution,
  });

  factory UserStatisticsModel.fromJson(Map<String, dynamic> json) {
    // Trata distribuição SRS garantindo níveis 0 a 6
    final rawDistribution = json['srs_distribution'];
    final Map<int, int> distributionMap = <int, int>{
      0: 0,
      1: 0,
      2: 0,
      3: 0,
      4: 0,
      5: 0,
      6: 0,
    };

    if (rawDistribution is Map) {
      rawDistribution.forEach((dynamic key, dynamic value) {
        final intLevel = int.tryParse(key.toString());
        final intCount = (value as num?)?.toInt() ?? 0;
        if (intLevel != null && intLevel >= 0 && intLevel <= 6) {
          distributionMap[intLevel] = intCount;
        }
      });
    }

    return UserStatisticsModel(
      retentionRate: (json['retention_rate'] as num?)?.toDouble() ?? 0.0,
      matureQuestionsCount:
          (json['mature_questions_count'] as num?)?.toInt() ?? 0,
      totalReviewsCount: (json['total_reviews_count'] as num?)?.toInt() ?? 0,
      activeDaysCount: (json['active_days_count'] as num?)?.toInt() ?? 0,
      srsDistribution: distributionMap,
    );
  }

  Map<String, dynamic> toJson() {
    return <String, dynamic>{
      'retention_rate': retentionRate,
      'mature_questions_count': matureQuestionsCount,
      'total_reviews_count': totalReviewsCount,
      'active_days_count': activeDaysCount,
      'srs_distribution': srsDistribution.map(
        (key, value) => MapEntry<String, int>(key.toString(), value),
      ),
    };
  }

  UserStatisticsEntity toEntity() => this;
}
