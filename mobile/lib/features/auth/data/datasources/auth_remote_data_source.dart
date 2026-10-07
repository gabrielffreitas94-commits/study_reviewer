import 'dart:io';
import 'package:dio/dio.dart';
import 'package:study_reviewer_mobile/core/constants/api_constants.dart';
import 'package:study_reviewer_mobile/core/errors/failures.dart';
import 'package:study_reviewer_mobile/features/auth/data/models/user_model.dart';

/// Contrato para comunicação remota com a API de autenticação.
abstract class AuthRemoteDataSource {
  /// Envia o token OIDC do Google para validação no backend e emissão do Bearer Token.
  Future<AuthResponseModel> loginWithGoogle({
    String? idToken,
    String? code,
    String? redirectUri,
  });

  /// Busca os dados cadastrais do usuário autenticado no backend.
  Future<UserModel> getCurrentUser();

  /// Solicita revogação e encerramento de sessão no backend.
  Future<void> logout();
}

/// Implementação da fonte remota utilizando o cliente HTTP Dio.
class AuthRemoteDataSourceImpl implements AuthRemoteDataSource {
  final Dio _dio;

  AuthRemoteDataSourceImpl({required Dio dio}) : _dio = dio;

  @override
  Future<AuthResponseModel> loginWithGoogle({
    String? idToken,
    String? code,
    String? redirectUri,
  }) async {
    try {
      final response = await _dio.post(
        ApiConstants.authGoogle,
        data: {
          if (idToken != null) 'id_token': idToken,
          if (code != null) 'code': code,
          'redirect_uri': redirectUri ?? '',
        },
      );

      if (response.statusCode == 200 && response.data != null) {
        final data = response.data as Map<String, dynamic>;
        return AuthResponseModel.fromJson(data);
      } else {
        throw ServerFailure(
          message: 'Resposta inesperada do servidor ao autenticar: ${response.statusCode}',
          statusCode: response.statusCode,
        );
      }
    } on DioException catch (e) {
      throw _handleDioException(e);
    } catch (e) {
      if (e is Failure) rethrow;
      throw ServerFailure(message: 'Erro desconhecido ao autenticar com Google: $e');
    }
  }

  @override
  Future<UserModel> getCurrentUser() async {
    try {
      final response = await _dio.get(ApiConstants.authMe);

      if (response.statusCode == 200 && response.data != null) {
        final data = response.data as Map<String, dynamic>;
        return UserModel.fromJson(data);
      } else {
        throw ServerFailure(
          message: 'Não foi possível carregar dados do usuário: ${response.statusCode}',
          statusCode: response.statusCode,
        );
      }
    } on DioException catch (e) {
      throw _handleDioException(e);
    } catch (e) {
      if (e is Failure) rethrow;
      throw ServerFailure(message: 'Erro desconhecido ao carregar perfil: $e');
    }
  }

  @override
  Future<void> logout() async {
    try {
      await _dio.post(ApiConstants.authLogout);
    } on DioException catch (e) {
      // Mesmo com falha remota no logout, a camada de repositório deve expurgar credenciais locais
      throw _handleDioException(e);
    } catch (e) {
      if (e is Failure) rethrow;
      throw ServerFailure(message: 'Erro desconhecido ao efetuar logout: $e');
    }
  }

  Failure _handleDioException(DioException e) {
    if (e.type == DioExceptionType.connectionTimeout ||
        e.type == DioExceptionType.sendTimeout ||
        e.type == DioExceptionType.receiveTimeout ||
        e.error is SocketException) {
      return const NetworkFailure(
        message: 'Conexão instável ou servidor indisponível. Verifique sua rede.',
      );
    }

    final statusCode = e.response?.statusCode;
    final detail = e.response?.data is Map
        ? (e.response?.data as Map)['detail']?.toString()
        : null;

    if (statusCode == 401) {
      return AuthFailure(
        message: detail ?? 'Credenciais inválidas ou sessão expirada.',
      );
    }

    if (statusCode == 403) {
      return AuthFailure(
        message: detail ?? 'Acesso não autorizado ao recurso solicitado.',
        statusCode: 403,
      );
    }

    return ServerFailure(
      message: detail ?? e.message ?? 'Falha de comunicação com o servidor.',
      statusCode: statusCode,
    );
  }
}
