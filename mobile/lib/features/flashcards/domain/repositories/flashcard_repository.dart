import 'package:study_reviewer_mobile/features/flashcards/domain/entities/flashcard_entity.dart';
import 'package:study_reviewer_mobile/features/flashcards/domain/entities/study_session_entity.dart';

abstract class FlashcardRepository {
  Future<List<FlashcardEntity>> getStudyBatch({
    String? subjectId,
    String? topicId,
    int limit = 50,
  });

  Future<StudySessionEntity> getNextCard({
    String? subjectId,
    String? topicId,
    int? currentIndex,
  });

  Future<void> markCardRead({
    required String cardId,
    String? subjectId,
    String? topicId,
  });

  Future<List<FlashcardEntity>> listTopicFlashcards({
    required String topicId,
    int limit = 50,
    int offset = 0,
  });
}
