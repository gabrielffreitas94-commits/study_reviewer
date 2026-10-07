import 'package:bloc_test/bloc_test.dart';
import 'package:flutter/material.dart';
import 'package:flutter_bloc/flutter_bloc.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:mocktail/mocktail.dart';
import 'package:study_reviewer_mobile/features/flashcards/domain/entities/flashcard_entity.dart';
import 'package:study_reviewer_mobile/features/flashcards/presentation/cubit/flashcard_cubit.dart';
import 'package:study_reviewer_mobile/features/flashcards/presentation/cubit/flashcard_state.dart';
import 'package:study_reviewer_mobile/features/flashcards/presentation/pages/flashcard_study_page.dart';
import 'package:study_reviewer_mobile/features/sync/presentation/widgets/sync_status_badge.dart';

class MockFlashcardCubit extends MockCubit<FlashcardState>
    implements FlashcardCubit {}

void main() {
  late MockFlashcardCubit mockCubit;

  const tCard = FlashcardEntity(
    id: 'c-1',
    front: 'O que é SRP?',
    back: 'Princípio da Responsabilidade Única.',
    position: 1,
    topicIds: ['top-1'],
    primaryTopicId: 'top-1',
  );

  setUp(() {
    mockCubit = MockFlashcardCubit();
    when(() => mockCubit.loadSession(
          subjectId: any(named: 'subjectId'),
          topicId: any(named: 'topicId'),
        )).thenAnswer((_) async {});
  });

  Widget createWidgetUnderTest() {
    return MaterialApp(
      home: BlocProvider<FlashcardCubit>.value(
        value: mockCubit,
        child: const FlashcardStudyPage(
          topicTitle: 'Engenharia de Software',
        ),
      ),
    );
  }

  group('FlashcardStudyPage 5 Interface States', () {
    testWidgets('State 3: Loading shows progress indicator and skeleton text',
        (tester) async {
      when(() => mockCubit.state).thenReturn(const FlashcardLoading());

      await tester.pumpWidget(createWidgetUnderTest());

      expect(find.byType(CircularProgressIndicator), findsOneWidget);
      expect(find.text('Preparando seus flashcards...'), findsOneWidget);
    });

    testWidgets('State 2: Empty / Inbox Zero shows celebration and restart button',
        (tester) async {
      when(() => mockCubit.state).thenReturn(const FlashcardEmpty(
        roundNumber: 1,
        message: 'Parabéns! Você revisou todos os flashcards desta rodada.',
      ));

      await tester.pumpWidget(createWidgetUnderTest());

      expect(find.text('Parabéns!'), findsOneWidget);
      expect(
        find.text('Parabéns! Você revisou todos os flashcards desta rodada.'),
        findsOneWidget,
      );
      expect(find.text('Reiniciar Rodada'), findsOneWidget);

      await tester.tap(find.text('Reiniciar Rodada'));
      verify(() => mockCubit.loadSession(
            subjectId: any(named: 'subjectId'),
            topicId: any(named: 'topicId'),
          )).called(1);
    });

    testWidgets('State 4: Error shows error message and retry button',
        (tester) async {
      when(() => mockCubit.state).thenReturn(const FlashcardError(
        message: 'Erro 500 do servidor',
        canRetry: true,
      ));

      await tester.pumpWidget(createWidgetUnderTest());

      expect(find.text('Não foi possível carregar os cards'), findsOneWidget);
      expect(find.text('Erro 500 do servidor'), findsOneWidget);
      expect(find.text('Tentar Novamente'), findsOneWidget);

      await tester.tap(find.text('Tentar Novamente'));
      verify(() => mockCubit.retry()).called(1);
    });

    testWidgets('State 1: Ideal loaded state shows card 3D, round counter, and thumb buttons',
        (tester) async {
      when(() => mockCubit.state).thenReturn(
        const FlashcardLoaded(
          currentCard: tCard,
          roundNumber: 1,
          currentIndex: 1,
          totalCards: 10,
          remainingInBuffer: 9,
          isFlipped: false,
          isPrefetching: false,
          isOffline: false,
        ),
      );

      await tester.pumpWidget(createWidgetUnderTest());

      expect(find.text('Engenharia de Software'), findsOneWidget);
      expect(find.text('Rodada 1'), findsOneWidget);
      expect(find.text('Card 1 de 10'), findsOneWidget);
      expect(find.text('O que é SRP?'), findsOneWidget);
      expect(find.text('Virar Card'), findsOneWidget);
      expect(find.text('Próximo Card'), findsOneWidget);
      expect(find.byType(SyncStatusBadge), findsOneWidget);

      await tester.tap(find.text('Virar Card'));
      verify(() => mockCubit.toggleFlip()).called(1);

      await tester.tap(find.text('Próximo Card'));
      verify(() => mockCubit.nextCard()).called(1);
    });

    testWidgets('State 5: Partial offline loaded state shows offline banner',
        (tester) async {
      when(() => mockCubit.state).thenReturn(
        const FlashcardLoaded(
          currentCard: tCard,
          roundNumber: 1,
          currentIndex: 2,
          totalCards: 5,
          remainingInBuffer: 3,
          isFlipped: false,
          isPrefetching: false,
          isOffline: true,
        ),
      );

      await tester.pumpWidget(createWidgetUnderTest());

      expect(
        find.text(
          'Modo offline ativo. Suas leituras serão sincronizadas ao reconectar.',
        ),
        findsOneWidget,
      );
      expect(find.byIcon(Icons.wifi_off_outlined), findsOneWidget);
    });
  });
}
