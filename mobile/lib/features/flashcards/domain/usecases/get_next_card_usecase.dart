import 'package:study_reviewer_mobile/features/flashcards/domain/entities/study_session_entity.dart';
import 'package:study_reviewer_mobile/features/flashcards/domain/repositories/flashcard_repository.dart';

class GetNextCardUseCase {
  final FlashcardRepository repository;

  const GetNextCardUseCase(this.repository);

  Future<StudySessionEntity> call({
    String? subjectId,
    String? topicId,
    int? currentIndex,
  }) {
    return repository.getNextCard(
      subjectId: subjectId,
      topicId: topicId,
      currentIndex: currentIndex,
    );
  }
}
