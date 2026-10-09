import 'package:bloc_test/bloc_test.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:mocktail/mocktail.dart';
import 'package:study_reviewer_mobile/core/errors/failures.dart';
import 'package:study_reviewer_mobile/features/srs_questions/domain/entities/due_question_entity.dart';
import 'package:study_reviewer_mobile/features/srs_questions/domain/entities/review_result_entity.dart';
import 'package:study_reviewer_mobile/features/srs_questions/domain/entities/text_evaluation_result_entity.dart';
import 'package:study_reviewer_mobile/features/srs_questions/domain/usecases/evaluate_text_question_usecase.dart';
import 'package:study_reviewer_mobile/features/srs_questions/domain/usecases/get_due_questions_usecase.dart';
import 'package:study_reviewer_mobile/features/srs_questions/domain/usecases/review_question_usecase.dart';
import 'package:study_reviewer_mobile/features/srs_questions/presentation/cubit/question_srs_cubit.dart';
import 'package:study_reviewer_mobile/features/srs_questions/presentation/cubit/question_srs_state.dart';

class MockGetDueQuestionsUseCase extends Mock implements GetDueQuestionsUseCase {}
class MockReviewQuestionUseCase extends Mock implements ReviewQuestionUseCase {}
class MockEvaluateTextQuestionUseCase extends Mock implements EvaluateTextQuestionUseCase {}

void main() {
  late MockGetDueQuestionsUseCase mockGetDueQuestionsUseCase;
  late MockReviewQuestionUseCase mockReviewQuestionUseCase;
  late MockEvaluateTextQuestionUseCase mockEvaluateTextQuestionUseCase;
  late QuestionSrsCubit cubit;

  setUpAll(() {
    registerFallbackValue(const GetDueQuestionsParams());
    registerFallbackValue(
      const ReviewQuestionParams(questionId: 'fallback', score: 100),
    );
    registerFallbackValue(
      const EvaluateTextQuestionParams(
        questionId: 'fallback',
        studentAnswer: 'fallback',
      ),
    );
  });

  setUp(() {
    mockGetDueQuestionsUseCase = MockGetDueQuestionsUseCase();
    mockReviewQuestionUseCase = MockReviewQuestionUseCase();
    mockEvaluateTextQuestionUseCase = MockEvaluateTextQuestionUseCase();

    cubit = QuestionSrsCubit(
      getDueQuestionsUseCase: mockGetDueQuestionsUseCase,
      reviewQuestionUseCase: mockReviewQuestionUseCase,
      evaluateTextQuestionUseCase: mockEvaluateTextQuestionUseCase,
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

  final tEvaluationResult = TextEvaluationResultEntity(
    questionId: 'q-1',
    score: 85,
    feedback: 'Excelente domínio!',
    coverageScore: 90,
    accuracyScore: 85,
    depthScore: 80,
    tokensConsumed: 482,
    remainingBalance: 1518,
    ragGroundingApplied: true,
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

  group('setAnswerMode', () {
    blocTest<QuestionSrsCubit, QuestionSrsState>(
      'deve alterar o modo de resposta para 1 (Gabarito Manual)',
      build: () => cubit,
      seed: () => QuestionSrsLoaded(questions: [tQuestion1], activeAnswerMode: 0),
      act: (c) => c.setAnswerMode(1),
      expect: () => [
        QuestionSrsLoaded(
          questions: [tQuestion1],
          activeAnswerMode: 1,
        ),
      ],
    );

    blocTest<QuestionSrsCubit, QuestionSrsState>(
      'não deve alterar o modo se isEvaluatingText for true',
      build: () => cubit,
      seed: () => QuestionSrsLoaded(
        questions: [tQuestion1],
        activeAnswerMode: 0,
        isEvaluatingText: true,
      ),
      act: (c) => c.setAnswerMode(1),
      expect: () => [],
    );
  });

  group('submitTextEvaluation', () {
    blocTest<QuestionSrsCubit, QuestionSrsState>(
      'deve emitir erro de validação se resposta for menor que 3 caracteres',
      build: () => cubit,
      seed: () => QuestionSrsLoaded(questions: [tQuestion1]),
      act: (c) => c.submitTextEvaluation(studentAnswer: 'oi'),
      expect: () => [
        QuestionSrsLoaded(
          questions: [tQuestion1],
          textEvaluationError: 'A resposta deve conter pelo menos 3 caracteres.',
        ),
      ],
    );

    blocTest<QuestionSrsCubit, QuestionSrsState>(
      'deve submeter resposta, sincronizar score e revelar resposta com sucesso',
      build: () {
        when(() => mockEvaluateTextQuestionUseCase(any()))
            .thenAnswer((_) async => tEvaluationResult);
        return cubit;
      },
      seed: () => QuestionSrsLoaded(
        questions: [tQuestion1],
        isAnswerRevealed: false,
        selectedScore: 100,
      ),
      act: (c) => c.submitTextEvaluation(studentAnswer: 'Mitose gera duas células'),
      expect: () => [
        QuestionSrsLoaded(
          questions: [tQuestion1],
          isEvaluatingText: true,
          isAnswerRevealed: false,
          selectedScore: 100,
        ),
        QuestionSrsLoaded(
          questions: [tQuestion1],
          isEvaluatingText: false,
          textEvaluationResult: tEvaluationResult,
          isAnswerRevealed: true,
          selectedScore: 85,
        ),
      ],
    );

    blocTest<QuestionSrsCubit, QuestionSrsState>(
      'deve capturar Failure e registrar textEvaluationError',
      build: () {
        when(() => mockEvaluateTextQuestionUseCase(any())).thenThrow(
          const ServerFailure(
            message: 'Saldo de tokens insuficiente para avaliação por IA',
            statusCode: 402,
          ),
        );
        return cubit;
      },
      seed: () => QuestionSrsLoaded(questions: [tQuestion1]),
      act: (c) => c.submitTextEvaluation(studentAnswer: 'Mitose gera duas células'),
      expect: () => [
        QuestionSrsLoaded(
          questions: [tQuestion1],
          isEvaluatingText: true,
        ),
        QuestionSrsLoaded(
          questions: [tQuestion1],
          isEvaluatingText: false,
          textEvaluationError: 'Saldo de tokens insuficiente para avaliação por IA',
        ),
      ],
    );
  });

  group('clearEvaluation', () {
    blocTest<QuestionSrsCubit, QuestionSrsState>(
      'deve limpar textEvaluationResult e textEvaluationError',
      build: () => cubit,
      seed: () => QuestionSrsLoaded(
        questions: [tQuestion1],
        textEvaluationResult: tEvaluationResult,
        textEvaluationError: 'Algum erro prévio',
      ),
      act: (c) => c.clearEvaluation(),
      expect: () => [
        QuestionSrsLoaded(
          questions: [tQuestion1],
          textEvaluationResult: null,
          textEvaluationError: null,
        ),
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
      'nextQuestion deve avançar para o próximo item e limpar avaliações prévias',
      build: () => cubit,
      seed: () => QuestionSrsLoaded(
        questions: [tQuestion1, tQuestion2],
        currentIndex: 0,
        isAnswerRevealed: true,
        lastReviewResult: tReviewResult,
        textEvaluationResult: tEvaluationResult,
      ),
      act: (c) => c.nextQuestion(),
      expect: () => [
        QuestionSrsLoaded(
          questions: [tQuestion1, tQuestion2],
          currentIndex: 1,
          isAnswerRevealed: false,
          selectedScore: 100,
          lastReviewResult: null,
          textEvaluationResult: null,
          textEvaluationError: null,
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
