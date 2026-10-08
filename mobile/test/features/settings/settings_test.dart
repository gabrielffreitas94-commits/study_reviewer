import 'package:bloc_test/bloc_test.dart';
import 'package:dio/dio.dart';
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:mocktail/mocktail.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:study_reviewer_mobile/core/constants/api_constants.dart';
import 'package:study_reviewer_mobile/core/errors/exceptions.dart';
import 'package:study_reviewer_mobile/core/errors/failures.dart';
import 'package:study_reviewer_mobile/core/storage/secure_storage_service.dart';
import 'package:study_reviewer_mobile/core/usecases/usecase.dart';
import 'package:study_reviewer_mobile/features/settings/data/datasources/settings_remote_data_source.dart';
import 'package:study_reviewer_mobile/features/settings/data/repositories/settings_repository_impl.dart';
import 'package:study_reviewer_mobile/features/settings/domain/repositories/settings_repository.dart';
import 'package:study_reviewer_mobile/features/settings/domain/usecases/delete_account_usecase.dart';
import 'package:study_reviewer_mobile/features/settings/presentation/cubit/settings_cubit.dart';
import 'package:study_reviewer_mobile/features/settings/presentation/cubit/settings_state.dart';

class MockDio extends Mock implements Dio {}
class MockSettingsRemoteDataSource extends Mock
    implements SettingsRemoteDataSource {}
class MockSettingsRepository extends Mock implements SettingsRepository {}
class MockDeleteAccountUseCase extends Mock implements DeleteAccountUseCase {}
class MockSecureStorageService extends Mock implements SecureStorageService {}

void main() {
  setUpAll(() {
    registerFallbackValue(const NoParams());
  });

  group('SettingsRemoteDataSourceImpl', () {
    late MockDio mockDio;
    late SettingsRemoteDataSourceImpl dataSource;

    setUp(() {
      mockDio = MockDio();
      dataSource = SettingsRemoteDataSourceImpl(client: mockDio);
    });

    test('deve chamar DELETE /api/v1/auth/account com sucesso', () async {
      when(() => mockDio.delete<dynamic>(ApiConstants.authAccount))
          .thenAnswer(
        (_) async => Response<dynamic>(
          data: {'message': 'Conta excluída'},
          statusCode: 200,
          requestOptions: RequestOptions(path: ApiConstants.authAccount),
        ),
      );

      await dataSource.deleteAccount();

      verify(() => mockDio.delete<dynamic>(ApiConstants.authAccount)).called(1);
    });

    test('deve lançar ServerException quando endpoint retornar erro', () async {
      when(() => mockDio.delete<dynamic>(ApiConstants.authAccount)).thenThrow(
        DioException(
          type: DioExceptionType.badResponse,
          requestOptions: RequestOptions(path: ApiConstants.authAccount),
          response: Response(
            statusCode: 404,
            data: {'detail': 'Usuário não encontrado'},
            requestOptions: RequestOptions(path: ApiConstants.authAccount),
          ),
        ),
      );

      expect(
        () => dataSource.deleteAccount(),
        throwsA(isA<ServerException>()),
      );
    });
  });

  group('SettingsRepositoryImpl', () {
    late MockSettingsRemoteDataSource mockRemoteDataSource;
    late SettingsRepositoryImpl repository;

    setUp(() {
      mockRemoteDataSource = MockSettingsRemoteDataSource();
      repository =
          SettingsRepositoryImpl(remoteDataSource: mockRemoteDataSource);
    });

    test('deve delegar exclusão para remoteDataSource', () async {
      when(() => mockRemoteDataSource.deleteAccount())
          .thenAnswer((_) async {});

      await repository.deleteAccount();

      verify(() => mockRemoteDataSource.deleteAccount()).called(1);
    });

    test('deve remapear exceções para ServerFailure', () async {
      when(() => mockRemoteDataSource.deleteAccount())
          .thenThrow(const ServerException(message: 'Erro'));

      expect(
        () => repository.deleteAccount(),
        throwsA(isA<ServerFailure>()),
      );
    });
  });

  group('DeleteAccountUseCase', () {
    late MockSettingsRepository mockRepo;
    late DeleteAccountUseCase useCase;

    setUp(() {
      mockRepo = MockSettingsRepository();
      useCase = DeleteAccountUseCase(repository: mockRepo);
    });

    test('deve invocar o repositório', () async {
      when(() => mockRepo.deleteAccount()).thenAnswer((_) async {});

      await useCase(const NoParams());

      verify(() => mockRepo.deleteAccount()).called(1);
    });
  });

  group('SettingsCubit', () {
    late MockDeleteAccountUseCase mockDeleteAccountUseCase;
    late MockSecureStorageService mockSecureStorage;
    late SettingsCubit cubit;

    setUp(() {
      SharedPreferences.setMockInitialValues({});
      mockDeleteAccountUseCase = MockDeleteAccountUseCase();
      mockSecureStorage = MockSecureStorageService();

      cubit = SettingsCubit(
        deleteAccountUseCase: mockDeleteAccountUseCase,
        secureStorageService: mockSecureStorage,
      );
    });

    tearDown(() {
      cubit.close();
    });

    test('estado inicial deve ter tema padrão e flags falsas', () {
      expect(cubit.state.isDeletingAccount, isFalse);
      expect(cubit.state.isAccountDeleted, isFalse);
    });

    test('setThemeMode deve atualizar o tema emitido', () async {
      await cubit.setThemeMode(ThemeMode.dark);
      expect(cubit.state.themeMode, ThemeMode.dark);

      await cubit.setThemeMode(ThemeMode.light);
      expect(cubit.state.themeMode, ThemeMode.light);
    });

    test('toggleTheme deve alternar entre dark e light', () async {
      await cubit.setThemeMode(ThemeMode.light);
      await cubit.toggleTheme();
      expect(cubit.state.themeMode, ThemeMode.dark);

      await cubit.toggleTheme();
      expect(cubit.state.themeMode, ThemeMode.light);
    });

    blocTest<SettingsCubit, SettingsState>(
      'deleteAccount deve invocar caso de uso, purgar Keystore e emitir isAccountDeleted = true',
      build: () {
        when(() => mockDeleteAccountUseCase(const NoParams()))
            .thenAnswer((_) async {});
        when(() => mockSecureStorage.deleteAll()).thenAnswer((_) async {});
        return cubit;
      },
      act: (c) => c.deleteAccount(),
      expect: () => [
        const SettingsState(isDeletingAccount: true),
        const SettingsState(isDeletingAccount: false, isAccountDeleted: true),
      ],
      verify: (_) {
        verify(() => mockDeleteAccountUseCase(const NoParams())).called(1);
        verify(() => mockSecureStorage.deleteAll()).called(1);
      },
    );

    blocTest<SettingsCubit, SettingsState>(
      'deleteAccount deve emitir errorMessage em caso de falha',
      build: () {
        when(() => mockDeleteAccountUseCase(const NoParams()))
            .thenThrow(const ServerFailure(message: 'Falha ao excluir'));
        return cubit;
      },
      act: (c) => c.deleteAccount(),
      expect: () => [
        const SettingsState(isDeletingAccount: true),
        const SettingsState(
          isDeletingAccount: false,
          errorMessage: 'Falha ao excluir',
        ),
      ],
    );
  });
}
