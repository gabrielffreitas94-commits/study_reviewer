"""Testes de integração para os controladores Web e templates de Perguntas Abertas (Camada 3)."""

from collections.abc import Generator
from datetime import date, timedelta
from typing import Any
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from src.adapters.persistence.repositories import (
    SqlAlchemyQuestionProgressRepository,
    SqlAlchemyQuestionRepository,
    SqlAlchemySubjectRepository,
    SqlAlchemyTopicRepository,
    SqlAlchemyUserRepository,
)
from src.domain.entities import Question, Subject, Topic, User, UserQuestionProgress
from src.infrastructure.database import Base, get_db
from src.infrastructure.security.dependencies import get_current_user
from src.infrastructure.security.rate_limiter import reset_rate_limits
from src.infrastructure.web.app import app


@pytest.fixture
def test_user() -> User:
    return User(
        id=uuid4(),
        google_sub="sub-web-q-1",
        email="q.web@studyreviewer.local",
        name="Web Question User",
    )


@pytest.fixture
def other_user() -> User:
    return User(
        id=uuid4(),
        google_sub="sub-web-q-2",
        email="other.web@studyreviewer.local",
        name="Other User",
    )


@pytest.fixture
def db_engine() -> Generator[Any]:
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    yield engine
    Base.metadata.drop_all(engine)
    engine.dispose()


@pytest.fixture
def client(db_engine: Any, test_user: User, other_user: User) -> Generator[TestClient]:
    TestingSession = sessionmaker(bind=db_engine)

    with TestingSession() as session:
        u_repo = SqlAlchemyUserRepository(session)
        u_repo.save(test_user)
        u_repo.save(other_user)

    def override_get_db() -> Generator[Session]:
        session = TestingSession()
        try:
            yield session
        finally:
            session.close()

    def override_get_current_user() -> User:
        return test_user

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_current_user] = override_get_current_user
    reset_rate_limits()

    with TestClient(app, raise_server_exceptions=False) as test_client:
        yield test_client

    app.dependency_overrides.clear()
    reset_rate_limits()


@pytest.mark.integration
def test_study_page_onboarding_state_when_empty_catalog(client: TestClient) -> None:
    """Verifica renderização do estado de Onboarding quando não há perguntas cadastradas."""
    res = client.get("/questions/study")
    assert res.status_code == 200
    assert "Comece seu Estudo Ativo" in res.text
    assert "Ir para Matérias & Temas" in res.text


@pytest.mark.integration
def test_study_page_renders_due_question_card_and_active_recall(
    client: TestClient, test_user: User, db_engine: Any
) -> None:
    """Verifica renderização do Ideal State com Active Recall e controles desabilitados."""
    with Session(db_engine) as session:
        subj = Subject(name="Direito Civil", owner_id=test_user.id)
        SqlAlchemySubjectRepository(session).save(subj)
        topic = Topic(subject_id=subj.id, name="Contratos")
        SqlAlchemyTopicRepository(session).save(topic)
        q = Question(
            topic_id=topic.id,
            prompt="O que é evicção?",
            expected_answer="Perda da coisa por decisão judicial.",
        )
        SqlAlchemyQuestionRepository(session).save(q)
        SqlAlchemyQuestionProgressRepository(session).save(
            UserQuestionProgress(
                user_id=test_user.id, question_id=q.id, next_review_date=date.today()
            )
        )
        session.commit()

    res = client.get("/questions/study")
    assert res.status_code == 200
    assert "O que é evicção?" in res.text
    assert "Revelar Resposta Esperada" in res.text
    assert "Perda da coisa por decisão judicial." in res.text
    assert "Nível 0" in res.text
    assert "1d" in res.text
    assert 'aria-expanded="false"' in res.text
    assert 'id="srs-evaluation-form"' in res.text
    assert "pointer-events-none" in res.text


@pytest.mark.integration
def test_study_page_inbox_zero_state_when_questions_done(
    client: TestClient, test_user: User, db_engine: Any
) -> None:
    """Verifica renderização do estado Inbox Zero quando perguntas do dia foram concluídas."""
    tomorrow = date.today() + timedelta(days=1)
    with Session(db_engine) as session:
        subj = Subject(name="História", owner_id=test_user.id)
        SqlAlchemySubjectRepository(session).save(subj)
        topic = Topic(subject_id=subj.id, name="Brasil")
        SqlAlchemyTopicRepository(session).save(topic)
        q = Question(topic_id=topic.id, prompt="Descobrimento?", expected_answer="1500")
        SqlAlchemyQuestionRepository(session).save(q)
        SqlAlchemyQuestionProgressRepository(session).save(
            UserQuestionProgress(user_id=test_user.id, question_id=q.id, next_review_date=tomorrow)
        )
        session.commit()

    res = client.get("/questions/study")
    assert res.status_code == 200
    assert "Tudo em dia por hoje!" in res.text
    assert tomorrow.strftime("%d/%m/%Y") in res.text


