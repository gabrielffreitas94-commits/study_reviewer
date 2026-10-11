import 'package:flutter_bloc/flutter_bloc.dart';
import 'package:study_reviewer_mobile/core/errors/failures.dart';
import 'package:study_reviewer_mobile/core/usecases/usecase.dart';
import 'package:study_reviewer_mobile/features/auth/domain/usecases/get_current_user_usecase.dart';
import 'package:study_reviewer_mobile/features/auth/domain/usecases/login_with_google_usecase.dart';
import 'package:study_reviewer_mobile/features/auth/domain/usecases/logout_usecase.dart';
import 'package:study_reviewer_mobile/features/auth/presentation/cubit/auth_state.dart';

/// Cubit responsável por gerenciar e emitir os estados de autenticação do aplicativo.
class AuthCubit extends Cubit<AuthState> {
  final LoginWithGoogleUseCase _loginWithGoogleUseCase;
  final GetCurrentUserUseCase _getCurrentUserUseCase;
  final LogoutUseCase _logoutUseCase;

  AuthCubit({
    required LoginWithGoogleUseCase loginWithGoogleUseCase,
    required GetCurrentUserUseCase getCurrentUserUseCase,
    required LogoutUseCase logoutUseCase,
  })  : _loginWithGoogleUseCase = loginWithGoogleUseCase,
        _getCurrentUserUseCase = getCurrentUserUseCase,
        _logoutUseCase = logoutUseCase,
        super(const AuthInitial());

  /// Verifica o status da sessão persistida na inicialização do app.
  Future<void> checkAuthStatus() async {
    emit(const AuthLoading());
    try {
      final user = await _getCurrentUserUseCase(const NoParams());
      if (user != null) {
        emit(Authenticated(user));
      } else {
        emit(const Unauthenticated());
      }
    } catch (e) {
      emit(const Unauthenticated());
    }
  }

  /// Inicia o fluxo de autenticação com a conta Google.
  Future<void> loginWithGoogle() async {
    emit(const AuthLoading());
    try {
      final user = await _loginWithGoogleUseCase(const NoParams());
      emit(Authenticated(user));
    } on Failure catch (failure) {
      emit(AuthError(failure.message));
      emit(const Unauthenticated());
    } catch (e) {
      emit(AuthError('Falha ao autenticar com o Google: $e'));
      emit(const Unauthenticated());
    }
  }

  /// Realiza o logout do usuário e encerra a sessão local e remota.
  Future<void> logout() async {
    emit(const AuthLoading());
    try {
      await _logoutUseCase(const NoParams());
    } catch (_) {
      // Ignora erro no logout para sempre finalizar como Unauthenticated
    }
    emit(const Unauthenticated());
  }

  /// Método utilitário acionado em caso de 401 interceptado pelo Dio.
  void forceUnauthenticated() {
    emit(const Unauthenticated());
  }
}
