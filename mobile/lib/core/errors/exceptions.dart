class ServerException implements Exception {
  final String message;
  final int? statusCode;

  const ServerException({
    this.message = 'Erro no servidor',
    this.statusCode,
  });

  @override
  String toString() => 'ServerException: $message (code: $statusCode)';
}

class CacheException implements Exception {
  final String message;

  const CacheException({this.message = 'Erro ao acessar cache local'});

  @override
  String toString() => 'CacheException: $message';
}

class NetworkException implements Exception {
  final String message;

  const NetworkException({this.message = 'Falha de conexão com a rede'});

  @override
  String toString() => 'NetworkException: $message';
}

class AuthException implements Exception {
  final String message;
  final int? statusCode;

  const AuthException({
    this.message = 'Falha de autenticação',
    this.statusCode = 401,
  });

  @override
  String toString() => 'AuthException: $message (code: $statusCode)';
}

