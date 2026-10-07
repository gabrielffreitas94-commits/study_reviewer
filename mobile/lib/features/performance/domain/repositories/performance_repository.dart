import 'package:study_reviewer_mobile/features/performance/domain/entities/user_statistics_entity.dart';

/// Contrato abstrato do repositório para o módulo de Performance e Estatísticas.
abstract class PerformanceRepository {
  /// Retorna as métricas consolidadas, KPIs e distribuição da pirâmide SRS.
  Future<UserStatisticsEntity> getUserStatistics();
}
