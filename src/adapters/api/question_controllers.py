"""Controladores de API REST para Perguntas Abertas e SRS Estrito (Camada 3 - Adaptadores)."""

from datetime import date
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from src.adapters.persistence.repositories import (
    SqlAlchemyQuestionProgressRepository,
    SqlAlchemyQuestionRepository,
    SqlAlchemyReviewAuditRepository,
    SqlAlchemySubjectRepository,
    SqlAlchemyTopicRepository,
    SqlAlchemyUnitOfWork,
)
from src.application.dto.question_dto import (
    CreateQuestionDTO,
    DueQuestionItemDTO,
    QuestionDTO,
    ReviewQuestionInputDTO,
    ReviewQuestionResultDTO,
    UpdateQuestionDTO,
)
from src.application.use_cases.question_use_cases import (
    CreateQuestionUseCase,
    DeleteQuestionUseCase,
    GetDueQuestionsUseCase,
    GetQuestionByIdUseCase,
    ListQuestionsByTopicUseCase,
    ReviewQuestionUseCase,
    UpdateQuestionUseCase,
)
from src.domain.entities import User
from src.domain.exceptions import (
    DomainValidationError,
    EntityNotFoundError,
    InvalidExpectedAnswerError,
    InvalidPromptError,
    InvalidScoreError,
    QuestionNotDueError,
    QuestionNotFoundError,
    ResourceOwnershipError,
)
from src.infrastructure.clock import system_clock
from src.infrastructure.database import get_db
from src.infrastructure.security.dependencies import get_current_user
from src.infrastructure.security.rate_limiter import question_review_rate_limiter
from src.infrastructure.security.sanitization import MarkdownSanitizerService

api_question_router = APIRouter(prefix="/api/v1", tags=["Questions SRS"])


class CreateQuestionRequest(BaseModel):
    """Payload de entrada para criação de pergunta aberta."""

    prompt: str = Field(..., min_length=3, max_length=5000)
    expected_answer: str = Field(..., min_length=1, max_length=10000)


class UpdateQuestionRequest(BaseModel):
    """Payload de entrada para atualização de pergunta aberta."""

    prompt: str = Field(..., min_length=3, max_length=5000)
    expected_answer: str = Field(..., min_length=1, max_length=10000)


class ReviewQuestionRequest(BaseModel):
    """Payload de entrada para submissão de nota de revisão."""

    score: int = Field(...)


class DueQuestionsResponse(BaseModel):
    """Resposta com lista de perguntas vencidas e metadados de agendamento."""

    items: list[DueQuestionItemDTO]
    total_due: int
    next_review_date: date | None


def _parse_uuid(val: str | None) -> UUID | None:
    try:
        if val is not None and str(val).strip():
            return UUID(str(val).strip())
    except (ValueError, AttributeError, TypeError):
        return None
    return None


