"""Testes unitários para casos de uso do Tomo do Nó (Node Grimoire) e Modo Treino Livre."""

from collections.abc import Generator
from datetime import date
from uuid import uuid4

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from src.adapters.persistence.repositories import (
    SqlAlchemyKnowledgeSourceRepository,
    SqlAlchemyNodeContentRepository,
    SqlAlchemyQuestionProgressRepository,
    SqlAlchemyQuestionRepository,
    SqlAlchemyStudyEdgeRepository,
    SqlAlchemyStudyMapRepository,
    SqlAlchemyStudyNodeRepository,
    SqlAlchemyUserRepository,
)
from src.application.dto.study_tree_dto import (
    ConnectNodesDTO,
    CreateStudyMapDTO,
    CreateStudyNodeDTO,
)
from src.application.use_cases.study_tree_use_cases import (
    ConnectStudyNodesUseCase,
    CreateNodeMaterialUseCase,
    CreateNodeQuestionUseCase,
    CreateStudyMapUseCase,
    CreateStudyNodeUseCase,
    DeleteNodeMaterialUseCase,
    DeleteNodeQuestionUseCase,
    GetNodeStudyHubUseCase,
    ReviewNodeQuestionUseCase,
    UpdateNodeTheoryUseCase,
)
from src.domain.entities import User
from src.domain.exceptions import (
    ResourceOwnershipError,
    StudyNodeNotFoundError,
)
from src.infrastructure.database import Base


@pytest.fixture
def db_session() -> Generator[Session]:
    """Cria banco SQLite em memória isolado para os testes unitários do Tomo do Nó."""
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    testing_session = sessionmaker(bind=engine)
    session = testing_session()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(engine)
        engine.dispose()


def test_node_grimoire_lifecycle_theory_question_and_free_training(db_session: Session) -> None:
    """Valida o ciclo de vida do Nó Grimoire: teoria, pergunta inline e modo treino livre."""
    user_id = uuid4()
    user_repo = SqlAlchemyUserRepository(db_session)
    user_repo.save(User(id=user_id, name="Mago do Conhecimento", email="mago@arcana.dev", google_sub="sub_test_grimoire"))

    map_repo = SqlAlchemyStudyMapRepository(db_session)
    node_repo = SqlAlchemyStudyNodeRepository(db_session)
    content_repo = SqlAlchemyNodeContentRepository(db_session)
    q_repo = SqlAlchemyQuestionRepository(db_session)
    prog_repo = SqlAlchemyQuestionProgressRepository(db_session)

    study_map = CreateStudyMapUseCase(map_repo, node_repo).execute(
        owner_id=user_id,
        dto=CreateStudyMapDTO(title="Grimório de Cálculo"),
    )
    node = CreateStudyNodeUseCase(map_repo, node_repo).execute(
        map_id=study_map.id,
        user_id=user_id,
        dto=CreateStudyNodeDTO(title="Derivadas Parciais", icon="scroll"),
    )

    updated = UpdateNodeTheoryUseCase(map_repo, node_repo).execute(
        map_id=study_map.id,
        node_id=node.id,
        user_id=user_id,
        theory_content="O gradiente aponta na direção de maior crescimento.",
    )
    assert updated.theory_content == "O gradiente aponta na direção de maior crescimento."

    created_q = CreateNodeQuestionUseCase(
        map_repo=map_repo,
        node_repo=node_repo,
        question_repo=q_repo,
        progress_repo=prog_repo,
        content_repo=content_repo,
    ).execute(
        map_id=study_map.id,
        node_id=node.id,
        user_id=user_id,
        prompt="Para onde aponta o vetor gradiente?",
        expected_answer="Direção de máxima taxa de crescimento.",
    )
    assert created_q["current_level"] == 0

    review_uc = ReviewNodeQuestionUseCase(
        map_repo=map_repo,
        node_repo=node_repo,
        question_repo=q_repo,
        progress_repo=prog_repo,
        content_repo=content_repo,
    )
    first_res = review_uc.execute(
        map_id=study_map.id,
        node_id=node.id,
        user_id=user_id,
        question_id=created_q["id"],
        score=100,
    )
    assert first_res["new_level"] == 1
    assert first_res["is_training_only"] is False
    assert first_res["node_effective_level"] == 1
    assert first_res["node_is_mastered"] is True

    # Segunda resposta no mesmo dia deve operar em Modo Treino Livre sem erro
    second_res = review_uc.execute(
        map_id=study_map.id,
        node_id=node.id,
        user_id=user_id,
        question_id=created_q["id"],
        score=50,
    )
    assert second_res["is_training_only"] is True
    assert second_res["new_level"] == 1


