import 'package:study_reviewer_mobile/core/usecases/usecase.dart';
import 'package:study_reviewer_mobile/features/auth/domain/entities/user_entity.dart';
import 'package:study_reviewer_mobile/features/auth/domain/repositories/auth_repository.dart';

/// Caso de uso para verificar o estado da sessão atual e obter os dados do usuário logado.
class GetCurrentUserUseCase implements UseCase<UserEntity?, NoParams> {
  final AuthRepository _repository;

  GetCurrentUserUseCase(this._repository);

  @override
  Future<UserEntity?> call(NoParams params) async {
    return await _repository.getCurrentUser();
  }
}
