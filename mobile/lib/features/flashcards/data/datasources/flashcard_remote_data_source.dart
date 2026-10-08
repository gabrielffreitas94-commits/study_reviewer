import 'package:dio/dio.dart';
import 'package:study_reviewer_mobile/core/constants/api_constants.dart';
import 'package:study_reviewer_mobile/core/errors/exceptions.dart';
import 'package:study_reviewer_mobile/features/flashcards/data/models/flashcard_model.dart';
import 'package:study_reviewer_mobile/features/flashcards/data/models/study_batch_model.dart';

abstract class FlashcardRemoteDataSource {
  Future<StudyBatchModel> getStudyBatch({
    String? subjectId,
    String? topicId,
    int limit = 50,
  });

  Future<StudySessionModel> getNextCard({
    String? subjectId,
    String? topicId,
    int? currentIndex,
  });

  Future<void> markCardRead({
    required String cardId,
    String? subjectId,
    String? topicId,
  });

  Future<List<FlashcardModel>> listTopicFlashcards({
    required String topicId,
    int limit = 50,
    int offset = 0,
  });
}

class FlashcardRemoteDataSourceImpl implements FlashcardRemoteDataSource {
  final Dio client;

  FlashcardRemoteDataSourceImpl({required this.client});

  @override
  Future<StudyBatchModel> getStudyBatch({
    String? subjectId,
    String? topicId,
    int limit = 50,
  }) async {
    try {
      final queryParams = <String, dynamic>{
        'limit': limit,
        if (subjectId != null) 'subject_id': subjectId,
        if (topicId != null) 'topic_id': topicId,
      };

      final response = await client.get<Map<String, dynamic>>(
        ApiConstants.studyBatch,
        queryParameters: queryParams,
      );

      final data = response.data;
      if (data == null) {
        throw const ServerException(message: 'Resposta vazia do servidor');
      }

      return StudyBatchModel.fromJson(data);
    } on DioException catch (e) {
      if (e.type == DioExceptionType.connectionError ||
          e.type == DioExceptionType.connectionTimeout) {
        throw NetworkException(
          message: e.message ?? 'Falha de conexão com a rede',
        );
      }
      throw ServerException(
        message: e.response?.data?['detail']?.toString() ?? e.message ?? 'Erro na requisição',
        statusCode: e.response?.statusCode,
      );
    }
  }

  @override
  Future<StudySessionModel> getNextCard({
    String? subjectId,
    String? topicId,
    int? currentIndex,
  }) async {
    try {
      final queryParams = <String, dynamic>{
        if (subjectId != null) 'subject_id': subjectId,
        if (topicId != null) 'topic_id': topicId,
        if (currentIndex != null) 'current_index': currentIndex,
      };

      final response = await client.get<Map<String, dynamic>>(
        ApiConstants.studyNext,
        queryParameters: queryParams,
      );

      final data = response.data;
      if (data == null) {
        throw const ServerException(message: 'Resposta vazia do servidor');
      }

      return StudySessionModel.fromJson(data);
    } on DioException catch (e) {
      if (e.type == DioExceptionType.connectionError ||
          e.type == DioExceptionType.connectionTimeout) {
        throw NetworkException(
          message: e.message ?? 'Falha de conexão com a rede',
        );
      }
      throw ServerException(
        message: e.response?.data?['detail']?.toString() ?? e.message ?? 'Erro na requisição',
        statusCode: e.response?.statusCode,
      );
    }
  }

  @override
  Future<void> markCardRead({
    required String cardId,
    String? subjectId,
    String? topicId,
  }) async {
    try {
      final queryParams = <String, dynamic>{
        if (subjectId != null) 'subject_id': subjectId,
        if (topicId != null) 'topic_id': topicId,
      };

      await client.post<dynamic>(
        ApiConstants.studyRead(cardId),
        queryParameters: queryParams,
      );
    } on DioException catch (e) {
      if (e.type == DioExceptionType.connectionError ||
          e.type == DioExceptionType.connectionTimeout) {
        throw NetworkException(
          message: e.message ?? 'Falha de conexão com a rede',
        );
      }
      throw ServerException(
        message: e.response?.data?['detail']?.toString() ?? e.message ?? 'Erro ao marcar card como lido',
        statusCode: e.response?.statusCode,
      );
    }
  }

  @override
  Future<List<FlashcardModel>> listTopicFlashcards({
    required String topicId,
    int limit = 50,
    int offset = 0,
  }) async {
    try {
      final response = await client.get<List<dynamic>>(
        ApiConstants.topicFlashcards(topicId),
        queryParameters: <String, dynamic>{
          'limit': limit,
          'offset': offset,
        },
      );

      final data = response.data;
      if (data == null) {
        return <FlashcardModel>[];
      }

      return data
          .map((dynamic item) =>
              FlashcardModel.fromJson(item as Map<String, dynamic>))
          .toList();
    } on DioException catch (e) {
      if (e.type == DioExceptionType.connectionError ||
          e.type == DioExceptionType.connectionTimeout) {
        throw NetworkException(
          message: e.message ?? 'Falha de conexão com a rede',
        );
      }
      throw ServerException(
        message: e.response?.data?['detail']?.toString() ?? e.message ?? 'Erro ao listar flashcards',
        statusCode: e.response?.statusCode,
      );
    }
  }
}
