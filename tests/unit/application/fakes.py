from datetime import UTC, date, datetime
from typing import Any
from uuid import UUID

from src.application.dto.question_dto import DueQuestionItemDTO
from src.application.ports.repositories import (
    IClockService,
    IFlashcardRepository,
    IQuestionProgressRepository,
    IQuestionRepository,
    ISessionRepository,
    ISubjectRepository,
    ITopicRepository,
)
from src.domain.entities import (
    Flashcard,
    FlashcardPoolSession,
    Question,
    Subject,
    Topic,
    UserQuestionProgress,
)
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

    def list_by_owner(self, owner_id: UUID) -> list[Subject]:
        return [
            s
            for s in sorted(self._subjects.values(), key=lambda s: s.name.lower())
            if s.owner_id == owner_id
        ]

    def list_accessible(self, user_id: UUID) -> list[Subject]:
        return [
            s
            for s in sorted(self._subjects.values(), key=lambda s: s.name.lower())
            if s.owner_id == user_id or s.is_public
        ]

    def exists_by_name(self, name: str, owner_id: UUID | None = None) -> bool:
        norm = name.strip().lower()
        for s in self._subjects.values():
            if s.name.lower() == norm:
                if owner_id is None or s.owner_id == owner_id:
                    return True
        return False

    def list_all_with_topics(
        self, user_id: UUID | None = None
    ) -> list[tuple[Subject, list[Topic]]]:
        if user_id is None:
            return [(s, []) for s in self.list_all()]
        return [(s, []) for s in self.list_accessible(user_id)]


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

    def list_pool(
        self,
        subject_id: UUID | None,
        topic_id: UUID | None,
        limit: int | None = None,
        min_position: int | None = None,
    ) -> list[Flashcard]:
        cards = list(self._cards.values())

        if topic_id is not None:
            cards = [c for c in cards if topic_id in c.topic_ids or c.topic_id == topic_id]
        elif subject_id is not None and self._topic_repo is not None:
            topics = self._topic_repo.list_by_subject(subject_id)
            valid_topic_ids = {t.id for t in topics}
            cards = [c for c in cards if any(tid in valid_topic_ids for tid in c.topic_ids)]

        sorted_cards = sorted(cards, key=lambda c: c.position)
        if min_position is not None:
            sorted_cards = [c for c in sorted_cards if c.position > min_position]

        if limit is not None:
            sorted_cards = sorted_cards[:limit]

        return sorted_cards

    def count_pool(self, subject_id: UUID | None, topic_id: UUID | None) -> int:
        return len(self.list_pool(subject_id, topic_id))

    def count_by_subjects(self) -> dict[UUID, int]:
        counts: dict[UUID, int] = {}
        if self._topic_repo is not None:
            for card in self._cards.values():
                for tid in card.topic_ids:
                    t = self._topic_repo.get_by_id(tid)
                    if t and t.subject_id:
                        counts[t.subject_id] = counts.get(t.subject_id, 0) + 1
        return counts

    def count_by_topics(self) -> dict[UUID, int]:
        counts: dict[UUID, int] = {}
        for card in self._cards.values():
            for tid in card.topic_ids:
                counts[tid] = counts.get(tid, 0) + 1
        return counts


class FakeSessionRepository(ISessionRepository):
    """Implementação em memória de ISessionRepository."""

    def __init__(self) -> None:
        self._sessions: dict[
            tuple[UUID | None, UUID | None, UUID | None], FlashcardPoolSession
        ] = {}

    def get_active_session(
        self,
        subject_id: UUID | None,
        topic_id: UUID | None,
        user_id: UUID | None = None,
    ) -> FlashcardPoolSession | None:
        # Tenta match exato com user_id primeiro
        if (subject_id, topic_id, user_id) in self._sessions:
            return self._sessions[(subject_id, topic_id, user_id)]
        # Fallback sem user_id para compatibilidade de testes existentes
        return self._sessions.get((subject_id, topic_id, None))

    def get_by_id(self, session_id: UUID) -> FlashcardPoolSession | None:
        for s in self._sessions.values():
            if s.id == session_id:
                return s
        return None

    def save_session(self, session: FlashcardPoolSession) -> None:
        self._sessions[(session.subject_id_filter, session.topic_id_filter, session.user_id)] = (
            session
        )
        self._sessions[(session.subject_id_filter, session.topic_id_filter, None)] = session


