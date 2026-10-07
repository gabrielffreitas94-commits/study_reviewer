"""Testes unitários para os casos de uso de Flashcards (Camada 2 - Aplicação)."""

from uuid import uuid4

import pytest

from src.application.dto.flashcard_dto import CreateFlashcardDTO, FlashcardDTO
from src.application.dto.study_dto import StudyCardDTO
from src.application.use_cases.flashcard_use_cases import (
    CreateFlashcardUseCase,
    DeleteFlashcardUseCase,
)
from src.domain.entities import Flashcard, FlashcardPoolSession, Subject, Topic
from src.domain.exceptions import (
    DomainValidationError,
    EntityNotFoundError,
    ResourceOwnershipError,
)
from tests.unit.application.fakes import (
    FakeFlashcardRepository,
    FakeRandomGenerator,
    FakeSessionRepository,
    FakeSubjectRepository,
    FakeTopicRepository,
)


@pytest.mark.unit
def test_create_flashcard_in_empty_pool() -> None:
    """Criação do primeiro flashcard em pool vazia recebe position = 100."""
    topic_repo = FakeTopicRepository()
    card_repo = FakeFlashcardRepository(topic_repo)
    session_repo = FakeSessionRepository()
    rng = FakeRandomGenerator()

    topic = Topic(subject_id=uuid4(), name="Tema 1")
    topic_repo.save(topic)

    use_case = CreateFlashcardUseCase(card_repo, topic_repo, session_repo, rng)
    dto = use_case.execute(
        CreateFlashcardDTO(
            topic_id=topic.id,
            front="O que é Clean Architecture?",
            back="Arquitetura concêntrica em camadas com regra de dependência.",
        )
    )

    assert dto.position == 100
    assert dto.front == "O que é Clean Architecture?"
    assert card_repo.count_pool(None, topic.id) == 1


@pytest.mark.unit
def test_create_flashcard_target_middle_point() -> None:
    """Inserção de novo card calcula ponto médio nos primeiros 10%."""
    topic_repo = FakeTopicRepository()
    card_repo = FakeFlashcardRepository(topic_repo)
    session_repo = FakeSessionRepository()
    rng = FakeRandomGenerator(fixed_randint=0)  # Sorteia índice 0 (cabeça)

    topic = Topic(subject_id=uuid4(), name="Tema 1")
    topic_repo.save(topic)

    # Inserir card inicial na posição 100
    c1 = Flashcard(topic_id=topic.id, front="C1", back="1", position=100)
    card_repo.save(c1)

    use_case = CreateFlashcardUseCase(card_repo, topic_repo, session_repo, rng)
    dto = use_case.execute(CreateFlashcardDTO(topic_id=topic.id, front="C2", back="2"))

    # Cabeça antes de 100 -> ponto médio floor(100 / 2) = 50
    assert dto.position == 50


@pytest.mark.unit
def test_create_flashcard_triggers_rebalance_when_gap_depleted() -> None:
    """Inserção que provoca colisão ou esgotamento de gap dispara rebalanceamento."""
    topic_repo = FakeTopicRepository()
    card_repo = FakeFlashcardRepository(topic_repo)
    session_repo = FakeSessionRepository()
    # Inserção no índice 0
    rng = FakeRandomGenerator(fixed_randint=0)

    topic = Topic(subject_id=uuid4(), name="Tema 1")
    topic_repo.save(topic)

    # Cards já com gap muito apertado: 2 e 3
    c1 = Flashcard(topic_id=topic.id, front="C1", back="1", position=2)
    c2 = Flashcard(topic_id=topic.id, front="C2", back="2", position=3)
    card_repo.save(c1)
    card_repo.save(c2)

    use_case = CreateFlashcardUseCase(card_repo, topic_repo, session_repo, rng)
    dto = use_case.execute(CreateFlashcardDTO(topic_id=topic.id, front="C0", back="0"))

    # Como a inserção gerou posição 1 (needs_rebalance=True),
    # todos são rebalanceados para 100, 200, 300
    pool = card_repo.list_pool(None, topic.id)
    assert [c.position for c in pool] == [100, 200, 300]
    assert dto.position == 100