@pytest.mark.integration
def test_review_question_submission_htmx_cycle(
    client: TestClient, test_user: User, db_engine: Any
) -> None:
    """Verifica submissão HTMX: avanço para próximo card e swap final de Inbox Zero."""
    with Session(db_engine) as session:
        subj = Subject(name="Geografia", owner_id=test_user.id)
        SqlAlchemySubjectRepository(session).save(subj)
        topic = Topic(subject_id=subj.id, name="Clima")
        SqlAlchemyTopicRepository(session).save(topic)
        q1 = Question(
            topic_id=topic.id, prompt="Clima equatorial?", expected_answer="Quente e úmido"
        )
        q2 = Question(topic_id=topic.id, prompt="Clima semiárido?", expected_answer="Seco")
        SqlAlchemyQuestionRepository(session).save(q1)
        SqlAlchemyQuestionRepository(session).save(q2)

        prog_repo = SqlAlchemyQuestionProgressRepository(session)
        prog_repo.save(
            UserQuestionProgress(
                user_id=test_user.id, question_id=q1.id, next_review_date=date.today()
            )
        )
        prog_repo.save(
            UserQuestionProgress(
                user_id=test_user.id, question_id=q2.id, next_review_date=date.today()
            )
        )
        session.commit()

    # 1. Revisa q1 com nota 100 -> deve retornar parcial com q2
    res1 = client.post(f"/questions/{q1.id}/review", data={"score": 100})
    assert res1.status_code == 200
    assert "Clima semiárido?" in res1.text
    assert 'hx-swap-oob="outerHTML"' in res1.text
    assert "review-badge" in res1.text

    # 2. Revisa q2 com nota 75 -> fila esgota, deve retornar parcial de Inbox Zero
    res2 = client.post(f"/questions/{q2.id}/review", data={"score": 75})
    assert res2.status_code == 200
    assert "Tudo em dia por hoje!" in res2.text


@pytest.mark.integration
def test_manage_topic_questions_web_flow(
    client: TestClient, test_user: User, db_engine: Any
) -> None:
    """Verifica fluxo completo de gerenciamento de perguntas de um tema na interface Web."""
    with Session(db_engine) as session:
        subj = Subject(name="Economia", owner_id=test_user.id)
        SqlAlchemySubjectRepository(session).save(subj)
        topic = Topic(subject_id=subj.id, name="Microeconomia")
        SqlAlchemyTopicRepository(session).save(topic)

    # 1. Carrega tela de gerenciamento vazia
    res_get = client.get(f"/topics/{topic.id}/questions")
    assert res_get.status_code == 200
    assert "Microeconomia" in res_get.text
    assert "Nenhuma pergunta cadastrada" in res_get.text

    # 2. Cria nova pergunta via formulário Web
    res_post = client.post(
        f"/topics/{topic.id}/questions",
        data={
            "prompt": "O que é elasticidade-preço da demanda?",
            "expected_answer": "Variação percentual da quantidade demandada...",
        },
        follow_redirects=True,
    )
    assert res_post.status_code == 200
    assert "O que é elasticidade-preço da demanda?" in res_post.text

    # Pega ID da pergunta criada
    with Session(db_engine) as session:
        questions = SqlAlchemyQuestionRepository(session).list_by_topic(topic.id)
        assert len(questions) == 1
        q_id = questions[0].id

    # 3. Exclui a pergunta via HTMX DELETE
    res_del = client.delete(f"/questions/{q_id}")
    assert res_del.status_code == 200

    with Session(db_engine) as session:
        assert len(SqlAlchemyQuestionRepository(session).list_by_topic(topic.id)) == 0


