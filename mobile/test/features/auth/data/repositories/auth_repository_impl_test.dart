import 'package:flutter_test/flutter_test.dart';
import 'package:google_sign_in/google_sign_in.dart';
import 'package:mocktail/mocktail.dart';
import 'package:study_reviewer_mobile/core/storage/secure_storage_service.dart';
import 'package:study_reviewer_mobile/features/auth/data/datasources/auth_remote_data_source.dart';
import 'package:study_reviewer_mobile/features/auth/data/models/user_model.dart';
import 'package:study_reviewer_mobile/features/auth/data/repositories/auth_repository_impl.dart';

class MockAuthRemoteDataSource extends Mock implements AuthRemoteDataSource {}
class MockSecureStorageService extends Mock implements SecureStorageService {}
class MockGoogleSignIn extends Mock implements GoogleSignIn {}
class MockGoogleSignInAccount extends Mock implements GoogleSignInAccount {}
class MockGoogleSignInAuthentication extends Mock implements GoogleSignInAuthentication {}

void main() {
  late MockAuthRemoteDataSource mockRemoteDataSource;
  late MockSecureStorageService mockSecureStorageService;
  late MockGoogleSignIn mockGoogleSignIn;
  late AuthRepositoryImpl repository;

  final tUserModel = UserModel(
    id: 1,
    email: 'test@studyreviewer.com',
    name: 'Test User',
    avatarUrl: null,
    createdAt: DateTime.now(),
  );

  setUp(() {
    mockRemoteDataSource = MockAuthRemoteDataSource();
    mockSecureStorageService = MockSecureStorageService();
    mockGoogleSignIn = MockGoogleSignIn();

    repository = AuthRepositoryImpl(
      remoteDataSource: mockRemoteDataSource,
      secureStorageService: mockSecureStorageService,
      googleSignIn: mockGoogleSignIn,
    );
  });

  group('getCurrentUser', () {
    test('deve retornar null se não houver token no SecureStorage', () async {
      when(() => mockSecureStorageService.read(key: SecureStorageService.accessTokenKey))
          .thenAnswer((_) async => null);

      final result = await repository.getCurrentUser();

      expect(result, isNull);
      verify(() => mockSecureStorageService.read(key: SecureStorageService.accessTokenKey)).called(1);
    });

    test('deve retornar usuário e atualizar cache quando token for válido', () async {
      when(() => mockSecureStorageService.read(key: SecureStorageService.accessTokenKey))
          .thenAnswer((_) async => 'valid_token');
      when(() => mockRemoteDataSource.getCurrentUser())
          .thenAnswer((_) async => tUserModel);
      when(() => mockSecureStorageService.write(
            key: any(named: 'key'),
            value: any(named: 'value'),
          )).thenAnswer((_) async {});

      final result = await repository.getCurrentUser();

      expect(result, tUserModel);
      verify(() => mockRemoteDataSource.getCurrentUser()).called(1);
      verify(() => mockSecureStorageService.write(
            key: SecureStorageService.userCacheKey,
            value: any(named: 'value'),
          )).called(1);
    });
  });

  group('logout', () {
    test('deve expurgar credenciais do SecureStorage e efetuar sign out', () async {
      when(() => mockRemoteDataSource.logout()).thenAnswer((_) async {});
      when(() => mockGoogleSignIn.signOut()).thenAnswer((_) async => null);
      when(() => mockSecureStorageService.delete(key: any(named: 'key')))
          .thenAnswer((_) async {});

      await repository.logout();

      verify(() => mockRemoteDataSource.logout()).called(1);
      verify(() => mockGoogleSignIn.signOut()).called(1);
      verify(() => mockSecureStorageService.delete(key: SecureStorageService.accessTokenKey)).called(1);
      verify(() => mockSecureStorageService.delete(key: SecureStorageService.userCacheKey)).called(1);
    });
  });
}
