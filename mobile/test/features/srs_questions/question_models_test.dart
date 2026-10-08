import 'package:flutter_test/flutter_test.dart';
import 'package:study_reviewer_mobile/features/srs_questions/data/models/due_question_model.dart';
import 'package:study_reviewer_mobile/features/srs_questions/data/models/review_result_model.dart';
import 'package:study_reviewer_mobile/features/srs_questions/domain/entities/due_question_entity.dart';
import 'package:study_reviewer_mobile/features/srs_questions/domain/entities/review_result_entity.dart';

void main() {
  group('DueQuestionModel', () {
    final tJson = <String, dynamic>{
      'question_id': 'q-101',
      'prompt': 'O que é ACID?',
      'expected_answer': 'Atomicidade, Consistência, Isolamento e Durabilidade.',
      'current_level': 2,
      'due_date': '2026-10-07',
      'is_due': true,
      'subject_name': 'Banco de Dados',
      'topic_name': 'Transações',
      'interval_days': 3,
    };

    test('deve instanciar DueQuestionModel corretamente via fromJson', () {
      final model = DueQuestionModel.fromJson(tJson);

      expect(model.id, 'q-101');
      expect(model.prompt, 'O que é ACID?');
      expect(model.expectedAnswer,
          'Atomicidade, Consistência, Isolamento e Durabilidade.');
      expect(model.currentLevel, 2);
      expect(model.isDue, isTrue);
      expect(model.subjectName, 'Banco de Dados');
      expect(model.topicName, 'Transações');
      expect(model.intervalDays, 3);
      expect(model, isA<DueQuestionEntity>());
    });

    test('deve converter para json compatível com toJson', () {
      final model = DueQuestionModel.fromJson(tJson);
      final json = model.toJson();

      expect(json['question_id'], 'q-101');
      expect(json['prompt'], 'O que é ACID?');
      expect(json['current_level'], 2);
      expect(json['is_due'], isTrue);
    });

    test('deve tratar fallback de id e datas nulas', () {
      final minimalJson = <String, dynamic>{
        'id': 'alt-id',
        'prompt': 'Pergunta simples',
        'expected_answer': 'Resposta simples',
      };
      final model = DueQuestionModel.fromJson(minimalJson);

      expect(model.id, 'alt-id');
      expect(model.currentLevel, 0);
      expect(model.intervalDays, 1);
    });
  });

  group('ReviewResultModel', () {
    final tJson = <String, dynamic>{
      'question_id': 'q-101',
      'score': 100,
      'previous_level': 2,
      'new_level': 3,
      'next_review_date': '2026-10-15',
      'is_promoted': true,
      'is_regressed': false,
      'interval_days': 7,
    };

    test('deve desserializar resultado SRS promovido via fromJson', () {
      final model = ReviewResultModel.fromJson(tJson);

      expect(model.questionId, 'q-101');
      expect(model.score, 100);
      expect(model.levelBefore, 2);
      expect(model.levelAfter, 3);
      expect(model.isPromoted, isTrue);
      expect(model.isDemoted, isFalse);
      expect(model.isMaintained, isFalse);
      expect(model.intervalDays, 7);
      expect(model, isA<ReviewResultEntity>());
    });

    test('deve calcular corretamente isDemoted e isMaintained', () {
      final demotedJson = <String, dynamic>{
        'question_id': 'q-102',
        'previous_level': 3,
        'new_level': 1,
        'is_promoted': false,
        'is_regressed': true,
      };
      final demotedModel =
          ReviewResultModel.fromJson(demotedJson, submittedScore: 25);
      expect(demotedModel.score, 25);
      expect(demotedModel.isPromoted, isFalse);
      expect(demotedModel.isDemoted, isTrue);
      expect(demotedModel.isMaintained, isFalse);

      final maintainedJson = <String, dynamic>{
        'question_id': 'q-103',
        'previous_level': 2,
        'new_level': 2,
        'is_promoted': false,
        'is_regressed': false,
      };
      final maintainedModel =
          ReviewResultModel.fromJson(maintainedJson, submittedScore: 50);
      expect(maintainedModel.isPromoted, isFalse);
      expect(maintainedModel.isDemoted, isFalse);
      expect(maintainedModel.isMaintained, isTrue);
    });

    test('deve gerar mapa correto em toJson', () {
      final model = ReviewResultModel.fromJson(tJson);
      final json = model.toJson();

      expect(json['question_id'], 'q-101');
      expect(json['previous_level'], 2);
      expect(json['new_level'], 3);
      expect(json['is_promoted'], isTrue);
    });
  });
}
