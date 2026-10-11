import 'package:equatable/equatable.dart';

/// Entidade de domínio representando uma Pergunta Aberta vencida para revisão SRS.
class DueQuestionEntity extends Equatable {
  final String id;
  final String prompt;
  final String expectedAnswer;
  final int currentLevel;
  final DateTime nextReviewDate;
  final bool isDue;
  final String? subjectName;
  final String? topicName;
  final int intervalDays;

  const DueQuestionEntity({
    required this.id,
    required this.prompt,
    required this.expectedAnswer,
    required this.currentLevel,
    required this.nextReviewDate,
    required this.isDue,
    this.subjectName,
    this.topicName,
    this.intervalDays = 1,
  });

  @override
  List<Object?> get props => [
        id,
        prompt,
        expectedAnswer,
        currentLevel,
        nextReviewDate,
        isDue,
        subjectName,
        topicName,
        intervalDays,
      ];
}
