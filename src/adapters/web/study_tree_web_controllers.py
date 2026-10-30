"""Controladores Web Jinja2 para a Árvore de Estudos RPG e Canvas Interativo (Camada 3)."""

from pathlib import Path
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from src.adapters.persistence.repositories import (
    SqlAlchemyFlashcardRepository,
    SqlAlchemyKnowledgeSourceRepository,
    SqlAlchemyNodeContentRepository,
    SqlAlchemyQuestionProgressRepository,
    SqlAlchemyQuestionRepository,
    SqlAlchemyStudyEdgeRepository,
    SqlAlchemyStudyMapRepository,
    SqlAlchemyStudyNodeRepository,
)
from src.adapters.web.rpg_icons import get_rpg_icon_svg
from src.application.use_cases.study_tree_use_cases import GetNodeStudyHubUseCase
from src.domain.entities import User
from src.domain.services import StudyTreeProgressionService
from src.infrastructure.database import get_db
from src.infrastructure.security.dependencies import get_current_user

templates_dir = Path(__file__).resolve().parent / "templates"
templates = Jinja2Templates(directory=str(templates_dir))
templates.env.globals["get_rpg_icon_svg"] = get_rpg_icon_svg

web_study_tree_router = APIRouter()


@web_study_tree_router.get("/study-maps", response_class=HTMLResponse)
def list_study_maps_page(
    request: Request,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Response:
    """Página de seleção de Árvores de Estudos RPG / Campanhas de Conhecimento."""
    map_repo = SqlAlchemyStudyMapRepository(db)
    node_repo = SqlAlchemyStudyNodeRepository(db)

    user_maps = map_repo.list_by_owner(current_user.id)
    root_maps_data: list[dict[str, object]] = []

    for m in user_maps:
        if m.parent_node_id is None:  # Apenas mapas raiz na visão de campanhas
            nodes = node_repo.list_by_map(m.id)
            root_maps_data.append(
                {
                    "id": str(m.id),
                    "title": m.title,
                    "description": m.description or "Sem descrição cadastrada.",
                    "is_public": m.is_public,
                    "nodes_count": len(nodes),
                    "created_at": m.created_at.strftime("%d/%m/%Y"),
                }
            )

    return templates.TemplateResponse(
        request=request,
        name="study_tree/maps_list.html",
        context={
            "current_user": current_user,
            "user": current_user,
            "maps": root_maps_data,
        },
    )


@web_study_tree_router.get("/study-maps/{map_id}/canvas", response_class=HTMLResponse)
def study_tree_canvas_page(
    request: Request,
    map_id: UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Response:
    """Página do Canvas Interativo RPG com editor visual e modo de estudo."""
    map_repo = SqlAlchemyStudyMapRepository(db)
    node_repo = SqlAlchemyStudyNodeRepository(db)

    study_map = map_repo.get_by_id(map_id)
    if study_map is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Mapa de estudos não encontrado.",
        )

    if study_map.owner_id != current_user.id and not study_map.is_public:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Acesso não autorizado ao mapa.",
        )

    parent_map_id: str | None = None
    parent_node_title: str | None = None
    if study_map.parent_node_id:
        parent_node = node_repo.get_by_id(study_map.parent_node_id)
        if parent_node:
            parent_map_id = str(parent_node.map_id)
            parent_node_title = parent_node.title

    return templates.TemplateResponse(
        request=request,
        name="study_tree/canvas.html",
        context={
            "current_user": current_user,
            "user": current_user,
            "map": {
                "id": str(study_map.id),
                "title": study_map.title,
                "description": study_map.description or "",
                "is_public": study_map.is_public,
                "is_submap": study_map.is_submap,
                "parent_map_id": parent_map_id,
                "parent_node_title": parent_node_title,
                "is_owner": study_map.owner_id == current_user.id,
            },
        },
    )


