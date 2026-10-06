"""Controladores de API REST (JSON para mobile e clientes externos - Camada 3)."""

from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from src.adapters.persistence.repositories import (
    SqlAlchemyFlashcardRepository,
    SqlAlchemySessionRepository,
    SqlAlchemyStudyEventRepository,
    SqlAlchemySubjectRepository,
    SqlAlchemyTopicRepository,
)
from src.application.dto.flashcard_dto import CreateFlashcardDTO, FlashcardDTO
from src.application.dto.study_dto import (
    GetNextCardDTO,
    StudyBatchDTO,
    StudyCardDTO,
    StudyEventDTO,
    SyncStudyBatchDTO,
)
from src.application.dto.subject_dto import CreateSubjectDTO, SubjectDTO
from src.application.dto.topic_dto import CreateTopicDTO, TopicDTO
from src.application.ports.repositories import IStudyEventRepository
from src.application.use_cases.auth_use_cases import ToggleSubjectPublicUseCase
from src.application.use_cases.flashcard_use_cases import CreateFlashcardUseCase
from src.application.use_cases.study_session_use_cases import (
    GetNextFlashcardUseCase,
    GetStudyBatchUseCase,
)
from src.application.use_cases.subject_use_cases import (
    CreateSubjectUseCase,
    ListSubjectsUseCase,
)
from src.application.use_cases.sync_study_answers_use_case import SyncStudyAnswersUseCase
from src.application.use_cases.topic_use_cases import (
    CreateTopicUseCase,
    ListTopicsBySubjectUseCase,
)
from src.domain.entities import User
from src.domain.exceptions import (
    DomainValidationError,
    DuplicateEntityError,
    EmptyPoolError,
    EntityNotFoundError,
    ResourceOwnershipError,
)
from src.infrastructure.config import settings
from src.infrastructure.database import get_db
from src.infrastructure.rng import default_rng
from src.infrastructure.security.dependencies import get_current_user
from src.infrastructure.security.rate_limiter import study_sync_rate_limiter
from src.infrastructure.security.sanitization import sanitize_html_content

api_router = APIRouter(prefix="/api/v1")


class CreateSubjectRequest(BaseModel):
    name: str = Field(..., min_length=2, max_length=100)
    is_public: bool = False


class TogglePublicRequest(BaseModel):
    is_public: bool


class CreateTopicRequest(BaseModel):
    subject_id: UUID
    name: str = Field(..., min_length=2, max_length=100)


class CreateFlashcardRequest(BaseModel):
    front: str = Field(..., min_length=1, max_length=5000)
    back: str = Field(..., min_length=1, max_length=10000)
    topic_ids: list[UUID] = Field(default_factory=list)
    topic_id: UUID | None = None


class StudyEventItemRequest(BaseModel):
    card_id: UUID
    reviewed_at: datetime
    status: str = Field(..., pattern="^(viewed|completed)$")
    id: UUID | None = None
    device_id: str | None = Field(default=None, max_length=50)


class SyncAnswersPayload(BaseModel):
    session_id: UUID
    events: list[StudyEventItemRequest] = Field(..., min_length=1, max_length=100)
    batch_index: int | None = Field(default=None, ge=0)


class SyncAnswersResponseModel(BaseModel):
    status: str = "ok"
    synced_count: int
    session_id: UUID
    current_index: int


def _parse_uuid(val: str | None) -> UUID | None:
    """Converte string para UUID com segurança, tratando valores vazios ou inválidos como None."""
    try:
        if val is not None and str(val).strip():
            return UUID(str(val).strip())
    except (ValueError, AttributeError, TypeError):
        return None
    return None


