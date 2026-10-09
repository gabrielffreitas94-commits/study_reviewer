import 'package:study_reviewer_mobile/core/errors/exceptions.dart';
import 'package:study_reviewer_mobile/core/errors/failures.dart';
import 'package:study_reviewer_mobile/features/srs_questions/data/datasources/question_remote_data_source.dart';
import 'package:study_reviewer_mobile/features/srs_questions/domain/entities/due_question_entity.dart';
import 'package:study_reviewer_mobile/features/srs_questions/domain/entities/review_result_entity.dart';
import 'package:study_reviewer_mobile/features/srs_questions/domain/entities/text_evaluation_result_entity.dart';
import 'package:study_reviewer_mobile/features/srs_questions/domain/repositories/question_repository.dart';

/// Implementação do repositório de perguntas abertas e SRS na camada de dados.
class QuestionRepositoryImpl implements QuestionRepository {
  final QuestionRemoteDataSource remoteDataSource;

  const QuestionRepositoryImpl({required this.remoteDataSource});

  @override
  Future<List<DueQuestionEntity>> getDueQuestions({
    String? subjectId,
    int limit = 50,
  }) async {
    try {
      final models = await remoteDataSource.getDueQuestions(
        subjectId: subjectId,
        limit: limit,
      );
      return models.map((m) => m.toEntity()).toList();
    } on NetworkException catch (e) {
      throw NetworkFailure(e.message);
    } on ServerException catch (e) {
      throw ServerFailure(message: e.message, statusCode: e.statusCode);
    } catch (e) {
      throw ServerFailure(message: 'Falha inesperada ao obter perguntas: $e');
    }
  }

  @override
  Future<ReviewResultEntity> reviewQuestion({
    required String questionId,
    required int score,
  }) async {
    try {
      final model = await remoteDataSource.reviewQuestion(
        questionId: questionId,
        score: score,
      );
      return model.toEntity();
    } on NetworkException catch (e) {
      throw NetworkFailure(e.message);
    } on ServerException catch (e) {
      throw ServerFailure(message: e.message, statusCode: e.statusCode);
    } catch (e) {
      throw ServerFailure(message: 'Falha inesperada ao submeter revisão: $e');
    }
  }

  @override
  Future<TextEvaluationResultEntity> evaluateTextQuestion({
    required String questionId,
    required String studentAnswer,
  }) async {
    try {
      final model = await remoteDataSource.evaluateTextQuestion(
        questionId: questionId,
        studentAnswer: studentAnswer,
      );
      return model.toEntity();
    } on NetworkException catch (e) {
      throw NetworkFailure(e.message);
    } on ServerException catch (e) {
      throw ServerFailure(message: e.message, statusCode: e.statusCode);
    } catch (e) {
      throw ServerFailure(
        message: 'Falha inesperada ao avaliar resposta dissertativa: $e',
      );
    }
  }
}
