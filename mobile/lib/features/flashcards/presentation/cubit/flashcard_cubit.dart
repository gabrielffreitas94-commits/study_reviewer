import 'package:flutter_bloc/flutter_bloc.dart';
import 'package:study_reviewer_mobile/features/flashcards/domain/entities/flashcard_entity.dart';
import 'package:study_reviewer_mobile/features/flashcards/domain/usecases/get_next_card_usecase.dart';
import 'package:study_reviewer_mobile/features/flashcards/domain/usecases/get_study_batch_usecase.dart';
import 'package:study_reviewer_mobile/features/flashcards/domain/usecases/mark_card_read_usecase.dart';
import 'package:study_reviewer_mobile/features/flashcards/presentation/cubit/flashcard_state.dart';

class FlashcardCubit extends Cubit<FlashcardState> {
  final GetStudyBatchUseCase getStudyBatchUseCase;
  final GetNextCardUseCase getNextCardUseCase;
  final MarkCardReadUseCase markCardReadUseCase;

  static const int lowWaterMarkThreshold = 10;
  static const int prefetchBatchLimit = 50;

  String? _subjectId;
  String? _topicId;
  final List<FlashcardEntity> _buffer = <FlashcardEntity>[];
  final Set<String> _seenCardIds = <String>{};

  int _roundNumber = 1;
  int _currentIndex = 1;
  int _totalCards = 0;
  bool _isPrefetching = false;
  bool _isOffline = false;

  FlashcardCubit({
    required this.getStudyBatchUseCase,
    required this.getNextCardUseCase,
    required this.markCardReadUseCase,
  }) : super(const FlashcardInitial());

  int get bufferCount => _buffer.length;
  bool get isPrefetching => _isPrefetching;

  Future<void> loadSession({String? subjectId, String? topicId}) async {
    _subjectId = subjectId;
    _topicId = topicId;
    _buffer.clear();
    _seenCardIds.clear();
    _roundNumber = 1;
    _currentIndex = 1;
    _isPrefetching = false;
    _isOffline = false;

    emit(const FlashcardLoading());

    try {
      final batch = await getStudyBatchUseCase(
        subjectId: _subjectId,
        topicId: _topicId,
        limit: prefetchBatchLimit,
      );

      if (batch.isEmpty) {
        emit(FlashcardEmpty(
          roundNumber: _roundNumber,
          message: 'Nenhum flashcard disponível para este tema.',
        ));
        return;
      }

      _buffer.addAll(batch);
      _totalCards = batch.length;

      final firstCard = _buffer.removeAt(0);
      _seenCardIds.add(firstCard.id);

      emit(FlashcardLoaded(
        currentCard: firstCard,
        roundNumber: _roundNumber,
        currentIndex: _currentIndex,
        totalCards: _totalCards,
        remainingInBuffer: _buffer.length,
        isFlipped: false,
        isPrefetching: false,
        isOffline: _isOffline,
      ));
    } catch (e) {
      emit(FlashcardError(
        message: 'Falha ao carregar flashcards: ${e.toString()}',
        canRetry: true,
      ));
    }
  }

  void toggleFlip() {
    final currentState = state;
    if (currentState is FlashcardLoaded) {
      emit(currentState.copyWith(isFlipped: !currentState.isFlipped));
    }
  }

  Future<void> nextCard() async {
    final currentState = state;
    if (currentState is! FlashcardLoaded) {
      return;
    }

    final currentCard = currentState.currentCard;

    // Dispara marcação de leitura de forma assíncrona (0ms percebidos pelo estudante)
    markCardReadUseCase(
      cardId: currentCard.id,
      subjectId: _subjectId,
      topicId: _topicId,
    ).catchError((Object _) {
      _isOffline = true;
    });

    if (_buffer.isEmpty) {
      emit(FlashcardEmpty(
        roundNumber: _roundNumber,
        message: 'Parabéns! Você revisou todos os flashcards desta rodada.',
      ));
      return;
    }

    final nextCard = _buffer.removeAt(0);
    _seenCardIds.add(nextCard.id);
    _currentIndex++;

    emit(currentState.copyWith(
      currentCard: nextCard,
      currentIndex: _currentIndex,
      remainingInBuffer: _buffer.length,
      isFlipped: false,
      isOffline: _isOffline,
    ));

    // Política de Low-Water Mark: quando buffer <= 10, prefetch em background
    _checkAndTriggerPrefetch();
  }

  void _checkAndTriggerPrefetch() {
    if (_buffer.length <= lowWaterMarkThreshold && !_isPrefetching) {
      _prefetchNextBatch();
    }
  }

  Future<void> _prefetchNextBatch() async {
    if (_isPrefetching) {
      return;
    }
    _isPrefetching = true;

    final currentState = state;
    if (currentState is FlashcardLoaded) {
      emit(currentState.copyWith(isPrefetching: true));
    }

    try {
      final newBatch = await getStudyBatchUseCase(
        subjectId: _subjectId,
        topicId: _topicId,
        limit: prefetchBatchLimit,
      );

      final unseenCards =
          newBatch.where((card) => !_seenCardIds.contains(card.id)).toList();

      if (unseenCards.isNotEmpty) {
        _buffer.addAll(unseenCards);
        _totalCards += unseenCards.length;
      }
    } catch (_) {
      _isOffline = true;
    } finally {
      _isPrefetching = false;
      if (!isClosed && state is FlashcardLoaded) {
        final updatedState = state as FlashcardLoaded;
        emit(updatedState.copyWith(
          isPrefetching: false,
          remainingInBuffer: _buffer.length,
          totalCards: _totalCards,
          isOffline: _isOffline,
        ));
      }
    }
  }

  void retry() {
    loadSession(subjectId: _subjectId, topicId: _topicId);
  }
}
