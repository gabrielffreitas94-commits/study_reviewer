import 'package:equatable/equatable.dart';
import 'package:study_reviewer_mobile/features/flashcards/data/models/flashcard_model.dart';
import 'package:study_reviewer_mobile/features/flashcards/domain/entities/study_session_entity.dart';

class StudyBatchModel extends Equatable {
  final List<FlashcardModel> cards;
  final int totalCards;
  final int roundNumber;
  final bool hasMore;

  const StudyBatchModel({
    required this.cards,
    required this.totalCards,
    required this.roundNumber,
    required this.hasMore,
  });

  factory StudyBatchModel.fromJson(Map<String, dynamic> json) {
    final rawCards = json['cards'];
    final List<FlashcardModel> cards = rawCards is List
        ? rawCards
            .map((dynamic item) =>
                FlashcardModel.fromJson(item as Map<String, dynamic>))
            .toList()
        : <FlashcardModel>[];

    return StudyBatchModel(
      cards: cards,
      totalCards: (json['total_cards'] as num?)?.toInt() ?? cards.length,
      roundNumber: (json['round_number'] as num?)?.toInt() ?? 1,
      hasMore: json['has_more'] as bool? ?? false,
    );
  }

  Map<String, dynamic> toJson() {
    return <String, dynamic>{
      'cards': cards.map((card) => card.toJson()).toList(),
      'total_cards': totalCards,
      'round_number': roundNumber,
      'has_more': hasMore,
    };
  }

  @override
  List<Object?> get props => [cards, totalCards, roundNumber, hasMore];
}

class StudySessionModel extends StudySessionEntity {
  final bool? roundShuffled;

  const StudySessionModel({
    required super.roundNumber,
    required super.currentIndex,
    required super.totalCards,
    super.currentCard,
    super.sessionId,
    this.roundShuffled,
  });

  factory StudySessionModel.fromJson(Map<String, dynamic> json) {
    final cardModel = FlashcardModel.fromJson(json);
    return StudySessionModel(
      roundNumber: (json['round_number'] as num?)?.toInt() ?? 1,
      currentIndex: (json['current_index'] as num?)?.toInt() ?? 1,
      totalCards: (json['total_cards'] as num?)?.toInt() ?? 1,
      currentCard: cardModel,
      sessionId: json['session_id']?.toString(),
      roundShuffled: json['round_shuffled'] as bool?,
    );
  }

  Map<String, dynamic> toJson() {
    return <String, dynamic>{
      if (currentCard is FlashcardModel)
        ...(currentCard! as FlashcardModel).toJson(),
      'round_number': roundNumber,
      'current_index': currentIndex,
      'total_cards': totalCards,
      if (sessionId != null) 'session_id': sessionId,
      if (roundShuffled != null) 'round_shuffled': roundShuffled,
    };
  }

  @override
  List<Object?> get props => [
        ...super.props,
        roundShuffled,
      ];
}
