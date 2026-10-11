import 'package:equatable/equatable.dart';
import 'package:study_reviewer_mobile/core/usecases/usecase.dart';
import 'package:study_reviewer_mobile/features/srs_questions/domain/entities/due_question_entity.dart';
import 'package:study_reviewer_mobile/features/srs_questions/domain/repositories/question_repository.dart';

/// Caso de uso para obter a lista de perguntas abertas vencidas para o dia corrente.
class GetDueQuestionsUseCase
    implements UseCase<List<DueQuestionEntity>, GetDueQuestionsParams> {
  final QuestionRepository repository;

  const GetDueQuestionsUseCase({required this.repository});

  @override
  Future<List<DueQuestionEntity>> call(GetDueQuestionsParams params) async {
    return repository.getDueQuestions(
      subjectId: params.subjectId,
      limit: params.limit,
    );
  }
}

/// Parâmetros de entrada para o caso de uso GetDueQuestionsUseCase.
class GetDueQuestionsParams extends Equatable {
  final String? subjectId;
  final int limit;

  const GetDueQuestionsParams({
    this.subjectId,
    this.limit = 50,
  });

  @override
  List<Object?> get props => [subjectId, limit];
}