class FakeClockService(IClockService):
    """Implementação em memória de IClockService para testes temporais."""

    def __init__(
        self, current_date: date | None = None, current_datetime: datetime | None = None
    ) -> None:
        self._date = current_date or date.today()
        self._datetime = current_datetime or datetime.now(UTC)

    def set_date(self, new_date: date) -> None:
        self._date = new_date

    def set_datetime(self, new_dt: datetime) -> None:
        self._datetime = new_dt

    def today(self) -> date:
        return self._date

    def now(self) -> datetime:
        return self._datetime


class FakeQuestionRepository(IQuestionRepository):
    """Implementação em memória de IQuestionRepository."""

    def __init__(self) -> None:
        self._questions: dict[UUID, Question] = {}

    def save(self, question: Question) -> None:
        self._questions[question.id] = question

    def get_by_id(self, question_id: UUID) -> Question | None:
        return self._questions.get(question_id)

    def list_by_topic(self, topic_id: UUID) -> list[Question]:
        return [
            q
            for q in sorted(self._questions.values(), key=lambda x: x.created_at)
            if q.topic_id == topic_id
        ]

    def delete(self, question_id: UUID) -> None:
        self._questions.pop(question_id, None)


class FakeQuestionProgressRepository(IQuestionProgressRepository):
    """Implementação em memória de IQuestionProgressRepository com suporte a joins."""

    def __init__(
        self,
        question_repo: FakeQuestionRepository | None = None,
        topic_repo: FakeTopicRepository | None = None,
        subject_repo: FakeSubjectRepository | None = None,
    ) -> None:
        self._progress: dict[tuple[UUID, UUID], UserQuestionProgress] = {}
        self._question_repo = question_repo or FakeQuestionRepository()
        self._topic_repo = topic_repo or FakeTopicRepository()
        self._subject_repo = subject_repo or FakeSubjectRepository()

    def save(self, progress: UserQuestionProgress) -> None:
        self._progress[(progress.user_id, progress.question_id)] = progress

    def get_by_user_and_question(
        self, user_id: UUID, question_id: UUID
    ) -> UserQuestionProgress | None:
        return self._progress.get((user_id, question_id))

    def get_due_questions(
        self,
        user_id: UUID,
        reference_date: date,
        subject_id: UUID | None = None,
        topic_id: UUID | None = None,
        limit: int = 50,
    ) -> list[DueQuestionItemDTO]:
        items: list[DueQuestionItemDTO] = []
        intervals = (1, 7, 15, 30, 60, 90, 180)

        user_progs = [p for (u_id, _), p in self._progress.items() if u_id == user_id]
        due_progs = [p for p in user_progs if p.next_review_date <= reference_date]

        # Ordenação determinística: next_review_date ASC, current_level ASC, question_id ASC
        sorted_progs = sorted(
            due_progs,
            key=lambda p: (p.next_review_date, p.current_level, p.question_id),
        )

        for p in sorted_progs:
            q = self._question_repo.get_by_id(p.question_id)
            if not q:
                continue
            topic = self._topic_repo.get_by_id(q.topic_id)
            topic_name = topic.name if topic else "Tema"
            subject_name = "Matéria"
            if topic:
                if topic_id is not None and topic.id != topic_id:
                    continue
                subj = self._subject_repo.get_by_id(topic.subject_id)
                if subj:
                    if subject_id is not None and subj.id != subject_id:
                        continue
                    subject_name = subj.name

            level_idx = min(p.current_level, 6)
            items.append(
                DueQuestionItemDTO(
                    question_id=q.id,
                    subject_name=subject_name,
                    topic_name=topic_name,
                    prompt=q.prompt,
                    expected_answer=q.expected_answer,
                    current_level=p.current_level,
                    interval_days=intervals[level_idx],
                    due_date=p.next_review_date,
                )
            )
            if len(items) >= limit:
                break

        return items

    def count_due_questions(self, user_id: UUID, reference_date: date) -> int:
        return sum(
            1
            for (u_id, _), p in self._progress.items()
            if u_id == user_id and p.next_review_date <= reference_date
        )

    def get_next_review_date(self, user_id: UUID, reference_date: date) -> date | None:
        future_dates = [
            p.next_review_date
            for (u_id, _), p in self._progress.items()
            if u_id == user_id and p.next_review_date > reference_date
        ]
        return min(future_dates) if future_dates else None

    def initialize_progress_for_questions(
        self, user_id: UUID, question_ids: list[UUID], initial_date: date
    ) -> None:
        for q_id in question_ids:
            if (user_id, q_id) not in self._progress:
                self._progress[(user_id, q_id)] = UserQuestionProgress(
                    user_id=user_id,
                    question_id=q_id,
                    current_level=0,
                    next_review_date=initial_date,
                    last_reviewed_at=None,
                )
