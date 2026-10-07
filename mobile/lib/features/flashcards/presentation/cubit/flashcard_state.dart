import 'package:equatable/equatable.dart';
import 'package:study_reviewer_mobile/features/flashcards/domain/entities/flashcard_entity.dart';

abstract class FlashcardState extends Equatable {
  const FlashcardState();

  @override
  List<Object?> get props => [];
}

class FlashcardInitial extends FlashcardState {
  const FlashcardInitial();
}

class FlashcardLoading extends FlashcardState {
  const FlashcardLoading();
}

class FlashcardLoaded extends FlashcardState {
  final FlashcardEntity currentCard;
  final int roundNumber;
  final int currentIndex;
  final int totalCards;
  final int remainingInBuffer;
  final bool isFlipped;
  final bool isPrefetching;
  final bool isOffline;

  const FlashcardLoaded({
    required this.currentCard,
    required this.roundNumber,
    required this.currentIndex,
    required this.totalCards,
    required this.remainingInBuffer,
    this.isFlipped = false,
    this.isPrefetching = false,
    this.isOffline = false,
  });

  FlashcardLoaded copyWith({
    FlashcardEntity? currentCard,
    int? roundNumber,
    int? currentIndex,
    int? totalCards,
    int? remainingInBuffer,
    bool? isFlipped,
    bool? isPrefetching,
    bool? isOffline,
  }) {
    return FlashcardLoaded(
      currentCard: currentCard ?? this.currentCard,
      roundNumber: roundNumber ?? this.roundNumber,
      currentIndex: currentIndex ?? this.currentIndex,
      totalCards: totalCards ?? this.totalCards,
      remainingInBuffer: remainingInBuffer ?? this.remainingInBuffer,
      isFlipped: isFlipped ?? this.isFlipped,
      isPrefetching: isPrefetching ?? this.isPrefetching,
      isOffline: isOffline ?? this.isOffline,
    );
  }

  @override
  List<Object?> get props => [
        currentCard,
        roundNumber,
        currentIndex,
        totalCards,
        remainingInBuffer,
        isFlipped,
        isPrefetching,
        isOffline,
      ];
}

class FlashcardEmpty extends FlashcardState {
  final String message;
  final int roundNumber;

  const FlashcardEmpty({
    this.message = 'Parabéns! Você revisou todos os flashcards desta rodada.',
    this.roundNumber = 1,
  });

  @override
  List<Object?> get props => [message, roundNumber];
}

class FlashcardError extends FlashcardState {
  final String message;
  final bool canRetry;

  const FlashcardError({
    required this.message,
    this.canRetry = true,
  });

  @override
  List<Object?> get props => [message, canRetry];
}
