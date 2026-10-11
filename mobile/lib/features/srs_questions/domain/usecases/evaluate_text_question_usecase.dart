import 'package:equatable/equatable.dart';
import 'package:study_reviewer_mobile/core/usecases/usecase.dart';
import 'package:study_reviewer_mobile/features/srs_questions/domain/entities/text_evaluation_result_entity.dart';
import 'package:study_reviewer_mobile/features/srs_questions/domain/repositories/question_repository.dart';

/// Caso de uso para submeter uma resposta dissertativa e receber avaliação por IA.
class EvaluateTextQuestionUseCase
    implements UseCase<TextEvaluationResultEntity, EvaluateTextQuestionParams> {
  final QuestionRepository repository;

  const EvaluateTextQuestionUseCase({required this.repository});

  @override
  Future<TextEvaluationResultEntity> call(EvaluateTextQuestionParams params) async {
    return repository.evaluateTextQuestion(
      questionId: params.questionId,
      studentAnswer: params.studentAnswer,
    );
  }
}

/// Parâmetros de entrada para o caso de uso EvaluateTextQuestionUseCase.
class EvaluateTextQuestionParams extends Equatable {
  final String questionId;
  final String studentAnswer;

  const EvaluateTextQuestionParams({
    required this.questionId,
    required this.studentAnswer,
  });

  @override
  List<Object?> get props => [questionId, studentAnswer];
}
