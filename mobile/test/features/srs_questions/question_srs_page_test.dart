import 'package:flutter/material.dart';
import 'package:flutter_bloc/flutter_bloc.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:mocktail/mocktail.dart';
import 'package:study_reviewer_mobile/features/srs_questions/domain/entities/due_question_entity.dart';
import 'package:study_reviewer_mobile/features/srs_questions/domain/entities/review_result_entity.dart';
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

  testWidgets('exibe enunciado da pergunta e botão Ver Resposta Esperada',
      (tester) async {
    when(() => mockCubit.state).thenReturn(
      QuestionSrsLoaded(
        questions: [tQuestion],
        currentIndex: 0,
        isAnswerRevealed: false,
      ),
    );
    when(() => mockCubit.stream).thenAnswer(
      (_) => Stream<QuestionSrsState>.value(
        QuestionSrsLoaded(questions: [tQuestion]),
      ),
    );
    when(() => mockCubit.revealAnswer()).thenReturn(null);

    await tester.pumpWidget(buildTestableWidget());
    await tester.pumpAndSettle();

    expect(find.text('Perguntas Abertas SRS'), findsOneWidget);
    expect(find.text('Explique o princípio Open-Closed da SOLID.'), findsOneWidget);
    expect(find.text('Ver Resposta Esperada'), findsOneWidget);

    await tester.tap(find.text('Ver Resposta Esperada'));
    await tester.pump();

    verify(() => mockCubit.revealAnswer()).called(1);
  });

  testWidgets('exibe gabarito e seletor de nota após revelação',
      (tester) async {
    when(() => mockCubit.state).thenReturn(
      QuestionSrsLoaded(
        questions: [tQuestion],
        currentIndex: 0,
        isAnswerRevealed: true,
        selectedScore: 100,
      ),
    );
    when(() => mockCubit.stream).thenAnswer(
      (_) => Stream<QuestionSrsState>.value(
        QuestionSrsLoaded(
          questions: [tQuestion],
          isAnswerRevealed: true,
          selectedScore: 100,
        ),
      ),
    );
    when(() => mockCubit.submitReview()).thenAnswer((_) async {});

    await tester.pumpWidget(buildTestableWidget());
    await tester.pumpAndSettle();

    expect(find.text('Resposta Esperada (Gabarito):'), findsOneWidget);
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
