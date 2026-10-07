import 'package:study_reviewer_mobile/features/flashcards/domain/entities/flashcard_entity.dart';
import 'package:study_reviewer_mobile/features/flashcards/domain/repositories/flashcard_repository.dart';

class GetStudyBatchUseCase {
  final FlashcardRepository repository;

  const GetStudyBatchUseCase(this.repository);

  Future<List<FlashcardEntity>> call({
    String? subjectId,
    String? topicId,
    int limit = 50,
  }) {
    return repository.getStudyBatch(
      subjectId: subjectId,
      topicId: topicId,
      limit: limit,
    );
  }
}
