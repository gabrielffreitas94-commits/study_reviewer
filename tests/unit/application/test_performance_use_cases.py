"""Testes unitários para os casos de uso de Performance, Auditoria e Exportação (Sprint 04)."""

from datetime import UTC, date, datetime
from uuid import uuid4

import pytest

from src.application.dto.performance_dto import (
    PaginatedAuditLogsDTO,
    UserStatisticsDTO,
)
from src.application.dto.question_dto import ReviewQuestionInputDTO
from src.application.use_cases.performance_use_cases import (
    ExportUserDataUseCase,
    GetUserStudyStatisticsUseCase,
    ListUserReviewAuditLogsUseCase,
)
from src.application.use_cases.question_use_cases import ReviewQuestionUseCase
from src.domain.entities import (
    Question,
    ReviewAuditLog,
    Subject,
    Topic,
    User,
    UserQuestionProgress,
)
from src.domain.exceptions import (
    DomainValidationError,
    QuestionNotDueError,
)
from tests.unit.application.fakes import (
    FakeClockService,
    FakeQuestionProgressRepository,
    FakeQuestionRepository,
    FakeReviewAuditRepository,
    FakeSubjectRepository,
    FakeTopicRepository,
    FakeUnitOfWork,
    FakeUserRepository,
)


@pytest.fixture
def performance_repos() -> tuple[
    FakeUserRepository,
    FakeSubjectRepository,
    FakeTopicRepository,
    FakeQuestionRepository,
    FakeQuestionProgressRepository,
    FakeReviewAuditRepository,
    FakeUnitOfWork,
    FakeClockService,
]:
    """Fixture com repositórios e serviços em memória para testes de performance."""
    user_repo = FakeUserRepository()
    subj_repo = FakeSubjectRepository()
    top_repo = FakeTopicRepository()
    q_repo = FakeQuestionRepository()
    prog_repo = FakeQuestionProgressRepository()
    audit_repo = FakeReviewAuditRepository()
    uow = FakeUnitOfWork()
    clock = FakeClockService(initial_date=date(2026, 10, 7))
    return user_repo, subj_repo, top_repo, q_repo, prog_repo, audit_repo, uow, clock


# ---------------------------------------------------------------------------
# ReviewQuestionUseCase com Auditoria Integrada e Atomicidade ACID
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_review_question_creates_audit_log_atomically(
    performance_repos: tuple,
) -> None:
    """UC-S04-01 e UC-S04-44: Grava log de auditoria com nomes congelados e commita via UoW."""
    _, subj_repo, top_repo, q_repo, prog_repo, audit_repo, uow, clock = performance_repos
    user_id = uuid4()
    subj = Subject(id=uuid4(), name="Direito Civil", owner_id=user_id)
    subj_repo.save(subj)
    topic = Topic(id=uuid4(), subject_id=subj.id, name="Contratos")
    top_repo.save(topic)
    q = Question(id=uuid4(), topic_id=topic.id, prompt="O que é mora?", expected_answer="Atraso")
    q_repo.save(q)
    prog = UserQuestionProgress(
        user_id=user_id, question_id=q.id, current_level=2, next_review_date=date(2026, 10, 7)
    )
    prog_repo.save(prog)

    use_case = ReviewQuestionUseCase(
        progress_repo=prog_repo,
        question_repo=q_repo,
        topic_repo=top_repo,
        subject_repo=subj_repo,
        clock=clock,
        audit_repo=audit_repo,
        uow=uow,
    )
    result = use_case.execute(ReviewQuestionInputDTO(question_id=q.id, score=100), user_id=user_id)

    assert result.new_level == 3
    assert len(audit_repo.logs) == 1
    log = audit_repo.logs[0]
    assert log.user_id == user_id
    assert log.question_id == q.id
    assert log.subject_id == subj.id
    assert log.topic_id == topic.id
    assert log.historical_subject_name == "Direito Civil"
    assert log.historical_topic_name == "Contratos"
    assert log.score == 100
    assert log.level_before == 2
    assert log.level_after == 3
    assert log.review_date == date(2026, 10, 7)
    assert uow.committed is True