@pytest.mark.unit
def test_create_flashcard_topic_not_found() -> None:
    """Tentativa de criar card para tema inexistente lança EntityNotFoundError."""
    topic_repo = FakeTopicRepository()
    card_repo = FakeFlashcardRepository(topic_repo)
    session_repo = FakeSessionRepository()
    rng = FakeRandomGenerator()

    use_case = CreateFlashcardUseCase(card_repo, topic_repo, session_repo, rng)
    with pytest.raises(EntityNotFoundError, match="Tema não encontrado."):
        use_case.execute(CreateFlashcardDTO(topic_id=uuid4(), front="F", back="B"))


@pytest.mark.unit
def test_delete_flashcard_success() -> None:
    """Exclusão de flashcard com sucesso."""
    topic_repo = FakeTopicRepository()
    card_repo = FakeFlashcardRepository(topic_repo)
    session_repo = FakeSessionRepository()
    rng = FakeRandomGenerator()

    c = Flashcard(topic_id=uuid4(), front="F", back="B")
    card_repo.save(c)

    use_case = DeleteFlashcardUseCase(card_repo, session_repo, rng)
    use_case.execute(c.id)

    assert card_repo.get_by_id(c.id) is None


@pytest.mark.unit
def test_delete_flashcard_not_found() -> None:
    """Tentativa de excluir flashcard inexistente lança EntityNotFoundError."""
    card_repo = FakeFlashcardRepository()
    session_repo = FakeSessionRepository()
    rng = FakeRandomGenerator()

    use_case = DeleteFlashcardUseCase(card_repo, session_repo, rng)
    with pytest.raises(EntityNotFoundError, match="Flashcard não encontrado."):
        use_case.execute(uuid4())


@pytest.mark.unit
def test_delete_flashcard_advances_active_session() -> None:
    """Excluir o card que estava em exibição na sessão avança o ponteiro."""
    topic_repo = FakeTopicRepository()
    card_repo = FakeFlashcardRepository(topic_repo)
    session_repo = FakeSessionRepository()
    rng = FakeRandomGenerator()

    t_id = uuid4()
    c1 = Flashcard(topic_id=t_id, front="1", back="1", position=100)
    c2 = Flashcard(topic_id=t_id, front="2", back="2", position=200)
    card_repo.save(c1)
    card_repo.save(c2)

    session = FlashcardPoolSession(
        topic_id_filter=t_id, current_position=100, card_queue=[c1.id, c2.id]
    )
    session_repo.save_session(session)

    use_case = DeleteFlashcardUseCase(card_repo, session_repo, rng)
    use_case.execute(c1.id)

    # Card 1 deletado
    assert card_repo.get_by_id(c1.id) is None
    # Sessão atualizada para o próximo card (200)
    updated_session = session_repo.get_active_session(None, t_id)
    assert updated_session is not None
    assert updated_session.current_position == 200


@pytest.mark.unit
def test_create_flashcard_tail_insertion() -> None:
    """Inserção com target_idx maior ou igual ao tamanho da pool insere no fim."""
    topic_repo = FakeTopicRepository()
    card_repo = FakeFlashcardRepository(topic_repo)
    session_repo = FakeSessionRepository()
    rng = FakeRandomGenerator(fixed_randint=99)  # Força índice maior que len(pool)

    topic = Topic(subject_id=uuid4(), name="Tema 1")
    topic_repo.save(topic)

    c1 = Flashcard(topic_id=topic.id, front="C1", back="1", position=100)
    card_repo.save(c1)

    use_case = CreateFlashcardUseCase(card_repo, topic_repo, session_repo, rng)
    dto = use_case.execute(CreateFlashcardDTO(topic_id=topic.id, front="C2", back="2"))

    assert dto.position == 200


