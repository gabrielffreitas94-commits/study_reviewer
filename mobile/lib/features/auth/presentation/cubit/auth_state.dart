import 'package:equatable/equatable.dart';
import 'package:study_reviewer_mobile/features/auth/domain/entities/user_entity.dart';

/// Estados possíveis do ciclo de vida da autenticação.
abstract class AuthState extends Equatable {
  const AuthState();

  @override
  List<Object?> get props => [];
}

/// Estado inicial antes de verificar persistência da sessão.
class AuthInitial extends AuthState {
  const AuthInitial();
}

/// Estado exibido durante requisições de login, validação ou logout.
class AuthLoading extends AuthState {
  const AuthLoading();
}

/// Estado em que o usuário está autenticado com sessão válida.
class Authenticated extends AuthState {
  final UserEntity user;

  const Authenticated(this.user);

  @override
  List<Object?> get props => [user];
}

/// Estado em que o usuário não está autenticado ou a sessão foi encerrada.
class Unauthenticated extends AuthState {
  const Unauthenticated();
}

/// Estado de erro contendo mensagem amigável para exibição ao usuário.
class AuthError extends AuthState {
  final String message;

  const AuthError(this.message);

  @override
  List<Object?> get props => [message];
}
