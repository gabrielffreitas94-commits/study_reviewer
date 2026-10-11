import 'package:study_reviewer_mobile/core/errors/exceptions.dart';
import 'package:study_reviewer_mobile/features/flashcards/data/datasources/flashcard_local_data_source.dart';
import 'package:study_reviewer_mobile/features/flashcards/data/datasources/flashcard_remote_data_source.dart';
import 'package:study_reviewer_mobile/features/flashcards/domain/entities/flashcard_entity.dart';
import 'package:study_reviewer_mobile/features/flashcards/domain/entities/study_session_entity.dart';
import 'package:study_reviewer_mobile/features/flashcards/domain/repositories/flashcard_repository.dart';

class FlashcardRepositoryImpl implements FlashcardRepository {
  final FlashcardRemoteDataSource remoteDataSource;
  final FlashcardLocalDataSource localDataSource;

  const FlashcardRepositoryImpl({
    required this.remoteDataSource,
    required this.localDataSource,
  });

  @override
  Future<List<FlashcardEntity>> getStudyBatch({
    String? subjectId,
    String? topicId,
    int limit = 50,
  }) async {
    try {
      final batch = await remoteDataSource.getStudyBatch(
        subjectId: subjectId,
        topicId: topicId,
        limit: limit,
      );

      // Atualiza o cache local para resiliência offline
      await localDataSource.cacheStudyBatch(batch.cards);

      return batch.cards.map((card) => card.toEntity()).toList();
    } catch (_) {
      // Fallback offline: busca do cache local
      final cachedCards = await localDataSource.getCachedStudyBatch();
      if (cachedCards.isNotEmpty) {
        return cachedCards.map((card) => card.toEntity()).toList();
      }
      rethrow;
    }
  }

  @override
  Future<StudySessionEntity> getNextCard({
    String? subjectId,
    String? topicId,
    int? currentIndex,
  }) async {
    try {
      final sessionModel = await remoteDataSource.getNextCard(
        subjectId: subjectId,
        topicId: topicId,
        currentIndex: currentIndex,
      );
      return sessionModel;
    } catch (_) {
      // Fallback offline: verifica se há cards no buffer local em memória
      final bufferedCard = localDataSource.popNextCard();
      if (bufferedCard != null) {
        return StudySessionEntity(
          roundNumber: 1,
          currentIndex: currentIndex ?? 1,
          totalCards: localDataSource.remainingCount + 1,
          currentCard: bufferedCard.toEntity(),
          sessionId: bufferedCard.sessionId,
        );
      }

      // Se o buffer estiver vazio, tenta o cache de lote salvo localmente
      final cachedBatch = await localDataSource.getCachedStudyBatch();
      if (cachedBatch.isNotEmpty) {
        final first = cachedBatch.first;
        return StudySessionEntity(
          roundNumber: 1,
          currentIndex: currentIndex ?? 1,
          totalCards: cachedBatch.length,
          currentCard: first.toEntity(),
          sessionId: first.sessionId,
        );
      }

      throw const NetworkException(
        message: 'Sem conexão de rede e nenhum card em cache offline.',
      );
    }
  }

  @override
  Future<void> markCardRead({
    required String cardId,
    String? subjectId,
    String? topicId,
  }) async {
    try {
      await remoteDataSource.markCardRead(
        cardId: cardId,
        subjectId: subjectId,
        topicId: topicId,
      );
    } catch (_) {
      // Em caso de falha de conexão, enfileira a leitura localmente para sincronização posterior
      await localDataSource.enqueueOfflineRead(cardId);
    }
  }

  @override
  Future<List<FlashcardEntity>> listTopicFlashcards({
    required String topicId,
    int limit = 50,
    int offset = 0,
  }) async {
    try {
      final cards = await remoteDataSource.listTopicFlashcards(
        topicId: topicId,
        limit: limit,
        offset: offset,
      );
      await localDataSource.cacheTopicCards(topicId, cards);
      return cards.map((c) => c.toEntity()).toList();
    } catch (_) {
      final cached = await localDataSource.getCachedTopicCards(topicId);
      if (cached.isNotEmpty) {
        return cached.map((c) => c.toEntity()).toList();
      }
      rethrow;
    }
  }
}
