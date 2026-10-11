import 'package:study_reviewer_mobile/core/usecases/usecase.dart';
import 'package:study_reviewer_mobile/features/auth/domain/repositories/auth_repository.dart';

/// Caso de uso para revogação de tokens e encerramento de sessão do usuário.
class LogoutUseCase implements UseCase<void, NoParams> {
  final AuthRepository _repository;

  LogoutUseCase(this._repository);

  @override
  Future<void> call(NoParams params) async {
    return await _repository.logout();
  }
}
