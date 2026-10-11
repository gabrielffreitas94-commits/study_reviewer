import 'package:equatable/equatable.dart';
import 'package:study_reviewer_mobile/core/usecases/usecase.dart';
import 'package:study_reviewer_mobile/features/srs_questions/domain/entities/review_result_entity.dart';
import 'package:study_reviewer_mobile/features/srs_questions/domain/repositories/question_repository.dart';

/// Caso de uso para submeter a autoavaliação (nota) de uma pergunta aberta.
class ReviewQuestionUseCase
    implements UseCase<ReviewResultEntity, ReviewQuestionParams> {
  final QuestionRepository repository;

  const ReviewQuestionUseCase({required this.repository});

  @override
  Future<ReviewResultEntity> call(ReviewQuestionParams params) async {
    return repository.reviewQuestion(
      questionId: params.questionId,
      score: params.score,
    );
  }
}

/// Parâmetros de entrada para o caso de uso ReviewQuestionUseCase.
class ReviewQuestionParams extends Equatable {
  final String questionId;
  final int score;

  const ReviewQuestionParams({
    required this.questionId,
    required this.score,
  });

  @override
  List<Object?> get props => [questionId, score];
}
