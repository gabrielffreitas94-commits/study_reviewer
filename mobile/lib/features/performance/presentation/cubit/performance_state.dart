import 'package:equatable/equatable.dart';
import 'package:study_reviewer_mobile/features/performance/domain/entities/user_statistics_entity.dart';

abstract class PerformanceState extends Equatable {
  const PerformanceState();

  @override
  List<Object?> get props => [];
}

class PerformanceInitial extends PerformanceState {
  const PerformanceInitial();
}

class PerformanceLoading extends PerformanceState {
  const PerformanceLoading();
}

class PerformanceLoaded extends PerformanceState {
  final UserStatisticsEntity statistics;

  const PerformanceLoaded(this.statistics);

  @override
  List<Object?> get props => [statistics];
}

class PerformanceError extends PerformanceState {
  final String message;

  const PerformanceError(this.message);

  @override
  List<Object?> get props => [message];
}
