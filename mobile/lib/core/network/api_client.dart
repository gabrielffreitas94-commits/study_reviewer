import 'dart:developer' as developer;
import 'package:dio/dio.dart';
import 'package:study_reviewer_mobile/core/constants/api_constants.dart';
import 'package:study_reviewer_mobile/core/network/auth_interceptor.dart';
import 'package:study_reviewer_mobile/core/storage/secure_storage_service.dart';

/// Interceptor de logging defensivo que protege contra vazamento de PII (Personally Identifiable Information)
/// e credenciais sensíveis (Bearer tokens, senhas, códigos de autorização).
class DefensiveLoggingInterceptor extends Interceptor {
  @override
  void onRequest(RequestOptions options, RequestInterceptorHandler handler) {
    // Registra apenas método e caminho da URL, omitindo cabeçalhos e payload sensível
    developer.log(
      '--> ${options.method} ${options.uri.path}',
      name: 'ApiClient',
    );
    handler.next(options);
  }

  @override
  void onResponse(Response response, ResponseInterceptorHandler handler) {
    developer.log(
      '<-- ${response.statusCode} ${response.requestOptions.method} ${response.requestOptions.uri.path}',
      name: 'ApiClient',
    );
    handler.next(response);
  }

  @override
  void onError(DioException err, ErrorInterceptorHandler handler) {
    final status = err.response?.statusCode ?? 'NETWORK_ERROR';
    developer.log(
      '<-- ERROR [$status] ${err.requestOptions.method} ${err.requestOptions.uri.path} : ${err.type}',
      name: 'ApiClient',
      error: err.message,
    );
    handler.next(err);
  }
}

/// Fábrica do cliente HTTP Dio configurado com timeouts rigorosos de 15s,
/// cabeçalhos padrão, interceptor de autenticação e logs defensivos.
class ApiClient {
  ApiClient._();

  static Dio createDioClient({
    required SecureStorageService secureStorageService,
    String? baseUrl,
    void Function()? onUnauthorized,
    List<Interceptor>? customInterceptors,
  }) {
    final dio = Dio(
      BaseOptions(
        baseUrl: baseUrl ?? ApiConstants.defaultBaseUrl,
        connectTimeout: ApiConstants.connectTimeout,
        receiveTimeout: ApiConstants.receiveTimeout,
        sendTimeout: ApiConstants.sendTimeout,
        headers: {
          'Content-Type': 'application/json',
          'Accept': 'application/json',
        },
        responseType: ResponseType.json,
      ),
    );

    // Injeta AuthInterceptor para gerenciamento de Bearer Tokens e 401
    dio.interceptors.add(
      AuthInterceptor(
        secureStorageService: secureStorageService,
        onUnauthorized: onUnauthorized,
      ),
    );

    // Injeta interceptor de log defensivo (sem PII nem tokens)
    dio.interceptors.add(DefensiveLoggingInterceptor());

    if (customInterceptors != null) {
      dio.interceptors.addAll(customInterceptors);
    }

    return dio;
  }
}
