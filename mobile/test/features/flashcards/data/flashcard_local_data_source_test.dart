import 'package:flutter_test/flutter_test.dart';
import 'package:study_reviewer_mobile/features/flashcards/data/datasources/flashcard_local_data_source.dart';
import 'package:study_reviewer_mobile/features/flashcards/data/models/flashcard_model.dart';

void main() {
  late FlashcardLocalDataSourceImpl dataSource;

  const card1 = FlashcardModel(
    id: 'c1',
    front: 'F1',
    back: 'B1',
    position: 1,
  );
  const card2 = FlashcardModel(
    id: 'c2',
    front: 'F2',
    back: 'B2',
    position: 2,
  );
  const card3 = FlashcardModel(
    id: 'c3',
    front: 'F3',
    back: 'B3',
    position: 3,
  );

  setUp(() {
    dataSource = FlashcardLocalDataSourceImpl();
  });

  group('FlashcardLocalDataSource - In-Memory Buffer', () {
    test('setCardBuffer replaces entire buffer', () {
      dataSource.setCardBuffer([card1, card2]);

      expect(dataSource.remainingCount, 2);
      expect(dataSource.peekCurrentCard(), card1);
    });

    test('appendCardsToBuffer adds only unseen cards (deduplication)', () {
      dataSource.setCardBuffer([card1]);
      dataSource.appendCardsToBuffer([card1, card2, card3]);

      expect(dataSource.remainingCount, 3);
      expect(dataSource.currentBuffer.map((c) => c.id).toList(), ['c1', 'c2', 'c3']);
    });

    test('popNextCard removes and returns FIFO elements', () {
      dataSource.setCardBuffer([card1, card2]);

      final popped1 = dataSource.popNextCard();
      expect(popped1, card1);
      expect(dataSource.remainingCount, 1);

      final popped2 = dataSource.popNextCard();
      expect(popped2, card2);
      expect(dataSource.remainingCount, 0);

      final poppedEmpty = dataSource.popNextCard();
      expect(poppedEmpty, isNull);
    });

    test('clearBuffer empties all buffered cards', () {
      dataSource.setCardBuffer([card1, card2]);
      dataSource.clearBuffer();

      expect(dataSource.remainingCount, 0);
      expect(dataSource.peekCurrentCard(), isNull);
    });
  });

  group('FlashcardLocalDataSource - Offline Cache', () {
    test('cacheStudyBatch and getCachedStudyBatch persist in-memory copy', () async {
      await dataSource.cacheStudyBatch([card1, card2]);

      final cached = await dataSource.getCachedStudyBatch();
      expect(cached.length, 2);
      expect(cached.first.id, 'c1');
    });

    test('cacheTopicCards and getCachedTopicCards isolate cards by topic', () async {
      await dataSource.cacheTopicCards('topic-A', [card1]);
      await dataSource.cacheTopicCards('topic-B', [card2, card3]);

      final cachedA = await dataSource.getCachedTopicCards('topic-A');
      final cachedB = await dataSource.getCachedTopicCards('topic-B');
      final cachedEmpty = await dataSource.getCachedTopicCards('topic-unknown');

      expect(cachedA.length, 1);
      expect(cachedB.length, 2);
      expect(cachedEmpty, isEmpty);
    });
  });

  group('FlashcardLocalDataSource - Offline Read Events Queue', () {
    test('enqueueOfflineRead prevents duplicates and maintains queue', () async {
      await dataSource.enqueueOfflineRead('c1');
      await dataSource.enqueueOfflineRead('c1');
      await dataSource.enqueueOfflineRead('c2');

      final pending = await dataSource.getPendingOfflineReads();
      expect(pending, ['c1', 'c2']);
    });

    test('removeOfflineReads removes specific processed ids', () async {
      await dataSource.enqueueOfflineRead('c1');
      await dataSource.enqueueOfflineRead('c2');
      await dataSource.enqueueOfflineRead('c3');

      await dataSource.removeOfflineReads(['c1', 'c3']);

      final pending = await dataSource.getPendingOfflineReads();
      expect(pending, ['c2']);
    });

    test('clearOfflineReads removes all enqueued reads', () async {
      await dataSource.enqueueOfflineRead('c1');
      await dataSource.clearOfflineReads();

      final pending = await dataSource.getPendingOfflineReads();
      expect(pending, isEmpty);
    });
  });
}
