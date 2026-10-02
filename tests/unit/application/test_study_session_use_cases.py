"""Testes unitários para o fluxo de estudo e rotação de rodadas (Camada 2 - Aplicação)."""

from uuid import uuid4

import pytest

from src.application.dto.study_dto import GetNextCardDTO
from src.application.use_cases.study_session_use_cases import GetNextFlashcardUseCase
from src.domain.entities import Flashcard, FlashcardPoolSession, Subject, Topic
from src.domain.exceptions import EmptyPoolError
from tests.unit.application.fakes import (
    FakeFlashcardRepository,
    FakeRandomGenerator,
    FakeSessionRepository,
    FakeSubjectRepository,
    FakeTopicRepository,
)


@pytest.mark.unit
def test_get_next_card_empty_pool_raises_empty_pool_error() -> None:
    """Tentativa de estudar com pool vazia dispara EmptyPoolError."""
    topic_repo = FakeTopicRepository()
    card_repo = FakeFlashcardRepository(topic_repo)
    session_repo = FakeSessionRepository()
    rng = FakeRandomGenerator()

    use_case = GetNextFlashcardUseCase(card_repo, session_repo, rng)

    with pytest.raises(EmptyPoolError, match="Nenhum flashcard disponível para estudo"):
        use_case.execute(GetNextCardDTO())


@pytest.mark.unit
def test_get_next_card_initial_round_first_card() -> None:
    """Primeira chamada de estudo em rodada nova retorna o primeiro card."""
    topic_repo = FakeTopicRepository()
    card_repo = FakeFlashcardRepository(topic_repo)
    session_repo = FakeSessionRepository()
    rng = FakeRandomGenerator()

    t_id = uuid4()
    c1 = Flashcard(topic_id=t_id, front="C1", back="1", position=100)
    c2 = Flashcard(topic_id=t_id, front="C2", back="2", position=200)
    card_repo.save(c1)
    card_repo.save(c2)

    use_case = GetNextFlashcardUseCase(card_repo, session_repo, rng)
    dto = use_case.execute(GetNextCardDTO(topic_id=t_id))

    assert dto.id == c1.id
    assert dto.front == "C1"
    assert dto.position == 100
    assert dto.current_index == 1
    assert dto.total_cards == 2
    assert dto.round_number == 1
    assert dto.round_shuffled is False

    session = session_repo.get_active_session(None, t_id)
    assert session is not None
    assert session.current_position == 100


@pytest.mark.unit
def test_get_next_card_sequential_advance() -> None:
    """Avanço sequencial dentro da mesma rodada."""
    topic_repo = FakeTopicRepository()
    card_repo = FakeFlashcardRepository(topic_repo)
    session_repo = FakeSessionRepository()
    rng = FakeRandomGenerator()

    t_id = uuid4()
    c1 = Flashcard(topic_id=t_id, front="C1", back="1", position=100)
    c2 = Flashcard(topic_id=t_id, front="C2", back="2", position=200)
    card_repo.save(c1)
    card_repo.save(c2)

    # Sessão já no card 1
    session = FlashcardPoolSession(topic_id_filter=t_id, current_position=100)
    session_repo.save_session(session)

    use_case = GetNextFlashcardUseCase(card_repo, session_repo, rng)
    dto = use_case.execute(GetNextCardDTO(topic_id=t_id))

    assert dto.id == c2.id
    assert dto.position == 200
    assert dto.current_index == 2
    assert dto.round_number == 1
    assert dto.round_shuffled is False


@pytest.mark.unit
def test_get_next_card_end_of_round_triggers_shuffle_and_increments_round() -> None:
    """Fim de rodada dispara shuffle geral, incrementa round_number e retorna primeiro card."""
    topic_repo = FakeTopicRepository()
    card_repo = FakeFlashcardRepository(topic_repo)
    session_repo = FakeSessionRepository()
    rng = FakeRandomGenerator()

    t_id = uuid4()
    c1 = Flashcard(topic_id=t_id, front="C1", back="1", position=100)
    c2 = Flashcard(topic_id=t_id, front="C2", back="2", position=200)
    card_repo.save(c1)
    card_repo.save(c2)

    # Sessão no último card da rodada 1
    session = FlashcardPoolSession(topic_id_filter=t_id, current_position=200, round_number=1)
    session_repo.save_session(session)

    use_case = GetNextFlashcardUseCase(card_repo, session_repo, rng)
    dto = use_case.execute(GetNextCardDTO(topic_id=t_id))

    assert rng.shuffled is True
    assert dto.round_number == 2
    assert dto.round_shuffled is True
    assert dto.current_index == 1
    # Como FakeRandomGenerator inverte a lista, C2 virou o primeiro card (position=100)
    assert dto.id == c2.id
    assert dto.position == 100


@pytest.mark.unit
def test_get_next_card_with_subject_filter() -> None:
    """Estudo com filtro de matéria considera todos os temas daquela matéria."""
    subject_repo = FakeSubjectRepository()
    topic_repo = FakeTopicRepository()
    card_repo = FakeFlashcardRepository(topic_repo)
    session_repo = FakeSessionRepository()
    rng = FakeRandomGenerator()

    sub = Subject(name="Direito")
    subject_repo.save(sub)

    t1 = Topic(subject_id=sub.id, name="Tema 1")
    t2 = Topic(subject_id=sub.id, name="Tema 2")
    topic_repo.save(t1)
    topic_repo.save(t2)

    c1 = Flashcard(topic_id=t1.id, front="C1", back="1", position=100)
    c2 = Flashcard(topic_id=t2.id, front="C2", back="2", position=200)
    card_repo.save(c1)
    card_repo.save(c2)

    use_case = GetNextFlashcardUseCase(card_repo, session_repo, rng)
    dto = use_case.execute(GetNextCardDTO(subject_id=sub.id))

    assert dto.total_cards == 2
    assert dto.id == c1.id
