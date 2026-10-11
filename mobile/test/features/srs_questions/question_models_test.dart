import 'package:flutter_test/flutter_test.dart';
import 'package:study_reviewer_mobile/features/srs_questions/data/models/due_question_model.dart';
import 'package:study_reviewer_mobile/features/srs_questions/data/models/review_result_model.dart';
import 'package:study_reviewer_mobile/features/srs_questions/data/models/text_evaluation_result_model.dart';
import 'package:study_reviewer_mobile/features/srs_questions/domain/entities/due_question_entity.dart';
import 'package:study_reviewer_mobile/features/srs_questions/domain/entities/review_result_entity.dart';
import 'package:study_reviewer_mobile/features/srs_questions/domain/entities/text_evaluation_result_entity.dart';

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

  group('TextEvaluationResultModel', () {
    final tJson = <String, dynamic>{
      'question_id': 'q-201',
      'score': 85,
      'feedback': 'Excelente domínio dos conceitos de telófase e citocinese.',
      'coverage_score': 90,
      'accuracy_score': 85,
      'depth_score': 80,
      'tokens_consumed': 482,
      'remaining_balance': 1518,
      'rag_grounding_applied': true,
    };

    test('deve instanciar TextEvaluationResultModel via fromJson com sucesso', () {
      final model = TextEvaluationResultModel.fromJson(tJson);

      expect(model.questionId, 'q-201');
      expect(model.score, 85);
      expect(model.feedback, 'Excelente domínio dos conceitos de telófase e citocinese.');
      expect(model.coverageScore, 90);
      expect(model.accuracyScore, 85);
      expect(model.depthScore, 80);
      expect(model.tokensConsumed, 482);
      expect(model.remainingBalance, 1518);
      expect(model.ragGroundingApplied, isTrue);
      expect(model, isA<TextEvaluationResultEntity>());
      expect(model.toEntity(), isA<TextEvaluationResultEntity>());
    });

    test('deve converter para json compatível com toJson', () {
      final model = TextEvaluationResultModel.fromJson(tJson);
      final json = model.toJson();

      expect(json['question_id'], 'q-201');
      expect(json['score'], 85);
      expect(json['coverage_score'], 90);
      expect(json['accuracy_score'], 85);
      expect(json['depth_score'], 80);
      expect(json['tokens_consumed'], 482);
      expect(json['remaining_balance'], 1518);
      expect(json['rag_grounding_applied'], isTrue);
    });

    test('deve tratar campos numéricos decimais ou nulos com fallback gracioso', () {
      final fallbackJson = <String, dynamic>{
        'questionId': 'q-202',
        'score': 89.6,
        'feedback': null,
        'coverageScore': 95.2,
        'accuracyScore': 88.0,
        'depthScore': 75.4,
        'tokensConsumed': 500,
        'remainingBalance': 1000,
        'ragGroundingApplied': false,
      };

      final model = TextEvaluationResultModel.fromJson(fallbackJson);

      expect(model.questionId, 'q-202');
      expect(model.score, 90);
      expect(model.feedback, '');
      expect(model.coverageScore, 95);
      expect(model.accuracyScore, 88);
      expect(model.depthScore, 75);
      expect(model.tokensConsumed, 500);
      expect(model.remainingBalance, 1000);
      expect(model.ragGroundingApplied, isFalse);
    });
  });
}
