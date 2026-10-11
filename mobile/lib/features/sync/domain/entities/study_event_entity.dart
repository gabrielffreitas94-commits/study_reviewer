import 'package:equatable/equatable.dart';

class StudyEventEntity extends Equatable {
  final String? id;
  final String cardId;
  final DateTime reviewedAt;
  final String status;
  final String? deviceId;

  const StudyEventEntity({
    this.id,
    required this.cardId,
    required this.reviewedAt,
    required this.status,
    this.deviceId,
  });

  @override
  List<Object?> get props => [id, cardId, reviewedAt, status, deviceId];
}
