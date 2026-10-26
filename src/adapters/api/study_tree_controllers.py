"""Controladores REST da Árvore de Estudos RPG e Grafo de Conhecimento (Camada 3 - Adaptadores)."""

from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from src.adapters.persistence.repositories import (
    SqlAlchemyFlashcardRepository,
    SqlAlchemyKnowledgeSourceRepository,
    SqlAlchemyNodeContentRepository,
    SqlAlchemyQuestionProgressRepository,
    SqlAlchemyQuestionRepository,
    SqlAlchemyReviewAuditRepository,
    SqlAlchemyStudyEdgeRepository,
    SqlAlchemyStudyMapRepository,
    SqlAlchemyStudyNodeRepository,
)
from src.application.dto.study_tree_dto import (
    ConnectNodesDTO,
    CreateStudyMapDTO,
    CreateStudyNodeDTO,
    NodePositionDTO,
    UpdateStudyEdgeDTO,
    UpdateStudyNodeDTO,
)
from src.application.use_cases.study_tree_use_cases import (
    AttachContentToNodeUseCase,
    ConnectStudyNodesUseCase,
    CreateNodeMaterialUseCase,
    CreateNodeQuestionUseCase,
    CreateStudyMapUseCase,
    CreateStudyNodeUseCase,
    DeleteNodeMaterialUseCase,
    DeleteNodeQuestionUseCase,
    DeleteStudyNodeUseCase,
    DetachContentFromNodeUseCase,
    DisconnectStudyNodesUseCase,
    GetNodeStudyHubUseCase,
    GetStudyMapGraphUseCase,
    ReviewNodeQuestionUseCase,
    UpdateNodePositionsBatchUseCase,
    UpdateNodeTheoryUseCase,
    UpdateStudyEdgeUseCase,
    UpdateStudyNodeUseCase,
)
from src.domain.entities import User
from src.domain.exceptions import (
    CrossMapEdgeError,
    CyclicDependencyError,
    DomainValidationError,
    EntityNotFoundError,
    QuestionNotFoundError,
    ResourceOwnershipError,
    SelfReferencingEdgeError,
    StudyEdgeNotFoundError,
    StudyMapNotFoundError,
    StudyNodeNotFoundError,
)
from src.infrastructure.database import get_db
from src.infrastructure.security.dependencies import get_current_user

_study_tree_base_router = APIRouter()


# --- Schemas de Entrada (Pydantic v2) ---


class CreateStudyMapRequest(BaseModel):
    title: str = Field(..., min_length=1, max_length=200)
    description: str | None = Field(default=None, max_length=2000)
    is_public: bool = Field(default=False)
    parent_node_id: UUID | None = Field(default=None)


class CreateStudyNodeRequest(BaseModel):
    title: str = Field(..., min_length=1, max_length=150)
    description: str | None = Field(default=None, max_length=2000)
    pos_x: float = Field(default=0.0)
    pos_y: float = Field(default=0.0)
    icon: str = Field(default="brain", max_length=50)


class UpdateStudyNodeRequest(BaseModel):
    title: str | None = Field(default=None, max_length=150)
    description: str | None = Field(default=None, max_length=2000)
    icon: str | None = Field(default=None, max_length=50)


class UpdateNodeTheoryRequest(BaseModel):
    theory_content: str = Field(default="", max_length=50000)


class CreateNodeQuestionRequest(BaseModel):
    prompt: str = Field(default="", max_length=5000)
    statement: str = Field(default="", max_length=5000)
    expected_answer: str = Field(..., min_length=1, max_length=5000)


class ReviewNodeQuestionRequest(BaseModel):
    score: int = Field(default=100, ge=0, le=100)
    difficulty: str | None = Field(default=None, max_length=20)


class CreateNodeMaterialRequest(BaseModel):
    title: str = Field(..., min_length=1, max_length=200)
    raw_text: str = Field(default="", max_length=100000)
    content_type: str = Field(default="TEXT", max_length=20)


class NodePositionItem(BaseModel):
    node_id: UUID
    pos_x: float
    pos_y: float


class UpdatePositionsBatchRequest(BaseModel):
    positions: list[NodePositionItem] = Field(..., min_length=1)