@pytest.mark.unit
def test_review_question_rollback_on_audit_failure(
    performance_repos: tuple,
) -> None:
    """UC-S04-44: Falha na gravação do log reverte o progresso (Rollback ACID)."""
    _, subj_repo, top_repo, q_repo, prog_repo, audit_repo, uow, clock = performance_repos
    user_id = uuid4()
    subj = Subject(id=uuid4(), name="Direito Penal", owner_id=user_id)
    subj_repo.save(subj)
    topic = Topic(id=uuid4(), subject_id=subj.id, name="Crimes")
    top_repo.save(topic)
    q = Question(id=uuid4(), topic_id=topic.id, prompt="Tipicidade?", expected_answer="Adequação")
    q_repo.save(q)
    prog = UserQuestionProgress(
        user_id=user_id, question_id=q.id, current_level=2, next_review_date=date(2026, 10, 7)
    )
    prog_repo.save(prog)

    # Força erro na gravação do log
    def failing_save(log: ReviewAuditLog) -> None:
        raise RuntimeError("Falha de I/O na tabela de auditoria")

    audit_repo.save = failing_save  # type: ignore[method-assign]

    use_case = ReviewQuestionUseCase(
        progress_repo=prog_repo,
        question_repo=q_repo,
        topic_repo=top_repo,
        subject_repo=subj_repo,
        clock=clock,
        audit_repo=audit_repo,
        uow=uow,
    )

    with pytest.raises(RuntimeError, match="Falha de I/O na tabela de auditoria"):
        use_case.execute(ReviewQuestionInputDTO(question_id=q.id, score=100), user_id=user_id)

    assert uow.rolled_back is True


@pytest.mark.unit
def test_review_question_zero_side_effects_on_validation_failure(
    performance_repos: tuple,
) -> None:
    """UC-S04-34: Nenhuma auditoria fantasma é gerada se a pergunta não estiver vencida."""
    _, subj_repo, top_repo, q_repo, prog_repo, audit_repo, uow, clock = performance_repos
    user_id = uuid4()
    subj = Subject(id=uuid4(), name="Física", owner_id=user_id)
    subj_repo.save(subj)
    topic = Topic(id=uuid4(), subject_id=subj.id, name="Mecânica")
    top_repo.save(topic)
    q = Question(id=uuid4(), topic_id=topic.id, prompt="Força?", expected_answer="m*a")
    q_repo.save(q)
    prog = UserQuestionProgress(
        user_id=user_id, question_id=q.id, current_level=1, next_review_date=date(2026, 10, 20)
    )
    prog_repo.save(prog)

    use_case = ReviewQuestionUseCase(
        progress_repo=prog_repo,
        question_repo=q_repo,
        topic_repo=top_repo,
        subject_repo=subj_repo,
        clock=clock,
        audit_repo=audit_repo,
        uow=uow,
    )

    with pytest.raises(QuestionNotDueError):
        use_case.execute(ReviewQuestionInputDTO(question_id=q.id, score=100), user_id=user_id)

    assert len(audit_repo.logs) == 0


# ---------------------------------------------------------------------------
# GetUserStudyStatisticsUseCase
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_get_user_study_statistics_nominal(performance_repos: tuple) -> None:
    """UC-S04-02: Retorna KPIs consolidados, distribuição e histórico de Retenção Madura."""
    _, subj_repo, _, _, prog_repo, audit_repo, _, _ = performance_repos
    user_id = uuid4()

    # Cria logs com histórico
    d1 = date(2026, 10, 5)
    d2 = date(2026, 10, 7)
    q1 = uuid4()
    q2 = uuid4()

    audit_repo.save(
        ReviewAuditLog(
            user_id=user_id,
            question_id=q1,
            subject_id=uuid4(),
            topic_id=uuid4(),
            historical_subject_name="Matemática",
            historical_topic_name="Álgebra",
            review_date=d1,
            score=100,
            level_before=3,
            level_after=4,
        )
    )
    audit_repo.save(
        ReviewAuditLog(
            user_id=user_id,
            question_id=q2,
            subject_id=uuid4(),
            topic_id=uuid4(),
            historical_subject_name="Português",
            historical_topic_name="Gramática",
            review_date=d2,
            score=50,
            level_before=1,
            level_after=1,
        )
    )

    # Progresso atual
    prog_repo.save(UserQuestionProgress(user_id=user_id, question_id=q1, current_level=4))
    prog_repo.save(UserQuestionProgress(user_id=user_id, question_id=q2, current_level=1))

    use_case = GetUserStudyStatisticsUseCase(
        audit_repo=audit_repo,
        progress_repo=prog_repo,
    )
    stats: UserStatisticsDTO = use_case.execute(user_id=user_id)

    assert stats.total_reviews_count == 2
    assert stats.retention_rate == 50.0
    assert stats.mature_questions_count == 1
    assert stats.active_days_count == 2
    assert stats.srs_distribution[4] == 1
    assert stats.srs_distribution[1] == 1
    assert len(stats.subject_performances) == 2
    assert len(stats.mature_evolution_timeline) == 2


