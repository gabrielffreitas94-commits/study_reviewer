import 'package:study_reviewer_mobile/features/flashcards/data/models/flashcard_model.dart';

abstract class FlashcardLocalDataSource {
  // Buffer de estudo em memória (prefetched queue)
  void setCardBuffer(List<FlashcardModel> cards);
  void appendCardsToBuffer(List<FlashcardModel> cards);
  FlashcardModel? popNextCard();
  FlashcardModel? peekCurrentCard();
  int get remainingCount;
  List<FlashcardModel> get currentBuffer;
  void clearBuffer();

  // Cache de cards offline
  Future<void> cacheStudyBatch(List<FlashcardModel> cards);
  Future<List<FlashcardModel>> getCachedStudyBatch();
  Future<void> cacheTopicCards(String topicId, List<FlashcardModel> cards);
  Future<List<FlashcardModel>> getCachedTopicCards(String topicId);

  // Fila de leituras pendentes offline
  Future<void> enqueueOfflineRead(String cardId);
  Future<List<String>> getPendingOfflineReads();
  Future<void> removeOfflineReads(List<String> cardIds);
  Future<void> clearOfflineReads();
}

class FlashcardLocalDataSourceImpl implements FlashcardLocalDataSource {
  final List<FlashcardModel> _cardBuffer = <FlashcardModel>[];
  final List<FlashcardModel> _cachedStudyBatch = <FlashcardModel>[];
  final Map<String, List<FlashcardModel>> _cachedTopicCards =
      <String, List<FlashcardModel>>{};
  final List<String> _pendingOfflineReads = <String>[];

  @override
  void setCardBuffer(List<FlashcardModel> cards) {
    _cardBuffer
      ..clear()
      ..addAll(cards);
  }

  @override
  void appendCardsToBuffer(List<FlashcardModel> cards) {
    final existingIds = _cardBuffer.map((c) => c.id).toSet();
    for (final card in cards) {
      if (!existingIds.contains(card.id)) {
        _cardBuffer.add(card);
        existingIds.add(card.id);
      }
    }
  }

  @override
  FlashcardModel? popNextCard() {
    if (_cardBuffer.isEmpty) {
      return null;
    }
    return _cardBuffer.removeAt(0);
  }

  @override
  FlashcardModel? peekCurrentCard() {
    if (_cardBuffer.isEmpty) {
      return null;
    }
    return _cardBuffer.first;
  }

  @override
  int get remainingCount => _cardBuffer.length;

  @override
  List<FlashcardModel> get currentBuffer => List.unmodifiable(_cardBuffer);

  @override
  void clearBuffer() {
    _cardBuffer.clear();
  }

  @override
  Future<void> cacheStudyBatch(List<FlashcardModel> cards) async {
    _cachedStudyBatch
      ..clear()
      ..addAll(cards);
  }

  @override
  Future<List<FlashcardModel>> getCachedStudyBatch() async {
    return List.unmodifiable(_cachedStudyBatch);
  }

  @override
  Future<void> cacheTopicCards(
    String topicId,
    List<FlashcardModel> cards,
  ) async {
    _cachedTopicCards[topicId] = List.from(cards);
  }

  @override
  Future<List<FlashcardModel>> getCachedTopicCards(String topicId) async {
    final cached = _cachedTopicCards[topicId];
    return cached != null ? List.unmodifiable(cached) : <FlashcardModel>[];
  }

  @override
  Future<void> enqueueOfflineRead(String cardId) async {
    if (!_pendingOfflineReads.contains(cardId)) {
      _pendingOfflineReads.add(cardId);
    }
  }

  @override
  Future<List<String>> getPendingOfflineReads() async {
    return List.unmodifiable(_pendingOfflineReads);
  }

  @override
  Future<void> removeOfflineReads(List<String> cardIds) async {
    _pendingOfflineReads.removeWhere((id) => cardIds.contains(id));
  }

  @override
  Future<void> clearOfflineReads() async {
    _pendingOfflineReads.clear();
  }
}
