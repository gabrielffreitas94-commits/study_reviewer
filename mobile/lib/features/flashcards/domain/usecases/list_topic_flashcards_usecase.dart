import 'package:study_reviewer_mobile/features/flashcards/domain/entities/flashcard_entity.dart';
import 'package:study_reviewer_mobile/features/flashcards/domain/repositories/flashcard_repository.dart';

class ListTopicFlashcardsUseCase {
  final FlashcardRepository repository;

  const ListTopicFlashcardsUseCase(this.repository);

  Future<List<FlashcardEntity>> call({
    required String topicId,
    int limit = 50,
    int offset = 0,
  }) {
    return repository.listTopicFlashcards(
      topicId: topicId,
      limit: limit,
      offset: offset,
    );
  }
}