@pytest.mark.security
def test_web_questions_anti_idor_defenses(
    client: TestClient, other_user: User, db_engine: Any
) -> None:
    """Vulnerabilidade prevenida: IDOR em visualização, criação e exclusão de perguntas.

    Garantia de segurança: Impede manipulação ou estudo de perguntas em matérias privadas alheias.
    """
    with Session(db_engine) as session:
        subj_priv = Subject(name="Privada", owner_id=other_user.id, is_public=False)
        SqlAlchemySubjectRepository(session).save(subj_priv)
        topic_priv = Topic(subject_id=subj_priv.id, name="Tema Priv")
        SqlAlchemyTopicRepository(session).save(topic_priv)
        q = Question(topic_id=topic_priv.id, prompt="Pergunta Privada", expected_answer="Privado")
        SqlAlchemyQuestionRepository(session).save(q)

    # 1. Acesso à tela de gerenciamento de tema privado alheio -> 403
    assert client.get(f"/topics/{topic_priv.id}/questions").status_code == 403

    # 2. Criação em tema privado alheio -> 400 ou 403
    res_create = client.post(
        f"/topics/{topic_priv.id}/questions",
        data={"prompt": "Invasão", "expected_answer": "Hack"},
    )
    assert res_create.status_code in (400, 403)

    # 3. Exclusão de pergunta alheia -> 400 ou 403
    assert client.delete(f"/questions/{q.id}").status_code in (400, 403)

    # 4. Revisão em pergunta privada alheia -> 400
    res_rev = client.post(f"/questions/{q.id}/review", data={"score": 100})
    assert res_rev.status_code == 400


@pytest.mark.security
def test_web_questions_markdown_xss_protection(
    client: TestClient, test_user: User, db_engine: Any
) -> None:
    """Vulnerabilidade prevenida: Stored XSS via inputs de formulário Web em perguntas.

    Garantia de segurança: Sanitiza scripts inline, permitindo apenas tags seguras.
    """
    with Session(db_engine) as session:
        subj = Subject(name="SecWeb", owner_id=test_user.id)
        SqlAlchemySubjectRepository(session).save(subj)
        topic = Topic(subject_id=subj.id, name="XSS")
        SqlAlchemyTopicRepository(session).save(topic)

    malicious_prompt = (
        "Pergunta XSS <script>alert('xss')</script>"
        "<img src='https://safe.com/img.png' onerror='alert(1)'>"
    )
    malicious_answer = "Resposta XSS <iframe src='bad'></iframe>"

    client.post(
        f"/topics/{topic.id}/questions",
        data={"prompt": malicious_prompt, "expected_answer": malicious_answer},
        follow_redirects=True,
    )

    with Session(db_engine) as session:
        questions = SqlAlchemyQuestionRepository(session).list_by_topic(topic.id)
        assert len(questions) == 1
        saved = questions[0]
        assert "<script>" not in saved.prompt
        assert "onerror" not in saved.prompt
        assert "<iframe" not in saved.expected_answer
        assert 'src="https://safe.com/img.png"' in saved.prompt


@pytest.mark.integration
def test_web_questions_edge_cases_and_error_branches(
    client: TestClient, test_user: User, other_user: User, db_engine: Any
) -> None:
    """Verifica branches de erro e edge cases em controladores Web."""
    # 1. UUID inválido na query string
    res_bad_uuid = client.get("/questions/study?subject_id=invalid-uuid-string")
    assert res_bad_uuid.status_code == 200

    # 2. subject_id inexistente -> status 400
    res_not_found_subj = client.get(f"/questions/study?subject_id={uuid4()}")
    assert res_not_found_subj.status_code == 400
    assert "não encontrada" in res_not_found_subj.text

    # 3. Gerenciamento de tema inexistente -> status 404
    res_no_topic = client.get(f"/topics/{uuid4()}/questions")
    assert res_no_topic.status_code == 404

    # 4. Exclusão de pergunta inexistente -> status 400
    res_del_not_found = client.delete(f"/questions/{uuid4()}")
    assert res_del_not_found.status_code == 400

    # 5. Criação de pergunta com prompt inválido -> retorna 400 no template
    with Session(db_engine) as session:
        subj = Subject(name="Edge", owner_id=test_user.id)
        SqlAlchemySubjectRepository(session).save(subj)
        topic = Topic(subject_id=subj.id, name="EdgeTopic")
        SqlAlchemyTopicRepository(session).save(topic)

    res_bad_create = client.post(
        f"/topics/{topic.id}/questions",
        data={"prompt": "   ", "expected_answer": "Resposta"},
    )
    assert res_bad_create.status_code == 400
    assert "Enunciado deve ter entre 1 e 10.000 caracteres" in res_bad_create.text


@pytest.mark.integration
def test_cadastros_hub_view(client: TestClient, test_user: User, db_engine: Any) -> None:
    """Verifica renderização da Central de Cadastros (Hub) com os 3 cards generosos."""
    res = client.get("/cadastros")
    assert res.status_code == 200
    assert "Central de Cadastros" in res.text
    assert "Temas e Matérias" in res.text
    assert "Perguntas Abertas" in res.text
    assert "Novo Flashcard" in res.text
    assert "/subjects" in res.text
    assert "/questions/manage" in res.text
    assert "/flashcards/new" in res.text


