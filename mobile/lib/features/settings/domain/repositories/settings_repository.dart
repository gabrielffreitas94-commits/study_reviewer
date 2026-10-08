/// Contrato abstrato do repositório para configurações e operações de conta (LGPD).
abstract class SettingsRepository {
  /// Invoca a exclusão definitiva da conta e dados pessoais do usuário (LGPD Art. 18).
  Future<void> deleteAccount();
}