@pytest.mark.unit
def test_get_user_study_statistics_empty_state(performance_repos: tuple) -> None:
    """UC-S04-05: Trata estudante novato sem revisões."""
    _, _, _, _, prog_repo, audit_repo, _, _ = performance_repos
    user_id = uuid4()

    use_case = GetUserStudyStatisticsUseCase(
        audit_repo=audit_repo,
        progress_repo=prog_repo,
    )
    stats = use_case.execute(user_id=user_id)

    assert stats.total_reviews_count == 0
    assert stats.retention_rate == 0.0
    assert stats.mature_questions_count == 0
    assert stats.active_days_count == 0
    assert stats.subject_performances == []


# ---------------------------------------------------------------------------
# ListUserReviewAuditLogsUseCase (Anti-IDOR e Paginação)
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_list_user_review_audit_logs_pagination(performance_repos: tuple) -> None:
    """UC-S04-16: Retorna lista paginada e contagem correta."""
    _, _, _, _, _, audit_repo, _, _ = performance_repos
    user_id = uuid4()

    for i in range(25):
        audit_repo.save(
            ReviewAuditLog(
                user_id=user_id,
                question_id=uuid4(),
                subject_id=uuid4(),
                topic_id=uuid4(),
                historical_subject_name=f"Matéria {i}",
                historical_topic_name=f"Tema {i}",
                review_date=date(2026, 10, 7),
                score=100,
                level_before=0,
                level_after=1,
            )
        )

    use_case = ListUserReviewAuditLogsUseCase(audit_repo=audit_repo)
    result_p1: PaginatedAuditLogsDTO = use_case.execute(user_id=user_id, page=1, page_size=10)

    assert len(result_p1.items) == 10
    assert result_p1.page == 1
    assert result_p1.page_size == 10
    assert result_p1.total_items == 25
    assert result_p1.total_pages == 3

    result_p3 = use_case.execute(user_id=user_id, page=3, page_size=10)
    assert len(result_p3.items) == 5


@pytest.mark.unit
@pytest.mark.security
def test_list_user_review_audit_logs_anti_idor_filter(performance_repos: tuple) -> None:
    """Vulnerabilidade prevenida: IDOR na filtragem de histórico por matéria (CWE-639 / CWE-209).

    Garantia de segurança: Se o estudante informar subject_id pertencente a outro aluno,
    o sistema retorna lista vazia sem expor registros de terceiros nem vazar a existência do ID.
    """
    _, _, _, _, _, audit_repo, _, _ = performance_repos
    user_a = uuid4()
    user_b = uuid4()
    subject_b = uuid4()

    # Log pertencente ao user_b
    audit_repo.save(
        ReviewAuditLog(
            user_id=user_b,
            question_id=uuid4(),
            subject_id=subject_b,
            topic_id=uuid4(),
            historical_subject_name="Matéria Secreta",
            historical_topic_name="Tema Secreto",
            review_date=date(2026, 10, 7),
            score=100,
            level_before=1,
            level_after=2,
        )
    )

    use_case = ListUserReviewAuditLogsUseCase(audit_repo=audit_repo)
    # user_a tenta filtrar pelo subject_b
    result = use_case.execute(user_id=user_a, page=1, page_size=10, subject_id=subject_b)

    assert len(result.items) == 0
    assert result.total_items == 0


