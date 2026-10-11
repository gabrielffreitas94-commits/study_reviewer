import 'package:dio/dio.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:mocktail/mocktail.dart';
import 'package:study_reviewer_mobile/core/network/auth_interceptor.dart';
import 'package:study_reviewer_mobile/core/storage/secure_storage_service.dart';

class MockSecureStorageService extends Mock implements SecureStorageService {}
class MockRequestInterceptorHandler extends Mock implements RequestInterceptorHandler {}
class MockErrorInterceptorHandler extends Mock implements ErrorInterceptorHandler {}

void main() {
  late MockSecureStorageService mockStorageService;
  late AuthInterceptor interceptor;
  late bool unauthorizedCalled;

  setUp(() {
    mockStorageService = MockSecureStorageService();
    unauthorizedCalled = false;
    interceptor = AuthInterceptor(
      secureStorageService: mockStorageService,
      onUnauthorized: () {
        unauthorizedCalled = true;
      },
    );
  });

  group('AuthInterceptor', () {
    test('deve injetar Bearer token no header de autorização quando token existir', () async {
      when(() => mockStorageService.read(key: SecureStorageService.accessTokenKey))
          .thenAnswer((_) async => 'valid_bearer_token');

      final options = RequestOptions(path: '/test');
      final handler = MockRequestInterceptorHandler();

      await interceptor.onRequest(options, handler);

      expect(options.headers['Authorization'], 'Bearer valid_bearer_token');
      expect(options.headers['Accept'], 'application/json');
      verify(() => handler.next(options)).called(1);
    });

    test('não deve sobrescrever header de autorização previamente definido', () async {
      when(() => mockStorageService.read(key: SecureStorageService.accessTokenKey))
          .thenAnswer((_) async => 'stored_token');

      final options = RequestOptions(
        path: '/test',
        headers: {'Authorization': 'CustomApiKey 12345'},
      );
      final handler = MockRequestInterceptorHandler();

      await interceptor.onRequest(options, handler);

      expect(options.headers['Authorization'], 'CustomApiKey 12345');
      verify(() => handler.next(options)).called(1);
    });

    test('deve expurgar token e disparar onUnauthorized em caso de status 401', () async {
      when(() => mockStorageService.delete(key: SecureStorageService.accessTokenKey))
          .thenAnswer((_) async {});

      final requestOptions = RequestOptions(path: '/api/v1/auth/me');
      final dioException = DioException(
        requestOptions: requestOptions,
        response: Response(
          requestOptions: requestOptions,
          statusCode: 401,
        ),
      );
      final handler = MockErrorInterceptorHandler();

      await interceptor.onError(dioException, handler);

      verify(() => mockStorageService.delete(key: SecureStorageService.accessTokenKey)).called(1);
      expect(unauthorizedCalled, isTrue);
      verify(() => handler.next(dioException)).called(1);
    });
  });
}
