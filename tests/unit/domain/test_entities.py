"""Testes unitários para as entidades de domínio e invariantes (ADR-001, ADR-002)."""

from datetime import date, datetime
from uuid import UUID, uuid4

import pytest

from src.domain.entities import Flashcard, FlashcardPoolSession, Subject, Topic
from src.domain.exceptions import DomainValidationError


@pytest.mark.unit
def test_subject_creation_valid() -> None:
    """Verifica a instanciação válida de uma Matéria."""
    sub_id = uuid4()
    today = date(2026, 10, 2)
    subject = Subject(id=sub_id, name="  Direito Constitucional  ", created_at=today)

    assert subject.id == sub_id
    assert subject.name == "Direito Constitucional"  # Trimming validado
    assert subject.created_at == today


@pytest.mark.unit
def test_subject_default_values() -> None:
    """Verifica a geração automática de ID e data de criação em Subject."""
    subject = Subject(name="Matemática")
    assert isinstance(subject.id, UUID)
    assert subject.name == "Matemática"
    assert isinstance(subject.created_at, date)


@pytest.mark.unit
@pytest.mark.parametrize("invalid_name", ["", "   ", "A", "x" * 101])
def test_subject_invalid_name_raises_domain_error(invalid_name: str) -> None:
    """Garante que nomes inválidos para Subject sejam rejeitados."""
    with pytest.raises(
        DomainValidationError, match="Nome da matéria deve ter entre 2 e 100 caracteres"
    ):
        Subject(name=invalid_name)


@pytest.mark.unit
def test_topic_creation_valid() -> None:
    """Verifica a instanciação válida de um Tema."""
    subject_id = uuid4()
    topic = Topic(subject_id=subject_id, name="  Direitos Fundamentais  ")

    assert isinstance(topic.id, UUID)
    assert topic.subject_id == subject_id
    assert topic.name == "Direitos Fundamentais"
    assert isinstance(topic.created_at, date)


@pytest.mark.unit
@pytest.mark.parametrize("invalid_name", ["", "   ", "A", "z" * 101])
def test_topic_invalid_name_raises_domain_error(invalid_name: str) -> None:
    """Garante que nomes inválidos para Topic sejam rejeitados."""
    with pytest.raises(
        DomainValidationError, match="Nome do tema deve ter entre 2 e 100 caracteres"
    ):
        Topic(subject_id=uuid4(), name=invalid_name)


@pytest.mark.unit
def test_flashcard_creation_valid() -> None:
    """Verifica a instanciação válida de um Flashcard com position."""
    topic_id = uuid4()
    card = Flashcard(
        topic_id=topic_id,
        front="  O que é CF/88?  ",
        back="  Constituição da República  ",
        position=100,
    )

    assert isinstance(card.id, UUID)
    assert card.topic_id == topic_id
    assert card.front == "O que é CF/88?"
    assert card.back == "Constituição da República"
    assert card.position == 100
    assert isinstance(card.created_at, date)


@pytest.mark.unit
def test_flashcard_default_position() -> None:
    """Verifica que a posição padrão é 100."""
    card = Flashcard(topic_id=uuid4(), front="Pergunta", back="Resposta")
    assert card.position == 100


@pytest.mark.unit
def test_flashcard_multi_topic_support() -> None:
    """Valida suporte a múltiplos temas, conversão de lista para tupla e primary_topic_id."""
    t1, t2, t3 = uuid4(), uuid4(), uuid4()
    card = Flashcard(topic_ids=[t1, t2, t3], front="Pergunta", back="Resposta")
    assert card.topic_ids == (t1, t2, t3)
    assert card.primary_topic_id == t1
    assert card.topic_id == t1


@pytest.mark.unit
def test_flashcard_empty_topics_raises_error() -> None:
    """Flashcard sem nenhum tema dispara DomainValidationError."""
    with pytest.raises(
        DomainValidationError, match="Flashcard deve estar associado a pelo menos 1 tema."
    ):
        Flashcard(topic_ids=(), front="P", back="R")


@pytest.mark.unit
def test_flashcard_more_than_five_topics_raises_error() -> None:
    """Flashcard com mais de 5 temas dispara DomainValidationError (teto defensivo)."""
    topics = [uuid4() for _ in range(6)]
    with pytest.raises(
        DomainValidationError, match="Flashcard pode estar associado a no máximo 5 temas."
    ):
        Flashcard(topic_ids=topics, front="P", back="R")


@pytest.mark.unit
def test_flashcard_duplicate_topics_raises_error() -> None:
    """Flashcard com temas duplicados dispara DomainValidationError."""
    dup_id = uuid4()
    with pytest.raises(DomainValidationError, match="Flashcard não pode conter temas duplicados."):
        Flashcard(topic_ids=[dup_id, dup_id], front="P", back="R")


@pytest.mark.unit
@pytest.mark.parametrize("invalid_front", ["", "   ", "x" * 5001])
def test_flashcard_invalid_front_raises_error(invalid_front: str) -> None:
    """Garante que frente vazia ou > 5000 chars seja rejeitada."""
    with pytest.raises(
        DomainValidationError, match="Frente do flashcard deve ter entre 1 e 5.000 caracteres"
    ):
        Flashcard(topic_id=uuid4(), front=invalid_front, back="Resposta válida")