def test_create_and_delete_node_question(db_session: Session) -> None:
    """Verifica criação e exclusão inline de perguntas em um nó."""
    user_id = uuid4()
    user_repo = SqlAlchemyUserRepository(db_session)
    user_repo.save(User(id=user_id, name="Alquimista", email="alquimia@arcana.dev", google_sub="sub_q_node"))

    map_repo = SqlAlchemyStudyMapRepository(db_session)
    node_repo = SqlAlchemyStudyNodeRepository(db_session)
    content_repo = SqlAlchemyNodeContentRepository(db_session)
    q_repo = SqlAlchemyQuestionRepository(db_session)
    prog_repo = SqlAlchemyQuestionProgressRepository(db_session)

    study_map = CreateStudyMapUseCase(map_repo, node_repo).execute(
        owner_id=user_id,
        dto=CreateStudyMapDTO(title="Árvore Alquímica"),
    )
    node = CreateStudyNodeUseCase(map_repo, node_repo).execute(
        map_id=study_map.id,
        user_id=user_id,
        dto=CreateStudyNodeDTO(title="Transmutação de Metais"),
    )

    created_q = CreateNodeQuestionUseCase(
        map_repo=map_repo,
        node_repo=node_repo,
        question_repo=q_repo,
        progress_repo=prog_repo,
        content_repo=content_repo,
    ).execute(
        map_id=study_map.id,
        node_id=node.id,
        user_id=user_id,
        prompt="Qual metal é a base da pedra filosofal?",
        expected_answer="Chumbo refinado através da grande obra.",
    )

    question_id = created_q["id"]
    saved_q = q_repo.get_by_id(question_id)
    assert saved_q is not None
    assert saved_q.node_id == node.id

    attached = content_repo.get_attached_ids(node.id)
    assert question_id in attached[1]

    # Exclusão da pergunta do nó
    DeleteNodeQuestionUseCase(
        map_repo=map_repo,
        node_repo=node_repo,
        question_repo=q_repo,
        content_repo=content_repo,
    ).execute(
        map_id=study_map.id,
        node_id=node.id,
        user_id=user_id,
        question_id=question_id,
    )

    assert q_repo.get_by_id(question_id) is None
    attached_after = content_repo.get_attached_ids(node.id)
    assert question_id not in attached_after[1]


def test_create_and_delete_node_material(db_session: Session) -> None:
    """Verifica criação e exclusão inline de materiais (pergaminhos) em um nó."""
    user_id = uuid4()
    user_repo = SqlAlchemyUserRepository(db_session)
    user_repo.save(User(id=user_id, name="Escriba", email="escriba@arcana.dev", google_sub="sub_mat_node"))

    map_repo = SqlAlchemyStudyMapRepository(db_session)
    node_repo = SqlAlchemyStudyNodeRepository(db_session)
    content_repo = SqlAlchemyNodeContentRepository(db_session)
    source_repo = SqlAlchemyKnowledgeSourceRepository(db_session)

    study_map = CreateStudyMapUseCase(map_repo, node_repo).execute(
        owner_id=user_id,
        dto=CreateStudyMapDTO(title="Biblioteca Arcana"),
    )
    node = CreateStudyNodeUseCase(map_repo, node_repo).execute(
        map_id=study_map.id,
        user_id=user_id,
        dto=CreateStudyNodeDTO(title="Runas Antigas"),
    )

    created_mat = CreateNodeMaterialUseCase(
        map_repo=map_repo,
        node_repo=node_repo,
        source_repo=source_repo,
        content_repo=content_repo,
    ).execute(
        map_id=study_map.id,
        node_id=node.id,
        user_id=user_id,
        title="Tratado das Runas",
        raw_text="As runas canalizam o éter primordial.",
        content_type="TEXT",
    )

    mat_id = created_mat["id"]
    saved_source = source_repo.get_by_id(mat_id)
    assert saved_source is not None
    assert saved_source.node_id == node.id
    assert saved_source.raw_text == "As runas canalizam o éter primordial."

    attached = content_repo.get_attached_ids(node.id)
    assert mat_id in attached[0]

    # Exclusão do material
    DeleteNodeMaterialUseCase(
        map_repo=map_repo,
        node_repo=node_repo,
        source_repo=source_repo,
        content_repo=content_repo,
    ).execute(
        map_id=study_map.id,
        node_id=node.id,
        user_id=user_id,
        material_id=mat_id,
    )

    assert source_repo.get_by_id(mat_id) is None
    attached_after = content_repo.get_attached_ids(node.id)
    assert mat_id not in attached_after[0]


