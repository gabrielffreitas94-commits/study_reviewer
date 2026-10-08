import 'package:study_reviewer_mobile/features/srs_questions/domain/entities/due_question_entity.dart';
import 'package:study_reviewer_mobile/features/srs_questions/domain/entities/review_result_entity.dart';

/// Contrato abstrato do repositório para o módulo de Perguntas Abertas e SRS.
abstract class QuestionRepository {
  /// Retorna as perguntas abertas vencidas para revisão no dia corrente.
  Future<List<DueQuestionEntity>> getDueQuestions({
    String? subjectId,
    int limit = 50,
  });

  /// Submete nota de autoavaliação (0 a 100) para recalcular intervalo SRS.
  Future<ReviewResultEntity> reviewQuestion({
    required String questionId,
    required int score,
  });
}