@pytest.mark.unit
@pytest.mark.parametrize("invalid_back", ["", "   ", "y" * 10001])
def test_flashcard_invalid_back_raises_error(invalid_back: str) -> None:
    """Garante que verso vazio ou > 10000 chars seja rejeitado."""
    with pytest.raises(
        DomainValidationError, match="Verso do flashcard deve ter entre 1 e 10.000 caracteres"
    ):
        Flashcard(topic_id=uuid4(), front="Pergunta válida", back=invalid_back)


@pytest.mark.unit
def test_flashcard_invalid_position_raises_error() -> None:
    """Garante que posição <= 0 seja rejeitada."""
    msg = "Posição do flashcard deve ser um inteiro positivo maior ou igual a 1"
    with pytest.raises(DomainValidationError, match=msg):
        Flashcard(topic_id=uuid4(), front="Pergunta", back="Resposta", position=0)

    with pytest.raises(DomainValidationError, match=msg):
        Flashcard(topic_id=uuid4(), front="Pergunta", back="Resposta", position=-10)


@pytest.mark.unit
def test_flashcard_pool_session_creation_valid() -> None:
    """Verifica a criação de sessão com valores padrão."""
    session = FlashcardPoolSession()

    assert isinstance(session.id, UUID)
    assert session.subject_id_filter is None
    assert session.topic_id_filter is None
    assert session.current_position == 0
    assert session.round_number == 1
    assert session.current_index == 0
    assert session.card_queue == []
    assert session.is_active is True
    assert isinstance(session.updated_at, datetime)


@pytest.mark.unit
def test_flashcard_pool_session_invalid_round_raises_error() -> None:
    """Garante que número de rodada < 1 seja rejeitado."""
    with pytest.raises(DomainValidationError, match="O número da rodada deve ser >= 1"):
        FlashcardPoolSession(round_number=0)


@pytest.mark.unit
def test_flashcard_pool_session_invalid_index_raises_error() -> None:
    """Garante que cursor negativo seja rejeitado com DomainValidationError."""
    with pytest.raises(DomainValidationError, match="O índice atual não pode ser negativo"):
        FlashcardPoolSession(current_index=-1)


@pytest.mark.unit
def test_flashcard_pool_session_advance() -> None:
    """Verifica métodos de transição de estado da sessão."""
    session = FlashcardPoolSession()
    session.advance_to(200)
    assert session.current_position == 200

    session.next_round(initial_position=100)
    assert session.round_number == 2
    assert session.current_position == 100


@pytest.mark.unit
def test_flashcard_pool_session_queue_advance_and_round_management() -> None:
    """Valida get_current_card_id, advance, is_round_finished e start_new_round."""
    id1, id2 = uuid4(), uuid4()
    session = FlashcardPoolSession(card_queue=[id1, id2])

    assert session.get_current_card_id() == id1
    assert session.is_round_finished() is False

    session.advance()
    assert session.current_index == 1
    assert session.get_current_card_id() == id2
    assert session.is_round_finished() is False

    session.advance()
    assert session.current_index == 2
    assert session.get_current_card_id() is None
    assert session.is_round_finished() is True

    # Nova rodada com lista vazia deve disparar erro
    with pytest.raises(DomainValidationError, match="A nova rodada requer uma lista não-vazia"):
        session.start_new_round([])

    # Nova rodada válida
    id3 = uuid4()
    session.start_new_round([id3])
    assert session.round_number == 2
    assert session.current_index == 0
    assert session.card_queue == [id3]
    assert session.get_current_card_id() == id3
    assert session.is_round_finished() is False


@pytest.mark.unit
def test_study_session_exceptions_hierarchy() -> None:
    """Valida a hierarquia de exceções de sessão de estudo."""
    from src.domain.exceptions import (
        DomainException,
        SessionDesynchronizedError,
        SessionExpiredError,
        SessionQueueEmptyError,
        StudySessionError,
    )

    err1 = SessionExpiredError("Sessão expirada")
    err2 = SessionQueueEmptyError("Fila vazia")
    err3 = SessionDesynchronizedError("Cursor dessincronizado")

    for err in [err1, err2, err3]:
        assert isinstance(err, StudySessionError)
        assert isinstance(err, DomainException)


@pytest.mark.unit
def test_subject_permissions_with_none_user_id() -> None:
    """Valida can_be_edited_by e can_be_studied_by com user_id nulo (None)."""
    subject_private = Subject(name="Direito Civil", owner_id=uuid4(), is_public=False)
    assert subject_private.can_be_edited_by(None) is False
    assert subject_private.can_be_studied_by(None) is False

    subject_public = Subject(name="Direito Público", owner_id=uuid4(), is_public=True)
    assert subject_public.can_be_edited_by(None) is False
    assert subject_public.can_be_studied_by(None) is True