def test_review_node_question_level_up_and_unlock_downstream(db_session: Session) -> None:
    """Verifica progressão de Rank do nó e destrancamento de nós a jusante."""
    user_id = uuid4()
    user_repo = SqlAlchemyUserRepository(db_session)
    user_repo.save(User(id=user_id, name="Cavaleiro", email="cavaleiro@arcana.dev", google_sub="sub_lvl_node"))

    map_repo = SqlAlchemyStudyMapRepository(db_session)
    node_repo = SqlAlchemyStudyNodeRepository(db_session)
    edge_repo = SqlAlchemyStudyEdgeRepository(db_session)
    content_repo = SqlAlchemyNodeContentRepository(db_session)
    q_repo = SqlAlchemyQuestionRepository(db_session)
    prog_repo = SqlAlchemyQuestionProgressRepository(db_session)

    study_map = CreateStudyMapUseCase(map_repo, node_repo).execute(
        owner_id=user_id,
        dto=CreateStudyMapDTO(title="Árvore de Habilidades Marciais"),
    )
    node_a = CreateStudyNodeUseCase(map_repo, node_repo).execute(
        map_id=study_map.id,
        user_id=user_id,
        dto=CreateStudyNodeDTO(title="Fundamentos de Espada"),
    )
    node_b = CreateStudyNodeUseCase(map_repo, node_repo).execute(
        map_id=study_map.id,
        user_id=user_id,
        dto=CreateStudyNodeDTO(title="Golpe Tempestuoso"),
    )

    # Conecta A -> B
    ConnectStudyNodesUseCase(map_repo, node_repo, edge_repo).execute(
        map_id=study_map.id,
        user_id=user_id,
        dto=ConnectNodesDTO(source_node_id=node_a.id, target_node_id=node_b.id),
    )

    # Adiciona pergunta a Node A
    q = CreateNodeQuestionUseCase(
        map_repo=map_repo,
        node_repo=node_repo,
        question_repo=q_repo,
        progress_repo=prog_repo,
        content_repo=content_repo,
    ).execute(
        map_id=study_map.id,
        node_id=node_a.id,
        user_id=user_id,
        prompt="Como empunhar a espada com equilíbrio?",
        expected_answer="Com firmeza no punho e peso distribuído nos pés.",
    )

    review_uc = ReviewNodeQuestionUseCase(
        map_repo=map_repo,
        node_repo=node_repo,
        question_repo=q_repo,
        progress_repo=prog_repo,
        content_repo=content_repo,
        edge_repo=edge_repo,
    )
    res = review_uc.execute(
        map_id=study_map.id,
        node_id=node_a.id,
        user_id=user_id,
        question_id=q["id"],
        score=100,
    )

    assert res["old_node_level"] == 0
    assert res["new_node_level"] == 1
    assert res["leveled_up"] is True
    assert res["node_is_mastered"] is True
    assert str(node_b.id) in res["unlocked_node_ids"]


