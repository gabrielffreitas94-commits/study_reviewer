import 'package:study_reviewer_mobile/core/errors/exceptions.dart';
import 'package:study_reviewer_mobile/core/errors/failures.dart';
import 'package:study_reviewer_mobile/features/performance/data/datasources/performance_remote_data_source.dart';
import 'package:study_reviewer_mobile/features/performance/domain/entities/user_statistics_entity.dart';
import 'package:study_reviewer_mobile/features/performance/domain/repositories/performance_repository.dart';

/// Implementação concreta do repositório de desempenho na camada de dados.
class PerformanceRepositoryImpl implements PerformanceRepository {
  final PerformanceRemoteDataSource remoteDataSource;

  const PerformanceRepositoryImpl({required this.remoteDataSource});

  @override
  Future<UserStatisticsEntity> getUserStatistics() async {
    try {
      final model = await remoteDataSource.getUserStatistics();
      return model.toEntity();
    } on NetworkException catch (e) {
      throw NetworkFailure(e.message);
    } on ServerException catch (e) {
      throw ServerFailure(message: e.message, statusCode: e.statusCode);
    } catch (e) {
      throw ServerFailure(
        message: 'Falha inesperada ao recuperar métricas de estudo: $e',
      );
    }
  }
}
