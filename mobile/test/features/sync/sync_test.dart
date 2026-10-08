import 'package:dio/dio.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:mocktail/mocktail.dart';
import 'package:study_reviewer_mobile/core/constants/api_constants.dart';
import 'package:study_reviewer_mobile/features/sync/data/datasources/sync_remote_data_source.dart';
import 'package:study_reviewer_mobile/features/sync/data/models/study_event_model.dart';
import 'package:study_reviewer_mobile/features/sync/domain/entities/study_event_entity.dart';

class MockDio extends Mock implements Dio {}

void main() {
  late MockDio mockDio;
  late SyncRemoteDataSourceImpl dataSource;

  final tTime = DateTime.parse('2026-10-07T20:00:00.000Z');

  final tEvent = StudyEventModel(
    id: 'ev-1',
    cardId: 'card-1',
    reviewedAt: tTime,
    status: 'viewed',
    deviceId: 'android-device-123',
  );

  setUp(() {
    mockDio = MockDio();
    dataSource = SyncRemoteDataSourceImpl(client: mockDio);
  });

  group('StudyEvent Entities & Models', () {
    test('StudyEventEntity supports value equality', () {
      final e1 = StudyEventEntity(
        id: '1',
        cardId: 'c1',
        reviewedAt: tTime,
        status: 'viewed',
        deviceId: 'd1',
      );
      final e2 = StudyEventEntity(
        id: '1',
        cardId: 'c1',
        reviewedAt: tTime,
        status: 'viewed',
        deviceId: 'd1',
      );

      expect(e1, equals(e2));
    });

    test('StudyEventModel serializes and deserializes correctly', () {
      final json = tEvent.toJson();

      expect(json['id'], 'ev-1');
      expect(json['card_id'], 'card-1');
      expect(json['status'], 'viewed');
      expect(json['device_id'], 'android-device-123');

      final deserialized = StudyEventModel.fromJson(json);
      expect(deserialized.id, tEvent.id);
      expect(deserialized.cardId, tEvent.cardId);
      expect(deserialized.status, tEvent.status);
    });

    test('SyncAnswersPayloadModel serializes with batch_index', () {
      final payload = SyncAnswersPayloadModel(
        sessionId: 'sess-100',
        events: [tEvent],
        batchIndex: 2,
      );

      final json = payload.toJson();
      expect(json['session_id'], 'sess-100');
      expect(json['batch_index'], 2);
      expect((json['events'] as List<dynamic>).length, 1);
    });

    test('SyncAnswersResponseModel parses backend response', () {
      final resJson = <String, dynamic>{
        'status': 'ok',
        'synced_count': 5,
        'session_id': 'sess-100',
        'current_index': 6,
      };

      final response = SyncAnswersResponseModel.fromJson(resJson);
      expect(response.status, 'ok');
      expect(response.syncedCount, 5);
      expect(response.sessionId, 'sess-100');
      expect(response.currentIndex, 6);
    });
  });

  group('SyncRemoteDataSourceImpl', () {
    test('syncAnswers sends POST with X-Correlation-ID header', () async {
      when(() => mockDio.post<Map<String, dynamic>>(
            ApiConstants.studySyncAnswers,
            data: any(named: 'data'),
            options: any(named: 'options'),
          )).thenAnswer(
        (_) async => Response<Map<String, dynamic>>(
          requestOptions: RequestOptions(path: ApiConstants.studySyncAnswers),
          statusCode: 200,
          data: <String, dynamic>{
            'status': 'ok',
            'synced_count': 1,
            'session_id': 'sess-100',
            'current_index': 2,
          },
        ),
      );

      final result = await dataSource.syncAnswers(
        sessionId: 'sess-100',
        events: [tEvent],
        correlationId: 'test-corr-id-12345',
      );

      expect(result.status, 'ok');
      expect(result.syncedCount, 1);
      expect(result.sessionId, 'sess-100');
      expect(result.currentIndex, 2);

      verify(() => mockDio.post<Map<String, dynamic>>(
            ApiConstants.studySyncAnswers,
            data: any(
              named: 'data',
              that: isA<Map<String, dynamic>>().having(
                (m) => m['session_id'],
                'session_id',
                'sess-100',
              ),
            ),
            options: any(
              named: 'options',
              that: isA<Options>().having(
                (o) => o.headers?['X-Correlation-ID'],
                'X-Correlation-ID',
                'test-corr-id-12345',
              ),
            ),
          )).called(1);
    });
  });
}
