import 'package:dio/dio.dart';
import 'package:study_reviewer_mobile/core/constants/api_constants.dart';
import 'package:study_reviewer_mobile/core/errors/exceptions.dart';
import 'package:study_reviewer_mobile/features/srs_questions/data/models/due_question_model.dart';
import 'package:study_reviewer_mobile/features/srs_questions/data/models/review_result_model.dart';
import 'package:study_reviewer_mobile/features/srs_questions/data/models/text_evaluation_result_model.dart';

/// Contrato abstrato do datasource remoto para perguntas abertas e SRS.
abstract class QuestionRemoteDataSource {
  Future<List<DueQuestionModel>> getDueQuestions({
    String? subjectId,
    int limit = 50,
  });

  Future<ReviewResultModel> reviewQuestion({
    required String questionId,
    required int score,
  });

  Future<TextEvaluationResultModel> evaluateTextQuestion({
    required String questionId,
    required String studentAnswer,
  });
}

/// Implementação do datasource remoto utilizando Dio para requisições HTTP REST.
class QuestionRemoteDataSourceImpl implements QuestionRemoteDataSource {
  final Dio client;

  QuestionRemoteDataSourceImpl({required this.client});

  @override
  Future<List<DueQuestionModel>> getDueQuestions({
    String? subjectId,
    int limit = 50,
  }) async {
    try {
      final queryParams = <String, dynamic>{
        'limit': limit,
        if (subjectId != null && subjectId.isNotEmpty) 'subject_id': subjectId,
      };

      final response = await client.get<dynamic>(
        ApiConstants.questionsDue,
        queryParameters: queryParams,
      );

      final dynamic responseData = response.data;
      if (responseData == null) {
        return <DueQuestionModel>[];
      }

      List<dynamic> itemsList;
      if (responseData is Map<String, dynamic> &&
          responseData.containsKey('items')) {
        itemsList = responseData['items'] as List<dynamic>;
      } else if (responseData is List<dynamic>) {
        itemsList = responseData;
      } else {
        itemsList = <dynamic>[];
      }

      return itemsList
          .map((dynamic item) =>
              DueQuestionModel.fromJson(item as Map<String, dynamic>))
          .toList();
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
            'Erro ao buscar perguntas vencidas',
        statusCode: e.response?.statusCode,
      );
    } catch (e) {
      if (e is NetworkException || e is ServerException) {
        rethrow;
      }
      throw ServerException(message: 'Erro inesperado: $e');
    }
  }

  @override
  Future<ReviewResultModel> reviewQuestion({
    required String questionId,
    required int score,
  }) async {
    try {
      final response = await client.post<Map<String, dynamic>>(
        ApiConstants.questionReview(questionId),
        data: <String, dynamic>{'score': score},
      );

      final data = response.data;
      if (data == null) {
        throw const ServerException(message: 'Resposta vazia do servidor');
      }

      return ReviewResultModel.fromJson(data, submittedScore: score);
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
            'Erro ao submeter revisão SRS',
        statusCode: e.response?.statusCode,
      );
    } catch (e) {
      if (e is NetworkException || e is ServerException) {
        rethrow;
      }
      throw ServerException(message: 'Erro inesperado: $e');
    }
  }

  @override
  Future<TextEvaluationResultModel> evaluateTextQuestion({
    required String questionId,
    required String studentAnswer,
  }) async {
    try {
      final response = await client.post<Map<String, dynamic>>(
        ApiConstants.questionEvaluateText(questionId),
        data: <String, dynamic>{'student_answer': studentAnswer},
      );

      final data = response.data;
      if (data == null) {
        throw const ServerException(message: 'Resposta vazia do servidor');
      }

      return TextEvaluationResultModel.fromJson(data);
    } on DioException catch (e) {
      if (e.type == DioExceptionType.connectionError ||
          e.type == DioExceptionType.connectionTimeout) {
        throw NetworkException(
          message: e.message ?? 'Falha de conexão com a rede',
        );
      }

      final statusCode = e.response?.statusCode;
      final dynamic rawData = e.response?.data;
      final String? detail = (rawData is Map<String, dynamic>)
          ? rawData['detail']?.toString()
          : null;

      if (statusCode == 402 || detail == 'INSUFFICIENT_FUNDS') {
        throw ServerException(
          message: (detail != null && detail != 'INSUFFICIENT_FUNDS')
              ? detail
              : 'Saldo de tokens insuficiente para avaliação por IA',
          statusCode: 402,
        );
      }

      throw ServerException(
        message: detail ??
            e.message ??
            'Erro ao avaliar resposta dissertativa com IA',
        statusCode: statusCode,
      );
    } catch (e) {
      if (e is NetworkException || e is ServerException) {
        rethrow;
      }
      throw ServerException(message: 'Erro inesperado: $e');
    }
  }
}
