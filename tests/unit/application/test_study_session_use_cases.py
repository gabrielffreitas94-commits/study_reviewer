"""Testes unitários para o fluxo de estudo e rotação de rodadas (Camada 2 - Aplicação)."""

from uuid import uuid4

import pytest

from src.application.dto.study_dto import GetNextCardDTO
from src.application.use_cases.study_session_use_cases import (
    GetCurrentStudyCardUseCase,
    GetNextFlashcardUseCase,
    GetStudyBatchUseCase,
)
from src.domain.entities import Flashcard, FlashcardPoolSession, Subject, Topic
from src.domain.exceptions import EmptyPoolError, ResourceOwnershipError
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
    # Como FakeRandomGenerator inverte a lista, C2 virou o primeiro card da fila efêmera da sessão
    assert dto.id == c2.id
    assert dto.position == 200  # Posição imutável do catálogo mantida (Zero Write Amplification)


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


@pytest.mark.unit
def test_get_current_card_empty_pool_raises() -> None:
    """GetCurrentStudyCardUseCase com pool vazia dispara EmptyPoolError."""
    topic_repo = FakeTopicRepository()
    card_repo = FakeFlashcardRepository(topic_repo)
    session_repo = FakeSessionRepository()
    use_case = GetCurrentStudyCardUseCase(card_repo, session_repo)

    with pytest.raises(EmptyPoolError):
        use_case.execute(GetNextCardDTO())


@pytest.mark.unit
def test_get_current_card_initial_session_returns_first_card_without_advancing() -> None:
    """GetCurrentStudyCardUseCase em nova sessão retorna primeiro card sem shuffle."""
    topic_repo = FakeTopicRepository()
    card_repo = FakeFlashcardRepository(topic_repo)
    session_repo = FakeSessionRepository()

    t_id = uuid4()
    c1 = Flashcard(topic_id=t_id, front="C1", back="1", position=100)
    c2 = Flashcard(topic_id=t_id, front="C2", back="2", position=200)
    card_repo.save(c1)
    card_repo.save(c2)

    use_case = GetCurrentStudyCardUseCase(card_repo, session_repo)
    dto = use_case.execute(GetNextCardDTO(topic_id=t_id))

    assert dto.id == c1.id
    assert dto.current_index == 1
    assert dto.round_shuffled is False
    assert dto.round_number == 1

    # Chamada repetida não avança e não faz shuffle
    dto2 = use_case.execute(GetNextCardDTO(topic_id=t_id))
    assert dto2.id == c1.id
    assert dto2.round_shuffled is False


@pytest.mark.unit
def test_get_current_card_existing_session_matches_current_position() -> None:
    """GetCurrentStudyCardUseCase recupera card exatamente na posição salva da sessão."""
    topic_repo = FakeTopicRepository()
    card_repo = FakeFlashcardRepository(topic_repo)
    session_repo = FakeSessionRepository()

    t_id = uuid4()
    c1 = Flashcard(topic_id=t_id, front="C1", back="1", position=100)
    c2 = Flashcard(topic_id=t_id, front="C2", back="2", position=200)
    card_repo.save(c1)
    card_repo.save(c2)

    session = FlashcardPoolSession(topic_id_filter=t_id, current_position=200, round_number=3)
    session_repo.save_session(session)

    use_case = GetCurrentStudyCardUseCase(card_repo, session_repo)
    dto = use_case.execute(GetNextCardDTO(topic_id=t_id))

    assert dto.id == c2.id
    assert dto.position == 200
    assert dto.current_index == 2
    assert dto.round_number == 3
    assert dto.round_shuffled is False


