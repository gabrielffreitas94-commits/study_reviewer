import 'package:study_reviewer_mobile/features/flashcards/domain/repositories/flashcard_repository.dart';

class MarkCardReadUseCase {
  final FlashcardRepository repository;

  const MarkCardReadUseCase(this.repository);

  Future<void> call({
    required String cardId,
    String? subjectId,
    String? topicId,
  }) {
    return repository.markCardRead(
      cardId: cardId,
      subjectId: subjectId,
      topicId: topicId,
    );
  }
}
