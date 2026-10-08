import 'package:bloc_test/bloc_test.dart';
import 'package:dio/dio.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:mocktail/mocktail.dart';
import 'package:study_reviewer_mobile/core/constants/api_constants.dart';
import 'package:study_reviewer_mobile/core/errors/exceptions.dart';
import 'package:study_reviewer_mobile/core/errors/failures.dart';
import 'package:study_reviewer_mobile/core/usecases/usecase.dart';
import 'package:study_reviewer_mobile/features/performance/data/datasources/performance_remote_data_source.dart';
import 'package:study_reviewer_mobile/features/performance/data/models/user_statistics_model.dart';
import 'package:study_reviewer_mobile/features/performance/data/repositories/performance_repository_impl.dart';
import 'package:study_reviewer_mobile/features/performance/domain/entities/user_statistics_entity.dart';
import 'package:study_reviewer_mobile/features/performance/domain/repositories/performance_repository.dart';
import 'package:study_reviewer_mobile/features/performance/domain/usecases/get_user_statistics_usecase.dart';
import 'package:study_reviewer_mobile/features/performance/presentation/cubit/performance_cubit.dart';
import 'package:study_reviewer_mobile/features/performance/presentation/cubit/performance_state.dart';

class MockDio extends Mock implements Dio {}
class MockPerformanceRemoteDataSource extends Mock
    implements PerformanceRemoteDataSource {}
class MockPerformanceRepository extends Mock implements PerformanceRepository {}
class MockGetUserStatisticsUseCase extends Mock
    implements GetUserStatisticsUseCase {}