@pytest.mark.unit
def test_get_current_card_fallback_when_card_deleted() -> None:
    """GetCurrentStudyCardUseCase faz fallback suave se o card da posição foi deletado."""
    topic_repo = FakeTopicRepository()
    card_repo = FakeFlashcardRepository(topic_repo)
    session_repo = FakeSessionRepository()

    t_id = uuid4()
    c2 = Flashcard(topic_id=t_id, front="C2", back="2", position=200)
    card_repo.save(c2)

    # Sessão apontava para posição 100 que não existe mais
    session = FlashcardPoolSession(topic_id_filter=t_id, current_position=100, round_number=1)
    session_repo.save_session(session)

    use_case = GetCurrentStudyCardUseCase(card_repo, session_repo)
    dto = use_case.execute(GetNextCardDTO(topic_id=t_id))

    assert dto.id == c2.id
    assert dto.position == 200
    assert dto.round_shuffled is False


@pytest.mark.unit
def test_get_study_batch_empty_pool_raises_empty_pool_error() -> None:
    """GetStudyBatchUseCase dispara EmptyPoolError quando a pool está vazia."""
    card_repo = FakeFlashcardRepository()
    session_repo = FakeSessionRepository()
    use_case = GetStudyBatchUseCase(card_repo, session_repo)

    with pytest.raises(EmptyPoolError):
        use_case.execute(GetNextCardDTO())


@pytest.mark.unit
def test_get_study_batch_success_with_topics_and_pagination() -> None:
    """GetStudyBatchUseCase retorna lote de cards com metadados de tópicos e paginação."""
    topic_repo = FakeTopicRepository()
    card_repo = FakeFlashcardRepository(topic_repo)
    session_repo = FakeSessionRepository()

    t = Topic(subject_id=uuid4(), name="Direito Tributário")
    topic_repo.save(t)

    c1 = Flashcard(topic_id=t.id, front="F1", back="V1", position=100)
    c2 = Flashcard(topic_id=t.id, front="F2", back="V2", position=200)
    card_repo.save(c1)
    card_repo.save(c2)

    use_case = GetStudyBatchUseCase(card_repo, session_repo, topic_repo)

    # 1. Busca lote inicial com limite 1
    batch1 = use_case.execute(GetNextCardDTO(topic_id=t.id), limit=1)
    assert len(batch1.cards) == 1
    assert batch1.cards[0].id == c1.id
    assert batch1.cards[0].topic_names == ["Direito Tributário"]
    assert batch1.total_cards == 2
    assert batch1.has_more is True

    # 2. Simula avanço na sessão e busca próximo lote
    session = session_repo.get_active_session(None, t.id)
    assert session is not None
    session.advance_to(100)
    session_repo.save_session(session)

    batch2 = use_case.execute(GetNextCardDTO(topic_id=t.id), limit=100)
    assert len(batch2.cards) == 1
    assert batch2.cards[0].id == c2.id
    assert batch2.has_more is False

    # 3. Quando não há mais cards após a posição atual, busca do início
    session.advance_to(300)
    session_repo.save_session(session)
    batch3 = use_case.execute(GetNextCardDTO(topic_id=t.id), limit=100)
    assert len(batch3.cards) == 2


@pytest.mark.unit
def test_get_next_and_current_card_with_topic_repo() -> None:
    """Verifica resolução de nomes de temas em GetNextFlashcardUseCase
    e GetCurrentStudyCardUseCase.
    """
    topic_repo = FakeTopicRepository()
    card_repo = FakeFlashcardRepository(topic_repo)
    session_repo = FakeSessionRepository()
    rng = FakeRandomGenerator()

    t = Topic(subject_id=uuid4(), name="Direito Penal")
    topic_repo.save(t)

    card = Flashcard(topic_id=t.id, front="Crime", back="Fato típico", position=100)
    card_repo.save(card)

    next_uc = GetNextFlashcardUseCase(card_repo, session_repo, rng, topic_repo)
    dto_next = next_uc.execute(GetNextCardDTO(topic_id=t.id))
    assert dto_next.topic_names == ["Direito Penal"]

    curr_uc = GetCurrentStudyCardUseCase(card_repo, session_repo, topic_repo)
    dto_curr = curr_uc.execute(GetNextCardDTO(topic_id=t.id))
    assert dto_curr.topic_names == ["Direito Penal"]


