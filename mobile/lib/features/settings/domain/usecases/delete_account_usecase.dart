import 'package:study_reviewer_mobile/core/usecases/usecase.dart';
import 'package:study_reviewer_mobile/features/settings/domain/repositories/settings_repository.dart';

/// Caso de uso para excluir permanentemente a conta do usuário conforme a LGPD e Google Play.
class DeleteAccountUseCase implements UseCase<void, NoParams> {
  final SettingsRepository repository;

  const DeleteAccountUseCase({required this.repository});

  @override
  Future<void> call(NoParams params) async {
    return repository.deleteAccount();
  }
}