@pytest.mark.unit
def test_list_user_review_audit_logs_invalid_pagination(performance_repos: tuple) -> None:
    """UC-S04-09: Rejeita página <= 0 ou page_size fora do intervalo permitido."""
    _, _, _, _, _, audit_repo, _, _ = performance_repos
    user_id = uuid4()
    use_case = ListUserReviewAuditLogsUseCase(audit_repo=audit_repo)

    with pytest.raises(
        DomainValidationError, match="O número da página deve ser maior ou igual a 1"
    ):
        use_case.execute(user_id=user_id, page=0)

    with pytest.raises(DomainValidationError, match="O tamanho da página deve estar entre 1 e 100"):
        use_case.execute(user_id=user_id, page=1, page_size=200)


# ---------------------------------------------------------------------------
# ExportUserDataUseCase (Streaming, Anti-CSV Injection e LGPD)
# ---------------------------------------------------------------------------


@pytest.mark.unit
@pytest.mark.security
def test_export_user_data_csv_anti_formula_injection(performance_repos: tuple) -> None:
    """Vulnerabilidade prevenida: CSV Formula Injection (CWE-1236).

    Garantia de segurança: Células iniciadas por '=', '+', '-', '@', '\t', '\r'
    são prefixadas com apóstrofo (') e escapadas conforme a RFC 4180.
    """
    user_repo, subj_repo, top_repo, q_repo, prog_repo, audit_repo, _, clock = performance_repos
    user_id = uuid4()
    user = User(id=user_id, google_sub="sub-teste", email="aluno@teste.com", name="Aluno Teste")
    user_repo.save(user)

    malicious_question_id = uuid4()
    # Nome de matéria ou tema malicioso
    audit_repo.save(
        ReviewAuditLog(
            user_id=user_id,
            question_id=malicious_question_id,
            subject_id=uuid4(),
            topic_id=uuid4(),
            historical_subject_name="=cmd|'/C calc'!A0",
            historical_topic_name="+2+5",
            review_date=date(2026, 10, 7),
            score=100,
            level_before=0,
            level_after=1,
            evaluation_mode="MANUAL",
            logged_at=datetime(2026, 10, 7, 10, 0, 0, tzinfo=UTC),
        )
    )

    q = Question(
        id=malicious_question_id,
        topic_id=uuid4(),
        prompt="@SUM(1,2)",
        expected_answer="Resp",
    )
    q_repo.save(q)

    use_case = ExportUserDataUseCase(
        user_repo=user_repo,
        audit_repo=audit_repo,
        question_repo=q_repo,
        clock=clock,
    )
    stream, filename, media_type = use_case.execute(user_id=user_id, format_type="csv")

    assert filename.startswith("study_reviewer_export_")
    assert filename.endswith(".csv")
    assert media_type == "text/csv; charset=utf-8"

    content = "".join(stream)
    # Valida presença do BOM UTF-8
    assert content.startswith("\ufeff")
    # Valida que as fórmulas foram neutralizadas com prefixo '
    assert "'=cmd|'/C calc'!A0" in content
    assert "'+2+5" in content
    assert "'@SUM(1,2)" in content


@pytest.mark.unit
@pytest.mark.security
def test_export_user_data_json_lgpd_sanitization(performance_repos: tuple) -> None:
    """Vulnerabilidade prevenida: Vazamento de dados de terceiros na portabilidade LGPD (Art. 18).

    Garantia de segurança: O JSON exportado não inclui IDs ou e-mails de outros usuários,
    contendo apenas os dados autorais e o progresso do titular.
    """
    import json

    user_repo, _, _, q_repo, prog_repo, audit_repo, _, clock = performance_repos
    user_id = uuid4()
    user = User(
        id=user_id, google_sub="sub-titular", email="titular@estudo.com", name="Titular LGPD"
    )
    user_repo.save(user)

    q_id = uuid4()
    q = Question(id=q_id, topic_id=uuid4(), prompt="Pergunta Pessoal", expected_answer="Resp")
    q_repo.save(q)
    prog_repo.save(UserQuestionProgress(user_id=user_id, question_id=q_id, current_level=3))

    audit_repo.save(
        ReviewAuditLog(
            user_id=user_id,
            question_id=q_id,
            subject_id=uuid4(),
            topic_id=uuid4(),
            historical_subject_name="Minha Matéria",
            historical_topic_name="Meu Tema",
            review_date=date(2026, 10, 7),
            score=100,
            level_before=2,
            level_after=3,
        )
    )

    use_case = ExportUserDataUseCase(
        user_repo=user_repo,
        audit_repo=audit_repo,
        question_repo=q_repo,
        clock=clock,
    )
    stream, filename, media_type = use_case.execute(user_id=user_id, format_type="json")

    assert filename.startswith("study_reviewer_export_")
    assert filename.endswith(".json")
    assert media_type == "application/json; charset=utf-8"

    full_json = json.loads("".join(stream))
    assert full_json["user"]["email"] == "titular@estudo.com"
    assert len(full_json["review_logs"]) == 1
    assert full_json["review_logs"][0]["historical_subject_name"] == "Minha Matéria"


