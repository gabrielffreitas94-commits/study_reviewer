import 'package:flutter/material.dart';
import 'package:flutter_bloc/flutter_bloc.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:study_reviewer_mobile/core/errors/failures.dart';
import 'package:study_reviewer_mobile/core/storage/secure_storage_service.dart';
import 'package:study_reviewer_mobile/core/usecases/usecase.dart';
import 'package:study_reviewer_mobile/features/settings/domain/usecases/delete_account_usecase.dart';
import 'package:study_reviewer_mobile/features/settings/presentation/cubit/settings_state.dart';

/// Cubit responsável por configurações visuais de tema e operações de conta (LGPD).
class SettingsCubit extends Cubit<SettingsState> {
  final DeleteAccountUseCase deleteAccountUseCase;
  final SecureStorageService secureStorageService;
  final SharedPreferences? sharedPreferences;

  static const String themePreferenceKey = 'user_theme_mode_preference';

  SettingsCubit({
    required this.deleteAccountUseCase,
    required this.secureStorageService,
    this.sharedPreferences,
  }) : super(const SettingsState()) {
    _loadInitialTheme();
  }

  /// Carrega o tema previamente salvo nas preferências locais.
  Future<void> _loadInitialTheme() async {
    try {
      final prefs = sharedPreferences ?? await SharedPreferences.getInstance();
      final savedThemeString = prefs.getString(themePreferenceKey);

      if (savedThemeString != null) {
        ThemeMode mode;
        switch (savedThemeString) {
          case 'dark':
            mode = ThemeMode.dark;
            break;
          case 'light':
            mode = ThemeMode.light;
            break;
          case 'system':
          default:
            mode = ThemeMode.system;
            break;
        }
        emit(state.copyWith(themeMode: mode));
      }
    } catch (_) {
      // Ignora erro de leitura inicial de preferências
    }
  }

  /// Altera o modo do tema e persiste a escolha no SharedPreferences.
  Future<void> setThemeMode(ThemeMode mode) async {
    emit(state.copyWith(themeMode: mode));
    try {
      final prefs = sharedPreferences ?? await SharedPreferences.getInstance();
      String modeStr;
      switch (mode) {
        case ThemeMode.dark:
          modeStr = 'dark';
          break;
        case ThemeMode.light:
          modeStr = 'light';
          break;
        case ThemeMode.system:
          modeStr = 'system';
          break;
      }
      await prefs.setString(themePreferenceKey, modeStr);
    } catch (_) {
      // Falhas ao persistir preferência não devem travar a UI
    }
  }

  /// Alterna entre Dark e Light mode.
  Future<void> toggleTheme() async {
    final nextMode =
        state.themeMode == ThemeMode.dark ? ThemeMode.light : ThemeMode.dark;
    await setThemeMode(nextMode);
  }

  /// Executa o fluxo definitivo de exclusão de conta conforme LGPD e Google Play.
  ///
  /// Invoca a rota DELETE /api/v1/auth/account e purga todas as credenciais do Keystore.
  Future<void> deleteAccount() async {
    emit(state.copyWith(
      isDeletingAccount: true,
      clearError: true,
    ));

    try {
      // 1. Invoca o endpoint remoto de deleção atômica no backend
      await deleteAccountUseCase(const NoParams());

      // 2. Purga o armazenamento seguro local (Keystore / Keychain)
      await secureStorageService.deleteAll();

      // 3. Limpa preferências locais do usuário
      try {
        final prefs =
            sharedPreferences ?? await SharedPreferences.getInstance();
        await prefs.clear();
      } catch (_) {
        // Ignora erro de limpeza de prefs
      }

      emit(state.copyWith(
        isDeletingAccount: false,
        isAccountDeleted: true,
      ));
    } on Failure catch (failure) {
      emit(state.copyWith(
        isDeletingAccount: false,
        errorMessage: failure.message,
      ));
    } catch (e) {
      emit(state.copyWith(
        isDeletingAccount: false,
        errorMessage: 'Não foi possível excluir sua conta: $e',
      ));
    }
  }
}
