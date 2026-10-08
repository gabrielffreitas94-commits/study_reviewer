import 'package:flutter/material.dart';
import 'package:flutter_bloc/flutter_bloc.dart';
import 'package:study_reviewer_mobile/features/flashcards/presentation/cubit/flashcard_cubit.dart';
import 'package:study_reviewer_mobile/features/flashcards/presentation/cubit/flashcard_state.dart';
import 'package:study_reviewer_mobile/features/flashcards/presentation/widgets/flip_card_3d.dart';
import 'package:study_reviewer_mobile/features/flashcards/presentation/widgets/swipe_gesture_detector.dart';
import 'package:study_reviewer_mobile/features/sync/presentation/widgets/sync_status_badge.dart';

class FlashcardStudyPage extends StatefulWidget {
  final String? subjectId;
  final String? topicId;
  final String? topicTitle;

  const FlashcardStudyPage({
    super.key,
    this.subjectId,
    this.topicId,
    this.topicTitle,
  });

  @override
  State<FlashcardStudyPage> createState() => _FlashcardStudyPageState();
}

class _FlashcardStudyPageState extends State<FlashcardStudyPage> {
  @override
  void initState() {
    super.initState();
    context.read<FlashcardCubit>().loadSession(
          subjectId: widget.subjectId,
          topicId: widget.topicId,
        );
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: Text(widget.topicTitle ?? 'Estudo de Flashcards'),
        actions: [
          BlocBuilder<FlashcardCubit, FlashcardState>(
            builder: (context, state) {
              if (state is FlashcardLoaded) {
                final syncStatus = state.isOffline
                    ? SyncStatus.offline
                    : (state.isPrefetching
                        ? SyncStatus.pendingSync
                        : SyncStatus.synced);
                return Padding(
                  padding: const EdgeInsets.only(right: 16.0),
                  child: Center(
                    child: SyncStatusBadge(status: syncStatus),
                  ),
                );
              }
              return const SizedBox.shrink();
            },
          ),
        ],
      ),
      body: SafeArea(
        child: BlocConsumer<FlashcardCubit, FlashcardState>(
          listener: (context, state) {},
          builder: (context, state) {
            return switch (state) {
              FlashcardInitial() || FlashcardLoading() => _buildLoadingState(),
              FlashcardEmpty() => _buildEmptyState(context, state),
              FlashcardError() => _buildErrorState(context, state),
              FlashcardLoaded() => _buildLoadedState(context, state),
              _ => _buildLoadingState(),
            };
          },
        ),
      ),
    );
  }

  // Estado 1 & 5: Ideal e Parcial (com indicador de sync / offline)
  Widget _buildLoadedState(BuildContext context, FlashcardLoaded state) {
    final theme = Theme.of(context);
    final isDark = theme.brightness == Brightness.dark;

    return Padding(
      padding: const EdgeInsets.symmetric(horizontal: 20.0, vertical: 12.0),
      child: Column(
        children: [
          // Banner de Estado Parcial (Modo Offline)
          if (state.isOffline)
            Container(
              margin: const EdgeInsets.only(bottom: 12.0),
              padding:
                  const EdgeInsets.symmetric(horizontal: 14.0, vertical: 8.0),
              decoration: BoxDecoration(
                color: isDark ? const Color(0xFF332A00) : const Color(0xFFFFF9C4),
                borderRadius: BorderRadius.circular(8.0),
                border: Border.all(
                  color: isDark ? const Color(0xFFFFB300) : const Color(0xFFFBC02D),
                ),
              ),
              child: Row(
                children: [
                  Icon(
                    Icons.wifi_off_outlined,
                    size: 18,
                    color: isDark ? const Color(0xFFFFD54F) : const Color(0xFFF57F17),
                  ),
                  const SizedBox(width: 8),
                  Expanded(
                    child: Text(
                      'Modo offline ativo. Suas leituras serão sincronizadas ao reconectar.',
                      style: TextStyle(
                        fontSize: 12,
                        fontWeight: FontWeight.w500,
                        color: isDark ? const Color(0xFFFFE082) : const Color(0xFF7F4700),
                      ),
                    ),
                  ),
                ],
              ),
            ),

          // Contador de Rodada e Progresso
          Row(
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            children: [
              Container(
                padding:
                    const EdgeInsets.symmetric(horizontal: 10.0, vertical: 4.0),
                decoration: BoxDecoration(
                  color: theme.colorScheme.primaryContainer,
                  borderRadius: BorderRadius.circular(12.0),
                ),
                child: Text(
                  'Rodada ${state.roundNumber}',
                  style: TextStyle(
                    fontSize: 13,
                    fontWeight: FontWeight.bold,
                    color: theme.colorScheme.onPrimaryContainer,
                  ),
                ),
              ),
              Text(
                'Card ${state.currentIndex} de ${state.totalCards}',
                style: theme.textTheme.bodyMedium?.copyWith(
                  fontWeight: FontWeight.w600,
                ),
              ),
            ],
          ),
          const SizedBox(height: 16),

          // Barra de progresso linear
          ClipRRect(
            borderRadius: BorderRadius.circular(4.0),
            child: LinearProgressIndicator(
              value: state.totalCards > 0
                  ? (state.currentIndex / state.totalCards).clamp(0.0, 1.0)
                  : 0.0,
              minHeight: 6,
              backgroundColor: theme.colorScheme.outline.withOpacity(0.2),
            ),
          ),
          const SizedBox(height: 24),

          // Card 3D Centralizado com Swipe Left
          Expanded(
            child: Center(
              child: SwipeGestureDetector(
                onSwipeLeft: () {
                  context.read<FlashcardCubit>().nextCard();
                },
                child: FlipCard3D(
                  isFlipped: state.isFlipped,
                  onFlip: () {
                    context.read<FlashcardCubit>().toggleFlip();
                  },
                  front: _buildCardFace(
                    context,
                    title: 'Frente',
                    content: state.currentCard.front,
                    hint: 'Toque para ver a resposta',
                    isFront: true,
                  ),
                  back: _buildCardFace(
                    context,
                    title: 'Verso',
                    content: state.currentCard.back,
                    hint: 'Deslize para a esquerda para o próximo',
                    isFront: false,
                  ),
                ),
              ),
            ),
          ),
          const SizedBox(height: 16),

          // Botões de Acessibilidade / Thumb Zone
          Row(
            children: [
              Expanded(
                child: OutlinedButton.icon(
                  style: OutlinedButton.styleFrom(
                    minimumSize: const Size.fromHeight(48), // Touch target >= 48dp
                  ),
                  onPressed: () {
                    context.read<FlashcardCubit>().toggleFlip();
                  },
                  icon: const Icon(Icons.flip_to_back),
                  label: Text(state.isFlipped ? 'Ver Frente' : 'Virar Card'),
                ),
              ),
              const SizedBox(width: 12),
              Expanded(
                child: FilledButton.icon(
                  style: FilledButton.styleFrom(
                    minimumSize: const Size.fromHeight(48), // Touch target >= 48dp
                  ),
                  onPressed: () {
                    context.read<FlashcardCubit>().nextCard();
                  },
                  icon: const Icon(Icons.arrow_forward),
                  label: const Text('Próximo Card'),
                ),
              ),
            ],
          ),
        ],
      ),
    );
  }

  // Face do Card (Frontal ou Traseira)
  Widget _buildCardFace(
    BuildContext context, {
    required String title,
    required String content,
    required String hint,
    required bool isFront,
  }) {
    final theme = Theme.of(context);
    final isDark = theme.brightness == Brightness.dark;

    return Container(
      width: double.infinity,
      constraints: const BoxConstraints(minHeight: 280, maxHeight: 420),
      decoration: BoxDecoration(
        color: isDark ? const Color(0xFF1E1E1E) : Colors.white,
        borderRadius: BorderRadius.circular(20),
        border: Border.all(
          color: isFront
              ? theme.colorScheme.primary.withOpacity(0.4)
              : theme.colorScheme.secondary.withOpacity(0.4),
          width: 2,
        ),
        boxShadow: [
          BoxShadow(
            color: Colors.black.withOpacity(isDark ? 0.3 : 0.08),
            blurRadius: 16,
            offset: const Offset(0, 8),
          ),
        ],
      ),
      padding: const EdgeInsets.all(24.0),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          Row(
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            children: [
              Container(
                padding:
                    const EdgeInsets.symmetric(horizontal: 10, vertical: 4),
                decoration: BoxDecoration(
                  color: isFront
                      ? theme.colorScheme.primary.withOpacity(0.12)
                      : theme.colorScheme.secondary.withOpacity(0.12),
                  borderRadius: BorderRadius.circular(8),
                ),
                child: Text(
                  title.toUpperCase(),
                  style: TextStyle(
                    fontSize: 11,
                    fontWeight: FontWeight.w700,
                    letterSpacing: 1.0,
                    color: isFront
                        ? theme.colorScheme.primary
                        : theme.colorScheme.secondary,
                  ),
                ),
              ),
              Icon(
                isFront ? Icons.touch_app_outlined : Icons.swipe_left_outlined,
                size: 20,
                color: theme.colorScheme.outline,
              ),
            ],
          ),
          const Spacer(),
          Center(
            child: SingleChildScrollView(
              child: Text(
                content,
                textAlign: TextAlign.center,
                style: theme.textTheme.headlineSmall?.copyWith(
                  fontWeight: FontWeight.w600,
                  height: 1.4,
                ),
              ),
            ),
          ),
          const Spacer(),
          Center(
            child: Text(
              hint,
              style: theme.textTheme.bodySmall?.copyWith(
                color: theme.colorScheme.outline,
                fontStyle: FontStyle.italic,
              ),
            ),
          ),
        ],
      ),
    );
  }

  // Estado 2: Vazio / Inbox Zero com mensagem acolhedora
  Widget _buildEmptyState(BuildContext context, FlashcardEmpty state) {
    final theme = Theme.of(context);

    return Center(
      child: Padding(
        padding: const EdgeInsets.all(32.0),
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            Container(
              padding: const EdgeInsets.all(24.0),
              decoration: BoxDecoration(
                color: theme.colorScheme.primaryContainer.withOpacity(0.4),
                shape: BoxShape.circle,
              ),
              child: Icon(
                Icons.celebration_outlined,
                size: 64,
                color: theme.colorScheme.primary,
              ),
            ),
            const SizedBox(height: 24),
            Text(
              'Parabéns!',
              style: theme.textTheme.headlineMedium?.copyWith(
                fontWeight: FontWeight.bold,
              ),
            ),
            const SizedBox(height: 12),
            Text(
              state.message,
              textAlign: TextAlign.center,
              style: theme.textTheme.bodyLarge?.copyWith(
                color: theme.colorScheme.onSurfaceVariant,
              ),
            ),
            const SizedBox(height: 32),
            FilledButton.icon(
              style: FilledButton.styleFrom(
                minimumSize: const Size(200, 48), // Touch target >= 48dp
              ),
              onPressed: () {
                context.read<FlashcardCubit>().loadSession(
                      subjectId: widget.subjectId,
                      topicId: widget.topicId,
                    );
              },
              icon: const Icon(Icons.replay),
              label: const Text('Reiniciar Rodada'),
            ),
          ],
        ),
      ),
    );
  }

  // Estado 3: Carregando com Skeleton
  Widget _buildLoadingState() {
    return Center(
      child: Padding(
        padding: const EdgeInsets.symmetric(horizontal: 24.0),
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            Container(
              width: double.infinity,
              height: 320,
              decoration: BoxDecoration(
                color: Colors.grey.withOpacity(0.12),
                borderRadius: BorderRadius.circular(20),
                border: Border.all(
                  color: Colors.grey.withOpacity(0.2),
                ),
              ),
              child: Column(
                mainAxisAlignment: MainAxisAlignment.center,
                children: [
                  const CircularProgressIndicator(),
                  const SizedBox(height: 20),
                  Text(
                    'Preparando seus flashcards...',
                    style: TextStyle(
                      color: Colors.grey.shade600,
                      fontWeight: FontWeight.w500,
                    ),
                  ),
                ],
              ),
            ),
          ],
        ),
      ),
    );
  }

  // Estado 4: Erro com Retry
  Widget _buildErrorState(BuildContext context, FlashcardError state) {
    final theme = Theme.of(context);

    return Center(
      child: Padding(
        padding: const EdgeInsets.all(32.0),
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            Icon(
              Icons.error_outline,
              size: 56,
              color: theme.colorScheme.error,
            ),
            const SizedBox(height: 16),
            Text(
              'Não foi possível carregar os cards',
              style: theme.textTheme.titleMedium?.copyWith(
                fontWeight: FontWeight.bold,
              ),
            ),
            const SizedBox(height: 8),
            Text(
              state.message,
              textAlign: TextAlign.center,
              style: theme.textTheme.bodyMedium?.copyWith(
                color: theme.colorScheme.onSurfaceVariant,
              ),
            ),
            const SizedBox(height: 24),
            if (state.canRetry)
              FilledButton.icon(
                style: FilledButton.styleFrom(
                  minimumSize: const Size(180, 48), // Touch target >= 48dp
                ),
                onPressed: () {
                  context.read<FlashcardCubit>().retry();
                },
                icon: const Icon(Icons.refresh),
                label: const Text('Tentar Novamente'),
              ),
          ],
        ),
      ),
    );
  }
}
