import 'package:study_reviewer_mobile/core/usecases/usecase.dart';
import 'package:study_reviewer_mobile/features/auth/domain/entities/user_entity.dart';
import 'package:study_reviewer_mobile/features/auth/domain/repositories/auth_repository.dart';

/// Caso de uso para autenticação via Google OAuth2.
class LoginWithGoogleUseCase implements UseCase<UserEntity, NoParams> {
  final AuthRepository _repository;

  LoginWithGoogleUseCase(this._repository);

  @override
  Future<UserEntity> call(NoParams params) async {
    return await _repository.loginWithGoogle();
  }
}
