import 'package:equatable/equatable.dart';
import 'package:study_reviewer_mobile/features/sync/domain/entities/study_event_entity.dart';

class StudyEventModel extends StudyEventEntity {
  const StudyEventModel({
    super.id,
    required super.cardId,
    required super.reviewedAt,
    required super.status,
    super.deviceId,
  });

  factory StudyEventModel.fromJson(Map<String, dynamic> json) {
    return StudyEventModel(
      id: json['id']?.toString(),
      cardId: json['card_id']?.toString() ?? '',
      reviewedAt: DateTime.parse(
          json['reviewed_at']?.toString() ?? DateTime.now().toIso8601String()),
      status: json['status']?.toString() ?? 'viewed',
      deviceId: json['device_id']?.toString(),
    );
  }

  Map<String, dynamic> toJson() {
    return <String, dynamic>{
      if (id != null) 'id': id,
      'card_id': cardId,
      'reviewed_at': reviewedAt.toUtc().toIso8601String(),
      'status': status,
      if (deviceId != null) 'device_id': deviceId,
    };
  }
}

class SyncAnswersPayloadModel extends Equatable {
  final String sessionId;
  final List<StudyEventModel> events;
  final int? batchIndex;

  const SyncAnswersPayloadModel({
    required this.sessionId,
    required this.events,
    this.batchIndex,
  });

  Map<String, dynamic> toJson() {
    return <String, dynamic>{
      'session_id': sessionId,
      'events': events.map((event) => event.toJson()).toList(),
      if (batchIndex != null) 'batch_index': batchIndex,
    };
  }

  @override
  List<Object?> get props => [sessionId, events, batchIndex];
}

class SyncAnswersResponseModel extends Equatable {
  final String status;
  final int syncedCount;
  final String sessionId;
  final int currentIndex;

  const SyncAnswersResponseModel({
    required this.status,
    required this.syncedCount,
    required this.sessionId,
    required this.currentIndex,
  });

  factory SyncAnswersResponseModel.fromJson(Map<String, dynamic> json) {
    return SyncAnswersResponseModel(
      status: json['status']?.toString() ?? 'ok',
      syncedCount: (json['synced_count'] as num?)?.toInt() ?? 0,
      sessionId: json['session_id']?.toString() ?? '',
      currentIndex: (json['current_index'] as num?)?.toInt() ?? 0,
    );
  }

  @override
  List<Object?> get props => [status, syncedCount, sessionId, currentIndex];
}
