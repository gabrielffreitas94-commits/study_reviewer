"""Controladores de API REST (JSON para mobile e clientes externos - Camada 3)."""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from src.adapters.persistence.repositories import (
    SqlAlchemyFlashcardRepository,
    SqlAlchemySessionRepository,
    SqlAlchemySubjectRepository,
    SqlAlchemyTopicRepository,
)
from src.application.dto.flashcard_dto import CreateFlashcardDTO, FlashcardDTO
from src.application.dto.study_dto import GetNextCardDTO, StudyCardDTO
from src.application.dto.subject_dto import CreateSubjectDTO, SubjectDTO
from src.application.dto.topic_dto import CreateTopicDTO, TopicDTO
from src.application.use_cases.flashcard_use_cases import CreateFlashcardUseCase
from src.application.use_cases.study_session_use_cases import GetNextFlashcardUseCase
from src.application.use_cases.subject_use_cases import (
    CreateSubjectUseCase,
    ListSubjectsUseCase,
)
from src.application.use_cases.topic_use_cases import (
    CreateTopicUseCase,
    ListTopicsBySubjectUseCase,
)
from src.domain.exceptions import (
    DomainValidationError,
    DuplicateEntityError,
    EmptyPoolError,
    EntityNotFoundError,
)
from src.infrastructure.database import get_db
from src.infrastructure.rng import default_rng
from src.infrastructure.security.sanitization import sanitize_html_content

api_router = APIRouter(prefix="/api/v1")


class CreateSubjectRequest(BaseModel):
    name: str = Field(..., min_length=2, max_length=100)


class CreateTopicRequest(BaseModel):
    subject_id: UUID
    name: str = Field(..., min_length=2, max_length=100)


class CreateFlashcardRequest(BaseModel):
    topic_id: UUID
    front: str = Field(..., min_length=1, max_length=5000)
    back: str = Field(..., min_length=1, max_length=10000)


@api_router.get("/study/next", response_model=StudyCardDTO)
def get_next_study_card_api(
    subject_id: UUID | None = None,
    topic_id: UUID | None = None,
    db: Session = Depends(get_db),
) -> StudyCardDTO:
    """Retorna o próximo card da pool e metadados de rodada em JSON."""
    card_repo = SqlAlchemyFlashcardRepository(db)
    session_repo = SqlAlchemySessionRepository(db)

    try:
        use_case = GetNextFlashcardUseCase(card_repo, session_repo, default_rng)
        return use_case.execute(GetNextCardDTO(subject_id=subject_id, topic_id=topic_id))
    except EmptyPoolError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc


@api_router.post("/flashcards", response_model=FlashcardDTO, status_code=status.HTTP_201_CREATED)
def create_flashcard_api(
    payload: CreateFlashcardRequest, db: Session = Depends(get_db)
) -> FlashcardDTO:
    """Criação de flashcard via JSON."""
    card_repo = SqlAlchemyFlashcardRepository(db)
    topic_repo = SqlAlchemyTopicRepository(db)
    session_repo = SqlAlchemySessionRepository(db)

    clean_front = sanitize_html_content(payload.front)
    clean_back = sanitize_html_content(payload.back)

    try:
        use_case = CreateFlashcardUseCase(card_repo, topic_repo, session_repo, default_rng)
        return use_case.execute(
            CreateFlashcardDTO(
                topic_id=payload.topic_id,
                front=clean_front,
                back=clean_back,
            )
        )
    except EntityNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except DomainValidationError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)
        ) from exc


@api_router.get("/subjects", response_model=list[SubjectDTO])
def list_subjects_api(db: Session = Depends(get_db)) -> list[SubjectDTO]:
    """Lista todas as matérias cadastradas."""
    subject_repo = SqlAlchemySubjectRepository(db)
    return ListSubjectsUseCase(subject_repo).execute()


@api_router.post("/subjects", response_model=SubjectDTO, status_code=status.HTTP_201_CREATED)
def create_subject_api(payload: CreateSubjectRequest, db: Session = Depends(get_db)) -> SubjectDTO:
    """Criação de matéria via JSON."""
    subject_repo = SqlAlchemySubjectRepository(db)
    try:
        return CreateSubjectUseCase(subject_repo).execute(CreateSubjectDTO(name=payload.name))
    except DuplicateEntityError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    except DomainValidationError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)
        ) from exc


@api_router.get("/subjects/{subject_id}/topics", response_model=list[TopicDTO])
def list_topics_api(subject_id: UUID, db: Session = Depends(get_db)) -> list[TopicDTO]:
    """Lista temas de uma matéria."""
    topic_repo = SqlAlchemyTopicRepository(db)
    return ListTopicsBySubjectUseCase(topic_repo).execute(subject_id)


@api_router.post("/topics", response_model=TopicDTO, status_code=status.HTTP_201_CREATED)
def create_topic_api(payload: CreateTopicRequest, db: Session = Depends(get_db)) -> TopicDTO:
    """Criação de tema via JSON."""
    subject_repo = SqlAlchemySubjectRepository(db)
    topic_repo = SqlAlchemyTopicRepository(db)
    try:
        return CreateTopicUseCase(subject_repo, topic_repo).execute(
            CreateTopicDTO(subject_id=payload.subject_id, name=payload.name)
        )
    except EntityNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except DuplicateEntityError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    except DomainValidationError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)
        ) from exc
