import 'package:study_reviewer_mobile/features/auth/domain/entities/user_entity.dart';

/// Contrato abstrato da camada de Domínio para autenticação e gestão de sessão.
abstract class AuthRepository {
  /// Executa fluxo OAuth2 com Google Sign-In, envia token ao backend e persiste credenciais.
  Future<UserEntity> loginWithGoogle();

  /// Recupera o usuário autenticado da sessão atual ou verifica validade no backend.
  Future<UserEntity?> getCurrentUser();

  /// Realiza o logout na API, desconecta da conta Google e expurga chaves do Keystore/Keychain.
  Future<void> logout();
}
