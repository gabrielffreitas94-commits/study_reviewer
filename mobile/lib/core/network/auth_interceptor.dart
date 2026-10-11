import 'package:dio/dio.dart';
import 'package:study_reviewer_mobile/core/storage/secure_storage_service.dart';

/// Interceptor do Dio responsável por injetar o Bearer Token obtido do SecureStorageService
/// em todas as requisições autenticadas e lidar com expiração (401 Unauthorized).
class AuthInterceptor extends QueuedInterceptor {
  final SecureStorageService _secureStorageService;
  final void Function()? _onUnauthorized;

  AuthInterceptor({
    required SecureStorageService secureStorageService,
    void Function()? onUnauthorized,
  })  : _secureStorageService = secureStorageService,
        _onUnauthorized = onUnauthorized;

  @override
  Future<void> onRequest(
    RequestOptions options,
    RequestInterceptorHandler handler,
  ) async {
    try {
      // Injeta token se não estiver previamente definido explicitamente
      if (!options.headers.containsKey('Authorization')) {
        final token = await _secureStorageService.read(
          key: SecureStorageService.accessTokenKey,
        );

        if (token != null && token.isNotEmpty) {
          options.headers['Authorization'] = 'Bearer $token';
        }
      }
      options.headers['Accept'] = 'application/json';
    } catch (_) {
      // Falhas no storage seguro não devem interromper a tentativa de request
    }
    return handler.next(options);
  }

  @override
  Future<void> onError(
    DioException err,
    ErrorInterceptorHandler handler,
  ) async {
    if (err.response?.statusCode == 401) {
      // Token expirado ou inválido: remove credencial segura do Keystore/Keychain
      try {
        await _secureStorageService.delete(
          key: SecureStorageService.accessTokenKey,
        );
      } catch (_) {
        // Ignora erro de deleção
      }

      // Notifica listeners para transição de estado da UI
      _onUnauthorized?.call();
    }

    return handler.next(err);
  }
}
