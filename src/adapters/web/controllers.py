"""Controladores Web com Jinja2 e HTMX (Camada 3 - Adaptadores)."""

from pathlib import Path
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Form, Query, Request, Response
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from src.adapters.persistence.repositories import (
    SqlAlchemyFlashcardRepository,
    SqlAlchemySessionRepository,
    SqlAlchemySubjectRepository,
    SqlAlchemyTopicRepository,
)
from src.application.dto.flashcard_dto import CreateFlashcardDTO
from src.application.dto.study_dto import GetNextCardDTO, StudyCardDTO
from src.application.dto.subject_dto import CreateSubjectDTO
from src.application.dto.topic_dto import CreateTopicDTO
from src.application.use_cases.auth_use_cases import ToggleSubjectPublicUseCase
from src.application.use_cases.flashcard_use_cases import CreateFlashcardUseCase
from src.application.use_cases.study_session_use_cases import (
    GetCurrentStudyCardUseCase,
    GetNextFlashcardUseCase,
)
from src.application.use_cases.subject_use_cases import (
    CreateSubjectUseCase,
    ListSubjectsUseCase,
)
from src.application.use_cases.topic_use_cases import (
    CreateTopicUseCase,
    ListTopicsBySubjectUseCase,
)
from src.domain.entities import User
from src.domain.exceptions import DomainException, EmptyPoolError
from src.infrastructure.database import get_db
from src.infrastructure.rng import default_rng
from src.infrastructure.security.dependencies import get_current_user
from src.infrastructure.security.sanitization import sanitize_html_content

templates_dir = Path(__file__).resolve().parent / "templates"
templates = Jinja2Templates(directory=str(templates_dir))

web_router = APIRouter()


def _parse_uuid(val: str | None) -> UUID | None:
    """Converte string para UUID com segurança, tratando valores vazios ou inválidos como None."""
    try:
        if val is not None and str(val).strip():
            return UUID(str(val).strip())
    except (ValueError, AttributeError, TypeError):
        return None
    return None


@web_router.get("/", response_class=RedirectResponse)
def index() -> RedirectResponse:
    """Redireciona a raiz para a tela principal de estudo."""
    return RedirectResponse(url="/study", status_code=303)