@pytest.mark.unit
def test_create_flashcard_between_insertion() -> None:
    """Inserção entre dois cards existentes no ponto intermediário."""
    topic_repo = FakeTopicRepository()
    card_repo = FakeFlashcardRepository(topic_repo)
    session_repo = FakeSessionRepository()
    rng = FakeRandomGenerator(fixed_randint=1)  # Índice 1 (entre o card 0 e o card 1)

    topic = Topic(subject_id=uuid4(), name="Tema 1")
    topic_repo.save(topic)

    c1 = Flashcard(topic_id=topic.id, front="C1", back="1", position=100)
    c2 = Flashcard(topic_id=topic.id, front="C2", back="2", position=200)
    card_repo.save(c1)
    card_repo.save(c2)

    use_case = CreateFlashcardUseCase(card_repo, topic_repo, session_repo, rng)
    dto = use_case.execute(CreateFlashcardDTO(topic_id=topic.id, front="C_meio", back="M"))

    # Ponto médio entre 100 e 200 -> 150
    assert dto.position == 150


@pytest.mark.unit
def test_delete_flashcard_last_card_triggers_shuffle() -> None:
    """Excluir o último card da rodada quando restam outros cards dispara shuffle."""
    topic_repo = FakeTopicRepository()
    card_repo = FakeFlashcardRepository(topic_repo)
    session_repo = FakeSessionRepository()
    rng = FakeRandomGenerator()

    t_id = uuid4()
    c1 = Flashcard(topic_id=t_id, front="1", back="1", position=100)
    c2 = Flashcard(topic_id=t_id, front="2", back="2", position=200)
    card_repo.save(c1)
    card_repo.save(c2)

    # Sessão no card 2 (último da rodada)
    session = FlashcardPoolSession(topic_id_filter=t_id, current_position=200, round_number=1)
    session_repo.save_session(session)

    use_case = DeleteFlashcardUseCase(card_repo, session_repo, rng)
    use_case.execute(c2.id)

    updated_session = session_repo.get_active_session(None, t_id)
    assert updated_session is not None
    assert updated_session.round_number == 2
    assert updated_session.current_position == 100


@pytest.mark.unit
def test_delete_flashcard_only_card_clears_session() -> None:
    """Excluir o único card existente zera a posição da sessão."""
    topic_repo = FakeTopicRepository()
    card_repo = FakeFlashcardRepository(topic_repo)
    session_repo = FakeSessionRepository()
    rng = FakeRandomGenerator()

    t_id = uuid4()
    c1 = Flashcard(topic_id=t_id, front="1", back="1", position=100)
    card_repo.save(c1)

    session = FlashcardPoolSession(topic_id_filter=t_id, current_position=100)
    session_repo.save_session(session)

    use_case = DeleteFlashcardUseCase(card_repo, session_repo, rng)
    use_case.execute(c1.id)

    updated_session = session_repo.get_active_session(None, t_id)
    assert updated_session is not None
    assert updated_session.current_position == 0


@pytest.mark.unit
def test_create_flashcard_empty_topics_raises_error() -> None:
    """CreateFlashcardUseCase com lista vazia de temas dispara DomainValidationError."""
    topic_repo = FakeTopicRepository()
    card_repo = FakeFlashcardRepository(topic_repo)
    session_repo = FakeSessionRepository()
    rng = FakeRandomGenerator()

    use_case = CreateFlashcardUseCase(card_repo, topic_repo, session_repo, rng)
    with pytest.raises(
        DomainValidationError, match="Flashcard deve estar associado a pelo menos 1 tema."
    ):
        use_case.execute(CreateFlashcardDTO(topic_ids=[], front="P", back="R"))


@pytest.mark.unit
def test_flashcard_dto_backward_compatibility() -> None:
    """Valida propriedades de compatibilidade bidirecional de FlashcardDTO."""
    from datetime import date

    t1, t2 = uuid4(), uuid4()

    # Passando apenas topic_id (antigo)
    dto_legacy = FlashcardDTO(
        id=uuid4(), front="P", back="R", position=100, created_at=date.today(), topic_id=t1
    )
    assert dto_legacy.topic_ids == [t1]
    assert dto_legacy.topic_id == t1

    # Passando apenas topic_ids (novo)
    dto_new = FlashcardDTO(
        id=uuid4(),
        front="P",
        back="R",
        position=100,
        created_at=date.today(),
        topic_ids=[t1, t2],
    )
    assert dto_new.topic_ids == [t1, t2]
    assert dto_new.topic_id == t1


