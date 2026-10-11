import 'package:flutter_test/flutter_test.dart';
import 'package:study_reviewer_mobile/features/auth/data/models/user_model.dart';
import 'package:study_reviewer_mobile/features/auth/domain/entities/user_entity.dart';

void main() {
  group('UserModel', () {
    final tUserModel = UserModel(
      id: 1,
      email: 'test@studyreviewer.com',
      name: 'Test User',
      avatarUrl: 'https://example.com/avatar.png',
      createdAt: DateTime.parse('2026-10-07T12:00:00Z'),
    );

    test('deve ser uma subclasse de UserEntity', () {
      expect(tUserModel, isA<UserEntity>());
    });

    test('deve converter corretamente de JSON para UserModel', () {
      final jsonMap = {
        'id': 1,
        'email': 'test@studyreviewer.com',
        'name': 'Test User',
        'avatar_url': 'https://example.com/avatar.png',
        'created_at': '2026-10-07T12:00:00.000Z',
      };

      final result = UserModel.fromJson(jsonMap);

      expect(result.id, 1);
      expect(result.email, 'test@studyreviewer.com');
      expect(result.name, 'Test User');
      expect(result.avatarUrl, 'https://example.com/avatar.png');
      expect(result.createdAt, DateTime.parse('2026-10-07T12:00:00.000Z'));
    });

    test('deve serializar corretamente de UserModel para JSON', () {
      final jsonMap = tUserModel.toJson();

      expect(jsonMap['id'], 1);
      expect(jsonMap['email'], 'test@studyreviewer.com');
      expect(jsonMap['name'], 'Test User');
      expect(jsonMap['avatar_url'], 'https://example.com/avatar.png');
      expect(jsonMap['created_at'], isNotNull);
    });

    test('deve criar UserModel a partir de UserEntity', () {
      const entity = UserEntity(
        id: 2,
        email: 'user2@example.com',
        name: 'User 2',
        avatarUrl: null,
      );

      final model = UserModel.fromEntity(entity);

      expect(model.id, 2);
      expect(model.email, 'user2@example.com');
      expect(model.name, 'User 2');
      expect(model.avatarUrl, isNull);
    });
  });

  group('AuthResponseModel', () {
    test('deve desserializar AuthResponseModel com token e user aninhado', () {
      final jsonMap = {
        'access_token': 'jwt_secret_token_123',
        'token_type': 'bearer',
        'user': {
          'id': 10,
          'email': 'bearer@studyreviewer.com',
          'name': 'Bearer User',
          'avatar_url': null,
          'created_at': null,
        },
      };

      final response = AuthResponseModel.fromJson(jsonMap);

      expect(response.accessToken, 'jwt_secret_token_123');
      expect(response.tokenType, 'bearer');
      expect(response.user.id, 10);
      expect(response.user.email, 'bearer@studyreviewer.com');
    });
  });
}