@web_router.get("/study", response_class=HTMLResponse)
def study_view(
    request: Request,
    subject_id: str | None = None,
    topic_id: str | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> HTMLResponse:
    """Renderiza a tela de estudo de flashcards com suporte a filtros e Gap Indexing."""
    sub_uuid = _parse_uuid(subject_id)
    top_uuid = _parse_uuid(topic_id)

    subject_repo = SqlAlchemySubjectRepository(db)
    topic_repo = SqlAlchemyTopicRepository(db)
    card_repo = SqlAlchemyFlashcardRepository(db)
    session_repo = SqlAlchemySessionRepository(db)

    subjects = ListSubjectsUseCase(subject_repo).execute(user_id=current_user.id)
    topics = ListTopicsBySubjectUseCase(topic_repo).execute(sub_uuid) if sub_uuid else []

    # Information Scent: Contagem de cards disponíveis por matéria/tema via GROUP BY
    global_card_count = card_repo.count_pool(None, None)
    subject_counts = card_repo.count_by_subjects()
    subject_card_counts: dict[str, int] = {
        str(sub.id): subject_counts.get(sub.id, 0) for sub in subjects
    }
    topic_counts = card_repo.count_by_topics()
    topic_card_counts: dict[str, int] = {str(top.id): topic_counts.get(top.id, 0) for top in topics}

    card: StudyCardDTO | None = None
    try:
        get_current_uc = GetCurrentStudyCardUseCase(
            card_repo, session_repo, topic_repo, subject_repo=subject_repo
        )
        card = get_current_uc.execute(
            GetNextCardDTO(subject_id=sub_uuid, topic_id=top_uuid),
            user_id=current_user.id,
        )
    except (EmptyPoolError, DomainException):
        card = None

    context = {
        "card": card,
        "side": "front",
        "subjects": subjects,
        "topics": topics,
        "selected_subject_id": str(sub_uuid) if sub_uuid else None,
        "selected_topic_id": str(top_uuid) if top_uuid else None,
        "subject_id": sub_uuid,
        "topic_id": top_uuid,
        "global_card_count": global_card_count,
        "subject_card_counts": subject_card_counts,
        "topic_card_counts": topic_card_counts,
        "update_filters": True,
        "current_user": current_user,
    }

    # Se for requisição ágil HTMX, renderiza apenas o fragmento parcial com swaps out-of-band
    if request.headers.get("HX-Request") == "true":
        return templates.TemplateResponse(
            request=request,
            name="partials/card.html",
            context=context,
        )

    return templates.TemplateResponse(
        request=request,
        name="study.html",
        context=context,
    )


@web_router.post("/study/flip", response_class=HTMLResponse)
def flip_card(
    request: Request,
    card_id: Annotated[UUID, Form()],
    side: Annotated[str, Form()],
    current_index: Annotated[int, Form()],
    total_cards: Annotated[int, Form()],
    round_number: Annotated[int, Form()],
    position: Annotated[int, Form()],
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> HTMLResponse:
    """Endpoint HTMX para alternar entre pergunta e resposta sem recarregar a tela."""
    card_repo = SqlAlchemyFlashcardRepository(db)
    topic_repo = SqlAlchemyTopicRepository(db)
    card = card_repo.get_by_id(card_id)

    if card is None:
        return templates.TemplateResponse(
            request=request,
            name="partials/card.html",
            context={"card": None, "side": "front", "current_user": current_user},
        )

    topic_names: list[str] = []
    for t_id in card.topic_ids:
        t = topic_repo.get_by_id(t_id)
        if t:
            topic_names.append(t.name)

    new_side = "back" if side == "front" else "front"
    study_dto = StudyCardDTO(
        id=card.id,
        topic_ids=list(card.topic_ids),
        topic_names=topic_names,
        front=card.front,
        back=card.back,
        position=position,
        current_index=current_index,
        total_cards=total_cards,
        round_number=round_number,
        round_shuffled=False,
    )

    return templates.TemplateResponse(
        request=request,
        name="partials/card.html",
        context={"card": study_dto, "side": new_side, "current_user": current_user},
    )


@web_router.post("/study/next", response_class=HTMLResponse)
def next_card(
    request: Request,
    subject_id: Annotated[str | None, Form()] = None,
    topic_id: Annotated[str | None, Form()] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> HTMLResponse:
    """Endpoint HTMX para avançar para o próximo card da rodada."""
    sub_uuid = _parse_uuid(subject_id)
    top_uuid = _parse_uuid(topic_id)

    card_repo = SqlAlchemyFlashcardRepository(db)
    session_repo = SqlAlchemySessionRepository(db)
    topic_repo = SqlAlchemyTopicRepository(db)
    subject_repo = SqlAlchemySubjectRepository(db)

    card: StudyCardDTO | None = None
    try:
        get_next_uc = GetNextFlashcardUseCase(
            card_repo,
            session_repo,
            default_rng,
            topic_repo=topic_repo,
            subject_repo=subject_repo,
        )
        card = get_next_uc.execute(
            GetNextCardDTO(subject_id=sub_uuid, topic_id=top_uuid),
            user_id=current_user.id,
        )
    except (EmptyPoolError, DomainException):
        card = None

    return templates.TemplateResponse(
        request=request,
        name="partials/card.html",
        context={
            "card": card,
            "side": "front",
            "subject_id": sub_uuid,
            "topic_id": top_uuid,
            "current_user": current_user,
        },
    )


@web_router.get("/flashcards/new", response_class=HTMLResponse)
def new_flashcard_view(
    request: Request,
    subject_id: str | None = None,
    topic_id: str | None = None,
    topic_ids: Annotated[list[str] | None, Query()] = None,
    success: bool = False,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> HTMLResponse:
    """Tela de cadastro ágil de flashcards com seleção de múltiplos temas (ADR-004)."""
    top_uuid = _parse_uuid(topic_id)
    subject_repo = SqlAlchemySubjectRepository(db)
    topic_repo = SqlAlchemyTopicRepository(db)

    subjects = subject_repo.list_by_owner(current_user.id)
    topics_by_subject = [
        {"subject": s, "topics": topic_repo.list_by_subject(s.id)} for s in subjects
    ]

    selected: list[str] = list(topic_ids) if topic_ids else []
    if top_uuid and str(top_uuid) not in selected:
        selected.append(str(top_uuid))

    return templates.TemplateResponse(
        request=request,
        name="flashcards_new.html",
        context={
            "topics_by_subject": topics_by_subject,
            "selected_topic_ids": selected,
            "front": "",
            "back": "",
            "success": success,
            "error": None,
            "current_user": current_user,
        },
    )


@web_router.post("/flashcards", response_model=None)
def create_flashcard_web(
    request: Request,
    topic_ids: Annotated[list[UUID] | None, Form()] = None,
    topic_id: Annotated[UUID | None, Form()] = None,
    front: Annotated[str, Form()] = "",
    back: Annotated[str, Form()] = "",
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Response:
    """Processa o cadastro ágil de flashcard e redireciona continuamente (Botão Único Salvar)."""
    card_repo = SqlAlchemyFlashcardRepository(db)
    topic_repo = SqlAlchemyTopicRepository(db)
    session_repo = SqlAlchemySessionRepository(db)
    subject_repo = SqlAlchemySubjectRepository(db)

    clean_front = sanitize_html_content(front)
    clean_back = sanitize_html_content(back)

    target_topic_ids = (topic_ids or []) or ([topic_id] if topic_id is not None else [])

    try:
        use_case = CreateFlashcardUseCase(
            card_repo,
            topic_repo,
            session_repo,
            default_rng,
            subject_repo=subject_repo,
        )
        use_case.execute(
            CreateFlashcardDTO(
                topic_ids=target_topic_ids,
                front=clean_front,
                back=clean_back,
            ),
            user_id=current_user.id,
        )
    except DomainException as exc:
        subjects = subject_repo.list_by_owner(current_user.id)
        topics_by_subject = [
            {"subject": s, "topics": topic_repo.list_by_subject(s.id)} for s in subjects
        ]
        return templates.TemplateResponse(
            request=request,
            name="flashcards_new.html",
            context={
                "topics_by_subject": topics_by_subject,
                "selected_topic_ids": [str(t) for t in target_topic_ids],
                "front": front,
                "back": back,
                "success": False,
                "error": str(exc),
                "current_user": current_user,
            },
            status_code=400,
        )

    query_params = "&".join(f"topic_ids={tid}" for tid in target_topic_ids)
    redirect_url = (
        f"/flashcards/new?success=1&{query_params}" if query_params else "/flashcards/new?success=1"
    )
    return RedirectResponse(url=redirect_url, status_code=303)


@web_router.get("/subjects", response_class=HTMLResponse)
def subjects_view(
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> HTMLResponse:
    """Gerenciamento de Matérias e Temas."""
    subject_repo = SqlAlchemySubjectRepository(db)

    subjects_with_topics = subject_repo.list_all_with_topics(user_id=current_user.id)
    subjects = [sub for sub, _ in subjects_with_topics]
    topics_by_subject = {sub.id: topics for sub, topics in subjects_with_topics}

    return templates.TemplateResponse(
        request=request,
        name="subjects.html",
        context={
            "subjects": subjects,
            "topics_by_subject": topics_by_subject,
            "error": None,
            "current_user": current_user,
        },
    )


@web_router.post("/subjects", response_model=None)
def create_subject_web(
    request: Request,
    name: Annotated[str, Form()],
    is_public: Annotated[bool, Form()] = False,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Response:
    """Criação de nova matéria via formulário."""
    subject_repo = SqlAlchemySubjectRepository(db)
    try:
        CreateSubjectUseCase(subject_repo).execute(
            CreateSubjectDTO(name=name, is_public=is_public),
            owner_id=current_user.id,
        )
    except DomainException as exc:
        subjects_with_topics = subject_repo.list_all_with_topics(user_id=current_user.id)
        subjects = [sub for sub, _ in subjects_with_topics]
        topics_by_subject = {sub.id: topics for sub, topics in subjects_with_topics}
        return templates.TemplateResponse(
            request=request,
            name="subjects.html",
            context={
                "subjects": subjects,
                "topics_by_subject": topics_by_subject,
                "error": str(exc),
                "current_user": current_user,
            },
            status_code=400,
        )
    return RedirectResponse(url="/subjects", status_code=303)


@web_router.post("/subjects/{subject_id}/toggle-public", response_model=None)
def toggle_subject_public_web(
    request: Request,
    subject_id: UUID,
    is_public: Annotated[bool, Form()] = False,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Response:
    """Alterna visibilidade pública da matéria pelo proprietário."""
    subject_repo = SqlAlchemySubjectRepository(db)
    try:
        ToggleSubjectPublicUseCase(subject_repo).execute(
            user_id=current_user.id,
            subject_id=subject_id,
            is_public=is_public,
        )
    except DomainException as exc:
        subjects_with_topics = subject_repo.list_all_with_topics(user_id=current_user.id)
        subjects = [sub for sub, _ in subjects_with_topics]
        topics_by_subject = {sub.id: topics for sub, topics in subjects_with_topics}
        return templates.TemplateResponse(
            request=request,
            name="subjects.html",
            context={
                "subjects": subjects,
                "topics_by_subject": topics_by_subject,
                "error": str(exc),
                "current_user": current_user,
            },
            status_code=400,
        )
    return RedirectResponse(url="/subjects", status_code=303)


@web_router.post("/topics", response_model=None)
def create_topic_web(
    request: Request,
    subject_id: Annotated[UUID, Form()],
    name: Annotated[str, Form()],
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Response:
    """Criação de novo tema via formulário."""
    subject_repo = SqlAlchemySubjectRepository(db)
    topic_repo = SqlAlchemyTopicRepository(db)
    try:
        CreateTopicUseCase(subject_repo, topic_repo).execute(
            CreateTopicDTO(subject_id=subject_id, name=name),
            user_id=current_user.id,
        )
    except DomainException as exc:
        subjects_with_topics = subject_repo.list_all_with_topics(user_id=current_user.id)
        subjects = [sub for sub, _ in subjects_with_topics]
        topics_by_subject = {sub.id: topics for sub, topics in subjects_with_topics}
        return templates.TemplateResponse(
            request=request,
            name="subjects.html",
            context={
                "subjects": subjects,
                "topics_by_subject": topics_by_subject,
                "error": str(exc),
                "current_user": current_user,
            },
            status_code=400,
        )
    return RedirectResponse(url="/subjects", status_code=303)
