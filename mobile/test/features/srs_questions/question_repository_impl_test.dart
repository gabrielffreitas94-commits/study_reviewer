import 'package:flutter_test/flutter_test.dart';
import 'package:mocktail/mocktail.dart';
import 'package:study_reviewer_mobile/core/errors/exceptions.dart';
import 'package:study_reviewer_mobile/core/errors/failures.dart';
import 'package:study_reviewer_mobile/features/srs_questions/data/datasources/question_remote_data_source.dart';
import 'package:study_reviewer_mobile/features/srs_questions/data/models/due_question_model.dart';
import 'package:study_reviewer_mobile/features/srs_questions/data/models/review_result_model.dart';
import 'package:study_reviewer_mobile/features/srs_questions/data/models/text_evaluation_result_model.dart';
import 'package:study_reviewer_mobile/features/srs_questions/data/repositories/question_repository_impl.dart';
import 'package:study_reviewer_mobile/features/srs_questions/domain/entities/text_evaluation_result_entity.dart';

class MockQuestionRemoteDataSource extends Mock
    implements QuestionRemoteDataSource {}

void main() {
  late MockQuestionRemoteDataSource mockRemoteDataSource;
  late QuestionRepositoryImpl repository;

  setUp(() {
    mockRemoteDataSource = MockQuestionRemoteDataSource();
    repository = QuestionRepositoryImpl(remoteDataSource: mockRemoteDataSource);
  });

  final tQuestionModel = DueQuestionModel(
    id: 'q-1',
    prompt: 'O que é ACID?',
    expectedAnswer: 'Propriedades de transação',
    currentLevel: 1,
    nextReviewDate: DateTime(2026, 10, 8),
    isDue: true,
  );

  final tReviewModel = ReviewResultModel(
    questionId: 'q-1',
    score: 100,
    levelBefore: 1,
    levelAfter: 2,
    nextReviewDate: DateTime(2026, 10, 10),
    isPromoted: true,
    isDemoted: false,
    isMaintained: false,
    intervalDays: 2,
  );

  final tEvaluationModel = TextEvaluationResultModel(
    questionId: 'q-1',
    score: 92,
    feedback: 'Excelente resposta',
    coverageScore: 95,
    accuracyScore: 90,
    depthScore: 90,
    tokensConsumed: 480,
    remainingBalance: 1520,
    ragGroundingApplied: true,
  );

  group('getDueQuestions', () {
    test('deve retornar lista de entidades de perguntas quando bem-sucedido',
        () async {
      when(() => mockRemoteDataSource.getDueQuestions(
            subjectId: any(named: 'subjectId'),
            limit: any(named: 'limit'),
          )).thenAnswer((_) async => [tQuestionModel]);

      final result = await repository.getDueQuestions();

      expect(result.length, 1);
      expect(result.first.id, 'q-1');
      verify(() => mockRemoteDataSource.getDueQuestions(limit: 50)).called(1);
    });

    test('deve remapear NetworkException para NetworkFailure', () async {
      when(() => mockRemoteDataSource.getDueQuestions(
            subjectId: any(named: 'subjectId'),
            limit: any(named: 'limit'),
          )).thenThrow(const NetworkException(message: 'Sem internet'));

      expect(
        () => repository.getDueQuestions(),
        throwsA(isA<NetworkFailure>()),
      );
    });

    test('deve remapear ServerException para ServerFailure', () async {
      when(() => mockRemoteDataSource.getDueQuestions(
            subjectId: any(named: 'subjectId'),
            limit: any(named: 'limit'),
          )).thenThrow(const ServerException(message: 'Erro interno 500'));

      expect(
        () => repository.getDueQuestions(),
        throwsA(isA<ServerFailure>()),
      );
    });
  });

  group('reviewQuestion', () {
    test('deve submeter e retornar ReviewResultEntity', () async {
      when(() => mockRemoteDataSource.reviewQuestion(
            questionId: 'q-1',
            score: 100,
          )).thenAnswer((_) async => tReviewModel);

      final result = await repository.reviewQuestion(
        questionId: 'q-1',
        score: 100,
      );

      expect(result.questionId, 'q-1');
      expect(result.levelAfter, 2);
      expect(result.isPromoted, isTrue);
    });

    test('deve remapear exceções para Failures em reviewQuestion', () async {
      when(() => mockRemoteDataSource.reviewQuestion(
            questionId: 'q-1',
            score: 100,
          )).thenThrow(const ServerException(message: 'Falha 400'));

      expect(
        () => repository.reviewQuestion(questionId: 'q-1', score: 100),
        throwsA(isA<ServerFailure>()),
      );
    });
  });

  group('evaluateTextQuestion', () {
    test('deve avaliar resposta dissertativa e retornar TextEvaluationResultEntity', () async {
      when(() => mockRemoteDataSource.evaluateTextQuestion(
            questionId: 'q-1',
            studentAnswer: 'Resposta do aluno',
          )).thenAnswer((_) async => tEvaluationModel);

      final result = await repository.evaluateTextQuestion(
        questionId: 'q-1',
        studentAnswer: 'Resposta do aluno',
      );

      expect(result.questionId, 'q-1');
      expect(result.score, 92);
      expect(result.ragGroundingApplied, isTrue);
      expect(result, isA<TextEvaluationResultEntity>());
    });

    test('deve remapear NetworkException para NetworkFailure em evaluateTextQuestion', () async {
      when(() => mockRemoteDataSource.evaluateTextQuestion(
            questionId: 'q-1',
            studentAnswer: 'Resposta do aluno',
          )).thenThrow(const NetworkException(message: 'Sem internet'));

      expect(
        () => repository.evaluateTextQuestion(
          questionId: 'q-1',
          studentAnswer: 'Resposta do aluno',
        ),
        throwsA(isA<NetworkFailure>()),
      );
    });

    test('deve remapear ServerException para ServerFailure em evaluateTextQuestion', () async {
      when(() => mockRemoteDataSource.evaluateTextQuestion(
            questionId: 'q-1',
            studentAnswer: 'Resposta do aluno',
          )).thenThrow(const ServerException(message: 'Saldo insuficiente', statusCode: 402));

      expect(
        () => repository.evaluateTextQuestion(
          questionId: 'q-1',
          studentAnswer: 'Resposta do aluno',
        ),
        throwsA(
          predicate<ServerFailure>(
            (f) => f.statusCode == 402 && f.message.contains('Saldo insuficiente'),
          ),
        ),
      );
    });
  });
}
