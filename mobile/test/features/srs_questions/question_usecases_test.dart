import 'package:flutter_test/flutter_test.dart';
import 'package:mocktail/mocktail.dart';
import 'package:study_reviewer_mobile/features/srs_questions/domain/entities/due_question_entity.dart';
import 'package:study_reviewer_mobile/features/srs_questions/domain/entities/review_result_entity.dart';
import 'package:study_reviewer_mobile/features/srs_questions/domain/repositories/question_repository.dart';
import 'package:study_reviewer_mobile/features/srs_questions/domain/usecases/get_due_questions_usecase.dart';
import 'package:study_reviewer_mobile/features/srs_questions/domain/usecases/review_question_usecase.dart';

class MockQuestionRepository extends Mock implements QuestionRepository {}

void main() {
  late MockQuestionRepository mockRepository;
  late GetDueQuestionsUseCase getDueQuestionsUseCase;
  late ReviewQuestionUseCase reviewQuestionUseCase;

  setUp(() {
    mockRepository = MockQuestionRepository();
    getDueQuestionsUseCase =
        GetDueQuestionsUseCase(repository: mockRepository);
    reviewQuestionUseCase = ReviewQuestionUseCase(repository: mockRepository);
  });

  final tQuestion = DueQuestionEntity(
    id: 'q-10',
    prompt: 'Qual a diferença entre Processo e Thread?',
    expectedAnswer: 'Processos têm espaço de memória isolado.',
    currentLevel: 0,
    nextReviewDate: DateTime(2026, 10, 7),
    isDue: true,
  );

  final tReviewResult = ReviewResultEntity(
    questionId: 'q-10',
    score: 75,
    levelBefore: 0,
    levelAfter: 1,
    nextReviewDate: DateTime(2026, 10, 8),
    isPromoted: true,
    isDemoted: false,
    isMaintained: false,
  );

  test('GetDueQuestionsUseCase deve delegar chamada ao repositório', () async {
    when(() => mockRepository.getDueQuestions(
          subjectId: any(named: 'subjectId'),
          limit: any(named: 'limit'),
        )).thenAnswer((_) async => [tQuestion]);

    final result = await getDueQuestionsUseCase(
      const GetDueQuestionsParams(subjectId: 'sub-db', limit: 20),
    );

    expect(result, [tQuestion]);
    verify(() => mockRepository.getDueQuestions(subjectId: 'sub-db', limit: 20))
        .called(1);
  });

  test('ReviewQuestionUseCase deve delegar submissão ao repositório', () async {
    when(() => mockRepository.reviewQuestion(
          questionId: 'q-10',
          score: 75,
        )).thenAnswer((_) async => tReviewResult);

    final result = await reviewQuestionUseCase(
      const ReviewQuestionParams(questionId: 'q-10', score: 75),
    );

    expect(result, tReviewResult);
    verify(() => mockRepository.reviewQuestion(questionId: 'q-10', score: 75))
        .called(1);
  });
}