@web_study_tree_router.get("/study-maps/{map_id}/nodes/{node_id}", response_class=HTMLResponse)
def study_node_grimoire_page(
    request: Request,
    map_id: UUID,
    node_id: UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Response:
    """Página Dedicada do Nó — O Grimório Aberto (Tomo de Sabedoria & Provações SRS)."""
    map_repo = SqlAlchemyStudyMapRepository(db)
    node_repo = SqlAlchemyStudyNodeRepository(db)
    edge_repo = SqlAlchemyStudyEdgeRepository(db)
    content_repo = SqlAlchemyNodeContentRepository(db)
    progress_repo = SqlAlchemyQuestionProgressRepository(db)
    question_repo = SqlAlchemyQuestionRepository(db)
    knowledge_repo = SqlAlchemyKnowledgeSourceRepository(db)
    flashcard_repo = SqlAlchemyFlashcardRepository(db)

    study_map = map_repo.get_by_id(map_id)
    if study_map is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Mapa de estudos não encontrado.",
        )

    if study_map.owner_id != current_user.id and not study_map.is_public:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Acesso não autorizado ao mapa.",
        )

    node = node_repo.get_by_id(node_id)
    if node is None or node.map_id != map_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Nó de estudo não encontrado no mapa informado.",
        )

    hub_uc = GetNodeStudyHubUseCase(
        map_repo=map_repo,
        node_repo=node_repo,
        content_repo=content_repo,
        progress_repo=progress_repo,
        question_repo=question_repo,
        knowledge_repo=knowledge_repo,
        flashcard_repo=flashcard_repo,
    )
    hub = hub_uc.execute(map_id=map_id, user_id=current_user.id, node_id=node_id)

    # Pré-requisitos e status de destrancamento
    map_edges = edge_repo.list_by_map(map_id)
    incoming_edges = [e for e in map_edges if e.target_node_id == node_id]
    prereq_nodes = [node_repo.get_by_id(e.source_node_id) for e in incoming_edges]
    prereq_titles = [pn.title for pn in prereq_nodes if pn is not None]

    all_map_nodes = node_repo.list_by_map(map_id)
    node_levels: dict[UUID, int] = {}
    for n in all_map_nodes:
        _, n_q_ids, _ = content_repo.get_attached_ids(n.id)
        if hasattr(question_repo, "list_by_node"):
            direct_qs = question_repo.list_by_node(n.id)
            n_q_ids = list(set(n_q_ids) | {q.id for q in direct_qs})
        if n_q_ids:
            n_prog = progress_repo.get_by_questions(current_user.id, n_q_ids)
            lvl = StudyTreeProgressionService.calculate_node_level(
                [n_prog[qid].current_level if qid in n_prog else 0 for qid in n_q_ids]
            )
        else:
            lvl = 0
        node_levels[n.id] = lvl

    is_unlocked = StudyTreeProgressionService.evaluate_unlock_status(incoming_edges, node_levels)

    incoming_requirements = []
    for edge in incoming_edges:
        parent_node = next((n for n in all_map_nodes if n.id == edge.source_node_id), None)
        parent_lvl = node_levels.get(edge.source_node_id, 0)
        req_lvl = getattr(edge, "required_level", 1) or 1
        parent_title = parent_node.title if parent_node else "Nó Ancestral"
        incoming_requirements.append(
            {
                "title": parent_title,
                "required_level": req_lvl,
                "current_level": parent_lvl,
                "satisfied": parent_lvl >= req_lvl,
            }
        )

    mastered_count = 0
    for q_item in hub.all_questions:
        if isinstance(q_item, dict):
            lvl_val = q_item.get("current_level", 0)
            if isinstance(lvl_val, int) and lvl_val >= 1:
                mastered_count += 1
    total_questions = len(hub.all_questions)
    progress_percent = (
        round((mastered_count / total_questions) * 100, 1) if total_questions > 0 else 0.0
    )

    return templates.TemplateResponse(
        request=request,
        name="study_tree/node_grimoire.html",
        context={
            "current_user": current_user,
            "user": current_user,
            "map": {
                "id": str(study_map.id),
                "title": study_map.title,
                "description": study_map.description or "",
                "is_public": study_map.is_public,
                "is_owner": study_map.owner_id == current_user.id,
            },
            "node": {
                "id": str(node.id),
                "map_id": str(node.map_id),
                "title": node.title,
                "description": node.description or "",
                "icon": node.icon,
                "theory_content": node.theory_content,
                "effective_level": hub.node.effective_level,
                "is_unlocked": is_unlocked,
                "overdue_questions_count": hub.node.overdue_questions_count,
                "prereq_titles": prereq_titles,
                "incoming_requirements": incoming_requirements,
                "mastered_questions_count": mastered_count,
                "total_questions_count": total_questions,
                "progress_percent": progress_percent,
            },
            "materials": hub.materials,
            "questions": hub.all_questions,
            "due_questions": hub.due_questions,
            "flashcards": hub.flashcards,
        },
    )
