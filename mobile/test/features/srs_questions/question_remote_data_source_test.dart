import 'package:dio/dio.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:mocktail/mocktail.dart';
import 'package:study_reviewer_mobile/core/constants/api_constants.dart';
import 'package:study_reviewer_mobile/core/errors/exceptions.dart';
import 'package:study_reviewer_mobile/features/srs_questions/data/datasources/question_remote_data_source.dart';

class MockDio extends Mock implements Dio {}

void main() {
  late MockDio mockDio;
  late QuestionRemoteDataSourceImpl dataSource;

  setUp(() {
    mockDio = MockDio();
    dataSource = QuestionRemoteDataSourceImpl(client: mockDio);
  });

  group('getDueQuestions', () {
    final tResponseMap = <String, dynamic>{
      'items': [
        <String, dynamic>{
          'question_id': 'q-1',
          'prompt': 'Prompt 1',
          'expected_answer': 'Answer 1',
          'current_level': 1,
          'due_date': '2026-10-07',
          'is_due': true,
        },
      ],
      'total_due': 1,
      'next_review_date': '2026-10-07',
    };

    test('deve retornar lista de DueQuestionModel quando chamada for bem-sucedida',
        () async {
      when(
        () => mockDio.get<dynamic>(
          ApiConstants.questionsDue,
          queryParameters: any(named: 'queryParameters'),
        ),
      ).thenAnswer(
        (_) async => Response<dynamic>(
          data: tResponseMap,
          statusCode: 200,
          requestOptions: RequestOptions(path: ApiConstants.questionsDue),
        ),
      );

      final result = await dataSource.getDueQuestions(subjectId: 'sub-1', limit: 10);

      expect(result.length, 1);
      expect(result.first.id, 'q-1');
      expect(result.first.prompt, 'Prompt 1');
    });

    test('deve lançar NetworkException quando Dio falhar por timeout ou rede',
        () async {
      when(
        () => mockDio.get<dynamic>(
          ApiConstants.questionsDue,
          queryParameters: any(named: 'queryParameters'),
        ),
      ).thenThrow(
        DioException(
          type: DioExceptionType.connectionTimeout,
          requestOptions: RequestOptions(path: ApiConstants.questionsDue),
          message: 'Timeout ao conectar',
        ),
      );

      expect(
        () => dataSource.getDueQuestions(),
        throwsA(isA<NetworkException>()),
      );
    });

    test('deve lançar ServerException com mensagem detalhada em erro HTTP 500',
        () async {
      when(
        () => mockDio.get<dynamic>(
          ApiConstants.questionsDue,
          queryParameters: any(named: 'queryParameters'),
        ),
      ).thenThrow(
        DioException(
          type: DioExceptionType.badResponse,
          requestOptions: RequestOptions(path: ApiConstants.questionsDue),
          response: Response(
            statusCode: 500,
            data: {'detail': 'Erro interno do servidor'},
            requestOptions: RequestOptions(path: ApiConstants.questionsDue),
          ),
        ),
      );

      expect(
        () => dataSource.getDueQuestions(),
        throwsA(isA<ServerException>()),
      );
    });
  });

  group('reviewQuestion', () {
    final tReviewResponse = <String, dynamic>{
      'question_id': 'q-1',
      'previous_level': 1,
      'new_level': 2,
      'next_review_date': '2026-10-09',
      'interval_days': 2,
      'is_promoted': true,
      'is_regressed': false,
    };

    test('deve submeter nota e retornar ReviewResultModel com sucesso', () async {
      when(
        () => mockDio.post<Map<String, dynamic>>(
          ApiConstants.questionReview('q-1'),
          data: {'score': 100},
        ),
      ).thenAnswer(
        (_) async => Response<Map<String, dynamic>>(
          data: tReviewResponse,
          statusCode: 200,
          requestOptions: RequestOptions(path: ApiConstants.questionReview('q-1')),
        ),
      );

      final result = await dataSource.reviewQuestion(
        questionId: 'q-1',
        score: 100,
      );

      expect(result.questionId, 'q-1');
      expect(result.levelBefore, 1);
      expect(result.levelAfter, 2);
      expect(result.isPromoted, isTrue);
    });

    test('deve lançar ServerException quando endpoint de review falhar', () async {
      when(
        () => mockDio.post<Map<String, dynamic>>(
          ApiConstants.questionReview('q-1'),
          data: {'score': 100},
        ),
      ).thenThrow(
        DioException(
          type: DioExceptionType.badResponse,
          requestOptions: RequestOptions(path: ApiConstants.questionReview('q-1')),
          response: Response(
            statusCode: 400,
            data: {'detail': 'Pergunta não está vencida'},
            requestOptions: RequestOptions(path: ApiConstants.questionReview('q-1')),
          ),
        ),
      );

      expect(
        () => dataSource.reviewQuestion(questionId: 'q-1', score: 100),
        throwsA(isA<ServerException>()),
      );
    });
  });
}
