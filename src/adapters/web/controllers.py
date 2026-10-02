"""Controladores Web com Jinja2 e HTMX (Camada 3 - Adaptadores)."""

from pathlib import Path
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Form, Request, Response
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
from src.domain.exceptions import DomainException, EmptyPoolError
from src.infrastructure.database import get_db
from src.infrastructure.rng import default_rng
from src.infrastructure.security.sanitization import sanitize_html_content

templates_dir = Path(__file__).resolve().parent / "templates"
templates = Jinja2Templates(directory=str(templates_dir))

web_router = APIRouter()


def _parse_uuid(val: str | None) -> UUID | None:
    """Converte string para UUID com segurança, tratando valores vazios como None."""
    if val and val.strip():
        try:
            return UUID(val.strip())
        except ValueError:
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
) -> HTMLResponse:
    """Renderiza a tela de estudo de flashcards com suporte a filtros e Gap Indexing."""
    sub_uuid = _parse_uuid(subject_id)
    top_uuid = _parse_uuid(topic_id)

    subject_repo = SqlAlchemySubjectRepository(db)
    topic_repo = SqlAlchemyTopicRepository(db)
    card_repo = SqlAlchemyFlashcardRepository(db)
    session_repo = SqlAlchemySessionRepository(db)

    subjects = ListSubjectsUseCase(subject_repo).execute()
    topics = ListTopicsBySubjectUseCase(topic_repo).execute(sub_uuid) if sub_uuid else []

    card: StudyCardDTO | None = None
    try:
        get_current_uc = GetCurrentStudyCardUseCase(card_repo, session_repo)
        card = get_current_uc.execute(GetNextCardDTO(subject_id=sub_uuid, topic_id=top_uuid))
    except EmptyPoolError:
        card = None

    return templates.TemplateResponse(
        request=request,
        name="study.html",
        context={
            "card": card,
            "side": "front",
            "subjects": subjects,
            "topics": topics,
            "selected_subject_id": str(sub_uuid) if sub_uuid else None,
            "selected_topic_id": str(top_uuid) if top_uuid else None,
            "subject_id": sub_uuid,
            "topic_id": top_uuid,
        },
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
) -> HTMLResponse:
    """Endpoint HTMX para alternar entre pergunta e resposta sem recarregar a tela."""
    card_repo = SqlAlchemyFlashcardRepository(db)
    card = card_repo.get_by_id(card_id)

    if card is None:
        return templates.TemplateResponse(
            request=request,
            name="partials/card.html",
            context={"card": None, "side": "front"},
        )

    new_side = "back" if side == "front" else "front"
    study_dto = StudyCardDTO(
        id=card.id,
        topic_id=card.topic_id,
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
        context={"card": study_dto, "side": new_side},
    )


@web_router.post("/study/next", response_class=HTMLResponse)
def next_card(
    request: Request,
    subject_id: Annotated[str | None, Form()] = None,
    topic_id: Annotated[str | None, Form()] = None,
    db: Session = Depends(get_db),
) -> HTMLResponse:
    """Endpoint HTMX para avançar para o próximo card da rodada."""
    sub_uuid = _parse_uuid(subject_id)
    top_uuid = _parse_uuid(topic_id)

    card_repo = SqlAlchemyFlashcardRepository(db)
    session_repo = SqlAlchemySessionRepository(db)

    card: StudyCardDTO | None = None
    try:
        get_next_uc = GetNextFlashcardUseCase(card_repo, session_repo, default_rng)
        card = get_next_uc.execute(GetNextCardDTO(subject_id=sub_uuid, topic_id=top_uuid))
    except EmptyPoolError:
        card = None

    return templates.TemplateResponse(
        request=request,
        name="partials/card.html",
        context={
            "card": card,
            "side": "front",
            "subject_id": sub_uuid,
            "topic_id": top_uuid,
        },
    )


@web_router.get("/flashcards/new", response_class=HTMLResponse)
def new_flashcard_view(
    request: Request,
    subject_id: str | None = None,
    topic_id: str | None = None,
    success: bool = False,
    db: Session = Depends(get_db),
) -> HTMLResponse:
    """Tela de cadastro ágil de flashcards com atalhos."""
    sub_uuid = _parse_uuid(subject_id)
    top_uuid = _parse_uuid(topic_id)
    topic_repo = SqlAlchemyTopicRepository(db)
    topics = topic_repo.list_by_subject(sub_uuid) if sub_uuid else []
    if not topics:
        # Se não filtrou por matéria, lista todos os temas existentes
        from sqlalchemy import select

        from src.adapters.persistence.mappers import TopicMapper
        from src.adapters.persistence.models import TopicModel

        all_models = db.scalars(select(TopicModel).order_by(TopicModel.name.asc())).all()
        topics = [TopicMapper.to_domain(m) for m in all_models]

    return templates.TemplateResponse(
        request=request,
        name="flashcards_new.html",
        context={
            "topics": topics,
            "selected_topic_id": str(top_uuid) if top_uuid else None,
            "success": success,
            "error": None,
        },
    )


