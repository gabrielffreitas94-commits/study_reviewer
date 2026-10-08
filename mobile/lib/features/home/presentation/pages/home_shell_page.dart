import 'package:flutter/material.dart';
import 'package:flutter_bloc/flutter_bloc.dart';
import 'package:study_reviewer_mobile/core/theme/app_theme.dart';
import 'package:study_reviewer_mobile/features/auth/domain/entities/user_entity.dart';
import 'package:study_reviewer_mobile/features/auth/presentation/cubit/auth_cubit.dart';
import 'package:study_reviewer_mobile/features/flashcards/presentation/cubit/flashcard_cubit.dart';
import 'package:study_reviewer_mobile/features/flashcards/presentation/pages/flashcard_study_page.dart';
import 'package:study_reviewer_mobile/features/performance/presentation/cubit/performance_cubit.dart';
import 'package:study_reviewer_mobile/features/performance/presentation/pages/performance_page.dart';
import 'package:study_reviewer_mobile/features/settings/presentation/cubit/settings_cubit.dart';
import 'package:study_reviewer_mobile/features/settings/presentation/pages/settings_page.dart';
import 'package:study_reviewer_mobile/features/srs_questions/presentation/cubit/question_srs_cubit.dart';
import 'package:study_reviewer_mobile/features/srs_questions/presentation/pages/question_srs_page.dart';
import 'package:study_reviewer_mobile/injection_container.dart' as di;


/// Shell principal da aplicação após login, provendo navegação entre 4 abas principais
/// com BottomNavigationBar acessível, touch targets de 48dp e semântica para leitores de tela.
class HomeShellPage extends StatefulWidget {
  final UserEntity user;

  const HomeShellPage({
    super.key,
    required this.user,
  });

  @override
  State<HomeShellPage> createState() => _HomeShellPageState();
}

class _HomeShellPageState extends State<HomeShellPage> {
  int _currentIndex = 0;

  final List<String> _titles = const [
    'Flashcards',
    'Perguntas SRS',
    'Desempenho',
    'Configurações',
  ];

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final isDark = theme.brightness == Brightness.dark;

    final tabs = [
      _buildFlashcardsTab(context, isDark),
      _buildSrsQuestionsTab(context, isDark),
      BlocProvider<PerformanceCubit>(
        create: (_) => di.sl<PerformanceCubit>(),
        child: const PerformancePage(),
      ),
      BlocProvider<SettingsCubit>(
        create: (_) => di.sl<SettingsCubit>(),
        child: SettingsPage(
          onAccountDeleted: () {
            context.read<AuthCubit>().checkAuthStatus();
          },
        ),
      ),
    ];