@api_router.get("/study/next", response_model=StudyCardDTO)
def get_next_study_card_api(
    subject_id: str | None = None,
    topic_id: str | None = None,
    current_index: int | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> StudyCardDTO:
    """Retorna o próximo card da pool e metadados de rodada em JSON."""
    sub_uuid = _parse_uuid(subject_id)
    top_uuid = _parse_uuid(topic_id)
    card_repo = SqlAlchemyFlashcardRepository(db)
    session_repo = SqlAlchemySessionRepository(db)
    subject_repo = SqlAlchemySubjectRepository(db)
    topic_repo = SqlAlchemyTopicRepository(db)

    try:
        use_case = GetNextFlashcardUseCase(
            card_repo,
            session_repo,
            default_rng,
            topic_repo=topic_repo,
            subject_repo=subject_repo,
        )
        return use_case.execute(
            GetNextCardDTO(subject_id=sub_uuid, topic_id=top_uuid, current_index=current_index),
            user_id=current_user.id,
        )
    except EmptyPoolError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except ResourceOwnershipError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc


@api_router.get("/study/batch", response_model=StudyBatchDTO)
def get_study_batch_api(
    subject_id: str | None = None,
    topic_id: str | None = None,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> StudyBatchDTO:
    """Retorna um lote paginado de flashcards (de 100 em 100) para estudo eficiente."""
    sub_uuid = _parse_uuid(subject_id)
    top_uuid = _parse_uuid(topic_id)
    card_repo = SqlAlchemyFlashcardRepository(db)
    session_repo = SqlAlchemySessionRepository(db)
    topic_repo = SqlAlchemyTopicRepository(db)
    subject_repo = SqlAlchemySubjectRepository(db)

    try:
        use_case = GetStudyBatchUseCase(
            card_repo,
            session_repo,
            topic_repo=topic_repo,
            subject_repo=subject_repo,
        )
        return use_case.execute(
            GetNextCardDTO(subject_id=sub_uuid, topic_id=top_uuid),
            limit=limit,
            user_id=current_user.id,
        )
    except EmptyPoolError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except ResourceOwnershipError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc


@api_router.post("/study/read/{card_id}")
def mark_card_read_api(
    card_id: UUID,
    subject_id: str | None = None,
    topic_id: str | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict[str, str]:
    """Registra leitura de um card na bateria de revisão atual e avança a posição da sessão."""
    sub_uuid = _parse_uuid(subject_id)
    top_uuid = _parse_uuid(topic_id)
    card_repo = SqlAlchemyFlashcardRepository(db)
    session_repo = SqlAlchemySessionRepository(db)

    card = card_repo.get_by_id(card_id)
    if not card:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Card não encontrado.")

    session = session_repo.get_active_session(sub_uuid, top_uuid, user_id=current_user.id)
    if session:
        session.advance_to(card.position)
        session_repo.save_session(session)

    return {"status": "ok"}


def get_study_event_repo(db: Session = Depends(get_db)) -> IStudyEventRepository:
    """Resolve o repositório de eventos de estudo (DynamoDB ou PostgreSQL)."""
    if settings.STUDY_EVENTS_BACKEND == "dynamodb":
        from src.adapters.persistence.dynamodb_study_event_repository import (
            DynamoDbStudyEventRepository,
        )

        return DynamoDbStudyEventRepository()
    return SqlAlchemyStudyEventRepository(db)


@api_router.post("/study/sync-answers", response_model=SyncAnswersResponseModel)
def sync_answers_api(
    request: Request,
    payload: SyncAnswersPayload,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    event_repo: IStudyEventRepository = Depends(get_study_event_repo),
) -> SyncAnswersResponseModel:
    """Ingestão em lote de respostas com blindagem anti-IDOR, rate limit e idempotência."""
    content_length = request.headers.get("content-length")
    if content_length and int(content_length) > 256 * 1024:
        raise HTTPException(
            status_code=status.HTTP_413_CONTENT_TOO_LARGE,
            detail="Payload Too Large: corpo da requisição excede 256 KB.",
        )

    rate_key = f"sync:{current_user.id}"
    if not study_sync_rate_limiter.is_allowed(rate_key):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Limite de taxa excedido (máximo de 20 requisições por minuto).",
            headers={"Retry-After": "60"},
        )

    if getattr(event_repo, "bulk_insert", None) is None:
        event_repo = get_study_event_repo(db)

    session_repo = SqlAlchemySessionRepository(db)
    use_case = SyncStudyAnswersUseCase(event_repo, session_repo)

    dto_events = [
        StudyEventDTO(
            id=ev.id,
            card_id=ev.card_id,
            reviewed_at=ev.reviewed_at,
            status=ev.status,
            device_id=ev.device_id,
        )
        for ev in payload.events
    ]
    input_dto = SyncStudyBatchDTO(
        session_id=payload.session_id,
        events=dto_events,
        batch_index=payload.batch_index,
    )

    try:
        result = use_case.execute(input_dto, user_id=current_user.id)
        return SyncAnswersResponseModel(
            status=result.status,
            synced_count=result.synced_count,
            session_id=result.session_id,
            current_index=result.current_index,
        )
    except EntityNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except ResourceOwnershipError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc
    except DomainValidationError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)
        ) from exc