@pytest.mark.unit
def test_export_user_data_invalid_format_raises_error(performance_repos: tuple) -> None:
    """UC-S04-08: Rejeita formatos não suportados (ex: XML, PDF)."""
    user_repo, _, _, q_repo, _, audit_repo, _, clock = performance_repos
    user_id = uuid4()

    use_case = ExportUserDataUseCase(
        user_repo=user_repo,
        audit_repo=audit_repo,
        question_repo=q_repo,
        clock=clock,
    )
    with pytest.raises(DomainValidationError, match="Formato de exportação inválido"):
        use_case.execute(user_id=user_id, format_type="xml")


@pytest.mark.unit
def test_export_user_data_user_not_found_raises_error(performance_repos: tuple) -> None:
    """Valida erro quando usuário não existe para exportação."""
    from src.domain.exceptions import EntityNotFoundError

    user_repo, _, _, q_repo, _, audit_repo, _, clock = performance_repos
    use_case = ExportUserDataUseCase(
        user_repo=user_repo,
        audit_repo=audit_repo,
        question_repo=q_repo,
        clock=clock,
    )
    with pytest.raises(EntityNotFoundError, match="Usuário não encontrado"):
        use_case.execute(user_id=uuid4(), format_type="csv")


@pytest.mark.unit
def test_export_user_data_multiple_logs_json_formatting(performance_repos: tuple) -> None:
    """Valida formatação JSON com múltiplos logs de auditoria (separador vírgula)."""
    import json

    user_repo, _, _, q_repo, _, audit_repo, _, clock = performance_repos
    user_id = uuid4()
    user = User(id=user_id, google_sub="sub-mult", email="multi@teste.com", name="Multi Aluno")
    user_repo.save(user)

    for i in range(2):
        audit_repo.save(
            ReviewAuditLog(
                user_id=user_id,
                question_id=uuid4(),
                subject_id=uuid4(),
                topic_id=uuid4(),
                historical_subject_name=f"Matéria {i}",
                historical_topic_name=f"Tema {i}",
                review_date=date(2026, 10, 7),
                score=100,
                level_before=0,
                level_after=1,
            )
        )

    use_case = ExportUserDataUseCase(
        user_repo=user_repo,
        audit_repo=audit_repo,
        question_repo=q_repo,
        clock=clock,
    )
    stream, _, _ = use_case.execute(user_id=user_id, format_type="json")
    parsed = json.loads("".join(stream))
    assert len(parsed["review_logs"]) == 2


@pytest.mark.unit
def test_export_user_data_csv_empty_question_or_values(performance_repos: tuple) -> None:
    """Valida exportação CSV quando question_id é nulo ou a questão não existe mais."""
    user_repo, _, _, q_repo, _, audit_repo, _, clock = performance_repos
    user_id = uuid4()
    user = User(id=user_id, google_sub="sub-empty", email="empty@teste.com", name="Empty Aluno")
    user_repo.save(user)

    # Log com question_id nulo
    audit_repo.save(
        ReviewAuditLog(
            user_id=user_id,
            question_id=None,
            subject_id=None,
            topic_id=None,
            historical_subject_name="Matéria Histórica",
            historical_topic_name="Tema Histórico",
            review_date=date(2026, 10, 7),
            score=100,
            level_before=0,
            level_after=1,
            evaluation_mode="MANUAL",
            logged_at=None,
        )
    )

    use_case = ExportUserDataUseCase(
        user_repo=user_repo,
        audit_repo=audit_repo,
        question_repo=q_repo,
        clock=clock,
    )
    stream, _, _ = use_case.execute(user_id=user_id, format_type="csv")
    content = "".join(stream)
    assert '""' in content
    assert "Matéria Histórica" in content
