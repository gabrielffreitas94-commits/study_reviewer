import 'package:equatable/equatable.dart';

/// Entidade de domínio para os KPIs de estudo e distribuição SRS do estudante.
class UserStatisticsEntity extends Equatable {
  final double retentionRate;
  final int matureQuestionsCount;
  final int totalReviewsCount;
  final int activeDaysCount;
  final Map<int, int> srsDistribution;

  const UserStatisticsEntity({
    required this.retentionRate,
    required this.matureQuestionsCount,
    required this.totalReviewsCount,
    required this.activeDaysCount,
    required this.srsDistribution,
  });

  /// Total de cards/perguntas em todos os níveis SRS combinados.
  int get totalCardsInSrs =>
      srsDistribution.values.fold<int>(0, (sum, count) => sum + count);

  @override
  List<Object?> get props => [
        retentionRate,
        matureQuestionsCount,
        totalReviewsCount,
        activeDaysCount,
        srsDistribution,
      ];
}
