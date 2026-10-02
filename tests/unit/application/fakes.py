"""Repositórios fake em memória para testes unitários da camada de aplicação."""

from typing import Any
from uuid import UUID

from src.application.ports.repositories import (
    IFlashcardRepository,
    ISessionRepository,
    ISubjectRepository,
    ITopicRepository,
)
from src.domain.entities import Flashcard, FlashcardPoolSession, Subject, Topic
from src.domain.protocols import IRandomGenerator


class FakeRandomGenerator(IRandomGenerator):
    """Gerador pseudoaleatório determinístico para testes."""

    def __init__(self, fixed_randint: int = 0) -> None:
        self.fixed_randint = fixed_randint
        self.shuffled = False

    def randint(self, a: int, b: int) -> int:
        return min(b, max(a, self.fixed_randint))

    def shuffle(self, items: list[Any]) -> None:
        self.shuffled = True
        items.reverse()


class FakeSubjectRepository(ISubjectRepository):
    """Implementação em memória de ISubjectRepository."""

    def __init__(self) -> None:
        self._subjects: dict[UUID, Subject] = {}

    def save(self, subject: Subject) -> None:
        self._subjects[subject.id] = subject

    def get_by_id(self, subject_id: UUID) -> Subject | None:
        return self._subjects.get(subject_id)

    def list_all(self) -> list[Subject]:
        return sorted(self._subjects.values(), key=lambda s: s.name.lower())

    def exists_by_name(self, name: str) -> bool:
        norm = name.strip().lower()
        return any(s.name.lower() == norm for s in self._subjects.values())


class FakeTopicRepository(ITopicRepository):
    """Implementação em memória de ITopicRepository."""

    def __init__(self) -> None:
        self._topics: dict[UUID, Topic] = {}

    def save(self, topic: Topic) -> None:
        self._topics[topic.id] = topic

    def get_by_id(self, topic_id: UUID) -> Topic | None:
        return self._topics.get(topic_id)

    def list_by_subject(self, subject_id: UUID) -> list[Topic]:
        return [
            t
            for t in sorted(self._topics.values(), key=lambda t: t.name.lower())
            if t.subject_id == subject_id
        ]

    def exists_by_name(self, subject_id: UUID, name: str) -> bool:
        norm = name.strip().lower()
        return any(
            t.subject_id == subject_id and t.name.lower() == norm for t in self._topics.values()
        )


class FakeFlashcardRepository(IFlashcardRepository):
    """Implementação em memória de IFlashcardRepository."""

    def __init__(self, topic_repo: ITopicRepository | None = None) -> None:
        self._cards: dict[UUID, Flashcard] = {}
        self._topic_repo = topic_repo

    def save(self, flashcard: Flashcard) -> None:
        self._cards[flashcard.id] = flashcard

    def save_all(self, flashcards: list[Flashcard]) -> None:
        for card in flashcards:
            self._cards[card.id] = card

    def get_by_id(self, flashcard_id: UUID) -> Flashcard | None:
        return self._cards.get(flashcard_id)

    def delete(self, flashcard_id: UUID) -> None:
        self._cards.pop(flashcard_id, None)

    def list_pool(self, subject_id: UUID | None, topic_id: UUID | None) -> list[Flashcard]:
        cards = list(self._cards.values())

        if topic_id is not None:
            cards = [c for c in cards if c.topic_id == topic_id]
        elif subject_id is not None and self._topic_repo is not None:
            topics = self._topic_repo.list_by_subject(subject_id)
            valid_topic_ids = {t.id for t in topics}
            cards = [c for c in cards if c.topic_id in valid_topic_ids]

        return sorted(cards, key=lambda c: c.position)

    def count_pool(self, subject_id: UUID | None, topic_id: UUID | None) -> int:
        return len(self.list_pool(subject_id, topic_id))


class FakeSessionRepository(ISessionRepository):
    """Implementação em memória de ISessionRepository."""

    def __init__(self) -> None:
        self._sessions: dict[tuple[UUID | None, UUID | None], FlashcardPoolSession] = {}

    def get_active_session(
        self, subject_id: UUID | None, topic_id: UUID | None
    ) -> FlashcardPoolSession | None:
        return self._sessions.get((subject_id, topic_id))

    def save_session(self, session: FlashcardPoolSession) -> None:
        self._sessions[(session.subject_id_filter, session.topic_id_filter)] = session
