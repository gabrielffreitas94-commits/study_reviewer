import 'package:flutter_test/flutter_test.dart';
import 'package:study_reviewer_mobile/features/flashcards/data/models/flashcard_model.dart';
import 'package:study_reviewer_mobile/features/flashcards/data/models/study_batch_model.dart';

void main() {
  group('FlashcardModel', () {
    final tJson = <String, dynamic>{
      'id': 'c1e40eb6-21a4-4d89-9fc6-07973715e751',
      'front': 'O que é Inversão de Dependência?',
      'back': 'Módulos de alto nível não devem depender de módulos de baixo nível.',
      'position': 1,
      'topic_ids': ['b2d863f6-424a-4a81-ba56-cb82eb2c3fa0'],
      'topic_names': ['Arquitetura'],
      'topic_id': 'b2d863f6-424a-4a81-ba56-cb82eb2c3fa0',
      'current_index': 1,
      'total_cards': 10,
      'round_number': 1,
      'round_shuffled': false,
      'session_id': '7fbcfef3-0ea1-4560-a292-ba78a08d249f',
    };

    test('fromJson correctly parses full backend StudyCardDTO payload', () {
      final model = FlashcardModel.fromJson(tJson);

      expect(model.id, 'c1e40eb6-21a4-4d89-9fc6-07973715e751');
      expect(model.front, 'O que é Inversão de Dependência?');
      expect(model.back,
          'Módulos de alto nível não devem depender de módulos de baixo nível.');
      expect(model.position, 1);
      expect(model.topicIds, ['b2d863f6-424a-4a81-ba56-cb82eb2c3fa0']);
      expect(model.primaryTopicId, 'b2d863f6-424a-4a81-ba56-cb82eb2c3fa0');
      expect(model.currentIndex, 1);
      expect(model.totalCards, 10);
      expect(model.roundNumber, 1);
      expect(model.roundShuffled, false);
      expect(model.sessionId, '7fbcfef3-0ea1-4560-a292-ba78a08d249f');
    });

    test('toJson produces expected serializable map', () {
      final model = FlashcardModel.fromJson(tJson);
      final json = model.toJson();

      expect(json['id'], model.id);
      expect(json['front'], model.front);
      expect(json['back'], model.back);
      expect(json['position'], 1);
      expect(json['topic_ids'], ['b2d863f6-424a-4a81-ba56-cb82eb2c3fa0']);
      expect(json['topic_id'], 'b2d863f6-424a-4a81-ba56-cb82eb2c3fa0');
    });

    test('toEntity returns clean FlashcardEntity', () {
      final model = FlashcardModel.fromJson(tJson);
      final entity = model.toEntity();

      expect(entity.id, model.id);
      expect(entity.front, model.front);
      expect(entity.back, model.back);
      expect(entity.position, model.position);
      expect(entity.topicIds, model.topicIds);
      expect(entity.primaryTopicId, model.primaryTopicId);
    });
  });

  group('StudyBatchModel', () {
    final tBatchJson = <String, dynamic>{
      'cards': [
        {
          'id': 'card-1',
          'front': 'Front 1',
          'back': 'Back 1',
          'position': 1,
          'topic_ids': ['topic-1'],
        },
        {
          'id': 'card-2',
          'front': 'Front 2',
          'back': 'Back 2',
          'position': 2,
          'topic_ids': ['topic-1'],
        }
      ],
      'total_cards': 2,
      'round_number': 1,
      'has_more': false,
    };

    test('fromJson parses batch payload correctly', () {
      final batch = StudyBatchModel.fromJson(tBatchJson);

      expect(batch.cards.length, 2);
      expect(batch.cards.first.id, 'card-1');
      expect(batch.totalCards, 2);
      expect(batch.roundNumber, 1);
      expect(batch.hasMore, false);
    });

    test('toJson serializes batch correctly', () {
      final batch = StudyBatchModel.fromJson(tBatchJson);
      final json = batch.toJson();

      expect(json['total_cards'], 2);
      expect(json['round_number'], 1);
      expect(json['has_more'], false);
      expect((json['cards'] as List<dynamic>).length, 2);
    });
  });

  group('StudySessionModel', () {
    final tSessionJson = <String, dynamic>{
      'id': 'c1',
      'front': 'F1',
      'back': 'B1',
      'position': 1,
      'current_index': 3,
      'total_cards': 15,
      'round_number': 2,
      'round_shuffled': true,
      'session_id': 'sess-99',
    };

    test('fromJson parses StudySessionModel and currentCard', () {
      final session = StudySessionModel.fromJson(tSessionJson);

      expect(session.currentIndex, 3);
      expect(session.totalCards, 15);
      expect(session.roundNumber, 2);
      expect(session.roundShuffled, true);
      expect(session.sessionId, 'sess-99');
      expect(session.currentCard?.id, 'c1');
    });

    test('toJson serializes session model', () {
      final session = StudySessionModel.fromJson(tSessionJson);
      final json = session.toJson();

      expect(json['current_index'], 3);
      expect(json['total_cards'], 15);
      expect(json['round_number'], 2);
      expect(json['session_id'], 'sess-99');
    });
  });
}
