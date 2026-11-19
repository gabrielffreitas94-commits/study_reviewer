"""Testes de integração End-to-End para Edição Inline de Pergunta e Gabarito na Fila Diária SRS.

Cobre o ciclo de vida completo:
1. Criação de Matéria (Pública), Tema e Pergunta pelo Usuário A.
2. Acesso à fila diária de revisão (/questions/study) pelo Usuário A:
   - Exibição do botão sutil de edição e modal acessível (WCAG 2.1 AA).
   - Validação dos atributos de acessibilidade (aria-haspopup, aria-expanded, role, aria-modal).
   - Pré-carregamento dos textareas de edição com prompt e gabarito atuais.
3. Edição inline via PUT /api/v1/questions/{question_id} com Markdown rico:
   - Blocos de código com linguagem especificada.
   - Listas com negrito.
   - Tabelas estruturadas em Markdown.
   - Callout blockquotes.
   - Higienização e persistência no banco de dados.
4. Renderização reativa do Markdown atualizado nas Provações Diárias (/questions/study):
   - Presença dos nós rpg-markdown e atributos data-rpg-markdown="true".
   - Atualização do conteúdo do prompt e gabarito.
5. Isolamento e Segurança com Usuário B (não-proprietário):
   - Acesso de leitura à fila diária sem os controles de edição (botão e modal ocultos).
   - Bloqueio de tentativa de edição arbitrária via PUT (HTTP 403 Forbidden com erro de propriedade).
6. Proteção adicional contra XSS malicioso e validação defensiva de payloads.
"""

from collections.abc import Generator
from datetime import date
from typing import Any
from uuid import UUID, uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from src.adapters.persistence.repositories import (
    SqlAlchemyQuestionProgressRepository,
    SqlAlchemyQuestionRepository,
    SqlAlchemyUserRepository,
)
from src.domain.entities import User, UserQuestionProgress
from src.infrastructure.database import Base, get_db
from src.infrastructure.security.dependencies import get_current_user
from src.infrastructure.security.rate_limiter import reset_rate_limits
from src.infrastructure.web.app import app


@pytest.fixture
def user_a() -> User:
    return User(
        id=uuid4(),
        google_sub="sub-user-a-e2e-edit",
        email="user_a.editor@studyreviewer.local",
        name="Arquiteto Usuário A",
    )


@pytest.fixture
def user_b() -> User:
    return User(
        id=uuid4(),
        google_sub="sub-user-b-e2e-edit",
        email="user_b.reader@studyreviewer.local",
        name="Estudante Usuário B",
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
def client(db_engine: Any, user_a: User, user_b: User) -> Generator[TestClient]:
    TestingSession = sessionmaker(bind=db_engine)

    with TestingSession() as session:
        u_repo = SqlAlchemyUserRepository(session)
        u_repo.save(user_a)
        u_repo.save(user_b)
        session.commit()

    def override_get_db() -> Generator[Session]:
        session = TestingSession()
        try:
            yield session
        finally:
            session.close()

    def override_get_current_user() -> User:
        return user_a

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_current_user] = override_get_current_user
    reset_rate_limits()

    with TestClient(app, raise_server_exceptions=False) as test_client:
        yield test_client

    app.dependency_overrides.clear()
    reset_rate_limits()


