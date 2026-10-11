import 'dart:developer' as developer;
import 'package:flutter_secure_storage/flutter_secure_storage.dart';
import 'package:study_reviewer_mobile/core/errors/failures.dart';

/// Serviço responsável pelo armazenamento seguro de credenciais, tokens e chaves
/// utilizando Android Keystore (via EncryptedSharedPreferences) e iOS Keychain.
class SecureStorageService {
  final FlutterSecureStorage _storage;

  static const String accessTokenKey = 'auth_access_token';
  static const String userCacheKey = 'auth_user_cache';

  SecureStorageService({FlutterSecureStorage? storage})
      : _storage = storage ??
            const FlutterSecureStorage(
              aOptions: AndroidOptions(
                encryptedSharedPreferences: true,
              ),
              iOptions: IOSOptions(
                accessibility: KeychainAccessibility.first_unlock,
              ),
            );

  /// Grava um par chave-valor de forma criptografada no Keystore/Keychain.
  Future<void> write({required String key, required String value}) async {
    try {
      await _storage.write(key: key, value: value);
    } catch (e, stackTrace) {
      developer.log(
        'Falha ao gravar no armazenamento seguro',
        name: 'SecureStorageService',
        error: e,
        stackTrace: stackTrace,
      );
      throw StorageFailure(
        message: 'Não foi possível gravar no armazenamento seguro: $e',
      );
    }
  }

  /// Recupera o valor seguro associado à chave. Retorna null se não existir.
  Future<String?> read({required String key}) async {
    try {
      return await _storage.read(key: key);
    } catch (e, stackTrace) {
      developer.log(
        'Falha ao ler do armazenamento seguro',
        name: 'SecureStorageService',
        error: e,
        stackTrace: stackTrace,
      );
      throw StorageFailure(
        message: 'Não foi possível ler do armazenamento seguro: $e',
      );
    }
  }

  /// Remove a chave especificada do armazenamento seguro.
  Future<void> delete({required String key}) async {
    try {
      await _storage.delete(key: key);
    } catch (e, stackTrace) {
      developer.log(
        'Falha ao remover item do armazenamento seguro',
        name: 'SecureStorageService',
        error: e,
        stackTrace: stackTrace,
      );
      throw StorageFailure(
        message: 'Não foi possível remover item do armazenamento seguro: $e',
      );
    }
  }

  /// Limpa integralmente todas as chaves e dados sensíveis persistidos.
  Future<void> deleteAll() async {
    try {
      await _storage.deleteAll();
    } catch (e, stackTrace) {
      developer.log(
        'Falha ao limpar armazenamento seguro',
        name: 'SecureStorageService',
        error: e,
        stackTrace: stackTrace,
      );
      throw StorageFailure(
        message: 'Não foi possível limpar o armazenamento seguro: $e',
      );
    }
  }

  /// Verifica se uma determinada chave existe no armazenamento seguro.
  Future<bool> containsKey({required String key}) async {
    try {
      return await _storage.containsKey(key: key);
    } catch (e, stackTrace) {
      developer.log(
        'Falha ao verificar chave no armazenamento seguro',
        name: 'SecureStorageService',
        error: e,
        stackTrace: stackTrace,
      );
      return false;
    }
  }
}
