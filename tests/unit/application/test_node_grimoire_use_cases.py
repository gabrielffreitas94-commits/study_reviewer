"""Testes unitários para casos de uso do Tomo do Nó (Node Grimoire) e Modo Treino Livre."""

from collections.abc import Generator
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
    UpdateStudyNodeDTO,
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
    UpdateStudyNodeUseCase,
)
from src.domain.entities import User
from src.domain.exceptions import (
    EntityNotFoundError,
    QuestionNotFoundError,
    ResourceOwnershipError,
    StudyMapNotFoundError,
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
    user_repo.save(
        User(
            id=user_id,
            name="Mago do Conhecimento",
            email="mago@arcana.dev",
            google_sub="sub_test_grimoire",
        )
    )

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
    user_repo.save(
        User(id=user_id, name="Alquimista", email="alquimia@arcana.dev", google_sub="sub_q_node")
    )

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
    user_repo.save(
        User(id=user_id, name="Escriba", email="escriba@arcana.dev", google_sub="sub_mat_node")
    )

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
    user_repo.save(
        User(id=user_id, name="Cavaleiro", email="cavaleiro@arcana.dev", google_sub="sub_lvl_node")
    )

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
    user_repo.save(
        User(id=owner_id, name="Mestre", email="mestre@arcana.dev", google_sub="sub_mestre")
    )
    user_repo.save(
        User(id=other_user_id, name="Intruso", email="intruso@arcana.dev", google_sub="sub_intruso")
    )

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
    user_repo.save(
        User(
            id=user_id, name="Arquivista", email="arquivista@arcana.dev", google_sub="sub_hub_node"
        )
    )

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

    assert (
        hub.node.theory_content
        == "## Origem dos Magos\nOs magos ancestrais dominaram as energias planares."
    )
    assert len(hub.materials) == 1
    assert hub.materials[0]["raw_text"] == "No princípio era o éter silencioso."
    assert len(hub.all_questions) == 1
    assert hub.all_questions[0]["prompt"] == "O que havia no princípio?"
    assert hub.all_questions[0]["is_due"] is True


def test_node_use_cases_edge_cases_and_error_branches(db_session: Session) -> None:
    """Testa todas as ramificações de erro e casos de borda dos casos de uso de nós."""
    user_id = uuid4()
    other_user_id = uuid4()
    user_repo = SqlAlchemyUserRepository(db_session)
    user_repo.save(
        User(id=user_id, name="Test Owner", email="owner@test.com", google_sub="sub_owner")
    )
    user_repo.save(
        User(id=other_user_id, name="Other User", email="other@test.com", google_sub="sub_other")
    )

    map_repo = SqlAlchemyStudyMapRepository(db_session)
    node_repo = SqlAlchemyStudyNodeRepository(db_session)
    q_repo = SqlAlchemyQuestionRepository(db_session)
    source_repo = SqlAlchemyKnowledgeSourceRepository(db_session)
    prog_repo = SqlAlchemyQuestionProgressRepository(db_session)
    content_repo = SqlAlchemyNodeContentRepository(db_session)

    study_map = CreateStudyMapUseCase(map_repo, node_repo).execute(
        owner_id=user_id,
        dto=CreateStudyMapDTO(title="Mapa para Teste de Bordas"),
    )
    node = CreateStudyNodeUseCase(map_repo, node_repo).execute(
        map_id=study_map.id,
        user_id=user_id,
        dto=CreateStudyNodeDTO(title="Nó Alpha"),
    )

    fake_id = uuid4()

    # 1. UpdateStudyNodeUseCase com theory_content (linha 288)
    updated_node = UpdateStudyNodeUseCase(map_repo, node_repo).execute(
        map_id=study_map.id,
        node_id=node.id,
        user_id=user_id,
        dto=UpdateStudyNodeDTO(theory_content="Teoria via UpdateStudyNodeDTO"),
    )
    assert updated_node.theory_content == "Teoria via UpdateStudyNodeDTO"

    # 2. UpdateNodeTheoryUseCase com mapa inexistente (linha 327)
    with pytest.raises(StudyMapNotFoundError):
        UpdateNodeTheoryUseCase(map_repo, node_repo).execute(
            map_id=fake_id,
            node_id=node.id,
            user_id=user_id,
            theory_content="...",
        )

    # 3. CreateNodeQuestionUseCase: mapa inexistente e nó inexistente (linhas 596, 604)
    with pytest.raises(StudyMapNotFoundError):
        CreateNodeQuestionUseCase(map_repo, node_repo, q_repo, prog_repo, content_repo).execute(
            map_id=fake_id, node_id=node.id, user_id=user_id, prompt="P", expected_answer="R"
        )

    with pytest.raises(StudyNodeNotFoundError):
        CreateNodeQuestionUseCase(map_repo, node_repo, q_repo, prog_repo, content_repo).execute(
            map_id=study_map.id, node_id=fake_id, user_id=user_id, prompt="P", expected_answer="R"
        )

    # 4. DeleteNodeQuestionUseCase: mapa inexistente, nó inexistente, pergunta inexistente (linhas 673, 681, 685)
    with pytest.raises(StudyMapNotFoundError):
        DeleteNodeQuestionUseCase(map_repo, node_repo, q_repo, content_repo).execute(
            map_id=fake_id, node_id=node.id, user_id=user_id, question_id=fake_id
        )

    with pytest.raises(StudyNodeNotFoundError):
        DeleteNodeQuestionUseCase(map_repo, node_repo, q_repo, content_repo).execute(
            map_id=study_map.id, node_id=fake_id, user_id=user_id, question_id=fake_id
        )

    with pytest.raises(QuestionNotFoundError):
        DeleteNodeQuestionUseCase(map_repo, node_repo, q_repo, content_repo).execute(
            map_id=study_map.id, node_id=node.id, user_id=user_id, question_id=fake_id
        )

    # 5. CreateNodeMaterialUseCase: mapa inexistente e nó inexistente (linhas 728, 736)
    with pytest.raises(StudyMapNotFoundError):
        CreateNodeMaterialUseCase(map_repo, node_repo, source_repo, content_repo).execute(
            map_id=fake_id, node_id=node.id, user_id=user_id, title="M", raw_text="T"
        )

    with pytest.raises(StudyNodeNotFoundError):
        CreateNodeMaterialUseCase(map_repo, node_repo, source_repo, content_repo).execute(
            map_id=study_map.id, node_id=fake_id, user_id=user_id, title="M", raw_text="T"
        )

    # 6. DeleteNodeMaterialUseCase: mapa inexistente, nó inexistente, material inexistente (linhas 800, 808, 812)
    with pytest.raises(StudyMapNotFoundError):
        DeleteNodeMaterialUseCase(map_repo, node_repo, source_repo, content_repo).execute(
            map_id=fake_id, node_id=node.id, user_id=user_id, material_id=fake_id
        )

    with pytest.raises(StudyNodeNotFoundError):
        DeleteNodeMaterialUseCase(map_repo, node_repo, source_repo, content_repo).execute(
            map_id=study_map.id, node_id=fake_id, user_id=user_id, material_id=fake_id
        )

    with pytest.raises(EntityNotFoundError):
        DeleteNodeMaterialUseCase(map_repo, node_repo, source_repo, content_repo).execute(
            map_id=study_map.id, node_id=node.id, user_id=user_id, material_id=fake_id
        )

    # Cria pergunta real para testar ReviewNodeQuestionUseCase
    created_q = CreateNodeQuestionUseCase(
        map_repo, node_repo, q_repo, prog_repo, content_repo
    ).execute(
        map_id=study_map.id, node_id=node.id, user_id=user_id, prompt="P1", expected_answer="R1"
    )
    q_id = created_q["id"]

    # 7. ReviewNodeQuestionUseCase: erros de validação (linhas 861, 863, 867, 871)
    rev_uc = ReviewNodeQuestionUseCase(
        map_repo=map_repo,
        node_repo=node_repo,
        question_repo=q_repo,
        progress_repo=prog_repo,
        content_repo=content_repo,
    )

    with pytest.raises(StudyMapNotFoundError):
        rev_uc.execute(map_id=fake_id, node_id=node.id, user_id=user_id, question_id=q_id)

    with pytest.raises(ResourceOwnershipError):
        rev_uc.execute(
            map_id=study_map.id, node_id=node.id, user_id=other_user_id, question_id=q_id
        )

    with pytest.raises(StudyNodeNotFoundError):
        rev_uc.execute(map_id=study_map.id, node_id=fake_id, user_id=user_id, question_id=q_id)

    with pytest.raises(QuestionNotFoundError):
        rev_uc.execute(map_id=study_map.id, node_id=node.id, user_id=user_id, question_id=fake_id)

    # 8. Review com difficulty HARD e AGAIN (linhas 881-884)
    res_hard = rev_uc.execute(
        map_id=study_map.id,
        node_id=node.id,
        user_id=user_id,
        question_id=q_id,
        difficulty="HARD",
    )
    assert res_hard["is_training_only"] is False

    res_again = rev_uc.execute(
        map_id=study_map.id,
        node_id=node.id,
        user_id=user_id,
        question_id=q_id,
        difficulty="AGAIN",
    )
    assert res_again["is_training_only"] is False

    # Cria pergunta 2 para subir de nível e acionar treino livre
    created_q2 = CreateNodeQuestionUseCase(
        map_repo, node_repo, q_repo, prog_repo, content_repo
    ).execute(
        map_id=study_map.id, node_id=node.id, user_id=user_id, prompt="P2", expected_answer="R2"
    )
    q2_id = created_q2["id"]

    res_easy = rev_uc.execute(
        map_id=study_map.id,
        node_id=node.id,
        user_id=user_id,
        question_id=q2_id,
        difficulty="EASY",
    )
    assert res_easy["is_training_only"] is False
    assert res_easy["current_question_level"] == 1

    # Segunda revisão no mesmo dia ativa o Modo Treino Livre
    res_training = rev_uc.execute(
        map_id=study_map.id,
        node_id=node.id,
        user_id=user_id,
        question_id=q2_id,
        difficulty="GOOD",
    )
    assert res_training["is_training_only"] is True