def test_update_node_theory_ownership_and_validation(db_session: Session) -> None:
    """Verifica que apenas o proprietário pode editar a teoria do nó."""
    owner_id = uuid4()
    other_user_id = uuid4()
    user_repo = SqlAlchemyUserRepository(db_session)
    user_repo.save(User(id=owner_id, name="Mestre", email="mestre@arcana.dev", google_sub="sub_mestre"))
    user_repo.save(User(id=other_user_id, name="Intruso", email="intruso@arcana.dev", google_sub="sub_intruso"))

    map_repo = SqlAlchemyStudyMapRepository(db_session)
    node_repo = SqlAlchemyStudyNodeRepository(db_session)

    study_map = CreateStudyMapUseCase(map_repo, node_repo).execute(
        owner_id=owner_id,
        dto=CreateStudyMapDTO(title="Tomo Sagrado"),
    )
    node = CreateStudyNodeUseCase(map_repo, node_repo).execute(
        map_id=study_map.id,
        user_id=owner_id,
        dto=CreateStudyNodeDTO(title="Encantamentos"),
    )

    with pytest.raises(ResourceOwnershipError):
        UpdateNodeTheoryUseCase(map_repo, node_repo).execute(
            map_id=study_map.id,
            node_id=node.id,
            user_id=other_user_id,
            theory_content="Texto não autorizado",
        )

    with pytest.raises(StudyNodeNotFoundError):
        UpdateNodeTheoryUseCase(map_repo, node_repo).execute(
            map_id=study_map.id,
            node_id=uuid4(),
            user_id=owner_id,
            theory_content="Nó inexistente",
        )


def test_get_node_study_hub_includes_theory_and_raw_text(db_session: Session) -> None:
    """Valida que GetNodeStudyHubUseCase retorna theory_content no nó e raw_text nos materiais."""
    user_id = uuid4()
    user_repo = SqlAlchemyUserRepository(db_session)
    user_repo.save(User(id=user_id, name="Arquivista", email="arquivista@arcana.dev", google_sub="sub_hub_node"))

    map_repo = SqlAlchemyStudyMapRepository(db_session)
    node_repo = SqlAlchemyStudyNodeRepository(db_session)
    content_repo = SqlAlchemyNodeContentRepository(db_session)
    q_repo = SqlAlchemyQuestionRepository(db_session)
    source_repo = SqlAlchemyKnowledgeSourceRepository(db_session)
    prog_repo = SqlAlchemyQuestionProgressRepository(db_session)

    study_map = CreateStudyMapUseCase(map_repo, node_repo).execute(
        owner_id=user_id,
        dto=CreateStudyMapDTO(title="Grimório Central"),
    )
    node = CreateStudyNodeUseCase(map_repo, node_repo).execute(
        map_id=study_map.id,
        user_id=user_id,
        dto=CreateStudyNodeDTO(title="História dos Magos"),
    )

    UpdateNodeTheoryUseCase(map_repo, node_repo).execute(
        map_id=study_map.id,
        node_id=node.id,
        user_id=user_id,
        theory_content="## Origem dos Magos\nOs magos ancestrais dominaram as energias planares.",
    )

    CreateNodeMaterialUseCase(
        map_repo=map_repo,
        node_repo=node_repo,
        source_repo=source_repo,
        content_repo=content_repo,
    ).execute(
        map_id=study_map.id,
        node_id=node.id,
        user_id=user_id,
        title="Crônicas da Primeira Era",
        raw_text="No princípio era o éter silencioso.",
    )

    CreateNodeQuestionUseCase(
        map_repo=map_repo,
        node_repo=node_repo,
        question_repo=q_repo,
        progress_repo=prog_repo,
        content_repo=content_repo,
    ).execute(
        map_id=study_map.id,
        node_id=node.id,
        user_id=user_id,
        prompt="O que havia no princípio?",
        expected_answer="O éter silencioso.",
    )

    hub = GetNodeStudyHubUseCase(
        map_repo=map_repo,
        node_repo=node_repo,
        content_repo=content_repo,
        progress_repo=prog_repo,
        question_repo=q_repo,
        knowledge_repo=source_repo,
    ).execute(
        map_id=study_map.id,
        user_id=user_id,
        node_id=node.id,
    )

    assert hub.node.theory_content == "## Origem dos Magos\nOs magos ancestrais dominaram as energias planares."
    assert len(hub.materials) == 1
    assert hub.materials[0]["raw_text"] == "No princípio era o éter silencioso."
    assert len(hub.all_questions) == 1
    assert hub.all_questions[0]["prompt"] == "O que havia no princípio?"
    assert hub.all_questions[0]["is_due"] is True
