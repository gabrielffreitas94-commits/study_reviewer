"""Testes unitários para os casos de uso de Tema (Camada 2 - Aplicação)."""

from uuid import uuid4

import pytest

from src.application.dto.topic_dto import CreateTopicDTO
from src.application.use_cases.topic_use_cases import (
    CreateTopicUseCase,
    ListTopicsBySubjectUseCase,
)
from src.domain.entities import Subject
from src.domain.exceptions import (
    DomainValidationError,
    DuplicateEntityError,
    EntityNotFoundError,
)
from tests.unit.application.fakes import FakeSubjectRepository, FakeTopicRepository


@pytest.mark.unit
def test_create_topic_success() -> None:
    """Criação bem-sucedida de tema vinculado à matéria."""
    subject_repo = FakeSubjectRepository()
    topic_repo = FakeTopicRepository()

    subject = Subject(name="Direito Constitucional")
    subject_repo.save(subject)

    use_case = CreateTopicUseCase(subject_repo, topic_repo)
    dto = use_case.execute(CreateTopicDTO(subject_id=subject.id, name="Direitos Fundamentais"))

    assert dto.name == "Direitos Fundamentais"
    assert dto.subject_id == subject.id
    assert topic_repo.exists_by_name(subject.id, "Direitos Fundamentais") is True


@pytest.mark.unit
def test_create_topic_subject_not_found() -> None:
    """Tentativa de criar tema para matéria inexistente lança EntityNotFoundError."""
    subject_repo = FakeSubjectRepository()
    topic_repo = FakeTopicRepository()

    use_case = CreateTopicUseCase(subject_repo, topic_repo)
    with pytest.raises(EntityNotFoundError, match="Matéria não encontrada."):
        use_case.execute(CreateTopicDTO(subject_id=uuid4(), name="Direitos Fundamentais"))


@pytest.mark.unit
def test_create_topic_duplicate_in_same_subject() -> None:
    """Tentativa de criar tema duplicado na mesma matéria lança DuplicateEntityError."""
    subject_repo = FakeSubjectRepository()
    topic_repo = FakeTopicRepository()

    subject = Subject(name="Direito Constitucional")
    subject_repo.save(subject)

    use_case = CreateTopicUseCase(subject_repo, topic_repo)
    use_case.execute(CreateTopicDTO(subject_id=subject.id, name="Direitos Fundamentais"))

    with pytest.raises(DuplicateEntityError, match="já cadastrado"):
        use_case.execute(CreateTopicDTO(subject_id=subject.id, name="direitos fundamentais"))


@pytest.mark.unit
def test_create_topic_duplicate_name_in_different_subjects_allowed() -> None:
    """Mesmo nome de tema em matérias diferentes é permitido."""
    subject_repo = FakeSubjectRepository()
    topic_repo = FakeTopicRepository()

    sub1 = Subject(name="Matéria 1")
    sub2 = Subject(name="Matéria 2")
    subject_repo.save(sub1)
    subject_repo.save(sub2)

    use_case = CreateTopicUseCase(subject_repo, topic_repo)
    dto1 = use_case.execute(CreateTopicDTO(subject_id=sub1.id, name="Geral"))
    dto2 = use_case.execute(CreateTopicDTO(subject_id=sub2.id, name="Geral"))

    assert dto1.subject_id == sub1.id
    assert dto2.subject_id == sub2.id


@pytest.mark.unit
def test_create_topic_invalid_name_raises_domain_error() -> None:
    """Nome inválido propaga DomainValidationError."""
    subject_repo = FakeSubjectRepository()
    topic_repo = FakeTopicRepository()
    sub = Subject(name="Biologia")
    subject_repo.save(sub)

    use_case = CreateTopicUseCase(subject_repo, topic_repo)
    with pytest.raises(DomainValidationError):
        use_case.execute(CreateTopicDTO(subject_id=sub.id, name="A"))


@pytest.mark.unit
def test_list_topics_by_subject() -> None:
    """Listagem de temas filtrada por matéria e ordenada."""
    subject_repo = FakeSubjectRepository()
    topic_repo = FakeTopicRepository()

    sub1 = Subject(name="Sub 1")
    sub2 = Subject(name="Sub 2")
    subject_repo.save(sub1)
    subject_repo.save(sub2)

    create_uc = CreateTopicUseCase(subject_repo, topic_repo)
    create_uc.execute(CreateTopicDTO(subject_id=sub1.id, name="Tema Z"))
    create_uc.execute(CreateTopicDTO(subject_id=sub1.id, name="Tema A"))
    create_uc.execute(CreateTopicDTO(subject_id=sub2.id, name="Outro"))

    list_uc = ListTopicsBySubjectUseCase(topic_repo)
    topics = list_uc.execute(sub1.id)

    assert [t.name for t in topics] == ["Tema A", "Tema Z"]
