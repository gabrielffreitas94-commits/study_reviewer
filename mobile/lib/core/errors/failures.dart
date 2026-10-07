import 'package:equatable/equatable.dart';

abstract class Failure extends Equatable {
  final String message;

  const Failure(this.message);

  @override
  List<Object?> get props => [message];
}

class ServerFailure extends Failure {
  final int? statusCode;

  const ServerFailure({
    String message = 'Erro no servidor. Tente novamente mais tarde.',
    this.statusCode,
  }) : super(message);

  @override
  List<Object?> get props => [message, statusCode];
}

class CacheFailure extends Failure {
  const CacheFailure([String message = 'Falha ao recuperar dados salvos localmente.'])
      : super(message);
}

class NetworkFailure extends Failure {
  const NetworkFailure([String message = 'Sem conexão com a internet.'])
      : super(message);
}

class AuthFailure extends Failure {
  final int? statusCode;

  const AuthFailure({
    String message = 'Falha de autenticação.',
    this.statusCode = 401,
  }) : super(message);

  @override
  List<Object?> get props => [message, statusCode];
}

class StorageFailure extends Failure {
  final int? statusCode;

  const StorageFailure({
    required String message,
    this.statusCode,
  }) : super(message);

  @override
  List<Object?> get props => [message, statusCode];
}