@pytest.mark.integration
def test_daily_srs_question_inline_edit_full_lifecycle_and_security(
    client: TestClient, user_a: User, user_b: User, db_engine: Any
) -> None:
    """Verifica o ciclo de vida completo da edição inline com Markdown rico e isolamento de segurança."""
    # 1. Usuário A cria Matéria Pública, Tema e Pergunta inicial via API REST
    res_sub = client.post(
        "/api/v1/subjects",
        json={"name": "Engenharia de Software e Arquitetura", "is_public": True},
    )
    assert res_sub.status_code == 201
    subject_id = res_sub.json()["id"]

    res_top = client.post(
        "/api/v1/topics",
        json={"subject_id": subject_id, "name": "Padrões Arquiteturais"},
    )
    assert res_top.status_code == 201
    topic_id = res_top.json()["id"]

    initial_prompt = "O que caracteriza uma Arquitetura Limpa (Clean Architecture)?"
    initial_answer = (
        "Independência de frameworks, testabilidade e separação por camadas concêntricas."
    )
    res_q = client.post(
        f"/api/v1/topics/{topic_id}/questions",
        json={"prompt": initial_prompt, "expected_answer": initial_answer},
    )
    assert res_q.status_code == 201
    question_id = res_q.json()["id"]

    # 2. Usuário A acessa a fila de estudo diária (/questions/study)
    res_study_a = client.get("/questions/study")
    assert res_study_a.status_code == 200
    html_a = res_study_a.text

    # Verifica presença do botão sutil de edição e seus atributos de acessibilidade
    assert 'id="btn-edit-question-modal"' in html_a
    assert 'aria-haspopup="dialog"' in html_a
    assert 'aria-expanded="false"' in html_a
    assert 'aria-controls="edit-question-modal"' in html_a

    # Verifica presença do modal acessível e seus atributos WCAG 2.1 AA
    assert 'id="edit-question-modal"' in html_a
    assert 'role="dialog"' in html_a
    assert 'aria-modal="true"' in html_a
    assert 'aria-labelledby="edit-question-modal-title"' in html_a
    assert 'aria-describedby="edit-question-modal-description"' in html_a

    # Verifica campos textareas pré-carregados com prompt e gabarito atuais
    assert 'id="edit-question-prompt"' in html_a
    assert initial_prompt in html_a
    assert 'id="edit-question-expected-answer"' in html_a
    assert initial_answer in html_a

    # 3. Usuário A realiza edição inline com Markdown rico via PUT /api/v1/questions/{question_id}
    rich_prompt = (
        "### Avaliação Arquitetural de Sistema\n\n"
        "Analise o seguinte trecho de código em Python:\n"
        "```python\n"
        "def calculate_metrics(code: str) -> dict[str, int]:\n"
        "    return {'complexity': 1, 'lines': len(code.splitlines())}\n"
        "```\n\n"
        "Classifique os seguintes critérios essenciais:\n"
        "- **DIP:** Inversão de dependência através de abstrações\n"
        "- **SRP:** Responsabilidade única por módulo de domínio\n\n"
        "| Critério | Peso | Prioridade |\n"
        "| :--- | :--- | :--- |\n"
        "| Desacoplamento | Alto | Crítica |\n"
        "| Coesão | Médio | Alta |\n\n"
        "> [!NOTE]\n"
        "> A arquitetura deve isolar frameworks de regras de negócio essenciais."
    )

    rich_answer = (
        "### Gabarito e Diretrizes Técnicas:\n\n"
        "1. **Código Corrigido:**\n"
        "```python\n"
        "class MetricCalculator:\n"
        "    def compute(self, lines: list[str]) -> int:\n"
        "        return len(lines)\n"
        "```\n\n"
        "2. **Critérios de Avaliação:**\n"
        "- **Isolamento de Domínio:** Entidades desconhecem banco de dados e UI.\n"
        "- **Inversão de Controle:** Uso de interfaces abstratas.\n\n"
        "| Item Avaliado | Resultado Esperado |\n"
        "| :--- | :--- |\n"
        "| Camadas Limpas | Aprovado |\n"
        "| Testabilidade | 100% |\n\n"
        "> [!TIP]\n"
        "> Utilize injeção de dependências para viabilizar testes unitários em memória."
    )

    res_put = client.put(
        f"/api/v1/questions/{question_id}",
        json={"prompt": rich_prompt, "expected_answer": rich_answer},
    )
    assert res_put.status_code == 200
    put_data = res_put.json()
    assert put_data["id"] == question_id
    assert "```python" in put_data["prompt"]
    assert "def calculate_metrics" in put_data["prompt"]
    assert "- **DIP:**" in put_data["prompt"]
    assert "| Critério | Peso | Prioridade |" in put_data["prompt"]
    assert "[!NOTE]" in put_data["prompt"]

    assert "### Gabarito e Diretrizes Técnicas:" in put_data["expected_answer"]
    assert "```python" in put_data["expected_answer"]
    assert "- **Isolamento de Domínio:**" in put_data["expected_answer"]
    assert "| Item Avaliado | Resultado Esperado |" in put_data["expected_answer"]
    assert "[!TIP]" in put_data["expected_answer"]

    # 4. Usuário A requisita novamente GET /questions/study e valida renderização reativa
    res_study_a_updated = client.get("/questions/study")
    assert res_study_a_updated.status_code == 200
    html_a_updated = res_study_a_updated.text

    # Verifica presença do prompt e gabarito atualizados no HTML
    assert "calculate_metrics" in html_a_updated
    assert "Avaliação Arquitetural de Sistema" in html_a_updated
    assert "Gabarito e Diretrizes Técnicas" in html_a_updated
    assert "Critério" in html_a_updated

    # Verifica classes rpg-markdown e atributos data-rpg-markdown="true"
    assert "rpg-markdown" in html_a_updated
    assert 'data-rpg-markdown="true"' in html_a_updated
    assert 'id="question-prompt"' in html_a_updated
    assert 'id="expected-answer-content"' in html_a_updated

    # Verifica textareas no modal do Usuário A com o novo conteúdo atualizado
    assert "calculate_metrics" in html_a_updated
    assert "MetricCalculator" in html_a_updated

    # 5. Configura progresso de estudo para Usuário B na matéria pública
    TestingSession = sessionmaker(bind=db_engine)
    with TestingSession() as session:
        SqlAlchemyQuestionProgressRepository(session).save(
            UserQuestionProgress(
                user_id=user_b.id,
                question_id=UUID(question_id),
                current_level=0,
                next_review_date=date.today(),
            )
        )
        session.commit()

    # Alterna o usuário autenticado para Usuário B (estudante/não-proprietário)
    app.dependency_overrides[get_current_user] = lambda: user_b

    res_study_b = client.get("/questions/study")
    assert res_study_b.status_code == 200
    html_b = res_study_b.text

    # O Usuário B visualiza a pergunta com o Markdown rico
    assert "calculate_metrics" in html_b
    assert "rpg-markdown" in html_b
    assert 'data-rpg-markdown="true"' in html_b

    # Controles de edição NÃO devem ser renderizados para o Usuário B
    assert 'id="btn-edit-question-modal"' not in html_b
    assert "btn-edit-question-modal" not in html_b
    assert 'id="edit-question-modal"' not in html_b

    # 6. Usuário B tenta editar a pergunta via PUT -> HTTP 403 Forbidden com erro de propriedade
    res_b_put = client.put(
        f"/api/v1/questions/{question_id}",
        json={
            "prompt": "Tentativa de injeção e adulteração pelo Usuário B",
            "expected_answer": "Gabarito adulterado indevidamente",
        },
    )
    assert res_b_put.status_code == 403
    assert "Apenas o proprietário da matéria pode editar a pergunta." in res_b_put.json()["detail"]


