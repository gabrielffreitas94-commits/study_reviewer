import 'package:equatable/equatable.dart';
import 'package:flutter/material.dart';

/// Estado imutável para a tela de configurações do aplicativo.
class SettingsState extends Equatable {
  final ThemeMode themeMode;
  final bool isDeletingAccount;
  final bool isAccountDeleted;
  final String? errorMessage;

  const SettingsState({
    this.themeMode = ThemeMode.system,
    this.isDeletingAccount = false,
    this.isAccountDeleted = false,
    this.errorMessage,
  });

  bool get isDarkMode => themeMode == ThemeMode.dark;

  SettingsState copyWith({
    ThemeMode? themeMode,
    bool? isDeletingAccount,
    bool? isAccountDeleted,
    String? errorMessage,
    bool clearError = false,
  }) {
    return SettingsState(
      themeMode: themeMode ?? this.themeMode,
      isDeletingAccount: isDeletingAccount ?? this.isDeletingAccount,
      isAccountDeleted: isAccountDeleted ?? this.isAccountDeleted,
      errorMessage: clearError ? null : (errorMessage ?? this.errorMessage),
    );
  }

  @override
  List<Object?> get props => [
        themeMode,
        isDeletingAccount,
        isAccountDeleted,
        errorMessage,
      ];
}