class ConnectNodesRequest(BaseModel):
    source_node_id: UUID
    target_node_id: UUID
    required_level: int = Field(default=1, ge=1, le=6)


class UpdateStudyEdgeRequest(BaseModel):
    required_level: int = Field(..., ge=1, le=6)


class AttachContentRequest(BaseModel):
    content_type: str = Field(..., max_length=50)
    content_id: UUID


# --- Serializadores Auxiliares ---


def _serialize_node(node: Any) -> dict[str, Any]:
    """Serializa dados de nó e suas estatísticas de estudo para JSON da API REST."""
    return {
        "id": str(node.id),
        "map_id": str(node.map_id),
        "title": node.title,
        "description": node.description,
        "pos_x": getattr(node, "pos_x", 0.0),
        "pos_y": getattr(node, "pos_y", 0.0),
        "icon": getattr(node, "icon", "brain"),
        "effective_level": getattr(node, "effective_level", 0),
        "is_unlocked": getattr(node, "is_unlocked", True),
        "overdue_questions_count": getattr(node, "overdue_questions_count", 0),
        "has_submap": getattr(node, "has_submap", False),
        "materials_count": getattr(node, "materials_count", 0),
        "questions_count": getattr(node, "questions_count", 0),
        "flashcards_count": getattr(node, "flashcards_count", 0),
        "theory_content": getattr(node, "theory_content", ""),
    }


def _serialize_edge(edge: Any) -> dict[str, Any]:
    """Serializa dados de aresta para JSON da API REST."""
    return {
        "id": str(edge.id),
        "map_id": str(edge.map_id),
        "source_node_id": str(edge.source_node_id),
        "target_node_id": str(edge.target_node_id),
        "required_level": getattr(edge, "required_level", 1),
    }


# --- Endpoints RESTful ---