@api_question_router.get("/questions/due", response_model=DueQuestionsResponse)
def get_due_questions_api(
    subject_id: str | None = None,
    topic_id: str | None = None,
    limit: int = Query(50, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> DueQuestionsResponse:
    """Retorna as perguntas abertas vencidas para revisão no dia corrente."""
    sub_uuid = _parse_uuid(subject_id)
    top_uuid = _parse_uuid(topic_id)

    q_repo = SqlAlchemyQuestionRepository(db)
    prog_repo = SqlAlchemyQuestionProgressRepository(db)
    top_repo = SqlAlchemyTopicRepository(db)
    subj_repo = SqlAlchemySubjectRepository(db)

    use_case = GetDueQuestionsUseCase(
        progress_repo=prog_repo,
        question_repo=q_repo,
        topic_repo=top_repo,
        subject_repo=subj_repo,
        clock=system_clock,
    )

    try:
        items = use_case.execute(
            user_id=current_user.id,
            subject_id=sub_uuid,
            topic_id=top_uuid,
            limit=limit,
        )
        total_due = prog_repo.count_due_questions(current_user.id, system_clock.today())
        next_review_date = prog_repo.get_next_review_date(current_user.id, system_clock.today())

        return DueQuestionsResponse(
            items=items,
            total_due=total_due,
            next_review_date=next_review_date,
        )
    except EntityNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except ResourceOwnershipError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc


@api_question_router.post("/questions/{question_id}/review", response_model=ReviewQuestionResultDTO)
def review_question_api(
    question_id: UUID,
    payload: ReviewQuestionRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ReviewQuestionResultDTO:
    """Submete nota de autoavaliação para recalcular intervalo SRS e próxima revisão."""
    if not question_review_rate_limiter.is_allowed(str(current_user.id)):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Limite de taxa excedido. Tente novamente mais tarde.",
        )

    q_repo = SqlAlchemyQuestionRepository(db)
    prog_repo = SqlAlchemyQuestionProgressRepository(db)
    top_repo = SqlAlchemyTopicRepository(db)
    subj_repo = SqlAlchemySubjectRepository(db)
    audit_repo = SqlAlchemyReviewAuditRepository(db)
    uow = SqlAlchemyUnitOfWork(db)

    use_case = ReviewQuestionUseCase(
        progress_repo=prog_repo,
        question_repo=q_repo,
        topic_repo=top_repo,
        subject_repo=subj_repo,
        clock=system_clock,
        audit_repo=audit_repo,
        uow=uow,
    )

    try:
        return use_case.execute(
            ReviewQuestionInputDTO(question_id=question_id, score=payload.score),
            user_id=current_user.id,
        )
    except QuestionNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except QuestionNotDueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    except (InvalidScoreError, DomainValidationError) as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    except ResourceOwnershipError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc


@api_question_router.post(
    "/topics/{topic_id}/questions",
    response_model=QuestionDTO,
    status_code=status.HTTP_201_CREATED,
)
def create_question_api(
    topic_id: UUID,
    payload: CreateQuestionRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> QuestionDTO:
    """Cria uma nova pergunta aberta no catálogo vinculada ao tema."""
    clean_prompt = MarkdownSanitizerService.sanitize(payload.prompt)
    clean_answer = MarkdownSanitizerService.sanitize(payload.expected_answer)

    q_repo = SqlAlchemyQuestionRepository(db)
    prog_repo = SqlAlchemyQuestionProgressRepository(db)
    top_repo = SqlAlchemyTopicRepository(db)
    subj_repo = SqlAlchemySubjectRepository(db)

    use_case = CreateQuestionUseCase(
        question_repo=q_repo,
        progress_repo=prog_repo,
        topic_repo=top_repo,
        subject_repo=subj_repo,
        clock=system_clock,
    )

    try:
        return use_case.execute(
            CreateQuestionDTO(
                topic_id=topic_id,
                prompt=clean_prompt,
                expected_answer=clean_answer,
            ),
            user_id=current_user.id,
        )
    except EntityNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except ResourceOwnershipError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc
    except (InvalidPromptError, InvalidExpectedAnswerError, DomainValidationError) as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


@api_question_router.get("/topics/{topic_id}/questions", response_model=list[QuestionDTO])
def list_questions_by_topic_api(
    topic_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[QuestionDTO]:
    """Lista todas as perguntas pertencentes a um determinado tema."""
    q_repo = SqlAlchemyQuestionRepository(db)
    top_repo = SqlAlchemyTopicRepository(db)
    subj_repo = SqlAlchemySubjectRepository(db)

    use_case = ListQuestionsByTopicUseCase(
        question_repo=q_repo,
        topic_repo=top_repo,
        subject_repo=subj_repo,
    )

    try:
        return use_case.execute(topic_id=topic_id, user_id=current_user.id)
    except EntityNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except ResourceOwnershipError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc


@api_question_router.get("/questions/{question_id}", response_model=QuestionDTO)
def get_question_by_id_api(
    question_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> QuestionDTO:
    """Busca os detalhes de uma pergunta aberta."""
    q_repo = SqlAlchemyQuestionRepository(db)
    top_repo = SqlAlchemyTopicRepository(db)
    subj_repo = SqlAlchemySubjectRepository(db)

    use_case = GetQuestionByIdUseCase(
        question_repo=q_repo,
        topic_repo=top_repo,
        subject_repo=subj_repo,
    )

    try:
        return use_case.execute(question_id=question_id, user_id=current_user.id)
    except QuestionNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except ResourceOwnershipError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc


@api_question_router.put("/questions/{question_id}", response_model=QuestionDTO)
def update_question_api(
    question_id: UUID,
    payload: UpdateQuestionRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> QuestionDTO:
    """Atualiza o enunciado ou gabarito de uma pergunta aberta."""
    clean_prompt = MarkdownSanitizerService.sanitize(payload.prompt)
    clean_answer = MarkdownSanitizerService.sanitize(payload.expected_answer)

    q_repo = SqlAlchemyQuestionRepository(db)
    top_repo = SqlAlchemyTopicRepository(db)
    subj_repo = SqlAlchemySubjectRepository(db)

    use_case = UpdateQuestionUseCase(
        question_repo=q_repo,
        topic_repo=top_repo,
        subject_repo=subj_repo,
    )

    try:
        return use_case.execute(
            UpdateQuestionDTO(
                question_id=question_id,
                prompt=clean_prompt,
                expected_answer=clean_answer,
            ),
            user_id=current_user.id,
        )
    except QuestionNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except ResourceOwnershipError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc
    except (InvalidPromptError, InvalidExpectedAnswerError, DomainValidationError) as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


@api_question_router.delete("/questions/{question_id}")
def delete_question_api(
    question_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict[str, str]:
    """Exclui permanentemente uma pergunta aberta."""
    q_repo = SqlAlchemyQuestionRepository(db)
    top_repo = SqlAlchemyTopicRepository(db)
    subj_repo = SqlAlchemySubjectRepository(db)

    use_case = DeleteQuestionUseCase(
        question_repo=q_repo,
        topic_repo=top_repo,
        subject_repo=subj_repo,
    )

    try:
        use_case.execute(question_id=question_id, user_id=current_user.id)
        return {"message": "Pergunta excluída com sucesso."}
    except QuestionNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except ResourceOwnershipError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc
