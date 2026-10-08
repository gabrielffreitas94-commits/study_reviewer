import 'package:equatable/equatable.dart';
import 'package:study_reviewer_mobile/features/flashcards/domain/entities/flashcard_entity.dart';

class StudySessionEntity extends Equatable {
  final int roundNumber;
  final int currentIndex;
  final int totalCards;
  final FlashcardEntity? currentCard;
  final String? sessionId;

  const StudySessionEntity({
    required this.roundNumber,
    required this.currentIndex,
    required this.totalCards,
    this.currentCard,
    this.sessionId,
  });

  @override
  List<Object?> get props => [
        roundNumber,
        currentIndex,
        totalCards,
        currentCard,
        sessionId,
      ];
}