@pytest.mark.integration
def test_daily_srs_question_inline_edit_sanitization_defense(
    client: TestClient, user_a: User
) -> None:
    """Garante que tags perigosas (<script>, onerror inline) sejam higienizadas durante edição inline."""
    # Cria matéria, tema e pergunta
    res_sub = client.post(
        "/api/v1/subjects",
        json={"name": "Segurança de Software", "is_public": False},
    )
    assert res_sub.status_code == 201
    subject_id = res_sub.json()["id"]

    res_top = client.post(
        "/api/v1/topics",
        json={"subject_id": subject_id, "name": "Prevenção XSS"},
    )
    assert res_top.status_code == 201
    topic_id = res_top.json()["id"]

    res_q = client.post(
        f"/api/v1/topics/{topic_id}/questions",
        json={
            "prompt": "Defina Cross-Site Scripting (XSS).",
            "expected_answer": "Injeção de scripts maliciosos em aplicações web.",
        },
    )
    assert res_q.status_code == 201
    question_id = res_q.json()["id"]

    # Edição inline com tentativa de injeção de script misturado com Markdown válido
    dirty_prompt = (
        "### Teste de Injeção XSS\n\n"
        "<script>alert('pwned')</script>\n"
        "Considere o código seguro:\n"
        "```python\n"
        "clean = sanitize(input_str)\n"
        "```\n"
        '<img src="x" onerror="alert(\'malicious\')">'
    )
    dirty_answer = (
        "### Resposta com tags seguras e scripts maliciosos:\n"
        "<strong>Texto em negrito permitido</strong>\n"
        "<script type=\"text/javascript\">window.location='http://evil.com'</script>\n"
        "- **Lista segura** com item válido."
    )

    res_put = client.put(
        f"/api/v1/questions/{question_id}",
        json={"prompt": dirty_prompt, "expected_answer": dirty_answer},
    )
    assert res_put.status_code == 200
    cleaned_data = res_put.json()

    # Valida neutralização de scripts e manipuladores maliciosos
    assert "<script" not in cleaned_data["prompt"]
    assert "alert('pwned')" not in cleaned_data["prompt"]
    assert "onerror=" not in cleaned_data["prompt"]

    assert "<script" not in cleaned_data["expected_answer"]
    assert "evil.com" not in cleaned_data["expected_answer"]

    # Valida preservação de Markdown e tags permitidas
    assert "```python" in cleaned_data["prompt"]
    assert "clean = sanitize(input_str)" in cleaned_data["prompt"]
    assert "<strong>Texto em negrito permitido</strong>" in cleaned_data["expected_answer"]
    assert "- **Lista segura**" in cleaned_data["expected_answer"]


