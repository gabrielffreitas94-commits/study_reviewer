import 'package:flutter_bloc/flutter_bloc.dart';
import 'package:study_reviewer_mobile/core/errors/failures.dart';
import 'package:study_reviewer_mobile/core/usecases/usecase.dart';
import 'package:study_reviewer_mobile/features/performance/domain/usecases/get_user_statistics_usecase.dart';
import 'package:study_reviewer_mobile/features/performance/presentation/cubit/performance_state.dart';

/// Cubit responsável por orquestrar o carregamento das métricas e dados de performance.
class PerformanceCubit extends Cubit<PerformanceState> {
  final GetUserStatisticsUseCase getUserStatisticsUseCase;

  PerformanceCubit({required this.getUserStatisticsUseCase})
      : super(const PerformanceInitial());

  Future<void> loadStatistics() async {
    emit(const PerformanceLoading());
    try {
      final statistics = await getUserStatisticsUseCase(const NoParams());
      emit(PerformanceLoaded(statistics));
    } on Failure catch (failure) {
      emit(PerformanceError(failure.message));
    } catch (e) {
      emit(PerformanceError('Erro ao carregar estatísticas: $e'));
    }
  }
}