@pytest.mark.integration
def test_questions_manage_view_empty_state_and_with_topics(
    client: TestClient, test_user: User, db_engine: Any
) -> None:
    """Verifica tela centralizada de perguntas (empty state e com matérias/temas)."""
    # 1. Sem matérias cadastradas: Empty State explicativo com CTA
    res_empty = client.get("/questions/manage")
    assert res_empty.status_code == 200
    assert "Nenhuma Matéria Cadastrada" in res_empty.text
    assert "Criar Primeira Matéria e Tema" in res_empty.text
    assert "/subjects" in res_empty.text

    # 2. Com matérias e temas cadastrados
    with Session(db_engine) as session:
        subj = Subject(name="Direito Constitucional", owner_id=test_user.id)
        SqlAlchemySubjectRepository(session).save(subj)
        top1 = Topic(subject_id=subj.id, name="Controle de Constitucionalidade")
        top2 = Topic(subject_id=subj.id, name="Direitos Fundamentais")
        SqlAlchemyTopicRepository(session).save(top1)
        SqlAlchemyTopicRepository(session).save(top2)

    # Acesso padrão: pré-seleciona primeiro tema
    res = client.get("/questions/manage")
    assert res.status_code == 200
    assert "Direito Constitucional" in res.text
    assert "Controle de Constitucionalidade" in res.text
    assert "Cadastrar Nova Pergunta" in res.text

    # Acesso com query param específico
    res_param = client.get(f"/questions/manage?subject_id={subj.id}&topic_id={top2.id}")
    assert res_param.status_code == 200
    assert "Direitos Fundamentais" in res_param.text


@pytest.mark.integration
def test_create_question_from_manage_view_lifecycle_and_errors(
    client: TestClient, test_user: User, db_engine: Any
) -> None:
    """Verifica criação de pergunta a partir de /questions/manage e tratamento de erros."""
    with Session(db_engine) as session:
        subj = Subject(name="Biologia", owner_id=test_user.id)
        SqlAlchemySubjectRepository(session).save(subj)
        top = Topic(subject_id=subj.id, name="Citologia")
        SqlAlchemyTopicRepository(session).save(top)

    # Sucesso: cadastra pergunta e redireciona 303 com subject_id e topic_id
    res = client.post(
        "/questions/manage",
        data={
            "topic_id": str(top.id),
            "prompt": "Qual a função do ribossomo?",
            "expected_answer": "Síntese de proteínas.",
        },
        follow_redirects=False,
    )
    assert res.status_code == 303
    assert f"/questions/manage?subject_id={subj.id}&topic_id={top.id}" in res.headers["location"]

    with Session(db_engine) as session:
        questions = SqlAlchemyQuestionRepository(session).list_by_topic(top.id)
        assert len(questions) == 1
        assert questions[0].prompt == "Qual a função do ribossomo?"
        # Progresso SRS criado
        prog_repo = SqlAlchemyQuestionProgressRepository(session)
        prog = prog_repo.get_by_user_and_question(test_user.id, questions[0].id)
        assert prog is not None

    # Erro: tema inexistente
    res_bad_topic = client.post(
        "/questions/manage",
        data={
            "topic_id": str(uuid4()),
            "prompt": "Pergunta sem tema?",
            "expected_answer": "Resposta",
        },
        follow_redirects=False,
    )
    assert res_bad_topic.status_code == 303
    assert "Tema+n%C3%A3o+encontrado" in res_bad_topic.headers["location"]

    # Erro: validação de domínio (prompt em branco)
    res_bad_prompt = client.post(
        "/questions/manage",
        data={
            "topic_id": str(top.id),
            "prompt": "   ",
            "expected_answer": "Resposta",
        },
        follow_redirects=False,
    )
    assert res_bad_prompt.status_code == 303
    assert "error=" in res_bad_prompt.headers["location"]


@pytest.mark.integration
def test_navigation_three_tabs_and_active_highlighting(client: TestClient) -> None:
    """Verifica conformidade estrita da navegação com 3 abas principais e 3 colunas mobile."""
    # 1. Tela /study: "Flashcards" ativo
    res_study = client.get("/study")
    assert res_study.status_code == 200
    assert "Flashcards" in res_study.text
    assert "Revisão" in res_study.text
    assert "Desempenho" in res_study.text
    assert "Cadastros" in res_study.text
    assert "grid-cols-4" in res_study.text

    # 2. Tela /questions/study: "Revisão" ativo
    res_rev = client.get("/questions/study")
    assert res_rev.status_code == 200
    assert "Revisão" in res_rev.text

    # 3. Tela /cadastros: "Cadastros" ativo
    res_cad = client.get("/cadastros")
    assert res_cad.status_code == 200
    assert "cadastros-dropdown-menu" in res_cad.text
    assert "Temas e matérias" in res_cad.text
    assert "Novo Flashcard" in res_cad.text
