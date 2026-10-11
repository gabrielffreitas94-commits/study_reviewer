import 'package:study_reviewer_mobile/features/srs_questions/domain/entities/due_question_entity.dart';

/// Modelo de dados para desserialização de perguntas abertas vencidas.
class DueQuestionModel extends DueQuestionEntity {
  const DueQuestionModel({
    required super.id,
    required super.prompt,
    required super.expectedAnswer,
    required super.currentLevel,
    required super.nextReviewDate,
    required super.isDue,
    super.subjectName,
    super.topicName,
    super.intervalDays = 1,
  });

  factory DueQuestionModel.fromJson(Map<String, dynamic> json) {
    final rawDueDate = json['due_date']?.toString() ??
        json['next_review_date']?.toString() ??
        DateTime.now().toIso8601String();
    final parsedDate = DateTime.tryParse(rawDueDate) ?? DateTime.now();

    final isDueValue = json['is_due'] != null
        ? json['is_due'] as bool
        : parsedDate.isBefore(DateTime.now().add(const Duration(days: 1)));

    return DueQuestionModel(
      id: (json['question_id'] ?? json['id'] ?? '').toString(),
      prompt: (json['prompt'] ?? '').toString(),
      expectedAnswer: (json['expected_answer'] ?? '').toString(),
      currentLevel: (json['current_level'] as num?)?.toInt() ?? 0,
      nextReviewDate: parsedDate,
      isDue: isDueValue,
      subjectName: json['subject_name']?.toString(),
      topicName: json['topic_name']?.toString(),
      intervalDays: (json['interval_days'] as num?)?.toInt() ?? 1,
    );
  }

  Map<String, dynamic> toJson() {
    return <String, dynamic>{
      'question_id': id,
      'prompt': prompt,
      'expected_answer': expectedAnswer,
      'current_level': currentLevel,
      'due_date': nextReviewDate.toIso8601String().split('T').first,
      'is_due': isDue,
      'subject_name': subjectName,
      'topic_name': topicName,
      'interval_days': intervalDays,
    };
  }

  DueQuestionEntity toEntity() => this;
}
