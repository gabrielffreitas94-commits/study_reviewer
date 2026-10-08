import 'package:flutter/material.dart';
import 'package:flutter_bloc/flutter_bloc.dart';
import 'package:study_reviewer_mobile/features/srs_questions/domain/entities/review_result_entity.dart';
import 'package:study_reviewer_mobile/features/srs_questions/presentation/cubit/question_srs_cubit.dart';
import 'package:study_reviewer_mobile/features/srs_questions/presentation/cubit/question_srs_state.dart';
import 'package:study_reviewer_mobile/features/srs_questions/presentation/widgets/score_thumb_selector.dart';
import 'package:study_reviewer_mobile/features/srs_questions/presentation/widgets/srs_level_badge.dart';

/// Tela principal para o ciclo de autoavaliação e repetição espaçada (SRS) de perguntas abertas.
class QuestionSrsPage extends StatefulWidget {
  final String? subjectId;

  const QuestionSrsPage({
    super.key,
    this.subjectId,
  });

  @override
  State<QuestionSrsPage> createState() => _QuestionSrsPageState();
}

class _QuestionSrsPageState extends State<QuestionSrsPage> {
  @override
  void initState() {
    super.initState();
    context.read<QuestionSrsCubit>().loadDueQuestions(subjectId: widget.subjectId);
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('Perguntas Abertas SRS'),
        centerTitle: true,
        actions: [
          IconButton(
            icon: const Icon(Icons.refresh),
            tooltip: 'Recarregar fila',
            onPressed: () => context
                .read<QuestionSrsCubit>()
                .loadDueQuestions(subjectId: widget.subjectId),
          ),
        ],
      ),
      body: BlocConsumer<QuestionSrsCubit, QuestionSrsState>(
        listener: (context, state) {
          if (state is QuestionSrsError) {
            ScaffoldMessenger.of(context).showSnackBar(
              SnackBar(
                content: Text(state.message),
                backgroundColor: Colors.redAccent,
              ),
            );
          }
        },
        builder: (context, state) {
          if (state is QuestionSrsLoading) {
            return const Center(
              child: Column(
                mainAxisAlignment: MainAxisAlignment.center,
                children: [
                  CircularProgressIndicator(),
                  SizedBox(height: 16.0),
                  Text('Carregando perguntas para revisão...'),
                ],
              ),
            );
          }

          if (state is QuestionSrsEmpty) {
            return _buildEmptyView(context, state.message);
          }

          if (state is QuestionSrsError) {
            return _buildErrorView(context, state.message);
          }

          if (state is QuestionSrsLoaded) {
            if (state.isSessionCompleted) {
              return _buildCompletedView(context, state.totalQuestions);
            }
            return _buildLoadedView(context, state);
          }

          return const SizedBox.shrink();
        },
      ),
    );
  }

  Widget _buildEmptyView(BuildContext context, String message) {
    return Center(
      child: Padding(
        padding: const EdgeInsets.all(24.0),
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            const Icon(
              Icons.task_alt_outlined,
              size: 72.0,
              color: Color(0xFF059669),
            ),
            const SizedBox(height: 16.0),
            Text(
              'Tudo revisado por hoje!',
              style: Theme.of(context).textTheme.headlineSmall?.copyWith(
                    fontWeight: FontWeight.bold,
                  ),
              textAlign: TextAlign.center,
            ),
            const SizedBox(height: 12.0),
            Text(
              message,
              style: Theme.of(context).textTheme.bodyMedium?.copyWith(
                    color: Colors.grey.shade600,
                  ),
              textAlign: TextAlign.center,
            ),
            const SizedBox(height: 24.0),
            ElevatedButton.icon(
              onPressed: () => Navigator.of(context).pop(),
              icon: const Icon(Icons.arrow_back),
              label: const Text('Voltar ao Início'),
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildErrorView(BuildContext context, String message) {
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
              'Não foi possível carregar a fila',
              style: Theme.of(context).textTheme.titleLarge,
              textAlign: TextAlign.center,
            ),
            const SizedBox(height: 8.0),
            Text(
              message,
              style: Theme.of(context).textTheme.bodyMedium?.copyWith(
                    color: Colors.grey.shade600,
                  ),
              textAlign: TextAlign.center,
            ),
            const SizedBox(height: 20.0),
            ElevatedButton(
              onPressed: () => context
                  .read<QuestionSrsCubit>()
                  .loadDueQuestions(subjectId: widget.subjectId),
              child: const Text('Tentar Novamente'),
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildCompletedView(BuildContext context, int totalCount) {
    return Center(
      child: Padding(
        padding: const EdgeInsets.all(24.0),
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            const Icon(
              Icons.emoji_events_outlined,
              size: 80.0,
              color: Color(0xFFD97706),
            ),
            const SizedBox(height: 16.0),
            Text(
              'Sessão Finalizada!',
              style: Theme.of(context).textTheme.headlineMedium?.copyWith(
                    fontWeight: FontWeight.bold,
                  ),
            ),
            const SizedBox(height: 8.0),
            Text(
              'Você completou a revisão de $totalCount ${totalCount == 1 ? "pergunta" : "perguntas"} hoje.',
              style: Theme.of(context).textTheme.bodyLarge?.copyWith(
                    color: Colors.grey.shade600,
                  ),
              textAlign: TextAlign.center,
            ),
            const SizedBox(height: 28.0),
            ElevatedButton.icon(
              onPressed: () => Navigator.of(context).maybePop(),
              icon: const Icon(Icons.home_outlined),
              label: const Text('Voltar ao Hub'),
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildLoadedView(BuildContext context, QuestionSrsLoaded state) {
    final question = state.currentQuestion;
    if (question == null) return const SizedBox.shrink();

    final theme = Theme.of(context);
    final progress = (state.currentIndex + 1) / state.totalQuestions;

    return Column(
      children: [
        // Barra de progresso da fila do dia
        LinearProgressIndicator(
          value: progress,
          backgroundColor: theme.colorScheme.surfaceVariant,
          valueColor: AlwaysStoppedAnimation<Color>(theme.colorScheme.primary),
          minHeight: 4.0,
        ),

        // Cabeçalho com índice da fila
        Padding(
          padding: const EdgeInsets.symmetric(horizontal: 16.0, vertical: 8.0),
          child: Row(
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            children: [
              Text(
                'Pergunta ${state.currentIndex + 1} de ${state.totalQuestions}',
                style: theme.textTheme.bodySmall?.copyWith(
                  fontWeight: FontWeight.bold,
                  color: theme.colorScheme.primary,
                ),
              ),
              if (question.subjectName != null)
                Text(
                  question.subjectName!,
                  style: theme.textTheme.bodySmall?.copyWith(
                    color: Colors.grey.shade600,
                  ),
                ),
            ],
          ),
        ),

        // Conteúdo rolável com o card da pergunta e resposta
        Expanded(
          child: SingleChildScrollView(
            padding: const EdgeInsets.symmetric(horizontal: 16.0, vertical: 8.0),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.stretch,
              children: [
                // Card da Pergunta
                Card(
                  elevation: 2.0,
                  shape: RoundedRectangleBorder(
                    borderRadius: BorderRadius.circular(16.0),
                  ),
                  child: Padding(
                    padding: const EdgeInsets.all(16.0),
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Row(
                          mainAxisAlignment: MainAxisAlignment.spaceBetween,
                          children: [
                            SrsLevelBadge.currentLevel(question.currentLevel),
                            if (question.topicName != null)
                              Flexible(
                                child: Text(
                                  question.topicName!,
                                  style: theme.textTheme.bodySmall?.copyWith(
                                    fontStyle: FontStyle.italic,
                                  ),
                                  overflow: TextOverflow.ellipsis,
                                ),
                              ),
                          ],
                        ),
                        const SizedBox(height: 16.0),
                        Text(
                          'Enunciado:',
                          style: theme.textTheme.titleSmall?.copyWith(
                            fontWeight: FontWeight.w600,
                            color: Colors.grey.shade600,
                          ),
                        ),
                        const SizedBox(height: 8.0),
                        Text(
                          question.prompt,
                          style: theme.textTheme.bodyLarge?.copyWith(
                            fontSize: 17.0,
                            height: 1.4,
                          ),
                        ),
                      ],
                    ),
                  ),
                ),

                const SizedBox(height: 16.0),

                // Card da Resposta Esperada (revelada ou oculta)
                if (state.isAnswerRevealed) ...[
                  Card(
                    elevation: 1.5,
                    color: theme.colorScheme.primaryContainer.withOpacity(0.3),
                    shape: RoundedRectangleBorder(
                      borderRadius: BorderRadius.circular(16.0),
                      side: BorderSide(
                        color: theme.colorScheme.primary.withOpacity(0.3),
                      ),
                    ),
                    child: Padding(
                      padding: const EdgeInsets.all(16.0),
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Row(
                            children: [
                              Icon(
                                Icons.check_circle_outline,
                                color: theme.colorScheme.primary,
                                size: 20.0,
                              ),
                              const SizedBox(width: 8.0),
                              Text(
                                'Resposta Esperada (Gabarito):',
                                style: theme.textTheme.titleSmall?.copyWith(
                                  fontWeight: FontWeight.bold,
                                  color: theme.colorScheme.primary,
                                ),
                              ),
                            ],
                          ),
                          const SizedBox(height: 12.0),
                          Text(
                            question.expectedAnswer,
                            style: theme.textTheme.bodyMedium?.copyWith(
                              fontSize: 16.0,
                              height: 1.45,
                            ),
                          ),
                        ],
                      ),
                    ),
                  ),

                  // Feedback imediato de transição de nível após submissão
                  if (state.lastReviewResult != null) ...[
                    const SizedBox(height: 16.0),
                    _buildReviewFeedbackBanner(
                      context,
                      state.lastReviewResult!,
                    ),
                  ],
                ] else ...[
                  // Botão para revelar gabarito
                  Center(
                    child: ConstrainedBox(
                      constraints: const BoxConstraints(minHeight: 48.0),
                      child: OutlinedButton.icon(
                        style: OutlinedButton.styleFrom(
                          padding: const EdgeInsets.symmetric(
                            horizontal: 24.0,
                            vertical: 12.0,
                          ),
                          shape: RoundedRectangleBorder(
                            borderRadius: BorderRadius.circular(12.0),
                          ),
                        ),
                        onPressed: () =>
                            context.read<QuestionSrsCubit>().revealAnswer(),
                        icon: const Icon(Icons.visibility_outlined),
                        label: const Text(
                          'Ver Resposta Esperada',
                          style: TextStyle(
                            fontSize: 15.0,
                            fontWeight: FontWeight.w600,
                          ),
                        ),
                      ),
                    ),
                  ),
                ],
              ],
            ),
          ),
        ),

        // Thumb Zone no terço inferior da tela
        if (state.isAnswerRevealed && state.lastReviewResult == null)
          ScoreThumbSelector(
            currentScore: state.selectedScore,
            isSubmitting: state.isSubmitting,
            onScoreChanged: (score) =>
                context.read<QuestionSrsCubit>().updateScore(score),
            onSubmit: () => context.read<QuestionSrsCubit>().submitReview(),
          )
        else if (state.lastReviewResult != null)
          _buildNextQuestionThumbZone(context),
      ],
    );
  }

  Widget _buildReviewFeedbackBanner(
    BuildContext context,
    ReviewResultEntity result,
  ) {
    return Container(
      padding: const EdgeInsets.all(16.0),
      decoration: BoxDecoration(
        color: Colors.white,
        borderRadius: BorderRadius.circular(14.0),
        border: Border.all(color: Colors.grey.shade300),
        boxShadow: [
          BoxShadow(
            color: Colors.black.withOpacity(0.04),
            blurRadius: 8.0,
            offset: const Offset(0, 2),
          ),
        ],
      ),
      child: Column(
        children: [
          Text(
            'Atualização SRS Processada',
            style: Theme.of(context).textTheme.titleSmall?.copyWith(
                  fontWeight: FontWeight.bold,
                ),
          ),
          const SizedBox(height: 10.0),
          SrsLevelBadge.fromResult(
            isPromoted: result.isPromoted,
            isDemoted: result.isDemoted,
            isMaintained: result.isMaintained,
            levelBefore: result.levelBefore,
            levelAfter: result.levelAfter,
          ),
          const SizedBox(height: 8.0),
          Text(
            'Próxima revisão em ${result.intervalDays} ${result.intervalDays == 1 ? "dia" : "dias"}',
            style: TextStyle(
              color: Colors.grey.shade700,
              fontSize: 13.0,
              fontWeight: FontWeight.w500,
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildNextQuestionThumbZone(BuildContext context) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 16.0, vertical: 14.0),
      decoration: BoxDecoration(
        color: Theme.of(context).colorScheme.surface,
        boxShadow: [
          BoxShadow(
            color: Colors.black.withOpacity(0.08),
            blurRadius: 8.0,
            offset: const Offset(0, -2),
          ),
        ],
      ),
      child: SafeArea(
        top: false,
        child: SizedBox(
          width: double.infinity,
          height: 50.0, // Touch target >= 48dp
          child: ElevatedButton.icon(
            style: ElevatedButton.styleFrom(
              backgroundColor: const Color(0xFF059669),
              foregroundColor: Colors.white,
              shape: RoundedRectangleBorder(
                borderRadius: BorderRadius.circular(12.0),
              ),
            ),
            onPressed: () => context.read<QuestionSrsCubit>().nextQuestion(),
            icon: const Icon(Icons.arrow_forward),
            label: const Text(
              'Próxima Pergunta',
              style: TextStyle(
                fontSize: 16.0,
                fontWeight: FontWeight.bold,
              ),
            ),
          ),
        ),
      ),
    );
  }
}