    return Scaffold(
      appBar: AppBar(
        title: Text(
          _titles[_currentIndex],
          style: const TextStyle(fontWeight: FontWeight.bold),
        ),
        actions: [
          Padding(
            padding: const EdgeInsets.only(right: 16.0),
            child: Semantics(
              label: 'Foto de perfil do usuário ${widget.user.name}',
              child: CircleAvatar(
                radius: 18,
                backgroundColor: AppTheme.indigo500,
                backgroundImage: widget.user.avatarUrl != null
                    ? NetworkImage(widget.user.avatarUrl!)
                    : null,
                child: widget.user.avatarUrl == null
                    ? Text(
                        widget.user.name.isNotEmpty
                            ? widget.user.name[0].toUpperCase()
                            : 'U',
                        style: const TextStyle(
                          color: Colors.white,
                          fontWeight: FontWeight.bold,
                        ),
                      )
                    : null,
              ),
            ),
          ),
        ],
      ),
      body: SafeArea(
        child: IndexedStack(
          index: _currentIndex,
          children: tabs,
        ),
      ),
      bottomNavigationBar: Semantics(
        label: 'Barra de navegação inferior',
        child: BottomNavigationBar(
          currentIndex: _currentIndex,
          onTap: (index) => setState(() => _currentIndex = index),
          items: const [
            BottomNavigationBarItem(
              icon: Icon(Icons.style_outlined),
              activeIcon: Icon(Icons.style),
              label: 'Flashcards',
              tooltip: 'Aba de Flashcards',
            ),
            BottomNavigationBarItem(
              icon: Icon(Icons.quiz_outlined),
              activeIcon: Icon(Icons.quiz),
              label: 'Perguntas SRS',
              tooltip: 'Aba de Perguntas de Repetição Espaçada',
            ),
            BottomNavigationBarItem(
              icon: Icon(Icons.insights_outlined),
              activeIcon: Icon(Icons.bar_chart),
              label: 'Desempenho',
              tooltip: 'Aba de Desempenho e Métricas',
            ),
            BottomNavigationBarItem(
              icon: Icon(Icons.settings_outlined),
              activeIcon: Icon(Icons.settings),
              label: 'Configurações',
              tooltip: 'Aba de Configurações da Conta',
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildFlashcardsTab(BuildContext context, bool isDark) {
    return SingleChildScrollView(
      padding: const EdgeInsets.all(20),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          _buildSummaryCard(
            title: 'Decks de Flashcards',
            subtitle: 'Revisão ativa baseada no algoritmo SuperMemo 2 (SM-2)',
            icon: Icons.style,
            color: AppTheme.indigo600,
            isDark: isDark,
          ),
          const SizedBox(height: 20),
          Text(
            'Baralhos Disponíveis',
            style: TextStyle(
              fontSize: 18,
              fontWeight: FontWeight.bold,
              color: isDark ? AppTheme.slate100 : AppTheme.slate900,
            ),
          ),
          const SizedBox(height: 12),
          _buildDeckItem(
            context,
            title: 'Clean Architecture & Flutter',
            cardsCount: 42,
            dueCount: 8,
            isDark: isDark,
          ),
          _buildDeckItem(
            context,
            title: 'Engenharia de Software & AWS',
            cardsCount: 65,
            dueCount: 15,
            isDark: isDark,
          ),
        ],
      ),
    );
  }

  Widget _buildSrsQuestionsTab(BuildContext context, bool isDark) {
    return SingleChildScrollView(
      padding: const EdgeInsets.all(20),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          _buildSummaryCard(
            title: 'Fila de Repetição Espaçada',
            subtitle: 'Itens com vencimento de revisão para hoje',
            icon: Icons.calendar_today_rounded,
            color: AppTheme.emerald500,
            isDark: isDark,
          ),
          const SizedBox(height: 24),
          Center(
            child: Padding(
              padding: const EdgeInsets.symmetric(vertical: 32),
              child: Column(
                children: [
                  const Icon(
                    Icons.check_circle_outline_rounded,
                    size: 64,
                    color: AppTheme.emerald500,
                  ),
                  const SizedBox(height: 16),
                  Text(
                    'Questões pendentes de revisão hoje',
                    style: TextStyle(
                      fontSize: 16,
                      fontWeight: FontWeight.w600,
                      color: isDark ? AppTheme.slate200 : AppTheme.slate800,
                    ),
                  ),
                  const SizedBox(height: 20),
                  ElevatedButton.icon(
                    onPressed: () {
                      Navigator.of(context).push(
                        MaterialPageRoute<void>(
                          builder: (_) => BlocProvider<QuestionSrsCubit>(
                            create: (_) => di.sl<QuestionSrsCubit>(),
                            child: const QuestionSrsPage(),
                          ),
                        ),
                      );
                    },
                    icon: const Icon(Icons.play_arrow_rounded),
                    label: const Text('Iniciar Sessão SRS'),
                    style: ElevatedButton.styleFrom(
                      minimumSize: AppTheme.minTouchTargetSize,
                      padding: const EdgeInsets.symmetric(
                        horizontal: 24,
                        vertical: 14,
                      ),
                    ),
                  ),
                ],
              ),
            ),
          ),
        ],
      ),
    );
  }


  Widget _buildSummaryCard({
    required String title,
    required String subtitle,
    required IconData icon,
    required Color color,
    required bool isDark,
  }) {
    return Container(
      padding: const EdgeInsets.all(18),
      decoration: BoxDecoration(
        color: isDark ? AppTheme.slate900 : Colors.white,
        borderRadius: BorderRadius.circular(14),
        border: Border.all(
          color: isDark ? AppTheme.slate800 : AppTheme.slate200,
        ),
      ),
      child: Row(
        children: [
          Container(
            padding: const EdgeInsets.all(12),
            decoration: BoxDecoration(
              color: color.withOpacity(0.15),
              borderRadius: BorderRadius.circular(12),
            ),
            child: Icon(icon, color: color, size: 28),
          ),
          const SizedBox(width: 16),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  title,
                  style: TextStyle(
                    fontSize: 16,
                    fontWeight: FontWeight.bold,
                    color: isDark ? AppTheme.slate100 : AppTheme.slate900,
                  ),
                ),
                const SizedBox(height: 4),
                Text(
                  subtitle,
                  style: TextStyle(
                    fontSize: 13,
                    color: isDark ? AppTheme.slate400 : AppTheme.slate600,
                  ),
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildDeckItem(
    BuildContext context, {
    required String title,
    required int cardsCount,
    required int dueCount,
    required bool isDark,
    String? topicId,
  }) {
    return InkWell(
      borderRadius: BorderRadius.circular(12),
      onTap: () {
        Navigator.of(context).push(
          MaterialPageRoute<void>(
            builder: (_) => BlocProvider<FlashcardCubit>(
              create: (_) => di.sl<FlashcardCubit>(),
              child: FlashcardStudyPage(
                topicId: topicId,
                topicTitle: title,
              ),
            ),
          ),
        );
      },
      child: Container(
        margin: const EdgeInsets.only(bottom: 12),
        padding: const EdgeInsets.all(16),
        decoration: BoxDecoration(
          color: isDark ? AppTheme.slate900 : Colors.white,
          borderRadius: BorderRadius.circular(12),
          border: Border.all(
            color: isDark ? AppTheme.slate800 : AppTheme.slate200,
          ),
        ),
        child: Row(
          children: [
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    title,
                    style: TextStyle(
                      fontSize: 15,
                      fontWeight: FontWeight.w600,
                      color: isDark ? AppTheme.slate100 : AppTheme.slate900,
                    ),
                  ),
                  const SizedBox(height: 4),
                  Text(
                    '$cardsCount cards totais • $dueCount para revisão',
                    style: TextStyle(
                      fontSize: 13,
                      color: isDark ? AppTheme.slate400 : AppTheme.slate600,
                    ),
                  ),
                ],
              ),
            ),
            const Icon(Icons.chevron_right_rounded, color: AppTheme.slate400),
          ],
        ),
      ),
    );
  }
}
