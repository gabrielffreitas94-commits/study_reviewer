"""Testes unitários para os casos de uso de Perguntas Abertas e SRS Estrito (Sprint 03)."""

from datetime import date
from uuid import uuid4

import pytest

from src.application.dto.question_dto import (
    CreateQuestionDTO,
    ReviewQuestionInputDTO,
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
from src.domain.entities import Question, Subject, Topic, UserQuestionProgress
from src.domain.exceptions import (
    EntityNotFoundError,
    QuestionNotDueError,
    QuestionNotFoundError,
    ResourceOwnershipError,
)
from tests.unit.application.fakes import (
    FakeClockService,
    FakeQuestionProgressRepository,
    FakeQuestionRepository,
    FakeReviewAuditRepository,
    FakeSubjectRepository,
    FakeTopicRepository,
    FakeUnitOfWork,
)

RepoFixture = tuple[
    FakeSubjectRepository,
    FakeTopicRepository,
    FakeQuestionRepository,
    FakeQuestionProgressRepository,
    FakeClockService,
]


@pytest.fixture
def repos() -> RepoFixture:
    subj_repo = FakeSubjectRepository()
    top_repo = FakeTopicRepository()
    q_repo = FakeQuestionRepository()
    prog_repo = FakeQuestionProgressRepository(q_repo, top_repo, subj_repo)
    clock = FakeClockService(current_date=date(2026, 10, 10))
    return subj_repo, top_repo, q_repo, prog_repo, clock


# ---------------------------------------------------------------------------
# CreateQuestionUseCase
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_create_question_success(repos: RepoFixture) -> None:
    subj_repo, top_repo, q_repo, prog_repo, clock = repos
    owner_id = uuid4()
    subj = Subject(id=uuid4(), name="Direito", owner_id=owner_id)
    subj_repo.save(subj)
    topic = Topic(id=uuid4(), subject_id=subj.id, name="Constitucional")
    top_repo.save(topic)

    use_case = CreateQuestionUseCase(q_repo, prog_repo, top_repo, subj_repo, clock)
    dto = CreateQuestionDTO(
        topic_id=topic.id, prompt="O que é CF?", expected_answer="Constituição Federal"
    )

    result = use_case.execute(dto, user_id=owner_id)

    assert result.prompt == "O que é CF?"
    assert result.expected_answer == "Constituição Federal"
    assert q_repo.get_by_id(result.id) is not None

    # Progresso inicial criado para o autor no nível 0 vencendo hoje
    prog = prog_repo.get_by_user_and_question(owner_id, result.id)
    assert prog is not None
    assert prog.current_level == 0
    assert prog.next_review_date == clock.today()


@pytest.mark.unit
def test_create_question_with_uow_commits_atomically(repos: RepoFixture) -> None:
    subj_repo, top_repo, q_repo, prog_repo, clock = repos
    owner_id = uuid4()
    subj = Subject(id=uuid4(), name="Direito", owner_id=owner_id)
    subj_repo.save(subj)
    topic = Topic(id=uuid4(), subject_id=subj.id, name="Constitucional")
    top_repo.save(topic)

    uow = FakeUnitOfWork()
    use_case = CreateQuestionUseCase(q_repo, prog_repo, top_repo, subj_repo, clock, uow=uow)
    dto = CreateQuestionDTO(
        topic_id=topic.id, prompt="O que é CF?", expected_answer="Constituição Federal"
    )

    result = use_case.execute(dto, user_id=owner_id)

    assert result.prompt == "O que é CF?"
    assert uow.committed is True
    assert uow.rolled_back is False


@pytest.mark.unit
def test_create_question_with_uow_rollback_on_failure(repos: RepoFixture) -> None:
    subj_repo, top_repo, q_repo, prog_repo, clock = repos
    owner_id = uuid4()
    subj = Subject(id=uuid4(), name="Direito", owner_id=owner_id)
    subj_repo.save(subj)
    topic = Topic(id=uuid4(), subject_id=subj.id, name="Constitucional")
    top_repo.save(topic)

    uow = FakeUnitOfWork()
    prog_repo.fail_on_save = True

    use_case = CreateQuestionUseCase(q_repo, prog_repo, top_repo, subj_repo, clock, uow=uow)
    dto = CreateQuestionDTO(
        topic_id=topic.id, prompt="O que é CF?", expected_answer="Constituição Federal"
    )

    with pytest.raises(RuntimeError, match="Erro ao persistir progresso"):
        use_case.execute(dto, user_id=owner_id)

    assert uow.committed is False
    assert uow.rolled_back is True


@pytest.mark.unit
def test_create_question_topic_not_found(repos: RepoFixture) -> None:
    subj_repo, top_repo, q_repo, prog_repo, clock = repos
    use_case = CreateQuestionUseCase(q_repo, prog_repo, top_repo, subj_repo, clock)
    dto = CreateQuestionDTO(topic_id=uuid4(), prompt="P", expected_answer="R")

    with pytest.raises(EntityNotFoundError, match="Tema não encontrado"):
        use_case.execute(dto, user_id=uuid4())


@pytest.mark.unit
@pytest.mark.security
def test_create_question_non_owner_forbidden(repos: RepoFixture) -> None:
    """Vulnerabilidade prevenida: IDOR na criação de perguntas em temas alheios.
    Garantia de segurança: Apenas o proprietário da matéria pode adicionar perguntas.
    """
    subj_repo, top_repo, q_repo, prog_repo, clock = repos
    owner_id = uuid4()
    attacker_id = uuid4()
    subj = Subject(id=uuid4(), name="Direito Privado", owner_id=owner_id, is_public=True)
    subj_repo.save(subj)
    topic = Topic(id=uuid4(), subject_id=subj.id, name="Contratos")
    top_repo.save(topic)

    use_case = CreateQuestionUseCase(q_repo, prog_repo, top_repo, subj_repo, clock)
    dto = CreateQuestionDTO(topic_id=topic.id, prompt="P", expected_answer="R")

    with pytest.raises(ResourceOwnershipError, match="Apenas o proprietário da matéria"):
        use_case.execute(dto, user_id=attacker_id)


# ---------------------------------------------------------------------------
# UpdateQuestionUseCase & DeleteQuestionUseCase
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_update_question_success(repos: RepoFixture) -> None:
    subj_repo, top_repo, q_repo, _, _ = repos
    owner_id = uuid4()
    subj = Subject(id=uuid4(), name="Matemática", owner_id=owner_id)
    subj_repo.save(subj)
    topic = Topic(id=uuid4(), subject_id=subj.id, name="Álgebra")
    top_repo.save(topic)
    q = Question(id=uuid4(), topic_id=topic.id, prompt="1+1?", expected_answer="2")
    q_repo.save(q)

    use_case = UpdateQuestionUseCase(q_repo, top_repo, subj_repo)
    updated = use_case.execute(
        UpdateQuestionDTO(question_id=q.id, prompt="Quanto é 1+1?", expected_answer="Dois"),
        user_id=owner_id,
    )

    assert updated.prompt == "Quanto é 1+1?"
    assert updated.expected_answer == "Dois"
    saved = q_repo.get_by_id(q.id)
    assert saved is not None
    assert saved.prompt == "Quanto é 1+1?"


@pytest.mark.unit
@pytest.mark.security
def test_update_question_non_owner_forbidden(repos: RepoFixture) -> None:
    """Vulnerabilidade prevenida: IDOR na edição de perguntas de outros usuários.
    Garantia de segurança: Tentativa de update por não-proprietário rejeitada com 403.
    """
    subj_repo, top_repo, q_repo, _, _ = repos
    owner_id = uuid4()
    subj = Subject(id=uuid4(), name="Física", owner_id=owner_id)
    subj_repo.save(subj)
    topic = Topic(id=uuid4(), subject_id=subj.id, name="Mecânica")
    top_repo.save(topic)
    q = Question(id=uuid4(), topic_id=topic.id, prompt="v=d/t?", expected_answer="Sim")
    q_repo.save(q)

    use_case = UpdateQuestionUseCase(q_repo, top_repo, subj_repo)
    with pytest.raises(ResourceOwnershipError):
        use_case.execute(
            UpdateQuestionDTO(question_id=q.id, prompt="X", expected_answer="Y"),
            user_id=uuid4(),
        )


@pytest.mark.unit
def test_update_question_not_found(repos: RepoFixture) -> None:
    subj_repo, top_repo, q_repo, _, _ = repos
    use_case = UpdateQuestionUseCase(q_repo, top_repo, subj_repo)
    with pytest.raises(QuestionNotFoundError):
        use_case.execute(
            UpdateQuestionDTO(question_id=uuid4(), prompt="X", expected_answer="Y"),
            user_id=uuid4(),
        )


@pytest.mark.unit
def test_delete_question_success(repos: RepoFixture) -> None:
    subj_repo, top_repo, q_repo, _, _ = repos
    owner_id = uuid4()
    subj = Subject(id=uuid4(), name="Química", owner_id=owner_id)
    subj_repo.save(subj)
    topic = Topic(id=uuid4(), subject_id=subj.id, name="Orgânica")
    top_repo.save(topic)
    q = Question(id=uuid4(), topic_id=topic.id, prompt="H2O?", expected_answer="Água")
    q_repo.save(q)

    use_case = DeleteQuestionUseCase(q_repo, top_repo, subj_repo)
    use_case.execute(q.id, user_id=owner_id)

    assert q_repo.get_by_id(q.id) is None


@pytest.mark.unit
@pytest.mark.security
def test_delete_question_non_owner_forbidden(repos: RepoFixture) -> None:
    """Vulnerabilidade prevenida: IDOR na exclusão de perguntas alheias.
    Garantia de segurança: Tentativa de delete por terceiros rejeitada com 403.
    """
    subj_repo, top_repo, q_repo, _, _ = repos
    owner_id = uuid4()
    subj = Subject(id=uuid4(), name="Química", owner_id=owner_id)
    subj_repo.save(subj)
    topic = Topic(id=uuid4(), subject_id=subj.id, name="Orgânica")
    top_repo.save(topic)
    q = Question(id=uuid4(), topic_id=topic.id, prompt="P?", expected_answer="R")
    q_repo.save(q)

    use_case = DeleteQuestionUseCase(q_repo, top_repo, subj_repo)
    with pytest.raises(ResourceOwnershipError):
        use_case.execute(q.id, user_id=uuid4())


# ---------------------------------------------------------------------------
# ListQuestionsByTopicUseCase & GetQuestionByIdUseCase
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_list_questions_by_topic_owner_and_public(repos: RepoFixture) -> None:
    subj_repo, top_repo, q_repo, _, _ = repos
    owner_id = uuid4()
    visitor_id = uuid4()

    # Matéria pública
    subj_pub = Subject(id=uuid4(), name="Pública", owner_id=owner_id, is_public=True)
    subj_repo.save(subj_pub)
    topic_pub = Topic(id=uuid4(), subject_id=subj_pub.id, name="Tema Pub")
    top_repo.save(topic_pub)
    q1 = Question(id=uuid4(), topic_id=topic_pub.id, prompt="P1", expected_answer="R1")
    q_repo.save(q1)

    use_case = ListQuestionsByTopicUseCase(q_repo, top_repo, subj_repo)

    # Visitante pode ler matéria pública
    res_visitor = use_case.execute(topic_pub.id, user_id=visitor_id)
    assert len(res_visitor) == 1
    assert res_visitor[0].prompt == "P1"

    # Matéria privada de outro usuário
    subj_priv = Subject(id=uuid4(), name="Privada", owner_id=owner_id, is_public=False)
    subj_repo.save(subj_priv)
    topic_priv = Topic(id=uuid4(), subject_id=subj_priv.id, name="Tema Priv")
    top_repo.save(topic_priv)

    with pytest.raises(ResourceOwnershipError):
        use_case.execute(topic_priv.id, user_id=visitor_id)


@pytest.mark.unit
def test_get_question_by_id(repos: RepoFixture) -> None:
    subj_repo, top_repo, q_repo, _, _ = repos
    owner_id = uuid4()
    subj = Subject(id=uuid4(), name="Biologia", owner_id=owner_id, is_public=False)
    subj_repo.save(subj)
    topic = Topic(id=uuid4(), subject_id=subj.id, name="Genética")
    top_repo.save(topic)
    q = Question(id=uuid4(), topic_id=topic.id, prompt="DNA?", expected_answer="Ácido...")
    q_repo.save(q)

    use_case = GetQuestionByIdUseCase(q_repo, top_repo, subj_repo)

    # Owner tem acesso
    found = use_case.execute(q.id, user_id=owner_id)
    assert found.prompt == "DNA?"

    # Visitante não tem acesso a matéria privada
    with pytest.raises(ResourceOwnershipError):
        use_case.execute(q.id, user_id=uuid4())

    # Pergunta inexistente
    with pytest.raises(QuestionNotFoundError):
        use_case.execute(uuid4(), user_id=owner_id)


# ---------------------------------------------------------------------------
# GetDueQuestionsUseCase
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_get_due_questions_deterministic_ordering(repos: RepoFixture) -> None:
    subj_repo, top_repo, q_repo, prog_repo, clock = repos
    user_id = uuid4()
    subj = Subject(id=uuid4(), name="História", owner_id=user_id)
    subj_repo.save(subj)
    topic = Topic(id=uuid4(), subject_id=subj.id, name="Brasil")
    top_repo.save(topic)

    q1 = Question(id=uuid4(), topic_id=topic.id, prompt="Q1", expected_answer="A1")
    q2 = Question(id=uuid4(), topic_id=topic.id, prompt="Q2", expected_answer="A2")
    q3 = Question(id=uuid4(), topic_id=topic.id, prompt="Q3", expected_answer="A3")
    q_repo.save(q1)
    q_repo.save(q2)
    q_repo.save(q3)

    # q1: vencida ontem no nível 1
    prog_repo.save(
        UserQuestionProgress(
            user_id=user_id, question_id=q1.id, current_level=1, next_review_date=date(2026, 10, 9)
        )
    )
    # q2: vencida hoje no nível 0
    prog_repo.save(
        UserQuestionProgress(
            user_id=user_id, question_id=q2.id, current_level=0, next_review_date=date(2026, 10, 10)
        )
    )
    # q3: agendada para amanhã (future - não deve vir na fila de hoje)
    prog_repo.save(
        UserQuestionProgress(
            user_id=user_id, question_id=q3.id, current_level=0, next_review_date=date(2026, 10, 11)
        )
    )

    use_case = GetDueQuestionsUseCase(prog_repo, q_repo, top_repo, subj_repo, clock)
    due_items = use_case.execute(user_id=user_id)

    assert len(due_items) == 2
    # Prioridade para o mais atrasado (q1 de ontem vem antes de q2 de hoje)
    assert due_items[0].question_id == q1.id
    assert due_items[1].question_id == q2.id


@pytest.mark.unit
def test_get_due_questions_filter_public_subject_auto_initializes_batch(repos: RepoFixture) -> None:
    subj_repo, top_repo, q_repo, prog_repo, clock = repos
    owner_id = uuid4()
    student_id = uuid4()

    subj_pub = Subject(id=uuid4(), name="Direito Público", owner_id=owner_id, is_public=True)
    subj_repo.save(subj_pub)
    topic = Topic(id=uuid4(), subject_id=subj_pub.id, name="Admin")
    top_repo.save(topic)

    q1 = Question(id=uuid4(), topic_id=topic.id, prompt="Q1", expected_answer="A1")
    q2 = Question(id=uuid4(), topic_id=topic.id, prompt="Q2", expected_answer="A2")
    q_repo.save(q1)
    q_repo.save(q2)

    use_case = GetDueQuestionsUseCase(prog_repo, q_repo, top_repo, subj_repo, clock)

    # Sem filtro, o estudante não recebe as perguntas públicas não-iniciadas
    assert len(use_case.execute(user_id=student_id)) == 0

    # Com filtro explícito da matéria pública, o progresso é inicializado em lote
    items = use_case.execute(user_id=student_id, subject_id=subj_pub.id)
    assert len(items) == 2
    assert prog_repo.get_by_user_and_question(student_id, q1.id) is not None


# ---------------------------------------------------------------------------
# ReviewQuestionUseCase
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_review_question_promotion_success(repos: RepoFixture) -> None:
    subj_repo, top_repo, q_repo, prog_repo, clock = repos
    user_id = uuid4()
    subj = Subject(id=uuid4(), name="Sociologia", owner_id=user_id)
    subj_repo.save(subj)
    topic = Topic(id=uuid4(), subject_id=subj.id, name="Geral")
    top_repo.save(topic)
    q = Question(id=uuid4(), topic_id=topic.id, prompt="Q?", expected_answer="A")
    q_repo.save(q)
    prog = UserQuestionProgress(
        user_id=user_id, question_id=q.id, current_level=1, next_review_date=date(2026, 10, 10)
    )
    prog_repo.save(prog)

    use_case = ReviewQuestionUseCase(prog_repo, q_repo, top_repo, subj_repo, clock)
    res = use_case.execute(ReviewQuestionInputDTO(question_id=q.id, score=100), user_id=user_id)

    assert res.previous_level == 1
    assert res.new_level == 2
    assert res.interval_days == 15
    assert res.next_review_date == date(2026, 10, 25)
    assert res.is_promoted is True
    assert res.is_regressed is False


@pytest.mark.unit
def test_review_question_uow_commit_and_rollback(repos: RepoFixture) -> None:
    subj_repo, top_repo, q_repo, prog_repo, clock = repos
    user_id = uuid4()
    subj = Subject(id=uuid4(), name="Sociologia", owner_id=user_id)
    subj_repo.save(subj)
    topic = Topic(id=uuid4(), subject_id=subj.id, name="Geral")
    top_repo.save(topic)
    q = Question(id=uuid4(), topic_id=topic.id, prompt="Q?", expected_answer="A")
    q_repo.save(q)
    prog = UserQuestionProgress(
        user_id=user_id, question_id=q.id, current_level=1, next_review_date=date(2026, 10, 10)
    )
    prog_repo.save(prog)

    uow = FakeUnitOfWork()
    audit_repo = FakeReviewAuditRepository()
    use_case = ReviewQuestionUseCase(
        prog_repo, q_repo, top_repo, subj_repo, clock, audit_repo=audit_repo, uow=uow
    )
    res = use_case.execute(ReviewQuestionInputDTO(question_id=q.id, score=100), user_id=user_id)
    assert res.new_level == 2
    assert uow.committed is True
    assert uow.rolled_back is False
    assert len(audit_repo.logs) == 1

    # Testa rollback quando o audit_repo falha
    uow2 = FakeUnitOfWork()
    audit_repo2 = FakeReviewAuditRepository()
    audit_repo2.fail_on_save = True

    prog.next_review_date = date(2026, 10, 10)
    prog_repo.save(prog)

    use_case2 = ReviewQuestionUseCase(
        prog_repo, q_repo, top_repo, subj_repo, clock, audit_repo=audit_repo2, uow=uow2
    )
    with pytest.raises(RuntimeError, match="Falha de I/O na tabela de auditoria"):
        use_case2.execute(ReviewQuestionInputDTO(question_id=q.id, score=100), user_id=user_id)

    assert uow2.committed is False
    assert uow2.rolled_back is True


@pytest.mark.unit
def test_review_question_level_6_penalty_regression(repos: RepoFixture) -> None:
    subj_repo, top_repo, q_repo, prog_repo, clock = repos
    user_id = uuid4()
    subj = Subject(id=uuid4(), name="Filosofia", owner_id=user_id)
    subj_repo.save(subj)
    topic = Topic(id=uuid4(), subject_id=subj.id, name="Ética")
    top_repo.save(topic)
    q = Question(id=uuid4(), topic_id=topic.id, prompt="Q?", expected_answer="A")
    q_repo.save(q)
    prog = UserQuestionProgress(
        user_id=user_id, question_id=q.id, current_level=6, next_review_date=date(2026, 10, 10)
    )
    prog_repo.save(prog)

    use_case = ReviewQuestionUseCase(prog_repo, q_repo, top_repo, subj_repo, clock)
    res = use_case.execute(ReviewQuestionInputDTO(question_id=q.id, score=99), user_id=user_id)

    assert res.previous_level == 6
    assert res.new_level == 2  # Penalidade severa: regride para o Nível 2 (+15d)
    assert res.interval_days == 15
    assert res.next_review_date == date(2026, 10, 25)
    assert res.is_promoted is False
    assert res.is_regressed is True


@pytest.mark.unit
@pytest.mark.security
def test_review_question_premature_review_rejected(repos: RepoFixture) -> None:
    """Vulnerabilidade prevenida: Exploit temporal de SRS (saltar níveis no mesmo dia).
    Garantia de segurança: Submissões em perguntas cuja data de vencimento é futura são rejeitadas.
    """
    subj_repo, top_repo, q_repo, prog_repo, clock = repos
    user_id = uuid4()
    subj = Subject(id=uuid4(), name="Física", owner_id=user_id)
    subj_repo.save(subj)
    topic = Topic(id=uuid4(), subject_id=subj.id, name="Óptica")
    top_repo.save(topic)
    q = Question(id=uuid4(), topic_id=topic.id, prompt="Q?", expected_answer="A")
    q_repo.save(q)
    # Agendado para o futuro (amanhã 2026-10-11, sendo hoje 2026-10-10)
    prog = UserQuestionProgress(
        user_id=user_id, question_id=q.id, current_level=1, next_review_date=date(2026, 10, 11)
    )
    prog_repo.save(prog)

    use_case = ReviewQuestionUseCase(prog_repo, q_repo, top_repo, subj_repo, clock)
    with pytest.raises(QuestionNotDueError, match="não está vencida para revisão"):
        use_case.execute(ReviewQuestionInputDTO(question_id=q.id, score=100), user_id=user_id)


@pytest.mark.unit
@pytest.mark.security
def test_review_question_private_subject_idor_forbidden(repos: RepoFixture) -> None:
    """Vulnerabilidade prevenida: IDOR na revisão de perguntas privadas de outros alunos.
    Garantia de segurança: Se a matéria for privada de terceiro, o acesso é rejeitado com 403.
    """
    subj_repo, top_repo, q_repo, prog_repo, clock = repos
    author_id = uuid4()
    attacker_id = uuid4()
    subj = Subject(id=uuid4(), name="Segredos", owner_id=author_id, is_public=False)
    subj_repo.save(subj)
    topic = Topic(id=uuid4(), subject_id=subj.id, name="Confidencial")
    top_repo.save(topic)
    q = Question(id=uuid4(), topic_id=topic.id, prompt="Senha?", expected_answer="123")
    q_repo.save(q)

    use_case = ReviewQuestionUseCase(prog_repo, q_repo, top_repo, subj_repo, clock)
    with pytest.raises(ResourceOwnershipError):
        use_case.execute(ReviewQuestionInputDTO(question_id=q.id, score=100), user_id=attacker_id)


@pytest.mark.unit
def test_review_question_public_subject_jit_creation(repos: RepoFixture) -> None:
    subj_repo, top_repo, q_repo, prog_repo, clock = repos
    author_id = uuid4()
    student_id = uuid4()
    subj = Subject(id=uuid4(), name="Pública", owner_id=author_id, is_public=True)
    subj_repo.save(subj)
    topic = Topic(id=uuid4(), subject_id=subj.id, name="Comum")
    top_repo.save(topic)
    q = Question(id=uuid4(), topic_id=topic.id, prompt="Pública?", expected_answer="Sim")
    q_repo.save(q)

    # O estudante ainda não tinha registro em user_question_progress
    use_case = ReviewQuestionUseCase(prog_repo, q_repo, top_repo, subj_repo, clock)
    res = use_case.execute(ReviewQuestionInputDTO(question_id=q.id, score=100), user_id=student_id)

    assert res.previous_level == 0
    assert res.new_level == 1
    assert prog_repo.get_by_user_and_question(student_id, q.id) is not None


@pytest.mark.unit
def test_use_cases_orphan_and_missing_entities_coverage(repos: RepoFixture) -> None:
    subj_repo, top_repo, q_repo, prog_repo, clock = repos
    user_id = uuid4()

    # Pergunta órfã (sem tema)
    orphan_q = Question(id=uuid4(), topic_id=uuid4(), prompt="P", expected_answer="R")
    q_repo.save(orphan_q)

    # 1. Update órfão
    update_uc = UpdateQuestionUseCase(q_repo, top_repo, subj_repo)
    with pytest.raises(EntityNotFoundError, match="Tema não encontrado"):
        update_uc.execute(
            UpdateQuestionDTO(question_id=orphan_q.id, prompt="P2", expected_answer="R2"),
            user_id=user_id,
        )

    # 2. Delete órfão
    delete_uc = DeleteQuestionUseCase(q_repo, top_repo, subj_repo)
    with pytest.raises(EntityNotFoundError, match="Tema não encontrado"):
        delete_uc.execute(orphan_q.id, user_id=user_id)

    # 3. GetById órfão
    get_by_id_uc = GetQuestionByIdUseCase(q_repo, top_repo, subj_repo)
    with pytest.raises(EntityNotFoundError, match="Tema não encontrado"):
        get_by_id_uc.execute(orphan_q.id, user_id=user_id)

    # 4. Review órfão
    review_uc = ReviewQuestionUseCase(prog_repo, q_repo, top_repo, subj_repo, clock)
    with pytest.raises(EntityNotFoundError, match="Tema não encontrado"):
        review_uc.execute(
            ReviewQuestionInputDTO(question_id=orphan_q.id, score=100), user_id=user_id
        )


@pytest.mark.unit
def test_use_cases_missing_subject_coverage(repos: RepoFixture) -> None:
    subj_repo, top_repo, q_repo, prog_repo, clock = repos
    user_id = uuid4()

    # Tema apontando para matéria inexistente
    orphan_topic = Topic(id=uuid4(), subject_id=uuid4(), name="Tema Órfão")
    top_repo.save(orphan_topic)
    q = Question(id=uuid4(), topic_id=orphan_topic.id, prompt="P", expected_answer="R")
    q_repo.save(q)

    # 1. Update com matéria inexistente
    with pytest.raises(ResourceOwnershipError):
        UpdateQuestionUseCase(q_repo, top_repo, subj_repo).execute(
            UpdateQuestionDTO(question_id=q.id, prompt="P2", expected_answer="R2"), user_id=user_id
        )

    # 2. Delete com matéria inexistente
    with pytest.raises(ResourceOwnershipError):
        DeleteQuestionUseCase(q_repo, top_repo, subj_repo).execute(q.id, user_id=user_id)

    # 3. ListByTopic com matéria inexistente
    with pytest.raises(ResourceOwnershipError):
        ListQuestionsByTopicUseCase(q_repo, top_repo, subj_repo).execute(
            orphan_topic.id, user_id=user_id
        )

    # 4. GetById com matéria inexistente
    with pytest.raises(ResourceOwnershipError):
        GetQuestionByIdUseCase(q_repo, top_repo, subj_repo).execute(q.id, user_id=user_id)

    # 5. Review com matéria inexistente
    with pytest.raises(ResourceOwnershipError):
        ReviewQuestionUseCase(prog_repo, q_repo, top_repo, subj_repo, clock).execute(
            ReviewQuestionInputDTO(question_id=q.id, score=100), user_id=user_id
        )


@pytest.mark.unit
def test_get_due_questions_topic_filter_and_error_cases(repos: RepoFixture) -> None:
    subj_repo, top_repo, q_repo, prog_repo, clock = repos
    user_id = uuid4()
    other_id = uuid4()

    # Matéria do usuário
    subj = Subject(id=uuid4(), name="Matéria", owner_id=user_id)
    subj_repo.save(subj)
    topic = Topic(id=uuid4(), subject_id=subj.id, name="Tema")
    top_repo.save(topic)
    q = Question(id=uuid4(), topic_id=topic.id, prompt="P", expected_answer="R")
    q_repo.save(q)

    use_case = GetDueQuestionsUseCase(prog_repo, q_repo, top_repo, subj_repo, clock)

    # 1. Filtro com topic_id válido -> inicializa e retorna
    items = use_case.execute(user_id=user_id, topic_id=topic.id)
    assert len(items) == 1

    # 2. Filtro com topic_id inexistente -> EntityNotFoundError
    with pytest.raises(EntityNotFoundError, match="Tema não encontrado"):
        use_case.execute(user_id=user_id, topic_id=uuid4())

    # 3. Filtro com subject_id inexistente -> EntityNotFoundError
    with pytest.raises(EntityNotFoundError, match="Matéria não encontrada"):
        use_case.execute(user_id=user_id, subject_id=uuid4())

    # 4. Filtro com subject_id privado de outro usuário -> ResourceOwnershipError
    subj_priv = Subject(id=uuid4(), name="Privada", owner_id=other_id, is_public=False)
    subj_repo.save(subj_priv)
    with pytest.raises(ResourceOwnershipError):
        use_case.execute(user_id=user_id, subject_id=subj_priv.id)

    # 5. Filtro com topic de matéria privada de outro usuário -> ResourceOwnershipError
    topic_priv = Topic(id=uuid4(), subject_id=subj_priv.id, name="Priv")
    top_repo.save(topic_priv)
    with pytest.raises(ResourceOwnershipError):
        use_case.execute(user_id=user_id, topic_id=topic_priv.id)


@pytest.mark.unit
def test_missing_question_or_topic_not_found_errors(repos: RepoFixture) -> None:
    subj_repo, top_repo, q_repo, prog_repo, clock = repos
    user_id = uuid4()

    # 1. DeleteQuestion com pergunta inexistente -> QuestionNotFoundError
    with pytest.raises(QuestionNotFoundError, match="Pergunta não encontrada"):
        DeleteQuestionUseCase(q_repo, top_repo, subj_repo).execute(uuid4(), user_id=user_id)

    # 2. ListQuestionsByTopic com tema inexistente -> EntityNotFoundError
    with pytest.raises(EntityNotFoundError, match="Tema não encontrado"):
        ListQuestionsByTopicUseCase(q_repo, top_repo, subj_repo).execute(uuid4(), user_id=user_id)

    # 3. ReviewQuestion com pergunta inexistente -> QuestionNotFoundError
    with pytest.raises(QuestionNotFoundError, match="Pergunta não encontrada"):
        ReviewQuestionUseCase(prog_repo, q_repo, top_repo, subj_repo, clock).execute(
            ReviewQuestionInputDTO(question_id=uuid4(), score=100), user_id=user_id
        )