@web_router.post("/flashcards", response_model=None)
def create_flashcard_web(
    request: Request,
    topic_id: Annotated[UUID, Form()],
    front: Annotated[str, Form()] = "",
    back: Annotated[str, Form()] = "",
    action: Annotated[str, Form()] = "save_and_study",
    db: Session = Depends(get_db),
) -> Response:
    """Processa o cadastro ágil de flashcard e redireciona conforme a ação."""
    card_repo = SqlAlchemyFlashcardRepository(db)
    topic_repo = SqlAlchemyTopicRepository(db)
    session_repo = SqlAlchemySessionRepository(db)

    clean_front = sanitize_html_content(front)
    clean_back = sanitize_html_content(back)

    try:
        use_case = CreateFlashcardUseCase(card_repo, topic_repo, session_repo, default_rng)
        use_case.execute(CreateFlashcardDTO(topic_id=topic_id, front=clean_front, back=clean_back))
    except DomainException as exc:
        from sqlalchemy import select

        from src.adapters.persistence.mappers import TopicMapper
        from src.adapters.persistence.models import TopicModel

        all_models = db.scalars(select(TopicModel).order_by(TopicModel.name.asc())).all()
        all_topics = [TopicMapper.to_domain(m) for m in all_models]
        return templates.TemplateResponse(
            request=request,
            name="flashcards_new.html",
            context={
                "topics": all_topics,
                "selected_topic_id": str(topic_id),
                "success": False,
                "error": str(exc),
            },
            status_code=400,
        )

    if action == "save_and_new":
        return RedirectResponse(
            url=f"/flashcards/new?topic_id={topic_id}&success=1", status_code=303
        )

    return RedirectResponse(url=f"/study?topic_id={topic_id}", status_code=303)


@web_router.get("/subjects", response_class=HTMLResponse)
def subjects_view(request: Request, db: Session = Depends(get_db)) -> HTMLResponse:
    """Gerenciamento de Matérias e Temas."""
    subject_repo = SqlAlchemySubjectRepository(db)
    topic_repo = SqlAlchemyTopicRepository(db)

    subjects = ListSubjectsUseCase(subject_repo).execute()
    topics_by_subject = {
        s.id: ListTopicsBySubjectUseCase(topic_repo).execute(s.id) for s in subjects
    }

    return templates.TemplateResponse(
        request=request,
        name="subjects.html",
        context={
            "subjects": subjects,
            "topics_by_subject": topics_by_subject,
            "error": None,
        },
    )


@web_router.post("/subjects", response_model=None)
def create_subject_web(
    request: Request,
    name: Annotated[str, Form()],
    db: Session = Depends(get_db),
) -> Response:
    """Criação de nova matéria via formulário."""
    subject_repo = SqlAlchemySubjectRepository(db)
    try:
        CreateSubjectUseCase(subject_repo).execute(CreateSubjectDTO(name=name))
    except DomainException as exc:
        subjects = ListSubjectsUseCase(subject_repo).execute()
        return templates.TemplateResponse(
            request=request,
            name="subjects.html",
            context={"subjects": subjects, "topics_by_subject": {}, "error": str(exc)},
            status_code=400,
        )
    return RedirectResponse(url="/subjects", status_code=303)


@web_router.post("/topics", response_model=None)
def create_topic_web(
    request: Request,
    subject_id: Annotated[UUID, Form()],
    name: Annotated[str, Form()],
    db: Session = Depends(get_db),
) -> Response:
    """Criação de novo tema via formulário."""
    subject_repo = SqlAlchemySubjectRepository(db)
    topic_repo = SqlAlchemyTopicRepository(db)
    try:
        CreateTopicUseCase(subject_repo, topic_repo).execute(
            CreateTopicDTO(subject_id=subject_id, name=name)
        )
    except DomainException as exc:
        subjects = ListSubjectsUseCase(subject_repo).execute()
        return templates.TemplateResponse(
            request=request,
            name="subjects.html",
            context={"subjects": subjects, "topics_by_subject": {}, "error": str(exc)},
            status_code=400,
        )
    return RedirectResponse(url="/subjects", status_code=303)