@pytest.mark.integration
def test_daily_srs_question_inline_edit_validation_errors(
    client: TestClient, user_a: User, db_engine: Any
) -> None:
    """Verifica que payloads vazios, inválidos ou inconsistentes são rejeitados com 400 ou 422."""
    res_sub = client.post(
        "/api/v1/subjects",
        json={"name": "Validação de Entrada", "is_public": False},
    )
    assert res_sub.status_code == 201
    subject_id = res_sub.json()["id"]

    res_top = client.post(
        "/api/v1/topics",
        json={"subject_id": subject_id, "name": "Regras de Validação"},
    )
    assert res_top.status_code == 201
    topic_id = res_top.json()["id"]

    res_q = client.post(
        f"/api/v1/topics/{topic_id}/questions",
        json={"prompt": "Pergunta de Teste Válida", "expected_answer": "Gabarito Válido"},
    )
    assert res_q.status_code == 201
    question_id = res_q.json()["id"]

    # 1. Prompt em branco (somente espaços) pós sanitização -> 400 Bad Request
    res_empty_prompt = client.put(
        f"/api/v1/questions/{question_id}",
        json={"prompt": "    ", "expected_answer": "Gabarito mantido"},
    )
    assert res_empty_prompt.status_code in (400, 422)

    # 2. Resposta esperada em branco -> 400 ou 422
    res_empty_answer = client.put(
        f"/api/v1/questions/{question_id}",
        json={"prompt": "Enunciado mantido", "expected_answer": "   "},
    )
    assert res_empty_answer.status_code in (400, 422)

    # 3. ID inexistente -> 404 Not Found
    res_not_found = client.put(
        f"/api/v1/questions/{uuid4()}",
        json={"prompt": "Enunciado novo", "expected_answer": "Gabarito novo"},
    )
    assert res_not_found.status_code == 404

    # 4. Garante que os dados originais no banco não foram corrompidos
    TestingSession = sessionmaker(bind=db_engine)
    with TestingSession() as session:
        original = SqlAlchemyQuestionRepository(session).get_by_id(UUID(question_id))
        assert original is not None
        assert original.prompt == "Pergunta de Teste Válida"
        assert original.expected_answer == "Gabarito Válido"
