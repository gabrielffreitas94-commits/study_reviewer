import 'package:bloc_test/bloc_test.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:mocktail/mocktail.dart';
import 'package:study_reviewer_mobile/core/errors/failures.dart';
import 'package:study_reviewer_mobile/features/srs_questions/domain/entities/due_question_entity.dart';
import 'package:study_reviewer_mobile/features/srs_questions/domain/entities/review_result_entity.dart';
import 'package:study_reviewer_mobile/features/srs_questions/domain/usecases/get_due_questions_usecase.dart';
import 'package:study_reviewer_mobile/features/srs_questions/domain/usecases/review_question_usecase.dart';
import 'package:study_reviewer_mobile/features/srs_questions/presentation/cubit/question_srs_cubit.dart';
import 'package:study_reviewer_mobile/features/srs_questions/presentation/cubit/question_srs_state.dart';

class MockGetDueQuestionsUseCase extends Mock implements GetDueQuestionsUseCase {}
class MockReviewQuestionUseCase extends Mock implements ReviewQuestionUseCase {}

void main() {
  late MockGetDueQuestionsUseCase mockGetDueQuestionsUseCase;
  late MockReviewQuestionUseCase mockReviewQuestionUseCase;
  late QuestionSrsCubit cubit;

  setUpAll(() {
    registerFallbackValue(const GetDueQuestionsParams());
    registerFallbackValue(
      const ReviewQuestionParams(questionId: 'fallback', score: 100),
    );
  });

  setUp(() {
    mockGetDueQuestionsUseCase = MockGetDueQuestionsUseCase();
    mockReviewQuestionUseCase = MockReviewQuestionUseCase();

    cubit = QuestionSrsCubit(
      getDueQuestionsUseCase: mockGetDueQuestionsUseCase,
      reviewQuestionUseCase: mockReviewQuestionUseCase,
    );
  });

  tearDown(() {
    cubit.close();
  });

  final tQuestion1 = DueQuestionEntity(
    id: 'q-1',
    prompt: 'Prompt 1',
    expectedAnswer: 'Answer 1',
    currentLevel: 1,
    nextReviewDate: DateTime(2026, 10, 7),
    isDue: true,
  );

  final tQuestion2 = DueQuestionEntity(
    id: 'q-2',
    prompt: 'Prompt 2',
    expectedAnswer: 'Answer 2',
    currentLevel: 2,
    nextReviewDate: DateTime(2026, 10, 7),
    isDue: true,
  );

  final tReviewResult = ReviewResultEntity(
    questionId: 'q-1',
    score: 100,
    levelBefore: 1,
    levelAfter: 2,
    nextReviewDate: DateTime(2026, 10, 9),
    isPromoted: true,
    isDemoted: false,
    isMaintained: false,
  );

  test('estado inicial deve ser QuestionSrsInitial', () {
    expect(cubit.state, const QuestionSrsInitial());
  });

  group('loadDueQuestions', () {
    blocTest<QuestionSrsCubit, QuestionSrsState>(
      'deve emitir [QuestionSrsLoading, QuestionSrsLoaded] com lista de perguntas',
      build: () {
        when(() => mockGetDueQuestionsUseCase(any()))
            .thenAnswer((_) async => [tQuestion1, tQuestion2]);
        return cubit;
      },
      act: (c) => c.loadDueQuestions(),
      expect: () => [
        const QuestionSrsLoading(),
        QuestionSrsLoaded(
          questions: [tQuestion1, tQuestion2],
          currentIndex: 0,
          isAnswerRevealed: false,
          selectedScore: 100,
        ),
      ],
    );

    blocTest<QuestionSrsCubit, QuestionSrsState>(
      'deve emitir [QuestionSrsLoading, QuestionSrsEmpty] quando lista for vazia',
      build: () {
        when(() => mockGetDueQuestionsUseCase(any()))
            .thenAnswer((_) async => <DueQuestionEntity>[]);
        return cubit;
      },
      act: (c) => c.loadDueQuestions(),
      expect: () => [
        const QuestionSrsLoading(),
        const QuestionSrsEmpty(),
      ],
    );

    blocTest<QuestionSrsCubit, QuestionSrsState>(
      'deve emitir [QuestionSrsLoading, QuestionSrsError] em caso de falha',
      build: () {
        when(() => mockGetDueQuestionsUseCase(any()))
            .thenThrow(const ServerFailure(message: 'Erro no servidor'));
        return cubit;
      },
      act: (c) => c.loadDueQuestions(),
      expect: () => [
        const QuestionSrsLoading(),
        const QuestionSrsError('Erro no servidor'),
      ],
    );
  });

  group('revealAnswer and updateScore', () {
    blocTest<QuestionSrsCubit, QuestionSrsState>(
      'revealAnswer deve alterar isAnswerRevealed para true',
      build: () => cubit,
      seed: () => QuestionSrsLoaded(questions: [tQuestion1]),
      act: (c) => c.revealAnswer(),
      expect: () => [
        QuestionSrsLoaded(
          questions: [tQuestion1],
          isAnswerRevealed: true,
        ),
      ],
    );

    blocTest<QuestionSrsCubit, QuestionSrsState>(
      'updateScore deve atualizar a nota selecionada',
      build: () => cubit,
      seed: () => QuestionSrsLoaded(
        questions: [tQuestion1],
        isAnswerRevealed: true,
        selectedScore: 100,
      ),
      act: (c) => c.updateScore(75),
      expect: () => [
        QuestionSrsLoaded(
          questions: [tQuestion1],
          isAnswerRevealed: true,
          selectedScore: 75,
        ),
      ],
    );
  });

  group('submitReview and nextQuestion', () {
    blocTest<QuestionSrsCubit, QuestionSrsState>(
      'submitReview deve submeter nota e emitir estado com lastReviewResult',
      build: () {
        when(() => mockReviewQuestionUseCase(any()))
            .thenAnswer((_) async => tReviewResult);
        return cubit;
      },
      seed: () => QuestionSrsLoaded(
        questions: [tQuestion1],
        isAnswerRevealed: true,
        selectedScore: 100,
      ),
      act: (c) => c.submitReview(),
      expect: () => [
        QuestionSrsLoaded(
          questions: [tQuestion1],
          isAnswerRevealed: true,
          selectedScore: 100,
          isSubmitting: true,
        ),
        QuestionSrsLoaded(
          questions: [tQuestion1],
          isAnswerRevealed: true,
          selectedScore: 100,
          isSubmitting: false,
          lastReviewResult: tReviewResult,
        ),
      ],
    );

    blocTest<QuestionSrsCubit, QuestionSrsState>(
      'nextQuestion deve avançar para o próximo item',
      build: () => cubit,
      seed: () => QuestionSrsLoaded(
        questions: [tQuestion1, tQuestion2],
        currentIndex: 0,
        isAnswerRevealed: true,
        lastReviewResult: tReviewResult,
      ),
      act: (c) => c.nextQuestion(),
      expect: () => [
        QuestionSrsLoaded(
          questions: [tQuestion1, tQuestion2],
          currentIndex: 1,
          isAnswerRevealed: false,
          selectedScore: 100,
          lastReviewResult: null,
        ),
      ],
    );

    blocTest<QuestionSrsCubit, QuestionSrsState>(
      'nextQuestion na última pergunta deve marcar isSessionCompleted = true',
      build: () => cubit,
      seed: () => QuestionSrsLoaded(
        questions: [tQuestion1],
        currentIndex: 0,
        isAnswerRevealed: true,
        lastReviewResult: tReviewResult,
      ),
      act: (c) => c.nextQuestion(),
      expect: () => [
        QuestionSrsLoaded(
          questions: [tQuestion1],
          currentIndex: 0,
          isAnswerRevealed: true,
          lastReviewResult: tReviewResult,
          isSessionCompleted: true,
        ),
      ],
    );
  });
}
