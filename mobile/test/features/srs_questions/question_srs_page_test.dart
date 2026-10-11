import 'package:flutter/material.dart';
import 'package:flutter_bloc/flutter_bloc.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:mocktail/mocktail.dart';
import 'package:study_reviewer_mobile/features/srs_questions/domain/entities/due_question_entity.dart';
import 'package:study_reviewer_mobile/features/srs_questions/domain/entities/review_result_entity.dart';
import 'package:study_reviewer_mobile/features/srs_questions/domain/entities/text_evaluation_result_entity.dart';
import 'package:study_reviewer_mobile/features/srs_questions/presentation/cubit/question_srs_cubit.dart';
import 'package:study_reviewer_mobile/features/srs_questions/presentation/cubit/question_srs_state.dart';
import 'package:study_reviewer_mobile/features/srs_questions/presentation/pages/question_srs_page.dart';

class MockQuestionSrsCubit extends Mock implements QuestionSrsCubit {}

void main() {
  late MockQuestionSrsCubit mockCubit;

  setUp(() {
    mockCubit = MockQuestionSrsCubit();
    when(() => mockCubit.loadDueQuestions(subjectId: any(named: 'subjectId')))
        .thenAnswer((_) async {});
  });

  Widget buildTestableWidget() {
    return MaterialApp(
      home: BlocProvider<QuestionSrsCubit>.value(
        value: mockCubit,
        child: const QuestionSrsPage(),
      ),
    );
  }

  final tQuestion = DueQuestionEntity(
    id: 'q-10',
    prompt: 'Explique o princípio Open-Closed da SOLID.',
    expectedAnswer: 'Aberto para extensão, fechado para modificação.',
    currentLevel: 1,
    nextReviewDate: DateTime(2026, 10, 7),
    isDue: true,
    subjectName: 'Engenharia de Software',
    topicName: 'Arquitetura Limpa',
  );

  final tReviewResult = ReviewResultEntity(
    questionId: 'q-10',
    score: 100,
    levelBefore: 1,
    levelAfter: 2,
    nextReviewDate: DateTime(2026, 10, 9),
    isPromoted: true,
    isDemoted: false,
    isMaintained: false,
    intervalDays: 2,
  );

  final tEvaluationResult = TextEvaluationResultEntity(
    questionId: 'q-10',
    score: 90,
    feedback: 'Excelente definição do princípio OCP.',
    coverageScore: 95,
    accuracyScore: 90,
    depthScore: 85,
    tokensConsumed: 480,
    remainingBalance: 1520,
    ragGroundingApplied: true,
  );

  testWidgets('exibe abas de modo e campo de digitação no modo texto padrão',
      (tester) async {
    when(() => mockCubit.state).thenReturn(
      QuestionSrsLoaded(
        questions: [tQuestion],
        currentIndex: 0,
        activeAnswerMode: 0,
        isAnswerRevealed: false,
      ),
    );
    when(() => mockCubit.stream).thenAnswer(
      (_) => Stream<QuestionSrsState>.value(
        QuestionSrsLoaded(questions: [tQuestion], activeAnswerMode: 0),
      ),
    );

    await tester.pumpWidget(buildTestableWidget());
    await tester.pumpAndSettle();

    expect(find.text('Perguntas Abertas SRS'), findsOneWidget);
    expect(find.text('Explique o princípio Open-Closed da SOLID.'), findsOneWidget);
    expect(find.text('✍️ Digitar Resposta'), findsOneWidget);
    expect(find.text('💡 Apenas Gabarito'), findsOneWidget);
    expect(find.text('✨ Avaliar com IA'), findsOneWidget);
    expect(find.byType(TextField), findsOneWidget);
  });

  testWidgets('exibe botão Ver Resposta Esperada quando no modo manual',
      (tester) async {
    when(() => mockCubit.state).thenReturn(
      QuestionSrsLoaded(
        questions: [tQuestion],
        currentIndex: 0,
        activeAnswerMode: 1,
        isAnswerRevealed: false,
      ),
    );
    when(() => mockCubit.stream).thenAnswer(
      (_) => Stream<QuestionSrsState>.value(
        QuestionSrsLoaded(questions: [tQuestion], activeAnswerMode: 1),
      ),
    );
    when(() => mockCubit.revealAnswer()).thenReturn(null);

    await tester.pumpWidget(buildTestableWidget());
    await tester.pumpAndSettle();

    expect(find.text('Ver Resposta Esperada'), findsOneWidget);

    await tester.tap(find.text('Ver Resposta Esperada'));
    await tester.pump();

    verify(() => mockCubit.revealAnswer()).called(1);
  });

  testWidgets('aciona submitTextEvaluation ao tocar no botão Avaliar com IA',
      (tester) async {
    when(() => mockCubit.state).thenReturn(
      QuestionSrsLoaded(
        questions: [tQuestion],
        currentIndex: 0,
        activeAnswerMode: 0,
        isAnswerRevealed: false,
      ),
    );
    when(() => mockCubit.stream).thenAnswer(
      (_) => Stream<QuestionSrsState>.value(
        QuestionSrsLoaded(questions: [tQuestion], activeAnswerMode: 0),
      ),
    );
    when(() => mockCubit.submitTextEvaluation(
          studentAnswer: any(named: 'studentAnswer'),
        )).thenAnswer((_) async {});

    await tester.pumpWidget(buildTestableWidget());
    await tester.pumpAndSettle();

    await tester.enterText(
      find.byType(TextField),
      'Entidades devem estar abertas para extensão',
    );
    await tester.pump();

    await tester.tap(find.text('✨ Avaliar com IA'));
    await tester.pump();

    verify(() => mockCubit.submitTextEvaluation(
          studentAnswer: 'Entidades devem estar abertas para extensão',
        )).called(1);
  });

  testWidgets('exibe EvaluationFeedbackCard e gabarito oficial após avaliação por IA',
      (tester) async {
    when(() => mockCubit.state).thenReturn(
      QuestionSrsLoaded(
        questions: [tQuestion],
        currentIndex: 0,
        activeAnswerMode: 0,
        isAnswerRevealed: true,
        textEvaluationResult: tEvaluationResult,
        selectedScore: 90,
      ),
    );
    when(() => mockCubit.stream).thenAnswer(
      (_) => Stream<QuestionSrsState>.value(
        QuestionSrsLoaded(
          questions: [tQuestion],
          activeAnswerMode: 0,
          isAnswerRevealed: true,
          textEvaluationResult: tEvaluationResult,
          selectedScore: 90,
        ),
      ),
    );

    await tester.pumpWidget(buildTestableWidget());
    await tester.pumpAndSettle();

    expect(find.text('Avaliação da IA'), findsOneWidget);
    expect(find.text('90% de Domínio'), findsOneWidget);
    expect(find.text('Excelente definição do princípio OCP.'), findsOneWidget);
    expect(find.text('Resposta Esperada (Gabarito Oficial):'), findsOneWidget);
    expect(find.text('Aberto para extensão, fechado para modificação.'), findsOneWidget);
    expect(find.text('Confirmar e Avançar'), findsOneWidget);
  });

  testWidgets('exibe gabarito e seletor de nota após revelação manual',
      (tester) async {
    when(() => mockCubit.state).thenReturn(
      QuestionSrsLoaded(
        questions: [tQuestion],
        currentIndex: 0,
        activeAnswerMode: 1,
        isAnswerRevealed: true,
        selectedScore: 100,
      ),
    );
    when(() => mockCubit.stream).thenAnswer(
      (_) => Stream<QuestionSrsState>.value(
        QuestionSrsLoaded(
          questions: [tQuestion],
          activeAnswerMode: 1,
          isAnswerRevealed: true,
          selectedScore: 100,
        ),
      ),
    );
    when(() => mockCubit.submitReview()).thenAnswer((_) async {});

    await tester.pumpWidget(buildTestableWidget());
    await tester.pumpAndSettle();

    expect(find.text('Resposta Esperada (Gabarito Oficial):'), findsOneWidget);
    expect(find.text('Aberto para extensão, fechado para modificação.'),
        findsOneWidget);
    expect(find.text('Confirmar e Avançar'), findsOneWidget);

    await tester.tap(find.text('Confirmar e Avançar'));
    await tester.pump();

    verify(() => mockCubit.submitReview()).called(1);
  });

  testWidgets('exibe banner de feedback de transição de nível após submissão',
      (tester) async {
    when(() => mockCubit.state).thenReturn(
      QuestionSrsLoaded(
        questions: [tQuestion],
        currentIndex: 0,
        isAnswerRevealed: true,
        lastReviewResult: tReviewResult,
      ),
    );
    when(() => mockCubit.stream).thenAnswer(
      (_) => Stream<QuestionSrsState>.value(
        QuestionSrsLoaded(
          questions: [tQuestion],
          isAnswerRevealed: true,
          lastReviewResult: tReviewResult,
        ),
      ),
    );
    when(() => mockCubit.nextQuestion()).thenReturn(null);

    await tester.pumpWidget(buildTestableWidget());
    await tester.pumpAndSettle();

    expect(find.text('Atualização SRS Processada'), findsOneWidget);
    expect(find.text('↑ Nível Superior (Nível 2)'), findsOneWidget);
    expect(find.text('Próxima Pergunta'), findsOneWidget);

    await tester.tap(find.text('Próxima Pergunta'));
    await tester.pump();

    verify(() => mockCubit.nextQuestion()).called(1);
  });
}