@pytest.mark.unit
def test_study_card_dto_backward_compatibility() -> None:
    """Valida propriedades de compatibilidade bidirecional de StudyCardDTO."""
    t1 = uuid4()

    # Passando apenas topic_id (antigo)
    dto_legacy = StudyCardDTO(
        id=uuid4(),
        front="P",
        back="R",
        position=100,
        current_index=1,
        total_cards=1,
        round_number=1,
        round_shuffled=False,
        topic_id=t1,
    )
    assert dto_legacy.topic_ids == [t1]
    assert dto_legacy.topic_id == t1

    # Passando topic_ids (novo) sem topic_id
    dto_new = StudyCardDTO(
        id=uuid4(),
        front="P",
        back="R",
        position=100,
        current_index=1,
        total_cards=1,
        round_number=1,
        round_shuffled=False,
        topic_ids=[t1],
    )
    assert dto_new.topic_ids == [t1]
    assert dto_new.topic_id == t1


@pytest.mark.unit
@pytest.mark.security
def test_delete_flashcard_by_non_owner_raises_ownership_error() -> None:
    """Impede que usuários excluam flashcards pertencentes a matérias de terceiros.

    Vulnerabilidade prevenida: Insecure Direct Object Reference (IDOR) e destruição de dados.
    Garantia de segurança: Lança ResourceOwnershipError ao tentar excluir card sem ownership.
    """
    subject_repo = FakeSubjectRepository()
    topic_repo = FakeTopicRepository()
    card_repo = FakeFlashcardRepository(topic_repo)
    session_repo = FakeSessionRepository()
    rng = FakeRandomGenerator()

    owner_id = uuid4()
    intruder_id = uuid4()

    subject = Subject(name="Direito Processual", owner_id=owner_id, is_public=True)
    subject_repo.save(subject)

    topic = Topic(subject_id=subject.id, name="Recursos")
    topic_repo.save(topic)

    card = Flashcard(topic_id=topic.id, front="Frente", back="Verso", position=100)
    card_repo.save(card)

    use_case = DeleteFlashcardUseCase(
        card_repo=card_repo,
        session_repo=session_repo,
        rng=rng,
        topic_repo=topic_repo,
        subject_repo=subject_repo,
    )

    with pytest.raises(
        ResourceOwnershipError, match="Você não tem permissão para excluir cards desta matéria"
    ):
        use_case.execute(card.id, user_id=intruder_id)


@pytest.mark.unit
@pytest.mark.security
def test_create_flashcard_by_non_owner_raises_ownership_error() -> None:
    """Impede que usuários adicionem flashcards a matérias de terceiros.

    Vulnerabilidade prevenida: IDOR na inserção de conteúdo não autorizado.
    Garantia de segurança: Lança ResourceOwnershipError ao tentar criar card em matéria alheia.
    """
    subject_repo = FakeSubjectRepository()
    topic_repo = FakeTopicRepository()
    card_repo = FakeFlashcardRepository(topic_repo)
    session_repo = FakeSessionRepository()
    rng = FakeRandomGenerator()

    owner_id = uuid4()
    intruder_id = uuid4()

    subject = Subject(name="Direito", owner_id=owner_id, is_public=True)
    subject_repo.save(subject)
    topic = Topic(subject_id=subject.id, name="Artigos")
    topic_repo.save(topic)

    use_case = CreateFlashcardUseCase(
        card_repo=card_repo,
        topic_repo=topic_repo,
        session_repo=session_repo,
        rng=rng,
        subject_repo=subject_repo,
    )
    with pytest.raises(ResourceOwnershipError, match="Você não tem permissão para adicionar cards"):
        use_case.execute(
            CreateFlashcardDTO(topic_id=topic.id, front="F", back="V"),
            user_id=intruder_id,
        )
