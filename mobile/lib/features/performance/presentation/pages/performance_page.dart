import 'dart:math' as math;
import 'package:flutter/material.dart';
import 'package:flutter_bloc/flutter_bloc.dart';
import 'package:study_reviewer_mobile/features/performance/domain/entities/user_statistics_entity.dart';
import 'package:study_reviewer_mobile/features/performance/presentation/cubit/performance_cubit.dart';
import 'package:study_reviewer_mobile/features/performance/presentation/cubit/performance_state.dart';

/// Tela do Hub de Desempenho com KPIs consolidados, reserva de layout e pirâmide SRS.
class PerformancePage extends StatefulWidget {
  const PerformancePage({super.key});

  @override
  State<PerformancePage> createState() => _PerformancePageState();
}

class _PerformancePageState extends State<PerformancePage> {
  @override
  void initState() {
    super.initState();
    context.read<PerformanceCubit>().loadStatistics();
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('Hub de Desempenho'),
        centerTitle: true,
      ),
      body: BlocConsumer<PerformanceCubit, PerformanceState>(
        listener: (context, state) {
          if (state is PerformanceError) {
            ScaffoldMessenger.of(context).showSnackBar(
              SnackBar(
                content: Text(state.message),
                backgroundColor: Colors.redAccent,
              ),
            );
          }
        },
        builder: (context, state) {
          if (state is PerformanceLoading) {
            return _buildSkeletonReservationView();
          }

          if (state is PerformanceError) {
            return Center(
              child: Padding(
                padding: const EdgeInsets.all(24.0),
                child: Column(
                  mainAxisAlignment: MainAxisAlignment.center,
                  children: [
                    const Icon(
                      Icons.error_outline,
                      size: 64.0,
                      color: Colors.redAccent,
                    ),
                    const SizedBox(height: 16.0),
                    Text(
                      'Erro ao carregar métricas',
                      style: Theme.of(context).textTheme.titleLarge,
                    ),
                    const SizedBox(height: 8.0),
                    Text(
                      state.message,
                      textAlign: TextAlign.center,
                      style: TextStyle(color: Colors.grey.shade600),
                    ),
                    const SizedBox(height: 20.0),
                    ElevatedButton(
                      onPressed: () =>
                          context.read<PerformanceCubit>().loadStatistics(),
                      child: const Text('Tentar Novamente'),
                    ),
                  ],
                ),
              ),
            );
          }

          if (state is PerformanceLoaded) {
            return RefreshIndicator(
              onRefresh: () =>
                  context.read<PerformanceCubit>().loadStatistics(),
              child: SingleChildScrollView(
                physics: const AlwaysScrollableScrollPhysics(),
                padding: const EdgeInsets.all(16.0),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.stretch,
                  children: [
                    // Seção 1: KPIs Principais (Reserva de Layout)
                    _buildKpiGrid(context, state.statistics),
                    const SizedBox(height: 20.0),

                    // Seção 2: Resumo de Retenção
                    _buildRetentionSummaryCard(context, state.statistics),
                    const SizedBox(height: 20.0),

                    // Seção 3: Visualização da Pirâmide SRS (Níveis 0 a 6)
                    _buildSrsPyramidCard(context, state.statistics),
                    const SizedBox(height: 24.0),
                  ],
                ),
              ),
            );
          }

          return const SizedBox.shrink();
        },
      ),
    );
  }

  /// Estrutura esqueleto com reserva de layout de mesma altura/largura para evitar Cumulative Layout Shift (CLS).
  Widget _buildSkeletonReservationView() {
    return SingleChildScrollView(
      padding: const EdgeInsets.all(16.0),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          // Grade 2x2 esqueleto (reserva exata de altura: ~220dp)
          SizedBox(
            height: 220.0,
            child: GridView.count(
              crossAxisCount: 2,
              crossAxisSpacing: 12.0,
              mainAxisSpacing: 12.0,
              childAspectRatio: 1.5,
              physics: const NeverScrollableScrollPhysics(),
              children: List.generate(
                4,
                (index) => Container(
                  decoration: BoxDecoration(
                    color: Colors.grey.withOpacity(0.12),
                    borderRadius: BorderRadius.circular(16.0),
                  ),
                ),
              ),
            ),
          ),
          const SizedBox(height: 20.0),

          // Card de Resumo de Retenção esqueleto (~140dp)
          Container(
            height: 140.0,
            decoration: BoxDecoration(
              color: Colors.grey.withOpacity(0.12),
              borderRadius: BorderRadius.circular(16.0),
            ),
          ),
          const SizedBox(height: 20.0),

          // Card Pirâmide SRS esqueleto (~340dp)
          Container(
            height: 340.0,
            decoration: BoxDecoration(
              color: Colors.grey.withOpacity(0.12),
              borderRadius: BorderRadius.circular(16.0),
            ),
          ),
        ],
      ),
    );
  }

  /// Seção 1: Grade de KPIs com 4 cartões com touch targets e alto contraste
  Widget _buildKpiGrid(BuildContext context, UserStatisticsEntity stats) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(
          'Métricas Gerais',
          style: Theme.of(context).textTheme.titleMedium?.copyWith(
                fontWeight: FontWeight.bold,
              ),
        ),
        const SizedBox(height: 12.0),
        GridView.count(
          crossAxisCount: 2,
          crossAxisSpacing: 12.0,
          mainAxisSpacing: 12.0,
          childAspectRatio: 1.45,
          shrinkWrap: true,
          physics: const NeverScrollableScrollPhysics(),
          children: [
            _buildKpiCard(
              context: context,
              title: 'Retenção Global',
              value: '${stats.retentionRate.toStringAsFixed(1)}%',
              icon: Icons.pie_chart_outline,
              color: const Color(0xFF0284C7),
            ),
            _buildKpiCard(
              context: context,
              title: 'Itens Maduros (N4+)',
              value: '${stats.matureQuestionsCount}',
              icon: Icons.workspace_premium_outlined,
              color: const Color(0xFF059669),
            ),
            _buildKpiCard(
              context: context,
              title: 'Total de Revisões',
              value: '${stats.totalReviewsCount}',
              icon: Icons.history_edu_outlined,
              color: const Color(0xFF7C3AED),
            ),
            _buildKpiCard(
              context: context,
              title: 'Dias Ativos',
              value: '${stats.activeDaysCount}',
              icon: Icons.calendar_month_outlined,
              color: const Color(0xFFEA580C),
            ),
          ],
        ),
      ],
    );
  }

  Widget _buildKpiCard({
    required BuildContext context,
    required String title,
    required String value,
    required IconData icon,
    required Color color,
  }) {
    final theme = Theme.of(context);
    return Card(
      elevation: 2.0,
      shape: RoundedRectangleBorder(
        borderRadius: BorderRadius.circular(16.0),
        side: BorderSide(color: color.withOpacity(0.3), width: 1.2),
      ),
      child: Padding(
        padding: const EdgeInsets.all(12.0),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          mainAxisAlignment: MainAxisAlignment.spaceBetween,
          children: [
            Row(
              mainAxisAlignment: MainAxisAlignment.spaceBetween,
              children: [
                Flexible(
                  child: Text(
                    title,
                    style: theme.textTheme.bodySmall?.copyWith(
                      fontWeight: FontWeight.w600,
                      color: Colors.grey.shade600,
                    ),
                    overflow: TextOverflow.ellipsis,
                  ),
                ),
                Icon(icon, color: color, size: 20.0),
              ],
            ),
            Text(
              value,
              style: theme.textTheme.headlineSmall?.copyWith(
                fontWeight: FontWeight.bold,
                color: color,
              ),
            ),
          ],
        ),
      ),
    );
  }

  /// Seção 2: Resumo Analítico de Retenção
  Widget _buildRetentionSummaryCard(
    BuildContext context,
    UserStatisticsEntity stats,
  ) {
    final theme = Theme.of(context);
    final rateRatio = (stats.retentionRate / 100.0).clamp(0.0, 1.0);

    return Card(
      elevation: 2.0,
      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(16.0)),
      child: Padding(
        padding: const EdgeInsets.all(16.0),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                const Icon(
                  Icons.trending_up,
                  color: Color(0xFF059669),
                  size: 22.0,
                ),
                const SizedBox(width: 8.0),
                Text(
                  'Saúde da Memória (SRS)',
                  style: theme.textTheme.titleMedium?.copyWith(
                    fontWeight: FontWeight.bold,
                  ),
                ),
              ],
            ),
            const SizedBox(height: 12.0),
            ClipRRect(
              borderRadius: BorderRadius.circular(8.0),
              child: LinearProgressIndicator(
                value: rateRatio,
                minHeight: 12.0,
                backgroundColor: Colors.grey.shade200,
                valueColor: AlwaysStoppedAnimation<Color>(
                  rateRatio >= 0.8
                      ? const Color(0xFF059669)
                      : (rateRatio >= 0.6
                          ? const Color(0xFFD97706)
                          : const Color(0xFFDC2626)),
                ),
              ),
            ),
            const SizedBox(height: 12.0),
            Text(
              '${stats.matureQuestionsCount} de ${stats.totalCardsInSrs} itens já alcançaram a fase madura (nível 4 ou superior), garantindo estabilidade de longo prazo no aprendizado.',
              style: theme.textTheme.bodyMedium?.copyWith(
                color: Colors.grey.shade700,
                height: 1.35,
              ),
            ),
          ],
        ),
      ),
    );
  }

  /// Seção 3: Pirâmide SRS com distribuição visual dos níveis 0 a 6
  Widget _buildSrsPyramidCard(
    BuildContext context,
    UserStatisticsEntity stats,
  ) {
    final theme = Theme.of(context);
    final total = stats.totalCardsInSrs;
    final maxInAnyLevel = stats.srsDistribution.values.isEmpty
        ? 1
        : stats.srsDistribution.values.reduce(math.max);
    final effectiveMax = maxInAnyLevel > 0 ? maxInAnyLevel : 1;

    final List<_SrsLevelConfig> levelConfigs = <_SrsLevelConfig>[
      const _SrsLevelConfig(
        level: 6,
        name: 'Mestre / Permanente',
        color: Color(0xFF059669),
      ),
      const _SrsLevelConfig(
        level: 5,
        name: 'Consolidado',
        color: Color(0xFF10B981),
      ),
      const _SrsLevelConfig(
        level: 4,
        name: 'Maduro Inicial',
        color: Color(0xFF0284C7),
      ),
      const _SrsLevelConfig(
        level: 3,
        name: 'Retenção Estável',
        color: Color(0xFF6366F1),
      ),
      const _SrsLevelConfig(
        level: 2,
        name: 'Fixação Intermediária',
        color: Color(0xFFD97706),
      ),
      const _SrsLevelConfig(
        level: 1,
        name: 'Aprendizagem Inicial',
        color: Color(0xFFEA580C),
      ),
      const _SrsLevelConfig(
        level: 0,
        name: 'Novo / Não memorizado',
        color: Color(0xFFDC2626),
      ),
    ];

    return Card(
      elevation: 2.0,
      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(16.0)),
      child: Padding(
        padding: const EdgeInsets.all(16.0),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              mainAxisAlignment: MainAxisAlignment.spaceBetween,
              children: [
                Text(
                  'Pirâmide SRS (Níveis 0 a 6)',
                  style: theme.textTheme.titleMedium?.copyWith(
                    fontWeight: FontWeight.bold,
                  ),
                ),
                Container(
                  padding: const EdgeInsets.symmetric(
                    horizontal: 8.0,
                    vertical: 2.0,
                  ),
                  decoration: BoxDecoration(
                    color: theme.colorScheme.primary.withOpacity(0.1),
                    borderRadius: BorderRadius.circular(8.0),
                  ),
                  child: Text(
                    '$total itens totais',
                    style: TextStyle(
                      fontSize: 12.0,
                      fontWeight: FontWeight.bold,
                      color: theme.colorScheme.primary,
                    ),
                  ),
                ),
              ],
            ),
            const SizedBox(height: 16.0),
            ...levelConfigs.map((config) {
              final count = stats.srsDistribution[config.level] ?? 0;
              final barFraction = (count / effectiveMax).clamp(0.0, 1.0);

              return Padding(
                padding: const EdgeInsets.symmetric(vertical: 6.0),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Row(
                      mainAxisAlignment: MainAxisAlignment.spaceBetween,
                      children: [
                        Row(
                          children: [
                            Container(
                              width: 10.0,
                              height: 10.0,
                              decoration: BoxDecoration(
                                color: config.color,
                                shape: BoxShape.circle,
                              ),
                            ),
                            const SizedBox(width: 8.0),
                            Text(
                              'Nível ${config.level} - ${config.name}',
                              style: theme.textTheme.bodySmall?.copyWith(
                                fontWeight: FontWeight.w600,
                              ),
                            ),
                          ],
                        ),
                        Text(
                          '$count',
                          style: TextStyle(
                            fontWeight: FontWeight.bold,
                            color: config.color,
                            fontSize: 13.0,
                          ),
                        ),
                      ],
                    ),
                    const SizedBox(height: 4.0),
                    ClipRRect(
                      borderRadius: BorderRadius.circular(4.0),
                      child: Stack(
                        children: [
                          Container(
                            height: 8.0,
                            color: Colors.grey.shade200,
                          ),
                          FractionallySizedBox(
                            widthFactor: barFraction,
                            child: Container(
                              height: 8.0,
                              color: config.color,
                            ),
                          ),
                        ],
                      ),
                    ),
                  ],
                ),
              );
            }),
          ],
        ),
      ),
    );
  }
}

class _SrsLevelConfig {
  final int level;
  final String name;
  final Color color;

  const _SrsLevelConfig({
    required this.level,
    required this.name,
    required this.color,
  });
}
