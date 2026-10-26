"""Testes unitários para CreateSampleMathStudyMapUseCase."""

from uuid import UUID, uuid4

from src.application.ports.repositories import (
    IFlashcardRepository,
    IKnowledgeSourceRepository,
    IQuestionRepository,
    ISubjectRepository,
    ITopicRepository,
)
from src.application.use_cases.sample_study_map_use_case import (
    CreateSampleMathStudyMapUseCase,
)
from src.domain.entities import Flashcard, KnowledgeSource, Question, Subject, Topic
from tests.unit.application.test_study_tree_use_cases import (
    FakeNodeContentRepository,
    FakeStudyEdgeRepository,
    FakeStudyMapRepository,
    FakeStudyNodeRepository,
)


class FakeSubjectRepo(ISubjectRepository):
    def __init__(self) -> None:
        self.subjects: dict[UUID, Subject] = {}

    def get_by_id(self, subject_id: UUID) -> Subject | None:
        return self.subjects.get(subject_id)

    def list_all(self) -> list[Subject]:
        return list(self.subjects.values())

    def list_accessible(self, user_id: UUID) -> list[Subject]:
        return [s for s in self.subjects.values() if s.owner_id == user_id]

    def list_all_with_topics(self) -> list[Subject]:
        return list(self.subjects.values())

    def list_by_owner(self, owner_id: UUID) -> list[Subject]:
        return [s for s in self.subjects.values() if s.owner_id == owner_id]

    def exists_by_name(self, name: str, owner_id: UUID) -> bool:
        return any(s.name == name and s.owner_id == owner_id for s in self.subjects.values())

    def save(self, subject: Subject) -> Subject:
        self.subjects[subject.id] = subject
        return subject


class FakeTopicRepo(ITopicRepository):
    def __init__(self) -> None:
        self.topics: dict[UUID, Topic] = {}

    def get_by_id(self, topic_id: UUID) -> Topic | None:
        return self.topics.get(topic_id)

    def list_by_subject(self, subject_id: UUID) -> list[Topic]:
        return [t for t in self.topics.values() if t.subject_id == subject_id]

    def exists_by_name(self, subject_id: UUID, name: str) -> bool:
        return any(t.subject_id == subject_id and t.name == name for t in self.topics.values())

    def save(self, topic: Topic) -> Topic:
        self.topics[topic.id] = topic
        return topic


class FakeSourceRepository(IKnowledgeSourceRepository):
    def __init__(self) -> None:
        self.sources: dict[UUID, KnowledgeSource] = {}

    def get_by_id(self, source_id: UUID) -> KnowledgeSource | None:
        return self.sources.get(source_id)

    def list_by_topic(self, topic_id: UUID) -> list[KnowledgeSource]:
        return list(self.sources.values())

    def list_by_topics(self, topic_ids: list[UUID]) -> list[KnowledgeSource]:
        return list(self.sources.values())

    def save(self, source: KnowledgeSource) -> KnowledgeSource:
        self.sources[source.id] = source
        return source

    def delete(self, source_id: UUID) -> None:
        self.sources.pop(source_id, None)


class FakeQuestionRepo(IQuestionRepository):
    def __init__(self) -> None:
        self.questions: dict[UUID, Question] = {}

    def get_by_id(self, question_id: UUID) -> Question | None:
        return self.questions.get(question_id)

    def list_by_topic(self, topic_id: UUID) -> list[Question]:
        return list(self.questions.values())

    def list_by_topics(self, topic_ids: list[UUID]) -> list[Question]:
        return list(self.questions.values())

    def count_by_topic(self, topic_id: UUID) -> int:
        return len(self.questions)

    def count_by_topics(self, topic_ids: list[UUID]) -> int:
        return len(self.questions)

    def save(self, question: Question) -> Question:
        self.questions[question.id] = question
        return question

    def delete(self, question_id: UUID) -> None:
        self.questions.pop(question_id, None)


class FakeFlashcardRepo(IFlashcardRepository):
    def __init__(self) -> None:
        self.flashcards: dict[UUID, Flashcard] = {}

    def get_by_id(self, flashcard_id: UUID) -> Flashcard | None:
        return self.flashcards.get(flashcard_id)

    def list_by_topic(self, topic_id: UUID) -> list[Flashcard]:
        return list(self.flashcards.values())

    def list_by_topics(self, topic_ids: list[UUID]) -> list[Flashcard]:
        return list(self.flashcards.values())

    def count_by_topic(self, topic_id: UUID) -> int:
        return len(self.flashcards)

    def count_by_topics(self, topic_ids: list[UUID]) -> int:
        return len(self.flashcards)

    def save(self, flashcard: Flashcard) -> Flashcard:
        self.flashcards[flashcard.id] = flashcard
        return flashcard

    def delete(self, flashcard_id: UUID) -> None:
        self.flashcards.pop(flashcard_id, None)


def test_create_sample_math_study_map_use_case() -> None:
    map_repo = FakeStudyMapRepository()
    node_repo = FakeStudyNodeRepository()
    edge_repo = FakeStudyEdgeRepository()
    content_repo = FakeNodeContentRepository()
    source_repo = FakeSourceRepository()
    question_repo = FakeQuestionRepo()
    flashcard_repo = FakeFlashcardRepo()
    subject_repo = FakeSubjectRepo()
    topic_repo = FakeTopicRepo()

    use_case = CreateSampleMathStudyMapUseCase(
        map_repo=map_repo,
        node_repo=node_repo,
        edge_repo=edge_repo,
        content_repo=content_repo,
        source_repo=source_repo,
        question_repo=question_repo,
        flashcard_repo=flashcard_repo,
        subject_repo=subject_repo,
        topic_repo=topic_repo,
    )

    user_id = uuid4()
    s_map = use_case.execute(user_id=user_id)

    assert s_map.owner_id == user_id
    assert "Matemática Aplicada" in s_map.title

    nodes = node_repo.list_by_map(s_map.id)
    assert len(nodes) == 5

    edges = edge_repo.list_by_map(s_map.id)
    assert len(edges) == 5

    # Cada nó deve ter 1 material, 3 flashcards e 3 questões
    for node in nodes:
        mats, questions, flashcards = content_repo.get_attached_ids(node.id)
        assert len(mats) == 1
        assert len(questions) == 3
        assert len(flashcards) == 3
