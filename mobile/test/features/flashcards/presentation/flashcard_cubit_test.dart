import 'package:bloc_test/bloc_test.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:mocktail/mocktail.dart';
import 'package:study_reviewer_mobile/features/flashcards/domain/entities/flashcard_entity.dart';
import 'package:study_reviewer_mobile/features/flashcards/domain/usecases/get_next_card_usecase.dart';
import 'package:study_reviewer_mobile/features/flashcards/domain/usecases/get_study_batch_usecase.dart';
import 'package:study_reviewer_mobile/features/flashcards/domain/usecases/mark_card_read_usecase.dart';
import 'package:study_reviewer_mobile/features/flashcards/presentation/cubit/flashcard_cubit.dart';
import 'package:study_reviewer_mobile/features/flashcards/presentation/cubit/flashcard_state.dart';

class MockGetStudyBatchUseCase extends Mock implements GetStudyBatchUseCase {}

class MockGetNextCardUseCase extends Mock implements GetNextCardUseCase {}

class MockMarkCardReadUseCase extends Mock implements MarkCardReadUseCase {}

void main() {
  late MockGetStudyBatchUseCase mockGetStudyBatchUseCase;
  late MockGetNextCardUseCase mockGetNextCardUseCase;
  late MockMarkCardReadUseCase mockMarkCardReadUseCase;
  late FlashcardCubit cubit;

  FlashcardEntity makeCard(int id) => FlashcardEntity(
        id: 'card-$id',
        front: 'Front $id',
        back: 'Back $id',
        position: id,
        topicIds: const ['top-1'],
        primaryTopicId: 'top-1',
      );

  setUp(() {
    mockGetStudyBatchUseCase = MockGetStudyBatchUseCase();
    mockGetNextCardUseCase = MockGetNextCardUseCase();
    mockMarkCardReadUseCase = MockMarkCardReadUseCase();

    cubit = FlashcardCubit(
      getStudyBatchUseCase: mockGetStudyBatchUseCase,
      getNextCardUseCase: mockGetNextCardUseCase,
      markCardReadUseCase: mockMarkCardReadUseCase,
    );
  });

  tearDown(() {
    cubit.close();
  });

  test('initial state is FlashcardInitial', () {
    expect(cubit.state, equals(const FlashcardInitial()));
  });

  group('loadSession', () {
    blocTest<FlashcardCubit, FlashcardState>(
      'emits [FlashcardLoading, FlashcardLoaded] when cards are found',
      build: () {
        when(() => mockGetStudyBatchUseCase(
              subjectId: any(named: 'subjectId'),
              topicId: any(named: 'topicId'),
              limit: any(named: 'limit'),
            )).thenAnswer((_) async => [makeCard(1), makeCard(2), makeCard(3)]);
        return cubit;
      },
      act: (cubit) => cubit.loadSession(subjectId: 'sub-1', topicId: 'top-1'),
      expect: () => [
        const FlashcardLoading(),
        FlashcardLoaded(
          currentCard: makeCard(1),
          roundNumber: 1,
          currentIndex: 1,
          totalCards: 3,
          remainingInBuffer: 2,
          isFlipped: false,
          isPrefetching: false,
          isOffline: false,
        ),
      ],
    );

    blocTest<FlashcardCubit, FlashcardState>(
      'emits [FlashcardLoading, FlashcardEmpty] when batch is empty',
      build: () {
        when(() => mockGetStudyBatchUseCase(
              subjectId: any(named: 'subjectId'),
              topicId: any(named: 'topicId'),
              limit: any(named: 'limit'),
            )).thenAnswer((_) async => []);
        return cubit;
      },
      act: (cubit) => cubit.loadSession(),
      expect: () => [
        const FlashcardLoading(),
        const FlashcardEmpty(
          roundNumber: 1,
          message: 'Nenhum flashcard disponível para este tema.',
        ),
      ],
    );

    blocTest<FlashcardCubit, FlashcardState>(
      'emits [FlashcardLoading, FlashcardError] when use case throws',
      build: () {
        when(() => mockGetStudyBatchUseCase(
              subjectId: any(named: 'subjectId'),
              topicId: any(named: 'topicId'),
              limit: any(named: 'limit'),
            )).thenThrow(Exception('Falha de rede'));
        return cubit;
      },
      act: (cubit) => cubit.loadSession(),
      expect: () => [
        const FlashcardLoading(),
        const FlashcardError(
          message: 'Falha ao carregar flashcards: Exception: Falha de rede',
          canRetry: true,
        ),
      ],
    );
  });

  group('toggleFlip', () {
    blocTest<FlashcardCubit, FlashcardState>(
      'toggles isFlipped state when loaded',
      build: () => cubit,
      seed: () => FlashcardLoaded(
        currentCard: makeCard(1),
        roundNumber: 1,
        currentIndex: 1,
        totalCards: 2,
        remainingInBuffer: 1,
        isFlipped: false,
      ),
      act: (cubit) {
        cubit.toggleFlip();
      },
      expect: () => [
        FlashcardLoaded(
          currentCard: makeCard(1),
          roundNumber: 1,
          currentIndex: 1,
          totalCards: 2,
          remainingInBuffer: 1,
          isFlipped: true,
        ),
      ],
    );
  });

  group('nextCard and Low-Water Mark policy', () {
    blocTest<FlashcardCubit, FlashcardState>(
      'advances to next card and invokes markCardReadUseCase',
      build: () {
        when(() => mockMarkCardReadUseCase(
              cardId: any(named: 'cardId'),
              subjectId: any(named: 'subjectId'),
              topicId: any(named: 'topicId'),
            )).thenAnswer((_) async {});
        when(() => mockGetStudyBatchUseCase(
              subjectId: any(named: 'subjectId'),
              topicId: any(named: 'topicId'),
              limit: any(named: 'limit'),
            )).thenAnswer((_) async => [makeCard(1), makeCard(2)]);
        return cubit;
      },
      act: (cubit) async {
        await cubit.loadSession();
        await cubit.nextCard();
      },
      verify: (_) {
        verify(() => mockMarkCardReadUseCase(
              cardId: 'card-1',
              subjectId: any(named: 'subjectId'),
              topicId: any(named: 'topicId'),
            )).called(1);
      },
    );

    blocTest<FlashcardCubit, FlashcardState>(
      'emits FlashcardEmpty when last card is advanced',
      build: () {
        when(() => mockMarkCardReadUseCase(
              cardId: any(named: 'cardId'),
              subjectId: any(named: 'subjectId'),
              topicId: any(named: 'topicId'),
            )).thenAnswer((_) async {});
        when(() => mockGetStudyBatchUseCase(
              subjectId: any(named: 'subjectId'),
              topicId: any(named: 'topicId'),
              limit: any(named: 'limit'),
            )).thenAnswer((_) async => [makeCard(1)]);
        return cubit;
      },
      act: (cubit) async {
        await cubit.loadSession();
        await cubit.nextCard();
      },
      expect: () => [
        const FlashcardLoading(),
        FlashcardLoaded(
          currentCard: makeCard(1),
          roundNumber: 1,
          currentIndex: 1,
          totalCards: 1,
          remainingInBuffer: 0,
          isFlipped: false,
        ),
        const FlashcardEmpty(
          roundNumber: 1,
          message: 'Parabéns! Você revisou todos os flashcards desta rodada.',
        ),
      ],
    );

    test('triggers Low-Water Mark prefetch when remaining buffer <= 10 cards',
        () async {
      // Cria um lote inicial com 12 cards
      final initialBatch = List.generate(12, (i) => makeCard(i + 1));
      final nextBatch = List.generate(10, (i) => makeCard(i + 13));

      when(() => mockGetStudyBatchUseCase(
            subjectId: any(named: 'subjectId'),
            topicId: any(named: 'topicId'),
            limit: any(named: 'limit'),
          )).thenAnswer((_) async => initialBatch);
      when(() => mockMarkCardReadUseCase(
            cardId: any(named: 'cardId'),
            subjectId: any(named: 'subjectId'),
            topicId: any(named: 'topicId'),
          )).thenAnswer((_) async {});

      await cubit.loadSession();
      // Após loadSession: card 1 em exibição, buffer tem 11 cards.
      expect(cubit.bufferCount, 11);

      // Agora prepara o mock para retornar o próximo lote quando o prefetch for disparado
      when(() => mockGetStudyBatchUseCase(
            subjectId: any(named: 'subjectId'),
            topicId: any(named: 'topicId'),
            limit: any(named: 'limit'),
          )).thenAnswer((_) async => nextBatch);

      // Ao avançar o próximo card: buffer vai para 10 cards (<= 10 dispara prefetch!)
      await cubit.nextCard();

      // Aguarda microtasks do prefetch
      await Future<void>.delayed(const Duration(milliseconds: 50));

      // Verifica que o prefetch foi disparado (totalizando 2 chamadas de getStudyBatch)
      verify(() => mockGetStudyBatchUseCase(
            subjectId: any(named: 'subjectId'),
            topicId: any(named: 'topicId'),
            limit: any(named: 'limit'),
          )).called(2);

      // E o buffer foi ampliado com os cards prefetchados
      expect(cubit.bufferCount, greaterThan(10));
    });
  });
}