@api_router.post("/flashcards", response_model=FlashcardDTO, status_code=status.HTTP_201_CREATED)
def create_flashcard_api(
    payload: CreateFlashcardRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> FlashcardDTO:
    """Criação de flashcard via JSON (ADR-004)."""
    card_repo = SqlAlchemyFlashcardRepository(db)
    topic_repo = SqlAlchemyTopicRepository(db)
    session_repo = SqlAlchemySessionRepository(db)
    subject_repo = SqlAlchemySubjectRepository(db)

    clean_front = sanitize_html_content(payload.front)
    clean_back = sanitize_html_content(payload.back)

    target_topic_ids = payload.topic_ids or (
        [payload.topic_id] if payload.topic_id is not None else []
    )

    try:
        use_case = CreateFlashcardUseCase(
            card_repo,
            topic_repo,
            session_repo,
            default_rng,
            subject_repo=subject_repo,
        )
        return use_case.execute(
            CreateFlashcardDTO(
                topic_ids=target_topic_ids,
                front=clean_front,
                back=clean_back,
            ),
            user_id=current_user.id,
        )
    except EntityNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except ResourceOwnershipError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc
    except DomainValidationError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)
        ) from exc


@api_router.get("/subjects", response_model=list[SubjectDTO])
def list_subjects_api(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[SubjectDTO]:
    """Lista matérias acessíveis pelo usuário autenticado (próprias + públicas)."""
    subject_repo = SqlAlchemySubjectRepository(db)
    return ListSubjectsUseCase(subject_repo).execute(user_id=current_user.id)


@api_router.post("/subjects", response_model=SubjectDTO, status_code=status.HTTP_201_CREATED)
def create_subject_api(
    payload: CreateSubjectRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> SubjectDTO:
    """Criação de matéria vinculada ao usuário autenticado."""
    subject_repo = SqlAlchemySubjectRepository(db)
    try:
        return CreateSubjectUseCase(subject_repo).execute(
            CreateSubjectDTO(name=payload.name, is_public=payload.is_public),
            owner_id=current_user.id,
        )
    except DuplicateEntityError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    except DomainValidationError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)
        ) from exc


@api_router.post("/subjects/{subject_id}/toggle-public", response_model=SubjectDTO)
def toggle_subject_public_api(
    subject_id: UUID,
    payload: TogglePublicRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> SubjectDTO:
    """Alterna visibilidade pública da matéria pelo proprietário."""
    subject_repo = SqlAlchemySubjectRepository(db)
    try:
        return ToggleSubjectPublicUseCase(subject_repo).execute(
            user_id=current_user.id,
            subject_id=subject_id,
            is_public=payload.is_public,
        )
    except EntityNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except ResourceOwnershipError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc


@api_router.get("/subjects/{subject_id}/topics", response_model=list[TopicDTO])
def list_topics_api(
    subject_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[TopicDTO]:
    """Lista temas de uma matéria acessível."""
    subject_repo = SqlAlchemySubjectRepository(db)
    subject = subject_repo.get_by_id(subject_id)
    if subject is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Matéria não encontrada.")
    if not subject.can_be_studied_by(current_user.id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Você não tem acesso a esta matéria privada.",
        )

    topic_repo = SqlAlchemyTopicRepository(db)
    return ListTopicsBySubjectUseCase(topic_repo).execute(subject_id)


@api_router.post("/topics", response_model=TopicDTO, status_code=status.HTTP_201_CREATED)
def create_topic_api(
    payload: CreateTopicRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> TopicDTO:
    """Criação de tema via JSON validando permissão de escrita na matéria."""
    subject_repo = SqlAlchemySubjectRepository(db)
    topic_repo = SqlAlchemyTopicRepository(db)
    try:
        return CreateTopicUseCase(subject_repo, topic_repo).execute(
            CreateTopicDTO(subject_id=payload.subject_id, name=payload.name),
            user_id=current_user.id,
        )
    except EntityNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except ResourceOwnershipError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc
    except DuplicateEntityError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    except DomainValidationError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)
        ) from exc
