import 'package:dio/dio.dart';
import 'package:study_reviewer_mobile/core/constants/api_constants.dart';
import 'package:study_reviewer_mobile/core/errors/exceptions.dart';

/// Contrato abstrato do datasource remoto para gerenciamento de configurações e conta.
abstract class SettingsRemoteDataSource {
  Future<void> deleteAccount();
}

/// Implementação remota da exclusão de conta via cliente Dio.
class SettingsRemoteDataSourceImpl implements SettingsRemoteDataSource {
  final Dio client;

  SettingsRemoteDataSourceImpl({required this.client});

  @override
  Future<void> deleteAccount() async {
    try {
      await client.delete<dynamic>(ApiConstants.authAccount);
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
            'Erro ao solicitar exclusão de conta',
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
