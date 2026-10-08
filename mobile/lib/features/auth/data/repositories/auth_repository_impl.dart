import 'dart:convert';
import 'package:google_sign_in/google_sign_in.dart';
import 'package:study_reviewer_mobile/core/errors/failures.dart';
import 'package:study_reviewer_mobile/core/storage/secure_storage_service.dart';
import 'package:study_reviewer_mobile/features/auth/data/datasources/auth_remote_data_source.dart';
import 'package:study_reviewer_mobile/features/auth/data/models/user_model.dart';
import 'package:study_reviewer_mobile/features/auth/domain/entities/user_entity.dart';
import 'package:study_reviewer_mobile/features/auth/domain/repositories/auth_repository.dart';

/// Implementação do repositório de autenticação orquestrando Google Sign-In,
/// API REST remota e armazenamento seguro com Android Keystore / iOS Keychain.
class AuthRepositoryImpl implements AuthRepository {
  final AuthRemoteDataSource _remoteDataSource;
  final SecureStorageService _secureStorageService;
  final GoogleSignIn _googleSignIn;

  AuthRepositoryImpl({
    required AuthRemoteDataSource remoteDataSource,
    required SecureStorageService secureStorageService,
    GoogleSignIn? googleSignIn,
  })  : _remoteDataSource = remoteDataSource,
        _secureStorageService = secureStorageService,
        _googleSignIn = googleSignIn ??
            GoogleSignIn(
              scopes: ['email', 'profile'],
            );

  @override
  Future<UserEntity> loginWithGoogle() async {
    try {
      // 1. Inicia o fluxo de login nativo do Google
      final GoogleSignInAccount? account = await _googleSignIn.signIn();
      if (account == null) {
        throw const AuthFailure(message: 'Login com Google cancelado pelo usuário.');
      }

      // 2. Obtém tokens de autenticação OIDC
      final GoogleSignInAuthentication auth = await account.authentication;
      final String? idToken = auth.idToken;
      final String? serverAuthCode = account.serverAuthCode;

      if (idToken == null && serverAuthCode == null) {
        throw const AuthFailure(
          message: 'Falha ao recuperar credenciais e tokens do Google.',
        );
      }

      // 3. Valida no backend e obtém a sessão Bearer Token
      final authResponse = await _remoteDataSource.loginWithGoogle(
        idToken: idToken,
        code: serverAuthCode,
      );

      // 4. Armazena o Bearer token de forma segura no Keystore / Keychain
      await _secureStorageService.write(
        key: SecureStorageService.accessTokenKey,
        value: authResponse.accessToken,
      );

      // 5. Atualiza cache criptografado do usuário
      await _secureStorageService.write(
        key: SecureStorageService.userCacheKey,
        value: jsonEncode(authResponse.user.toJson()),
      );

      return authResponse.user;
    } on Failure {
      rethrow;
    } catch (e) {
      throw AuthFailure(
        message: 'Falha inesperada no fluxo de autenticação com Google: $e',
      );
    }
  }

  @override
  Future<UserEntity?> getCurrentUser() async {
    try {
      final token = await _secureStorageService.read(
        key: SecureStorageService.accessTokenKey,
      );

      if (token == null || token.isEmpty) {
        return null;
      }

      try {
        // Valida token diretamente no backend via /auth/me
        final user = await _remoteDataSource.getCurrentUser();
        await _secureStorageService.write(
          key: SecureStorageService.userCacheKey,
          value: jsonEncode(user.toJson()),
        );
        return user;
      } on AuthFailure {
        // Token revogado ou expirado no backend: expurga credenciais locais
        await _secureStorageService.delete(key: SecureStorageService.accessTokenKey);
        await _secureStorageService.delete(key: SecureStorageService.userCacheKey);
        return null;
      } on NetworkFailure {
        // Em caso de falha de conexão temporária, tenta recuperar cache local
        final cachedUserJson = await _secureStorageService.read(
          key: SecureStorageService.userCacheKey,
        );
        if (cachedUserJson != null && cachedUserJson.isNotEmpty) {
          final Map<String, dynamic> data = jsonDecode(cachedUserJson) as Map<String, dynamic>;
          return UserModel.fromJson(data);
        }
        rethrow;
      }
    } catch (e) {
      if (e is Failure) rethrow;
      throw AuthFailure(message: 'Erro ao verificar sessão do usuário: $e');
    }
  }

  @override
  Future<void> logout() async {
    try {
      // 1. Tenta notificar o backend para revogação da sessão
      try {
        await _remoteDataSource.logout();
      } catch (_) {
        // Ignora eventuais falhas na rede durante logout para sempre limpar dados locais
      }

      // 2. Desconecta da conta Google local
      try {
        await _googleSignIn.signOut();
      } catch (_) {
        // Ignora erros no sign out do Google
      }

      // 3. Expurga credenciais e tokens do Android Keystore / iOS Keychain
      await _secureStorageService.delete(key: SecureStorageService.accessTokenKey);
      await _secureStorageService.delete(key: SecureStorageService.userCacheKey);
    } catch (e) {
      if (e is Failure) rethrow;
      throw StorageFailure(message: 'Falha ao encerrar sessão localmente: $e');
    }
  }
}