@pytest.mark.unit
@pytest.mark.security
def test_get_next_card_private_subject_raises_ownership_error() -> None:
    """Impede que estudante acesse card de matéria privada pertencente a outrem.

    Vulnerabilidade prevenida: Insecure Direct Object Reference (IDOR) e quebra de privacidade.
    Garantia de segurança: Lança ResourceOwnershipError ao tentar estudar matéria privada de outro.
    """
    subject_repo = FakeSubjectRepository()
    card_repo = FakeFlashcardRepository(FakeTopicRepository())
    session_repo = FakeSessionRepository()
    rng = FakeRandomGenerator()

    owner_id = uuid4()
    intruder_id = uuid4()
    subject = Subject(name="Privada", owner_id=owner_id, is_public=False)
    subject_repo.save(subject)

    use_case = GetNextFlashcardUseCase(
        card_repo=card_repo,
        session_repo=session_repo,
        rng=rng,
        subject_repo=subject_repo,
    )

    with pytest.raises(ResourceOwnershipError, match="Você não tem acesso a esta matéria privada"):
        use_case.execute(GetNextCardDTO(subject_id=subject.id), user_id=intruder_id)


@pytest.mark.unit
@pytest.mark.security
def test_get_study_batch_private_subject_raises_ownership_error() -> None:
    """Impede que estudante solicite lote de revisão de matéria privada pertencente a outrem.

    Vulnerabilidade prevenida: Insecure Direct Object Reference (IDOR) e vazamento de dados.
    Garantia de segurança: Lança ResourceOwnershipError ao solicitar batch
    de matéria privada alheia.
    """
    subject_repo = FakeSubjectRepository()
    card_repo = FakeFlashcardRepository(FakeTopicRepository())
    session_repo = FakeSessionRepository()

    owner_id = uuid4()
    intruder_id = uuid4()
    subject = Subject(name="Privada Batch", owner_id=owner_id, is_public=False)
    subject_repo.save(subject)

    use_case = GetStudyBatchUseCase(
        card_repo=card_repo,
        session_repo=session_repo,
        subject_repo=subject_repo,
    )

    with pytest.raises(ResourceOwnershipError, match="Você não tem acesso a esta matéria privada"):
        use_case.execute(GetNextCardDTO(subject_id=subject.id), user_id=intruder_id)


@pytest.mark.unit
@pytest.mark.security
def test_get_current_study_card_private_subject_raises_ownership_error() -> None:
    """Impede leitura de card corrente de matéria privada pertencente a outrem.

    Vulnerabilidade prevenida: Insecure Direct Object Reference (IDOR) e quebra
    de confidencialidade.
    Garantia de segurança: Lança ResourceOwnershipError ao inspecionar card corrente
    de matéria privada alheia.
    """
    subject_repo = FakeSubjectRepository()
    card_repo = FakeFlashcardRepository(FakeTopicRepository())
    session_repo = FakeSessionRepository()

    owner_id = uuid4()
    intruder_id = uuid4()
    subject = Subject(name="Privada Current", owner_id=owner_id, is_public=False)
    subject_repo.save(subject)

    use_case = GetCurrentStudyCardUseCase(
        card_repo=card_repo,
        session_repo=session_repo,
        subject_repo=subject_repo,
    )

    with pytest.raises(ResourceOwnershipError, match="Você não tem acesso a esta matéria privada"):
        use_case.execute(GetNextCardDTO(subject_id=subject.id), user_id=intruder_id)


@pytest.mark.unit
def test_get_next_card_uninitialized_session_zero_position() -> None:
    """Sessão existente com current_position=0 e card_queue vazia inicializa current_index=0."""
    card_repo = FakeFlashcardRepository()
    session_repo = FakeSessionRepository()
    rng = FakeRandomGenerator()

    t_id = uuid4()
    c1 = Flashcard(topic_id=t_id, front="C1", back="1", position=100)
    card_repo.save(c1)

    session = FlashcardPoolSession(topic_id_filter=t_id, current_position=0, card_queue=[])
    session_repo.save_session(session)

    use_case = GetNextFlashcardUseCase(card_repo, session_repo, rng)
    dto = use_case.execute(GetNextCardDTO(topic_id=t_id))
    assert dto.id == c1.id
    assert dto.current_index == 1