void main() {
  const tStatistics = UserStatisticsEntity(
    retentionRate: 88.5,
    matureQuestionsCount: 42,
    totalReviewsCount: 150,
    activeDaysCount: 15,
    srsDistribution: <int, int>{
      0: 5,
      1: 10,
      2: 20,
      3: 15,
      4: 25,
      5: 12,
      6: 5,
    },
  );

  group('UserStatisticsModel', () {
    final tJson = <String, dynamic>{
      'retention_rate': 88.5,
      'mature_questions_count': 42,
      'total_reviews_count': 150,
      'active_days_count': 15,
      'srs_distribution': {
        '0': 5,
        '1': 10,
        '2': 20,
        '3': 15,
        '4': 25,
        '5': 12,
        '6': 5,
      },
    };

    test('deve criar modelo a partir de fromJson', () {
      final model = UserStatisticsModel.fromJson(tJson);

      expect(model.retentionRate, 88.5);
      expect(model.matureQuestionsCount, 42);
      expect(model.totalReviewsCount, 150);
      expect(model.activeDaysCount, 15);
      expect(model.srsDistribution[4], 25);
      expect(model.totalCardsInSrs, 92);
      expect(model, isA<UserStatisticsEntity>());
    });

    test('deve converter modelo para json via toJson', () {
      final model = UserStatisticsModel.fromJson(tJson);
      final json = model.toJson();

      expect(json['retention_rate'], 88.5);
      expect(json['mature_questions_count'], 42);
      expect(json['srs_distribution']['4'], 25);
    });
  });

  group('PerformanceRemoteDataSourceImpl', () {
    late MockDio mockDio;
    late PerformanceRemoteDataSourceImpl dataSource;

    setUp(() {
      mockDio = MockDio();
      dataSource = PerformanceRemoteDataSourceImpl(client: mockDio);
    });

    test('deve retornar UserStatisticsModel em sucesso', () async {
      when(() => mockDio.get<Map<String, dynamic>>(ApiConstants.performanceStatistics))
          .thenAnswer(
        (_) async => Response<Map<String, dynamic>>(
          data: {
            'retention_rate': 80.0,
            'mature_questions_count': 10,
            'total_reviews_count': 50,
            'active_days_count': 5,
            'srs_distribution': {'0': 2},
          },
          statusCode: 200,
          requestOptions: RequestOptions(path: ApiConstants.performanceStatistics),
        ),
      );

      final result = await dataSource.getUserStatistics();

      expect(result.retentionRate, 80.0);
      expect(result.matureQuestionsCount, 10);
    });

    test('deve lançar ServerException em erro 500', () async {
      when(() => mockDio.get<Map<String, dynamic>>(ApiConstants.performanceStatistics))
          .thenThrow(
        DioException(
          type: DioExceptionType.badResponse,
          requestOptions: RequestOptions(path: ApiConstants.performanceStatistics),
          response: Response(
            statusCode: 500,
            data: {'detail': 'Erro no servidor'},
            requestOptions: RequestOptions(path: ApiConstants.performanceStatistics),
          ),
        ),
      );

      expect(
        () => dataSource.getUserStatistics(),
        throwsA(isA<ServerException>()),
      );
    });
  });

  group('PerformanceRepositoryImpl', () {
    late MockPerformanceRemoteDataSource mockRemoteDataSource;
    late PerformanceRepositoryImpl repository;

    setUp(() {
      mockRemoteDataSource = MockPerformanceRemoteDataSource();
      repository =
          PerformanceRepositoryImpl(remoteDataSource: mockRemoteDataSource);
    });

    test('deve retornar UserStatisticsEntity ao invocar datasource', () async {
      const model = UserStatisticsModel(
        retentionRate: 90.0,
        matureQuestionsCount: 20,
        totalReviewsCount: 100,
        activeDaysCount: 10,
        srsDistribution: {0: 1},
      );

      when(() => mockRemoteDataSource.getUserStatistics())
          .thenAnswer((_) async => model);

      final result = await repository.getUserStatistics();

      expect(result.retentionRate, 90.0);
      verify(() => mockRemoteDataSource.getUserStatistics()).called(1);
    });

    test('deve remapear exceções para Failures', () async {
      when(() => mockRemoteDataSource.getUserStatistics())
          .thenThrow(const ServerException(message: 'Erro'));

      expect(
        () => repository.getUserStatistics(),
        throwsA(isA<ServerFailure>()),
      );
    });
  });

  group('GetUserStatisticsUseCase', () {
    late MockPerformanceRepository mockRepo;
    late GetUserStatisticsUseCase useCase;

    setUp(() {
      mockRepo = MockPerformanceRepository();
      useCase = GetUserStatisticsUseCase(repository: mockRepo);
    });

    test('deve encaminhar chamada para o repositório', () async {
      when(() => mockRepo.getUserStatistics())
          .thenAnswer((_) async => tStatistics);

      final result = await useCase(const NoParams());

      expect(result, tStatistics);
      verify(() => mockRepo.getUserStatistics()).called(1);
    });
  });

  group('PerformanceCubit', () {
    late MockGetUserStatisticsUseCase mockUseCase;
    late PerformanceCubit cubit;

    setUp(() {
      mockUseCase = MockGetUserStatisticsUseCase();
      cubit = PerformanceCubit(getUserStatisticsUseCase: mockUseCase);
    });

    tearDown(() {
      cubit.close();
    });

    test('estado inicial deve ser PerformanceInitial', () {
      expect(cubit.state, const PerformanceInitial());
    });

    blocTest<PerformanceCubit, PerformanceState>(
      'deve emitir [PerformanceLoading, PerformanceLoaded] ao buscar com sucesso',
      build: () {
        when(() => mockUseCase(const NoParams()))
            .thenAnswer((_) async => tStatistics);
        return cubit;
      },
      act: (c) => c.loadStatistics(),
      expect: () => [
        const PerformanceLoading(),
        const PerformanceLoaded(tStatistics),
      ],
    );

    blocTest<PerformanceCubit, PerformanceState>(
      'deve emitir [PerformanceLoading, PerformanceError] em caso de falha',
      build: () {
        when(() => mockUseCase(const NoParams()))
            .thenThrow(const ServerFailure(message: 'Falha nas estatísticas'));
        return cubit;
      },
      act: (c) => c.loadStatistics(),
      expect: () => [
        const PerformanceLoading(),
        const PerformanceError('Falha nas estatísticas'),
      ],
    );
  });
}
