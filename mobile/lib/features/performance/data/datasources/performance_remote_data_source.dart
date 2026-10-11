import 'package:dio/dio.dart';
import 'package:study_reviewer_mobile/core/constants/api_constants.dart';
import 'package:study_reviewer_mobile/core/errors/exceptions.dart';
import 'package:study_reviewer_mobile/features/performance/data/models/user_statistics_model.dart';

/// Contrato abstrato do datasource remoto para estatísticas de desempenho.
abstract class PerformanceRemoteDataSource {
  Future<UserStatisticsModel> getUserStatistics();
}

/// Implementação remota via cliente Dio para o endpoint /api/v1/performance/statistics.
class PerformanceRemoteDataSourceImpl implements PerformanceRemoteDataSource {
  final Dio client;

  PerformanceRemoteDataSourceImpl({required this.client});

  @override
  Future<UserStatisticsModel> getUserStatistics() async {
    try {
      final response = await client.get<Map<String, dynamic>>(
        ApiConstants.performanceStatistics,
      );

      final data = response.data;
      if (data == null) {
        throw const ServerException(message: 'Resposta vazia do servidor');
      }

      return UserStatisticsModel.fromJson(data);
    } on DioException catch (e) {
      if (e.type == DioExceptionType.connectionError ||
          e.type == DioExceptionType.connectionTimeout) {
        throw NetworkException(
          message: e.message ?? 'Falha de conexão com a rede',
        );
      }
      throw ServerException(
        message: e.response?.data?['detail']?.toString() ??
            e.message ??
            'Erro ao carregar estatísticas de estudo',
        statusCode: e.response?.statusCode,
      );
    } catch (e) {
      if (e is NetworkException || e is ServerException) {
        rethrow;
      }
      throw ServerException(message: 'Erro inesperado: $e');
    }
  }
}
