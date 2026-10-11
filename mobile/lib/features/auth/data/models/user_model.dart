import 'package:study_reviewer_mobile/features/auth/domain/entities/user_entity.dart';

/// Modelo de dados de usuário correspondente ao DTO `UserDTO` retornado pela API FastAPI.
class UserModel extends UserEntity {
  final DateTime? createdAt;

  const UserModel({
    required super.id,
    required super.email,
    required super.name,
    super.avatarUrl,
    this.createdAt,
  });

  /// Desserialização resiliente a partir de Map JSON retornado pelo backend.
  factory UserModel.fromJson(Map<String, dynamic> json) {
    final rawId = json['id'];
    final int parsedId = (rawId is int)
        ? rawId
        : int.tryParse(rawId?.toString() ?? '') ?? 0;

    DateTime? parsedCreatedAt;
    if (json['created_at'] != null) {
      parsedCreatedAt = DateTime.tryParse(json['created_at'].toString());
    }

    return UserModel(
      id: parsedId,
      email: json['email'] as String? ?? '',
      name: json['name'] as String? ?? '',
      avatarUrl: json['avatar_url'] as String?,
      createdAt: parsedCreatedAt,
    );
  }

  /// Converte a instância para JSON no formato padrão dos DTOs do backend.
  Map<String, dynamic> toJson() {
    return {
      'id': id,
      'email': email,
      'name': name,
      'avatar_url': avatarUrl,
      'created_at': createdAt?.toIso8601String(),
    };
  }

  /// Construtor de cópia a partir de uma entidade de domínio genérica.
  factory UserModel.fromEntity(UserEntity entity) {
    return UserModel(
      id: entity.id,
      email: entity.email,
      name: entity.name,
      avatarUrl: entity.avatarUrl,
    );
  }
}

/// Modelo para encapsular a resposta de autenticação com token JWT (`AuthTokenResponse`).
class AuthResponseModel {
  final String accessToken;
  final String tokenType;
  final UserModel user;

  const AuthResponseModel({
    required this.accessToken,
    required this.tokenType,
    required this.user,
  });

  factory AuthResponseModel.fromJson(Map<String, dynamic> json) {
    return AuthResponseModel(
      accessToken: json['access_token'] as String? ?? '',
      tokenType: json['token_type'] as String? ?? 'bearer',
      user: UserModel.fromJson(
        json['user'] as Map<String, dynamic>? ?? <String, dynamic>{},
      ),
    );
  }
}
