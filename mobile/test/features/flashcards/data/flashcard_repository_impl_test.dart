import 'package:flutter_test/flutter_test.dart';
import 'package:mocktail/mocktail.dart';
import 'package:study_reviewer_mobile/core/errors/exceptions.dart';
import 'package:study_reviewer_mobile/features/flashcards/data/datasources/flashcard_local_data_source.dart';
import 'package:study_reviewer_mobile/features/flashcards/data/datasources/flashcard_remote_data_source.dart';
import 'package:study_reviewer_mobile/features/flashcards/data/models/flashcard_model.dart';
import 'package:study_reviewer_mobile/features/flashcards/data/models/study_batch_model.dart';
import 'package:study_reviewer_mobile/features/flashcards/data/repositories/flashcard_repository_impl.dart';

class MockFlashcardRemoteDataSource extends Mock
    implements FlashcardRemoteDataSource {}

class MockFlashcardLocalDataSource extends Mock
    implements FlashcardLocalDataSource {}

void main() {
  late MockFlashcardRemoteDataSource remoteDataSource;
  late MockFlashcardLocalDataSource localDataSource;
  late FlashcardRepositoryImpl repository;

  const tCardModel = FlashcardModel(
    id: 'c1',
    front: 'F1',
    back: 'B1',
    position: 1,
    topicIds: ['top-1'],
    primaryTopicId: 'top-1',
  );

  const tBatchModel = StudyBatchModel(
    cards: [tCardModel],
    totalCards: 1,
    roundNumber: 1,
    hasMore: false,
  );

  const tSessionModel = StudySessionModel(
    roundNumber: 1,
    currentIndex: 1,
    totalCards: 1,
    currentCard: tCardModel,
    sessionId: 'sess-1',
  );

  setUp(() {
    remoteDataSource = MockFlashcardRemoteDataSource();
    localDataSource = MockFlashcardLocalDataSource();
    repository = FlashcardRepositoryImpl(
      remoteDataSource: remoteDataSource,
      localDataSource: localDataSource,
    );
  });

  group('getStudyBatch', () {
    test('returns entities and caches batch when remote succeeds', () async {
      when(() => remoteDataSource.getStudyBatch(
            subjectId: any(named: 'subjectId'),
            topicId: any(named: 'topicId'),
            limit: any(named: 'limit'),
          )).thenAnswer((_) async => tBatchModel);
      when(() => localDataSource.cacheStudyBatch(any()))
          .thenAnswer((_) async {});

      final result = await repository.getStudyBatch(
        subjectId: 'sub-1',
        topicId: 'top-1',
        limit: 50,
      );

      expect(result.length, 1);
      expect(result.first.id, 'c1');
      verify(() => localDataSource.cacheStudyBatch([tCardModel])).called(1);
    });

    test('falls back to local cache when remote fails', () async {
      when(() => remoteDataSource.getStudyBatch(
            subjectId: any(named: 'subjectId'),
            topicId: any(named: 'topicId'),
            limit: any(named: 'limit'),
          )).thenThrow(const NetworkException());
      when(() => localDataSource.getCachedStudyBatch())
          .thenAnswer((_) async => [tCardModel]);

      final result = await repository.getStudyBatch(
        subjectId: 'sub-1',
        topicId: 'top-1',
      );

      expect(result.length, 1);
      expect(result.first.id, 'c1');
      verify(() => localDataSource.getCachedStudyBatch()).called(1);
    });

    test('rethrows error when remote fails and local cache is empty', () async {
      when(() => remoteDataSource.getStudyBatch(
            subjectId: any(named: 'subjectId'),
            topicId: any(named: 'topicId'),
            limit: any(named: 'limit'),
          )).thenThrow(const ServerException(message: 'Server Down'));
      when(() => localDataSource.getCachedStudyBatch())
          .thenAnswer((_) async => []);

      expect(
        () => repository.getStudyBatch(),
        throwsA(isA<ServerException>()),
      );
    });
  });

  group('getNextCard', () {
    test('returns remote session model when remote call succeeds', () async {
      when(() => remoteDataSource.getNextCard(
            subjectId: any(named: 'subjectId'),
            topicId: any(named: 'topicId'),
            currentIndex: any(named: 'currentIndex'),
          )).thenAnswer((_) async => tSessionModel);

      final result = await repository.getNextCard(
        subjectId: 'sub-1',
        topicId: 'top-1',
        currentIndex: 1,
      );

      expect(result.currentIndex, 1);
      expect(result.currentCard?.id, 'c1');
    });

    test('falls back to local buffer card when remote call fails', () async {
      when(() => remoteDataSource.getNextCard(
            subjectId: any(named: 'subjectId'),
            topicId: any(named: 'topicId'),
            currentIndex: any(named: 'currentIndex'),
          )).thenThrow(const NetworkException());
      when(() => localDataSource.popNextCard()).thenReturn(tCardModel);
      when(() => localDataSource.remainingCount).thenReturn(3);

      final result = await repository.getNextCard(
        currentIndex: 2,
      );

      expect(result.currentIndex, 2);
      expect(result.currentCard?.id, 'c1');
      expect(result.totalCards, 4);
    });

    test('falls back to local cached batch when buffer is empty', () async {
      when(() => remoteDataSource.getNextCard(
            subjectId: any(named: 'subjectId'),
            topicId: any(named: 'topicId'),
            currentIndex: any(named: 'currentIndex'),
          )).thenThrow(const NetworkException());
      when(() => localDataSource.popNextCard()).thenReturn(null);
      when(() => localDataSource.getCachedStudyBatch())
          .thenAnswer((_) async => [tCardModel]);

      final result = await repository.getNextCard();

      expect(result.currentCard?.id, 'c1');
    });
  });

  group('markCardRead', () {
    test('calls remoteDataSource when online', () async {
      when(() => remoteDataSource.markCardRead(
            cardId: any(named: 'cardId'),
            subjectId: any(named: 'subjectId'),
            topicId: any(named: 'topicId'),
          )).thenAnswer((_) async {});

      await repository.markCardRead(
        cardId: 'c1',
        subjectId: 'sub-1',
        topicId: 'top-1',
      );

      verify(() => remoteDataSource.markCardRead(
            cardId: 'c1',
            subjectId: 'sub-1',
            topicId: 'top-1',
          )).called(1);
    });

    test('enqueues offline read into localDataSource when remote fails', () async {
      when(() => remoteDataSource.markCardRead(
            cardId: any(named: 'cardId'),
            subjectId: any(named: 'subjectId'),
            topicId: any(named: 'topicId'),
          )).thenThrow(const NetworkException());
      when(() => localDataSource.enqueueOfflineRead(any()))
          .thenAnswer((_) async {});

      await repository.markCardRead(
        cardId: 'c1',
        subjectId: 'sub-1',
        topicId: 'top-1',
      );

      verify(() => localDataSource.enqueueOfflineRead('c1')).called(1);
    });
  });

  group('listTopicFlashcards', () {
    test('fetches from remote and caches locally on success', () async {
      when(() => remoteDataSource.listTopicFlashcards(
            topicId: any(named: 'topicId'),
            limit: any(named: 'limit'),
            offset: any(named: 'offset'),
          )).thenAnswer((_) async => [tCardModel]);
      when(() => localDataSource.cacheTopicCards(any(), any()))
          .thenAnswer((_) async {});

      final result = await repository.listTopicFlashcards(
        topicId: 'top-1',
        limit: 50,
        offset: 0,
      );

      expect(result.length, 1);
      verify(() => localDataSource.cacheTopicCards('top-1', [tCardModel]))
          .called(1);
    });

    test('falls back to cached topic cards on network error', () async {
      when(() => remoteDataSource.listTopicFlashcards(
            topicId: any(named: 'topicId'),
            limit: any(named: 'limit'),
            offset: any(named: 'offset'),
          )).thenThrow(const NetworkException());
      when(() => localDataSource.getCachedTopicCards('top-1'))
          .thenAnswer((_) async => [tCardModel]);

      final result = await repository.listTopicFlashcards(topicId: 'top-1');

      expect(result.length, 1);
      verify(() => localDataSource.getCachedTopicCards('top-1')).called(1);
    });
  });
}
