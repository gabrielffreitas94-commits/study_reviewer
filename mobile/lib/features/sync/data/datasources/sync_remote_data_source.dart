import 'dart:math';
import 'package:dio/dio.dart';
import 'package:study_reviewer_mobile/core/constants/api_constants.dart';
import 'package:study_reviewer_mobile/core/errors/exceptions.dart';
import 'package:study_reviewer_mobile/features/sync/data/models/study_event_model.dart';

abstract class SyncRemoteDataSource {
  Future<SyncAnswersResponseModel> syncAnswers({
    required String sessionId,
    required List<StudyEventModel> events,
    int? batchIndex,
    String? correlationId,
  });
}

class SyncRemoteDataSourceImpl implements SyncRemoteDataSource {
  final Dio client;

  SyncRemoteDataSourceImpl({required this.client});

  String _generateCorrelationId() {
    final timestamp = DateTime.now().millisecondsSinceEpoch;
    final randomPart = Random().nextInt(0xFFFFFF).toRadixString(16).padLeft(6, '0');
    return 'sync-$timestamp-$randomPart';
  }

  @override
  Future<SyncAnswersResponseModel> syncAnswers({
    required String sessionId,
    required List<StudyEventModel> events,
    int? batchIndex,
    String? correlationId,
  }) async {
    try {
      final effectiveCorrelationId = correlationId ?? _generateCorrelationId();
      final payload = SyncAnswersPayloadModel(
        sessionId: sessionId,
        events: events,
        batchIndex: batchIndex,
      );

      final response = await client.post<Map<String, dynamic>>(
        ApiConstants.studySyncAnswers,
        data: payload.toJson(),
        options: Options(
          headers: <String, dynamic>{
            'X-Correlation-ID': effectiveCorrelationId,
          },
        ),
      );

      final data = response.data;
      if (data == null) {
        throw const ServerException(message: 'Resposta vazia na sincronização');
      }

      return SyncAnswersResponseModel.fromJson(data);
    } on DioException catch (e) {
      if (e.type == DioExceptionType.connectionError ||
          e.type == DioExceptionType.connectionTimeout) {
        throw NetworkException(
          message: e.message ?? 'Falha de conexão ao sincronizar respostas',
        );
      }
      throw ServerException(
        message: e.response?.data?['detail']?.toString() ?? e.message ?? 'Erro ao sincronizar respostas',
        statusCode: e.response?.statusCode,
      );
    }
  }
}