@pytest.mark.unit
def test_get_next_card_stale_card_id_regenerates_shuffle() -> None:
    """Card ID na fila que não existe mais no repositório aciona reembaralhamento da rodada."""
    card_repo = FakeFlashcardRepository()
    session_repo = FakeSessionRepository()
    rng = FakeRandomGenerator()

    t_id = uuid4()
    c1 = Flashcard(topic_id=t_id, front="C1", back="1", position=100)
    card_repo.save(c1)

    # Sessão aponta para um UUID que não existe mais no catálogo
    session = FlashcardPoolSession(
        topic_id_filter=t_id, current_position=100, card_queue=[uuid4()], current_index=0
    )
    session_repo.save_session(session)

    use_case = GetNextFlashcardUseCase(card_repo, session_repo, rng)
    dto = use_case.execute(GetNextCardDTO(topic_id=t_id))
    assert dto.id == c1.id
    assert dto.round_shuffled is True


@pytest.mark.unit
def test_get_current_card_fallback_greater_equal_position() -> None:
    """Quando o card atual não existe na fila e não há match exato, busca próxima posição >=."""
    card_repo = FakeFlashcardRepository()
    session_repo = FakeSessionRepository()

    t_id = uuid4()
    c1 = Flashcard(topic_id=t_id, front="C1", back="1", position=100)
    c2 = Flashcard(topic_id=t_id, front="C2", back="2", position=200)
    card_repo.save(c1)
    card_repo.save(c2)

    # current_position = 150 (não há match exato, busca c2 que tem position >= 150)
    session = FlashcardPoolSession(
        topic_id_filter=t_id, current_position=150, card_queue=[uuid4()], current_index=0
    )
    session_repo.save_session(session)

    use_case = GetCurrentStudyCardUseCase(card_repo, session_repo)
    dto = use_case.execute(GetNextCardDTO(topic_id=t_id))
    assert dto.id == c2.id
    assert dto.position == 200


@pytest.mark.unit
def test_get_study_batch_uninitialized_session_and_fallbacks() -> None:
    """Testa inicialização de card_queue vazia e fallbacks de batch_ids e cards vazios."""
    card_repo = FakeFlashcardRepository()
    session_repo = FakeSessionRepository()

    t_id = uuid4()
    c1 = Flashcard(topic_id=t_id, front="C1", back="1", position=100)
    c2 = Flashcard(topic_id=t_id, front="C2", back="2", position=200)
    card_repo.save(c1)
    card_repo.save(c2)

    # 1. Sessão sem card_queue
    session = FlashcardPoolSession(topic_id_filter=t_id, current_position=0, card_queue=[])
    session_repo.save_session(session)

    use_case = GetStudyBatchUseCase(card_repo, session_repo)
    batch = use_case.execute(GetNextCardDTO(topic_id=t_id), limit=10)
    assert len(batch.cards) == 2

    # 2. Sessão onde start_index ultrapassa a fila (batch_ids vazio)
    session.current_position = 200
    session.card_queue = [c1.id, c2.id]
    session_repo.save_session(session)
    batch2 = use_case.execute(GetNextCardDTO(topic_id=t_id), limit=10)
    assert len(batch2.cards) == 2

    # 3. Sessão onde batch_ids contém UUIDs que não estão no cards_map (cards vazio)
    session.card_queue = [uuid4(), uuid4()]
    session.current_position = 0
    session_repo.save_session(session)
    batch3 = use_case.execute(GetNextCardDTO(topic_id=t_id), limit=10)
    assert len(batch3.cards) == 2
