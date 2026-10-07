import 'package:equatable/equatable.dart';

class FlashcardEntity extends Equatable {
  final String id;
  final String front;
  final String back;
  final int position;
  final List<String> topicIds;
  final String? primaryTopicId;

  const FlashcardEntity({
    required this.id,
    required this.front,
    required this.back,
    required this.position,
    this.topicIds = const <String>[],
    this.primaryTopicId,
  });

  @override
  List<Object?> get props => [
        id,
        front,
        back,
        position,
        topicIds,
        primaryTopicId,
      ];
}
