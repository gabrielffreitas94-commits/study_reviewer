import 'package:study_reviewer_mobile/core/usecases/usecase.dart';
import 'package:study_reviewer_mobile/features/performance/domain/entities/user_statistics_entity.dart';
import 'package:study_reviewer_mobile/features/performance/domain/repositories/performance_repository.dart';

/// Caso de uso para recuperar o resumo de estatísticas e KPIs do estudante.
class GetUserStatisticsUseCase
    implements UseCase<UserStatisticsEntity, NoParams> {
  final PerformanceRepository repository;

  const GetUserStatisticsUseCase({required this.repository});

  @override
  Future<UserStatisticsEntity> call(NoParams params) async {
    return repository.getUserStatistics();
  }
}
