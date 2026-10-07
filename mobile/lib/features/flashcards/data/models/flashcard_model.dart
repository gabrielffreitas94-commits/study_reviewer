import 'package:study_reviewer_mobile/features/flashcards/domain/entities/flashcard_entity.dart';

class FlashcardModel extends FlashcardEntity {
  final int? currentIndex;
  final int? totalCards;
  final int? roundNumber;
  final bool? roundShuffled;
  final List<String>? topicNames;
  final String? sessionId;

  const FlashcardModel({
    required super.id,
    required super.front,
    required super.back,
    required super.position,
    super.topicIds = const <String>[],
    super.primaryTopicId,
    this.currentIndex,
    this.totalCards,
    this.roundNumber,
    this.roundShuffled,
    this.topicNames,
    this.sessionId,
  });

  factory FlashcardModel.fromJson(Map<String, dynamic> json) {
    final rawTopicIds = json['topic_ids'];
    final List<String> topicIds = rawTopicIds is List
        ? rawTopicIds.map((dynamic e) => e.toString()).toList()
        : <String>[];

    final rawTopicNames = json['topic_names'];
    final List<String> topicNames = rawTopicNames is List
        ? rawTopicNames.map((dynamic e) => e.toString()).toList()
        : <String>[];

    final primaryTopicId = json['topic_id']?.toString() ??
        (topicIds.isNotEmpty ? topicIds.first : null);

    return FlashcardModel(
      id: json['id']?.toString() ?? '',
      front: json['front']?.toString() ?? '',
      back: json['back']?.toString() ?? '',
      position: (json['position'] as num?)?.toInt() ?? 0,
      topicIds: topicIds,
      primaryTopicId: primaryTopicId,
      currentIndex: (json['current_index'] as num?)?.toInt(),
      totalCards: (json['total_cards'] as num?)?.toInt(),
      roundNumber: (json['round_number'] as num?)?.toInt(),
      roundShuffled: json['round_shuffled'] as bool?,
      topicNames: topicNames,
      sessionId: json['session_id']?.toString(),
    );
  }

  Map<String, dynamic> toJson() {
    return <String, dynamic>{
      'id': id,
      'front': front,
      'back': back,
      'position': position,
      'topic_ids': topicIds,
      if (primaryTopicId != null) 'topic_id': primaryTopicId,
      if (currentIndex != null) 'current_index': currentIndex,
      if (totalCards != null) 'total_cards': totalCards,
      if (roundNumber != null) 'round_number': roundNumber,
      if (roundShuffled != null) 'round_shuffled': roundShuffled,
      if (topicNames != null && topicNames!.isNotEmpty)
        'topic_names': topicNames,
      if (sessionId != null) 'session_id': sessionId,
    };
  }

  FlashcardEntity toEntity() {
    return FlashcardEntity(
      id: id,
      front: front,
      back: back,
      position: position,
      topicIds: topicIds,
      primaryTopicId: primaryTopicId,
    );
  }

  @override
  List<Object?> get props => [
        ...super.props,
        currentIndex,
        totalCards,
        roundNumber,
        roundShuffled,
        topicNames,
        sessionId,
      ];
}
