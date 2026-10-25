"""Controladores Web Jinja2 para a Árvore de Estudos RPG e Canvas Interativo (Camada 3)."""

from pathlib import Path
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from src.adapters.persistence.repositories import (
    SqlAlchemyStudyMapRepository,
    SqlAlchemyStudyNodeRepository,
)
from src.domain.entities import User
from src.infrastructure.database import get_db
from src.infrastructure.security.dependencies import get_current_user

templates_dir = Path(__file__).resolve().parent / "templates"
templates = Jinja2Templates(directory=str(templates_dir))

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
