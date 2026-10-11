"""Controladores Web para Perguntas Abertas e SRS Estrito com Jinja2 e HTMX.
Camada 3 - Adaptadores.
"""

from pathlib import Path
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Form, HTTPException, Query, Request, Response, status
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
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
    ReviewQuestionInputDTO,
)
from src.application.use_cases.question_use_cases import (
    CreateQuestionUseCase,
    DeleteQuestionUseCase,
    GetDueQuestionsUseCase,
    ListQuestionsByTopicUseCase,
    ReviewQuestionUseCase,
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

templates_dir = Path(__file__).resolve().parent / "templates"
templates = Jinja2Templates(directory=str(templates_dir))

web_question_router = APIRouter()


def _parse_uuid(val: str | None) -> UUID | None:
    try:
        if val is not None and str(val).strip():
            return UUID(str(val).strip())
    except (ValueError, AttributeError, TypeError):
        return None
    return None


@web_question_router.get("/questions/study", response_model=None)
def study_questions_page(
    request: Request,
    subject_id: str | None = None,
    topic_id: str | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Response:
    """Renderiza a tela de estudo de perguntas abertas com repetição espaçada."""
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
        due_cards = use_case.execute(
            user_id=current_user.id,
            subject_id=sub_uuid,
            topic_id=top_uuid,
            limit=50,
        )
    except (EntityNotFoundError, ResourceOwnershipError) as exc:
        return HTMLResponse(
            status_code=400,
            content=f"<div class='p-4 bg-rose-50 text-rose-800 rounded-xl'>{exc}</div>",
        )

    total_due = prog_repo.count_due_questions(current_user.id, system_clock.today())
    next_review_date = prog_repo.get_next_review_date(current_user.id, system_clock.today())

    if due_cards:
        card = due_cards[0]
        state = "studying"
    else:
        card = None
        # Verifica se o catálogo do usuário está completamente vazio ou se é Inbox Zero
        user_subjects = subj_repo.list_accessible(current_user.id)
        has_any_question = False
        for s in user_subjects:
            topics = top_repo.list_by_subject(s.id)
            for t in topics:
                if q_repo.list_by_topic(t.id):
                    has_any_question = True
                    break
            if has_any_question:
                break

        state = "inbox_zero" if has_any_question else "onboarding"

    return templates.TemplateResponse(
        request=request,
        name="questions/study.html",
        context={
            "current_user": current_user,
            "card": card,
            "state": state,
            "total_due": len(due_cards),
            "current_num": 1 if card else 0,
            "next_review_date": next_review_date,
            "pending_questions_count": total_due,
        },
    )


@web_question_router.post("/questions/{question_id}/review", response_model=None)
def review_question_submission(
    request: Request,
    question_id: UUID,
    score: int = Form(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Response:
    """Processa a nota do estudante via HTMX e retorna o próximo card ou Inbox Zero."""
    if not question_review_rate_limiter.is_allowed(str(current_user.id)):
        return HTMLResponse(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            content=(
                "<div class='p-4 bg-rose-50 text-rose-800 rounded-xl'>"
                "Limite de taxa excedido. Aguarde alguns segundos.</div>"
            ),
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
        use_case.execute(
            ReviewQuestionInputDTO(question_id=question_id, score=score),
            user_id=current_user.id,
        )
    except (
        QuestionNotFoundError,
        QuestionNotDueError,
        InvalidScoreError,
        ResourceOwnershipError,
        DomainValidationError,
    ) as exc:
        return HTMLResponse(
            status_code=400,
            content=f"<div class='p-4 bg-rose-50 text-rose-800 rounded-xl'>{exc}</div>",
        )

    # Busca próximo card da fila
    get_due_use_case = GetDueQuestionsUseCase(
        progress_repo=prog_repo,
        question_repo=q_repo,
        topic_repo=top_repo,
        subject_repo=subj_repo,
        clock=system_clock,
    )
    remaining_due = get_due_use_case.execute(user_id=current_user.id, limit=50)
    total_due = prog_repo.count_due_questions(current_user.id, system_clock.today())

    if remaining_due:
        next_card = remaining_due[0]
        return templates.TemplateResponse(
            request=request,
            name="questions/partials/question_card.html",
            context={
                "current_user": current_user,
                "card": next_card,
                "total_due": len(remaining_due),
                "current_num": 1,
                "pending_questions_count": total_due,
            },
        )

    # Fila esgotada -> Inbox Zero
    next_review_date = prog_repo.get_next_review_date(current_user.id, system_clock.today())
    return templates.TemplateResponse(
        request=request,
        name="questions/partials/inbox_zero.html",
        context={
            "current_user": current_user,
            "next_review_date": next_review_date,
            "pending_questions_count": 0,
        },
    )


@web_question_router.get("/questions/manage", response_model=None)
def manage_all_questions_view(
    request: Request,
    subject_id: str | None = Query(None),
    topic_id: str | None = Query(None),
    error: str | None = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Response:
    """Visão centralizada para cadastro e gerenciamento de perguntas abertas."""
    subj_repo = SqlAlchemySubjectRepository(db)
    top_repo = SqlAlchemyTopicRepository(db)
    q_repo = SqlAlchemyQuestionRepository(db)
    prog_repo = SqlAlchemyQuestionProgressRepository(db)

    subjects = subj_repo.list_by_owner(current_user.id)
    total_due = prog_repo.count_due_questions(current_user.id, system_clock.today())

    if not subjects:
        return templates.TemplateResponse(
            request=request,
            name="questions/manage_all.html",
            context={
                "current_user": current_user,
                "subjects": [],
                "topics_by_subject": {},
                "selected_subject": None,
                "selected_topic": None,
                "questions": [],
                "pending_questions_count": total_due,
                "error": error,
            },
        )

    sub_uuid = _parse_uuid(subject_id)
    selected_subject = None
    if sub_uuid:
        for s in subjects:
            if s.id == sub_uuid:
                selected_subject = s
                break
    if not selected_subject:
        selected_subject = subjects[0]

    topics_by_subject = {}
    for s in subjects:
        topics_by_subject[str(s.id)] = top_repo.list_by_subject(s.id)

    current_topics = topics_by_subject.get(str(selected_subject.id), [])

    top_uuid = _parse_uuid(topic_id)
    selected_topic = None
    if top_uuid:
        for t in current_topics:
            if t.id == top_uuid:
                selected_topic = t
                break
    if not selected_topic and current_topics:
        selected_topic = current_topics[0]

    questions = []
    if selected_topic:
        use_case = ListQuestionsByTopicUseCase(q_repo, top_repo, subj_repo)
        questions = use_case.execute(selected_topic.id, current_user.id)

    return templates.TemplateResponse(
        request=request,
        name="questions/manage_all.html",
        context={
            "current_user": current_user,
            "subjects": subjects,
            "topics_by_subject": topics_by_subject,
            "selected_subject": selected_subject,
            "selected_topic": selected_topic,
            "questions": questions,
            "pending_questions_count": total_due,
            "error": error,
        },
    )


@web_question_router.post("/questions/manage", response_model=None)
def create_question_from_manage_view(
    request: Request,
    topic_id: Annotated[UUID, Form()],
    prompt: Annotated[str, Form()],
    expected_answer: Annotated[str, Form()],
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Response:
    """Cadastra nova pergunta aberta a partir da visão centralizada."""
    clean_prompt = MarkdownSanitizerService.sanitize(prompt)
    clean_answer = MarkdownSanitizerService.sanitize(expected_answer)

    q_repo = SqlAlchemyQuestionRepository(db)
    prog_repo = SqlAlchemyQuestionProgressRepository(db)
    top_repo = SqlAlchemyTopicRepository(db)
    subj_repo = SqlAlchemySubjectRepository(db)
    uow = SqlAlchemyUnitOfWork(db)

    topic = top_repo.get_by_id(topic_id)
    if not topic:
        return RedirectResponse(
            url="/questions/manage?error=Tema+n%C3%A3o+encontrado.",
            status_code=status.HTTP_303_SEE_OTHER,
        )

    use_case = CreateQuestionUseCase(
        question_repo=q_repo,
        progress_repo=prog_repo,
        topic_repo=top_repo,
        subject_repo=subj_repo,
        clock=system_clock,
        uow=uow,
    )

    try:
        use_case.execute(
            CreateQuestionDTO(topic_id=topic_id, prompt=clean_prompt, expected_answer=clean_answer),
            user_id=current_user.id,
        )
        return RedirectResponse(
            url=f"/questions/manage?subject_id={topic.subject_id}&topic_id={topic_id}",
            status_code=status.HTTP_303_SEE_OTHER,
        )
    except (
        InvalidPromptError,
        InvalidExpectedAnswerError,
        DomainValidationError,
        EntityNotFoundError,
        ResourceOwnershipError,
    ) as exc:
        return RedirectResponse(
            url=f"/questions/manage?subject_id={topic.subject_id}&topic_id={topic_id}&error={exc}",
            status_code=status.HTTP_303_SEE_OTHER,
        )


@web_question_router.get("/topics/{topic_id}/questions", response_model=None)
def manage_topic_questions(
    request: Request,
    topic_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Response:
    """Gerencia as perguntas abertas cadastradas no tema (apenas proprietário)."""
    top_repo = SqlAlchemyTopicRepository(db)
    subj_repo = SqlAlchemySubjectRepository(db)
    q_repo = SqlAlchemyQuestionRepository(db)
    prog_repo = SqlAlchemyQuestionProgressRepository(db)

    topic = top_repo.get_by_id(topic_id)
    if not topic:
        raise HTTPException(status_code=404, detail="Tema não encontrado.")

    subject = subj_repo.get_by_id(topic.subject_id)
    if not subject or not subject.can_be_edited_by(current_user.id):
        raise HTTPException(status_code=403, detail="Acesso negado a este tema.")

    use_case = ListQuestionsByTopicUseCase(q_repo, top_repo, subj_repo)
    questions = use_case.execute(topic_id, current_user.id)
    total_due = prog_repo.count_due_questions(current_user.id, system_clock.today())

    return templates.TemplateResponse(
        request=request,
        name="questions/manage.html",
        context={
            "current_user": current_user,
            "topic": topic,
            "subject": subject,
            "questions": questions,
            "pending_questions_count": total_due,
        },
    )


@web_question_router.post("/topics/{topic_id}/questions", response_model=None)
def create_topic_question(
    request: Request,
    topic_id: UUID,
    prompt: str = Form(...),
    expected_answer: str = Form(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Response:
    """Cadastra nova pergunta aberta vinculada a um tema."""
    clean_prompt = MarkdownSanitizerService.sanitize(prompt)
    clean_answer = MarkdownSanitizerService.sanitize(expected_answer)

    q_repo = SqlAlchemyQuestionRepository(db)
    prog_repo = SqlAlchemyQuestionProgressRepository(db)
    top_repo = SqlAlchemyTopicRepository(db)
    subj_repo = SqlAlchemySubjectRepository(db)
    uow = SqlAlchemyUnitOfWork(db)

    use_case = CreateQuestionUseCase(
        question_repo=q_repo,
        progress_repo=prog_repo,
        topic_repo=top_repo,
        subject_repo=subj_repo,
        clock=system_clock,
        uow=uow,
    )

    try:
        use_case.execute(
            CreateQuestionDTO(topic_id=topic_id, prompt=clean_prompt, expected_answer=clean_answer),
            user_id=current_user.id,
        )
        return RedirectResponse(
            url=f"/topics/{topic_id}/questions", status_code=status.HTTP_303_SEE_OTHER
        )
    except (
        InvalidPromptError,
        InvalidExpectedAnswerError,
        DomainValidationError,
        EntityNotFoundError,
        ResourceOwnershipError,
    ) as exc:
        topic = top_repo.get_by_id(topic_id)
        subject = subj_repo.get_by_id(topic.subject_id) if topic else None
        questions = q_repo.list_by_topic(topic_id) if topic else []
        return templates.TemplateResponse(
            request=request,
            name="questions/manage.html",
            context={
                "current_user": current_user,
                "topic": topic,
                "subject": subject,
                "questions": questions,
                "error": str(exc),
                "pending_questions_count": prog_repo.count_due_questions(
                    current_user.id, system_clock.today()
                ),
            },
            status_code=400,
        )


@web_question_router.delete("/questions/{question_id}", response_model=None)
def delete_question_web(
    question_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Response:
    """Exclui permanentemente uma pergunta e retorna 200 para swap vazio do HTMX."""
    q_repo = SqlAlchemyQuestionRepository(db)
    top_repo = SqlAlchemyTopicRepository(db)
    subj_repo = SqlAlchemySubjectRepository(db)

    use_case = DeleteQuestionUseCase(q_repo, top_repo, subj_repo)
    try:
        use_case.execute(question_id, current_user.id)
        return Response(status_code=status.HTTP_200_OK)
    except (QuestionNotFoundError, ResourceOwnershipError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
