import 'package:flutter/material.dart';
import 'package:flutter_bloc/flutter_bloc.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:mocktail/mocktail.dart';
import 'package:study_reviewer_mobile/features/performance/domain/entities/user_statistics_entity.dart';
import 'package:study_reviewer_mobile/features/performance/presentation/cubit/performance_cubit.dart';
import 'package:study_reviewer_mobile/features/performance/presentation/cubit/performance_state.dart';
import 'package:study_reviewer_mobile/features/performance/presentation/pages/performance_page.dart';

class MockPerformanceCubit extends Mock implements PerformanceCubit {}

void main() {
  late MockPerformanceCubit mockCubit;

  setUp(() {
    mockCubit = MockPerformanceCubit();
    when(() => mockCubit.loadStatistics()).thenAnswer((_) async {});
  });

  Widget buildTestableWidget() {
    return MaterialApp(
      home: BlocProvider<PerformanceCubit>.value(
        value: mockCubit,
        child: const PerformancePage(),
      ),
    );
  }

  const tStatistics = UserStatisticsEntity(
    retentionRate: 91.5,
    matureQuestionsCount: 45,
    totalReviewsCount: 220,
    activeDaysCount: 18,
    srsDistribution: <int, int>{
      0: 4,
      1: 8,
      2: 12,
      3: 20,
      4: 30,
      5: 15,
      6: 5,
    },
  );

  testWidgets('exibe cards de KPIs e pirâmide SRS quando carregado',
      (tester) async {
    when(() => mockCubit.state).thenReturn(const PerformanceLoaded(tStatistics));
    when(() => mockCubit.stream).thenAnswer(
      (_) => Stream<PerformanceState>.value(const PerformanceLoaded(tStatistics)),
    );

    await tester.pumpWidget(buildTestableWidget());
    await tester.pumpAndSettle();

    expect(find.text('Hub de Desempenho'), findsOneWidget);
    expect(find.text('Métricas Gerais'), findsOneWidget);
    expect(find.text('91.5%'), findsOneWidget);
    expect(find.text('45'), findsOneWidget);
    expect(find.text('220'), findsOneWidget);
    expect(find.text('18'), findsOneWidget);
    expect(find.text('Pirâmide SRS (Níveis 0 a 6)'), findsOneWidget);
    expect(find.text('94 itens totais'), findsOneWidget);
  });

  testWidgets('exibe mensagem de erro quando cubit emitir falha', (tester) async {
    when(() => mockCubit.state)
        .thenReturn(const PerformanceError('Falha de rede'));
    when(() => mockCubit.stream).thenAnswer(
      (_) => Stream<PerformanceState>.value(const PerformanceError('Falha de rede')),
    );

    await tester.pumpWidget(buildTestableWidget());
    await tester.pumpAndSettle();

    expect(find.text('Erro ao carregar métricas'), findsOneWidget);
    expect(find.text('Falha de rede'), findsOneWidget);
    expect(find.text('Tentar Novamente'), findsOneWidget);
  });
}
