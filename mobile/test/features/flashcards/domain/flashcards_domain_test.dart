import 'package:flutter_test/flutter_test.dart';
import 'package:mocktail/mocktail.dart';
import 'package:study_reviewer_mobile/features/flashcards/domain/entities/flashcard_entity.dart';
import 'package:study_reviewer_mobile/features/flashcards/domain/entities/study_session_entity.dart';
import 'package:study_reviewer_mobile/features/flashcards/domain/repositories/flashcard_repository.dart';
import 'package:study_reviewer_mobile/features/flashcards/domain/usecases/get_next_card_usecase.dart';
import 'package:study_reviewer_mobile/features/flashcards/domain/usecases/get_study_batch_usecase.dart';
import 'package:study_reviewer_mobile/features/flashcards/domain/usecases/list_topic_flashcards_usecase.dart';
import 'package:study_reviewer_mobile/features/flashcards/domain/usecases/mark_card_read_usecase.dart';

class MockFlashcardRepository extends Mock implements FlashcardRepository {}

void main() {
  late MockFlashcardRepository repository;
  late GetStudyBatchUseCase getStudyBatchUseCase;
  late GetNextCardUseCase getNextCardUseCase;
  late MarkCardReadUseCase markCardReadUseCase;
  late ListTopicFlashcardsUseCase listTopicFlashcardsUseCase;

  const tCard = FlashcardEntity(
    id: 'card-1',
    front: 'O que é Clean Architecture?',
    back: 'Uma arquitetura baseada em camadas concêntricas e inversão de dependência.',
    position: 1,
    topicIds: ['top-1'],
    primaryTopicId: 'top-1',
  );

  const tSession = StudySessionEntity(
    roundNumber: 1,
    currentIndex: 1,
    totalCards: 10,
    currentCard: tCard,
    sessionId: 'sess-1',
  );

  setUp(() {
    repository = MockFlashcardRepository();
    getStudyBatchUseCase = GetStudyBatchUseCase(repository);
    getNextCardUseCase = GetNextCardUseCase(repository);
    markCardReadUseCase = MarkCardReadUseCase(repository);
    listTopicFlashcardsUseCase = ListTopicFlashcardsUseCase(repository);
  });

  group('Flashcard Entities', () {
    test('FlashcardEntity supports value equality via Equatable', () {
      const cardA = FlashcardEntity(
        id: '1',
        front: 'A',
        back: 'B',
        position: 1,
        topicIds: ['t1'],
        primaryTopicId: 't1',
      );
      const cardB = FlashcardEntity(
        id: '1',
        front: 'A',
        back: 'B',
        position: 1,
        topicIds: ['t1'],
        primaryTopicId: 't1',
      );

      expect(cardA, equals(cardB));
    });

    test('StudySessionEntity supports value equality via Equatable', () {
      const sessionA = StudySessionEntity(
        roundNumber: 1,
        currentIndex: 1,
        totalCards: 5,
        currentCard: tCard,
        sessionId: 's1',
      );
      const sessionB = StudySessionEntity(
        roundNumber: 1,
        currentIndex: 1,
        totalCards: 5,
        currentCard: tCard,
        sessionId: 's1',
      );

      expect(sessionA, equals(sessionB));
    });
  });

  group('GetStudyBatchUseCase', () {
    test('should return list of flashcards from repository', () async {
      when(() => repository.getStudyBatch(
            subjectId: any(named: 'subjectId'),
            topicId: any(named: 'topicId'),
            limit: any(named: 'limit'),
          )).thenAnswer((_) async => [tCard]);

      final result = await getStudyBatchUseCase(
        subjectId: 'sub-1',
        topicId: 'top-1',
        limit: 50,
      );

      expect(result, equals([tCard]));
      verify(() => repository.getStudyBatch(
            subjectId: 'sub-1',
            topicId: 'top-1',
            limit: 50,
          )).called(1);
    });
  });

  group('GetNextCardUseCase', () {
    test('should return next study session entity from repository', () async {
      when(() => repository.getNextCard(
            subjectId: any(named: 'subjectId'),
            topicId: any(named: 'topicId'),
            currentIndex: any(named: 'currentIndex'),
          )).thenAnswer((_) async => tSession);

      final result = await getNextCardUseCase(
        subjectId: 'sub-1',
        topicId: 'top-1',
        currentIndex: 1,
      );

      expect(result, equals(tSession));
      verify(() => repository.getNextCard(
            subjectId: 'sub-1',
            topicId: 'top-1',
            currentIndex: 1,
          )).called(1);
    });
  });

  group('MarkCardReadUseCase', () {
    test('should invoke repository to mark card as read', () async {
      when(() => repository.markCardRead(
            cardId: any(named: 'cardId'),
            subjectId: any(named: 'subjectId'),
            topicId: any(named: 'topicId'),
          )).thenAnswer((_) async {});

      await markCardReadUseCase(
        cardId: 'card-1',
        subjectId: 'sub-1',
        topicId: 'top-1',
      );

      verify(() => repository.markCardRead(
            cardId: 'card-1',
            subjectId: 'sub-1',
            topicId: 'top-1',
          )).called(1);
    });
  });

  group('ListTopicFlashcardsUseCase', () {
    test('should return paginated topic flashcards from repository', () async {
      when(() => repository.listTopicFlashcards(
            topicId: any(named: 'topicId'),
            limit: any(named: 'limit'),
            offset: any(named: 'offset'),
          )).thenAnswer((_) async => [tCard]);

      final result = await listTopicFlashcardsUseCase(
        topicId: 'top-1',
        limit: 50,
        offset: 0,
      );

      expect(result, equals([tCard]));
      verify(() => repository.listTopicFlashcards(
            topicId: 'top-1',
            limit: 50,
            offset: 0,
          )).called(1);
    });
  });
}