@_study_tree_base_router.post("/study-maps/migrate-legacy")
def migrate_legacy_taxonomy(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    """Migra matérias e tópicos legados do usuário para Mapas e Nós de Estudo RPG."""
    from src.adapters.persistence.repositories import (
        SqlAlchemySubjectRepository,
        SqlAlchemyTopicRepository,
    )
    from src.application.use_cases.migrate_legacy_taxonomy_use_case import (
        MigrateLegacyTaxonomyUseCase,
    )

    use_case = MigrateLegacyTaxonomyUseCase(
        subject_repo=SqlAlchemySubjectRepository(db),
        topic_repo=SqlAlchemyTopicRepository(db),
        map_repo=SqlAlchemyStudyMapRepository(db),
        node_repo=SqlAlchemyStudyNodeRepository(db),
        content_repo=SqlAlchemyNodeContentRepository(db),
        question_repo=SqlAlchemyQuestionRepository(db),
        flashcard_repo=SqlAlchemyFlashcardRepository(db),
        knowledge_source_repo=SqlAlchemyKnowledgeSourceRepository(db),
    )
    report = use_case.execute(user_id=current_user.id)
    return {
        "maps_created": report.maps_created,
        "nodes_created": report.nodes_created,
        "questions_linked": report.questions_linked,
        "flashcards_linked": report.flashcards_linked,
        "sources_linked": report.sources_linked,
    }


@_study_tree_base_router.post("/study-maps/sample-math", status_code=status.HTTP_201_CREATED)
def create_sample_math_study_map(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    """Cria uma Árvore de Conhecimento demonstrativa completa
    de Matemática Aplicada & Computacional.
    """
    from src.adapters.persistence.repositories import (
        SqlAlchemySubjectRepository,
        SqlAlchemyTopicRepository,
    )
    from src.application.use_cases.sample_study_map_use_case import (
        CreateSampleMathStudyMapUseCase,
    )

    use_case = CreateSampleMathStudyMapUseCase(
        map_repo=SqlAlchemyStudyMapRepository(db),
        node_repo=SqlAlchemyStudyNodeRepository(db),
        edge_repo=SqlAlchemyStudyEdgeRepository(db),
        content_repo=SqlAlchemyNodeContentRepository(db),
        source_repo=SqlAlchemyKnowledgeSourceRepository(db),
        question_repo=SqlAlchemyQuestionRepository(db),
        flashcard_repo=SqlAlchemyFlashcardRepository(db),
        subject_repo=SqlAlchemySubjectRepository(db),
        topic_repo=SqlAlchemyTopicRepository(db),
    )
    study_map = use_case.execute(user_id=current_user.id)
    return {
        "id": str(study_map.id),
        "title": study_map.title,
        "description": study_map.description,
        "message": "Árvore de Matemática Aplicada gerada com sucesso!",
    }


@_study_tree_base_router.get("/study-maps")
def list_study_maps(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[dict[str, Any]]:
    """Lista todos os mapas de estudo pertencentes ao usuário autenticado."""
    map_repo = SqlAlchemyStudyMapRepository(db)
    maps = map_repo.list_by_owner(current_user.id)
    return [
        {
            "id": str(m.id),
            "owner_id": str(m.owner_id),
            "title": m.title,
            "description": m.description,
            "is_public": m.is_public,
            "parent_node_id": str(m.parent_node_id) if m.parent_node_id else None,
            "is_submap": m.is_submap,
            "created_at": m.created_at.isoformat(),
            "updated_at": m.updated_at.isoformat(),
        }
        for m in maps
    ]


@_study_tree_base_router.post("/study-maps", status_code=status.HTTP_201_CREATED)
def create_study_map(
    payload: CreateStudyMapRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    """Cria um novo mapa de estudo raiz ou sub-mapa."""
    map_repo = SqlAlchemyStudyMapRepository(db)
    node_repo = SqlAlchemyStudyNodeRepository(db)
    use_case = CreateStudyMapUseCase(map_repo=map_repo, node_repo=node_repo)

    dto = CreateStudyMapDTO(
        title=payload.title,
        description=payload.description,
        is_public=payload.is_public,
        parent_node_id=payload.parent_node_id,
    )
    result = use_case.execute(owner_id=current_user.id, dto=dto)
    return {
        "id": str(result.id),
        "owner_id": str(result.owner_id),
        "title": result.title,
        "description": result.description,
        "is_public": result.is_public,
        "parent_node_id": str(result.parent_node_id) if result.parent_node_id else None,
        "created_at": result.created_at.isoformat(),
        "updated_at": result.updated_at.isoformat(),
    }


@_study_tree_base_router.get("/study-maps/{map_id}")
def get_study_map_graph(
    map_id: UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    """Retorna o grafo completo do mapa com nós, arestas, níveis SRS e status de desbloqueio."""
    use_case = GetStudyMapGraphUseCase(
        map_repo=SqlAlchemyStudyMapRepository(db),
        node_repo=SqlAlchemyStudyNodeRepository(db),
        edge_repo=SqlAlchemyStudyEdgeRepository(db),
        content_repo=SqlAlchemyNodeContentRepository(db),
        progress_repo=SqlAlchemyQuestionProgressRepository(db),
    )
    try:
        graph = use_case.execute(map_id=map_id, user_id=current_user.id)
        return {
            "map": {
                "id": str(graph.map.id),
                "owner_id": str(graph.map.owner_id),
                "title": graph.map.title,
                "description": graph.map.description,
                "is_public": graph.map.is_public,
                "parent_node_id": str(graph.map.parent_node_id)
                if graph.map.parent_node_id
                else None,
            },
            "nodes": [_serialize_node(n) for n in graph.nodes],
            "edges": [_serialize_edge(e) for e in graph.edges],
        }
    except StudyMapNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except ResourceOwnershipError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc


@_study_tree_base_router.delete("/study-maps/{map_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_study_map(
    map_id: UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> None:
    """Remove um mapa de estudo e seus nós/arestas em cascata."""
    map_repo = SqlAlchemyStudyMapRepository(db)
    existing = map_repo.get_by_id(map_id)
    if existing is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Mapa não encontrado.")
    if existing.owner_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Acesso negado.")
    map_repo.delete(map_id)


@_study_tree_base_router.post("/study-maps/{map_id}/nodes", status_code=status.HTTP_201_CREATED)
def create_study_node(
    map_id: UUID,
    payload: CreateStudyNodeRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    """Cria um novo nó no mapa na posição (x, y) informada."""
    use_case = CreateStudyNodeUseCase(
        map_repo=SqlAlchemyStudyMapRepository(db),
        node_repo=SqlAlchemyStudyNodeRepository(db),
    )
    try:
        dto = CreateStudyNodeDTO(
            title=payload.title,
            description=payload.description,
            pos_x=payload.pos_x,
            pos_y=payload.pos_y,
            icon=payload.icon,
        )
        node = use_case.execute(map_id=map_id, user_id=current_user.id, dto=dto)
        return _serialize_node(node)
    except StudyMapNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except ResourceOwnershipError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc


@_study_tree_base_router.patch(
    "/study-maps/{map_id}/nodes/positions-batch", status_code=status.HTTP_204_NO_CONTENT
)
@_study_tree_base_router.put(
    "/study-maps/{map_id}/nodes/positions-batch", status_code=status.HTTP_204_NO_CONTENT
)
def update_node_positions_batch(
    map_id: UUID,
    payload: UpdatePositionsBatchRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> None:
    """Atualiza em lote as coordenadas (x, y) de múltiplos nós após arrastes no canvas."""
    use_case = UpdateNodePositionsBatchUseCase(
        map_repo=SqlAlchemyStudyMapRepository(db),
        node_repo=SqlAlchemyStudyNodeRepository(db),
    )
    try:
        dtos = [
            NodePositionDTO(node_id=item.node_id, pos_x=item.pos_x, pos_y=item.pos_y)
            for item in payload.positions
        ]
        use_case.execute(map_id=map_id, user_id=current_user.id, positions=dtos)
    except StudyMapNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except ResourceOwnershipError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc


@_study_tree_base_router.patch("/study-maps/{map_id}/nodes/{node_id}")
@_study_tree_base_router.put("/study-maps/{map_id}/nodes/{node_id}")
def update_study_node(
    map_id: UUID,
    node_id: UUID,
    payload: UpdateStudyNodeRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    """Atualiza título, descrição ou ícone de um nó."""
    use_case = UpdateStudyNodeUseCase(
        map_repo=SqlAlchemyStudyMapRepository(db),
        node_repo=SqlAlchemyStudyNodeRepository(db),
    )
    try:
        dto = UpdateStudyNodeDTO(
            title=payload.title,
            description=payload.description,
            icon=payload.icon,
        )
        node = use_case.execute(map_id=map_id, user_id=current_user.id, node_id=node_id, dto=dto)
        return _serialize_node(node)
    except (StudyMapNotFoundError, StudyNodeNotFoundError) as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except ResourceOwnershipError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc
    except DomainValidationError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


@_study_tree_base_router.delete(
    "/study-maps/{map_id}/nodes/{node_id}", status_code=status.HTTP_204_NO_CONTENT
)
def delete_study_node(
    map_id: UUID,
    node_id: UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> None:
    """Remove um nó do mapa."""
    use_case = DeleteStudyNodeUseCase(
        map_repo=SqlAlchemyStudyMapRepository(db),
        node_repo=SqlAlchemyStudyNodeRepository(db),
    )
    try:
        use_case.execute(map_id=map_id, user_id=current_user.id, node_id=node_id)
    except (StudyMapNotFoundError, StudyNodeNotFoundError) as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except ResourceOwnershipError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc


@_study_tree_base_router.patch("/study-maps/{map_id}/nodes/{node_id}/theory")
def update_node_theory(
    map_id: UUID,
    node_id: UUID,
    payload: UpdateNodeTheoryRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    """Atualiza o conteúdo do Tomo de Sabedoria (teoria) de um nó."""
    use_case = UpdateNodeTheoryUseCase(
        map_repo=SqlAlchemyStudyMapRepository(db),
        node_repo=SqlAlchemyStudyNodeRepository(db),
    )
    try:
        updated = use_case.execute(
            map_id=map_id,
            node_id=node_id,
            user_id=current_user.id,
            theory_content=payload.theory_content,
        )
        return _serialize_node(updated)
    except (StudyMapNotFoundError, StudyNodeNotFoundError) as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except ResourceOwnershipError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc


@_study_tree_base_router.post(
    "/study-maps/{map_id}/nodes/{node_id}/questions",
    status_code=status.HTTP_201_CREATED,
)
def create_node_question(
    map_id: UUID,
    node_id: UUID,
    payload: CreateNodeQuestionRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    """Cria uma provação SRS diretamente ancorada no nó."""
    effective_prompt = (payload.prompt or payload.statement).strip()
    if not effective_prompt:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="O enunciado da pergunta ('prompt' ou 'statement') é obrigatório.",
        )
    use_case = CreateNodeQuestionUseCase(
        map_repo=SqlAlchemyStudyMapRepository(db),
        node_repo=SqlAlchemyStudyNodeRepository(db),
        question_repo=SqlAlchemyQuestionRepository(db),
        progress_repo=SqlAlchemyQuestionProgressRepository(db),
        content_repo=SqlAlchemyNodeContentRepository(db),
    )
    try:
        res = use_case.execute(
            map_id=map_id,
            node_id=node_id,
            user_id=current_user.id,
            prompt=effective_prompt,
            expected_answer=payload.expected_answer.strip(),
        )
        return {
            "id": str(res["id"]),
            "question_id": str(res["id"]),
            "node_id": str(res["node_id"]),
            "prompt": res["prompt"],
            "statement": res["statement"],
            "expected_answer": res["expected_answer"],
            "current_level": res["current_level"],
            "next_review_date": res["next_review_date"],
            "created_at": res["created_at"],
        }
    except (StudyMapNotFoundError, StudyNodeNotFoundError) as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except ResourceOwnershipError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc


@_study_tree_base_router.delete(
    "/study-maps/{map_id}/nodes/{node_id}/questions/{question_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def delete_node_question(
    map_id: UUID,
    node_id: UUID,
    question_id: UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> None:
    """Exclui uma provação SRS associada ao nó."""
    use_case = DeleteNodeQuestionUseCase(
        map_repo=SqlAlchemyStudyMapRepository(db),
        node_repo=SqlAlchemyStudyNodeRepository(db),
        question_repo=SqlAlchemyQuestionRepository(db),
        content_repo=SqlAlchemyNodeContentRepository(db),
    )
    try:
        use_case.execute(
            map_id=map_id,
            node_id=node_id,
            user_id=current_user.id,
            question_id=question_id,
        )
    except (StudyMapNotFoundError, StudyNodeNotFoundError, QuestionNotFoundError) as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except ResourceOwnershipError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc


@_study_tree_base_router.post(
    "/study-maps/{map_id}/nodes/{node_id}/questions/{question_id}/review",
)
def review_node_question(
    map_id: UUID,
    node_id: UUID,
    question_id: UUID,
    payload: ReviewNodeQuestionRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    """Submete uma revisão SRS no nó com suporte ao Modo Treino Livre."""
    use_case = ReviewNodeQuestionUseCase(
        map_repo=SqlAlchemyStudyMapRepository(db),
        node_repo=SqlAlchemyStudyNodeRepository(db),
        question_repo=SqlAlchemyQuestionRepository(db),
        progress_repo=SqlAlchemyQuestionProgressRepository(db),
        content_repo=SqlAlchemyNodeContentRepository(db),
        edge_repo=SqlAlchemyStudyEdgeRepository(db),
        audit_repo=SqlAlchemyReviewAuditRepository(db),
    )
    try:
        res = use_case.execute(
            map_id=map_id,
            node_id=node_id,
            user_id=current_user.id,
            question_id=question_id,
            score=payload.score,
            difficulty=payload.difficulty,
        )
        return {k: (str(v) if isinstance(v, UUID) else v) for k, v in res.items()}
    except (StudyMapNotFoundError, StudyNodeNotFoundError, QuestionNotFoundError) as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except ResourceOwnershipError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc


@_study_tree_base_router.post(
    "/study-maps/{map_id}/nodes/{node_id}/materials",
    status_code=status.HTTP_201_CREATED,
)
def create_node_material(
    map_id: UUID,
    node_id: UUID,
    payload: CreateNodeMaterialRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    """Cria um material/pergaminho inline associado ao nó."""
    use_case = CreateNodeMaterialUseCase(
        map_repo=SqlAlchemyStudyMapRepository(db),
        node_repo=SqlAlchemyStudyNodeRepository(db),
        source_repo=SqlAlchemyKnowledgeSourceRepository(db),
        content_repo=SqlAlchemyNodeContentRepository(db),
    )
    try:
        res = use_case.execute(
            map_id=map_id,
            node_id=node_id,
            user_id=current_user.id,
            title=payload.title,
            raw_text=payload.raw_text,
            content_type=payload.content_type,
        )
        return {
            "id": str(res["id"]),
            "material_id": str(res["id"]),
            "node_id": str(res["node_id"]),
            "title": res["title"],
            "content_type": res["content_type"],
            "raw_text": res["raw_text"],
            "char_count": res["char_count"],
            "created_at": res["created_at"],
        }
    except (StudyMapNotFoundError, StudyNodeNotFoundError) as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except ResourceOwnershipError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc


@_study_tree_base_router.delete(
    "/study-maps/{map_id}/nodes/{node_id}/materials/{material_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def delete_node_material(
    map_id: UUID,
    node_id: UUID,
    material_id: UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> None:
    """Remove um material associado ao nó."""
    use_case = DeleteNodeMaterialUseCase(
        map_repo=SqlAlchemyStudyMapRepository(db),
        node_repo=SqlAlchemyStudyNodeRepository(db),
        source_repo=SqlAlchemyKnowledgeSourceRepository(db),
        content_repo=SqlAlchemyNodeContentRepository(db),
    )
    try:
        use_case.execute(
            map_id=map_id,
            node_id=node_id,
            user_id=current_user.id,
            material_id=material_id,
        )
    except (StudyMapNotFoundError, StudyNodeNotFoundError, EntityNotFoundError) as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except ResourceOwnershipError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc


@_study_tree_base_router.post("/study-maps/{map_id}/edges", status_code=status.HTTP_201_CREATED)
def connect_study_nodes(
    map_id: UUID,
    payload: ConnectNodesRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    """Cria uma aresta de pré-requisito entre dois nós com verificação de ciclo topológico."""
    use_case = ConnectStudyNodesUseCase(
        map_repo=SqlAlchemyStudyMapRepository(db),
        node_repo=SqlAlchemyStudyNodeRepository(db),
        edge_repo=SqlAlchemyStudyEdgeRepository(db),
    )
    try:
        dto = ConnectNodesDTO(
            source_node_id=payload.source_node_id,
            target_node_id=payload.target_node_id,
            required_level=payload.required_level,
        )
        edge = use_case.execute(map_id=map_id, user_id=current_user.id, dto=dto)
        return _serialize_edge(edge)
    except (StudyMapNotFoundError, StudyNodeNotFoundError) as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except (
        CyclicDependencyError,
        SelfReferencingEdgeError,
        CrossMapEdgeError,
        DomainValidationError,
    ) as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    except ResourceOwnershipError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc


@_study_tree_base_router.patch("/study-maps/{map_id}/edges/{edge_id}")
def update_study_edge(
    map_id: UUID,
    edge_id: UUID,
    payload: UpdateStudyEdgeRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    """Atualiza o nível de maestria requerido em uma dependência orientada."""
    use_case = UpdateStudyEdgeUseCase(
        map_repo=SqlAlchemyStudyMapRepository(db),
        edge_repo=SqlAlchemyStudyEdgeRepository(db),
    )
    try:
        dto = UpdateStudyEdgeDTO(required_level=payload.required_level)
        edge = use_case.execute(map_id=map_id, edge_id=edge_id, user_id=current_user.id, dto=dto)
        return _serialize_edge(edge)
    except (StudyMapNotFoundError, StudyEdgeNotFoundError) as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except ResourceOwnershipError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc
    except DomainValidationError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


@_study_tree_base_router.delete(
    "/study-maps/{map_id}/edges/{edge_id}", status_code=status.HTTP_204_NO_CONTENT
)
def disconnect_study_nodes(
    map_id: UUID,
    edge_id: UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> None:
    """Remove uma dependência orientada entre nós."""
    use_case = DisconnectStudyNodesUseCase(
        map_repo=SqlAlchemyStudyMapRepository(db),
        edge_repo=SqlAlchemyStudyEdgeRepository(db),
    )
    try:
        use_case.execute(map_id=map_id, user_id=current_user.id, edge_id=edge_id)
    except (StudyMapNotFoundError, StudyEdgeNotFoundError) as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except ResourceOwnershipError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc


@_study_tree_base_router.post(
    "/study-maps/{map_id}/nodes/{node_id}/contents", status_code=status.HTTP_204_NO_CONTENT
)
def attach_content_to_node(
    map_id: UUID,
    node_id: UUID,
    payload: AttachContentRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> None:
    """Vincula uma pergunta, material ou flashcard ao nó."""
    use_case = AttachContentToNodeUseCase(
        map_repo=SqlAlchemyStudyMapRepository(db),
        node_repo=SqlAlchemyStudyNodeRepository(db),
        content_repo=SqlAlchemyNodeContentRepository(db),
    )
    try:
        use_case.execute(
            map_id=map_id,
            user_id=current_user.id,
            node_id=node_id,
            content_type=payload.content_type,
            content_id=payload.content_id,
        )
    except (StudyMapNotFoundError, StudyNodeNotFoundError) as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except DomainValidationError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    except ResourceOwnershipError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc


@_study_tree_base_router.delete(
    "/study-maps/{map_id}/nodes/{node_id}/contents/{content_type}/{content_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def detach_content_from_node(
    map_id: UUID,
    node_id: UUID,
    content_type: str,
    content_id: UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> None:
    """Desvincula uma pergunta, material ou flashcard do nó."""
    use_case = DetachContentFromNodeUseCase(
        map_repo=SqlAlchemyStudyMapRepository(db),
        node_repo=SqlAlchemyStudyNodeRepository(db),
        content_repo=SqlAlchemyNodeContentRepository(db),
    )
    try:
        use_case.execute(
            map_id=map_id,
            user_id=current_user.id,
            node_id=node_id,
            content_type=content_type,
            content_id=content_id,
        )
    except (StudyMapNotFoundError, StudyNodeNotFoundError) as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except DomainValidationError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    except ResourceOwnershipError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc


@_study_tree_base_router.get("/study-maps/{map_id}/nodes/{node_id}/hub")
@_study_tree_base_router.get("/study-maps/{map_id}/nodes/{node_id}/study-hub")
def get_node_study_hub(
    map_id: UUID,
    node_id: UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    """Retorna todos os conteúdos agrupados do nó para sessão de estudo ativo."""
    use_case = GetNodeStudyHubUseCase(
        map_repo=SqlAlchemyStudyMapRepository(db),
        node_repo=SqlAlchemyStudyNodeRepository(db),
        content_repo=SqlAlchemyNodeContentRepository(db),
        progress_repo=SqlAlchemyQuestionProgressRepository(db),
        question_repo=SqlAlchemyQuestionRepository(db),
        knowledge_repo=SqlAlchemyKnowledgeSourceRepository(db),
        flashcard_repo=SqlAlchemyFlashcardRepository(db),
    )
    try:
        hub = use_case.execute(map_id=map_id, user_id=current_user.id, node_id=node_id)
        return {
            "node": _serialize_node(hub.node),
            "materials": hub.materials,
            "due_questions": hub.due_questions,
            "all_questions": hub.all_questions,
            "flashcards": hub.flashcards,
        }
    except (StudyMapNotFoundError, StudyNodeNotFoundError) as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except ResourceOwnershipError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc


# --- Roteadores Exportados (com suporte a /api/v1 e /api) ---

api_study_tree_router = APIRouter(prefix="/api/v1", tags=["Study Tree & Knowledge Graph"])
api_study_tree_router.include_router(_study_tree_base_router)

api_study_tree_compat_router = APIRouter(
    prefix="/api", tags=["Study Tree & Knowledge Graph (Compat)"]
)
api_study_tree_compat_router.include_router(_study_tree_base_router)

__all__ = [
    "api_study_tree_router",
    "api_study_tree_compat_router",
    "_serialize_node",
    "_serialize_edge",
    "UpdateStudyEdgeRequest",
]
