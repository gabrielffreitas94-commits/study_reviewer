"""Testes de integração para importação de questões em lote via JSON + Markdown,
botões auxiliares de prompt de IA e renderização de Markdown no Canvas e no Grimoire.
"""

from collections.abc import Generator
from pathlib import Path
from typing import Any
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from src.adapters.persistence.repositories import (
    SqlAlchemyStudyMapRepository,
    SqlAlchemyUserRepository,
)
from src.domain.entities import StudyMap, User
from src.infrastructure.database import Base, get_db
from src.infrastructure.security.dependencies import get_current_user
from src.infrastructure.web.app import app


@pytest.fixture
def test_user() -> User:
    return User(
        id=uuid4(),
        google_sub="sub-json-markdown-tester",
        email="json.markdown@test.com",
        name="Mago do Markdown",
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
def db_session(db_engine: Any) -> Generator[Session]:
    testing_session = sessionmaker(bind=db_engine, autoflush=False, autocommit=False)
    session = testing_session()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture
def authenticated_client(db_session: Session, test_user: User) -> Generator[TestClient]:
    user_repo = SqlAlchemyUserRepository(db_session)
    user_repo.save(test_user)

    def override_get_db() -> Generator[Session]:
        yield db_session

    def override_get_current_user() -> User:
        return test_user

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_current_user] = override_get_current_user

    with TestClient(app) as test_client:
        yield test_client

    app.dependency_overrides.clear()


@pytest.mark.integration
def test_canvas_template_and_js_contain_json_prompt_and_markdown_support(
    authenticated_client: TestClient, db_session: Session, test_user: User
) -> None:
    """Valida se canvas.html e study_canvas.js contêm os elementos de importação JSON e suporte a Markdown."""
    map_repo = SqlAlchemyStudyMapRepository(db_session)
    study_map = StudyMap(
        owner_id=test_user.id,
        title="Árvore de Teste de JSON e Markdown",
        description="Validação de importador e renderizador RPG",
    )
    map_repo.save(study_map)

    # 1. Validação dos elementos no canvas.html
    res = authenticated_client.get(f"/study-maps/{study_map.id}/canvas")
    assert res.status_code == 200
    html = res.text

    assert 'id="btn-copy-ai-json-prompt"' in html
    assert "copyAiJsonPrompt" in html
    assert 'id="copy-ai-prompt-status"' in html
    assert 'id="drawer-bulk-questions-input"' in html
    assert "Importar Questões em Lote (JSON + Markdown)" in html
    assert "expected_answer" in html
    assert "Strategy Pattern" in html

    # 2. Validação dos contratos em study_canvas.js
    js_path = Path("src/adapters/web/static/js/study_canvas.js")
    assert js_path.exists()
    js_code = js_path.read_text(encoding="utf-8")

    assert "copyAiJsonPrompt" in js_code
    assert "JSON.parse" in js_code
    assert "expected_answer" in js_code
    assert "renderRpgMarkdown" in js_code
    assert "renderDrawerQuestions" in js_code
    assert "parseBulkQuestions" in js_code


@pytest.mark.integration
def test_node_grimoire_template_contains_json_prompt_and_markdown_support(
    authenticated_client: TestClient, db_session: Session, test_user: User
) -> None:
    """Valida se node_grimoire.html contém o botão de copiar prompt de IA, suporte a JSON e classes rpg-markdown."""
    map_res = authenticated_client.post(
        "/api/v1/study-maps",
        json={"title": "Grimório com IA", "description": "Validação de Prompt e JSON"},
    )
    assert map_res.status_code == 201
    map_id = map_res.json()["id"]

    node_res = authenticated_client.post(
        f"/api/v1/study-maps/{map_id}/nodes",
        json={"title": "Estruturas de Dados Avançadas", "pos_x": 0, "pos_y": 0, "icon": "scroll"},
    )
    assert node_res.status_code == 201
    node_id = node_res.json()["id"]

    # Cadastra uma questão para ativar a Arena de Estudo
    q_res = authenticated_client.post(
        f"/api/v1/study-maps/{map_id}/nodes/{node_id}/questions",
        json={
            "prompt": "O que é uma B-Tree?",
            "expected_answer": "Árvore balanceada otimizada para armazenamento em bloco.",
        },
    )
    assert q_res.status_code == 201

    res = authenticated_client.get(f"/study-maps/{map_id}/nodes/{node_id}")
    assert res.status_code == 200
    html = res.text

    # Botão de cópia de prompt e textarea
    assert 'id="btn-grimoire-copy-ai-json"' in html
    assert "copyGrimoireAiJsonPrompt" in html
    assert 'id="grimoire-copy-prompt-status"' in html
    assert 'id="paste-questions-textarea"' in html
    assert "importPastedQuestions" in html

    # Elementos de renderização de Markdown
    assert 'id="theory-display-area"' in html
    assert 'id="arena-question-prompt"' in html
    assert 'id="arena-expected-answer"' in html
    assert 'class="rpg-markdown"' in html or "rpg-markdown" in html
    assert 'data-rpg-markdown="true"' in html

    # Validação do código JS embutido no node_grimoire.html
    assert "JSON.parse" in html
    assert "renderRpgMarkdown" in html
    assert "renderCurrentQuestion" in html


@pytest.mark.integration
def test_complex_markdown_questions_batch_persists_and_renders_in_study_arena(
    authenticated_client: TestClient,
) -> None:
    """Valida o envio e persistência de perguntas com Markdown rico (código, tabelas, headers)

    via POST /questions/batch e a renderização nas Provações Diárias (/questions/study).
    """
    # 1. Cria Mapa e Nó
    map_res = authenticated_client.post(
        "/api/v1/study-maps",
        json={"title": "Árvore de Algoritmos", "description": "Estudo de Complexidade"},
    )
    assert map_res.status_code == 201
    map_id = map_res.json()["id"]

    node_res = authenticated_client.post(
        f"/api/v1/study-maps/{map_id}/nodes",
        json={"title": "Teoria de Grafos", "pos_x": 100, "pos_y": 100, "icon": "brain"},
    )
    assert node_res.status_code == 201
    node_id = node_res.json()["id"]

    # 2. Pergunta com Markdown rico (headers, código Python, lista com negrito e tabela)
    complex_prompt = (
        "### Qual a complexidade e funcionamento do algoritmo **Dijkstra**?\n\n"
        "Considere a implementação padrão em Python:\n"
        "```python\n"
        "import heapq\n"
        "def dijkstra(graph, start):\n"
        "    dist = {start: 0}\n"
        "    pq = [(0, start)]\n"
        "    return dist\n"
        "```\n"
        "| Estrutura | Custo Inserção |\n"
        "| :--- | :--- |\n"
        "| Min-Heap Binária | O(log V) |\n"
    )
    complex_answer = (
        "### Critérios Técnicos:\n"
        "- **Tempo Total:** `O((V + E) \\log V)` usando heap binária.\n"
        "- **Espaço:** `O(V)` para vetor de distâncias.\n"
        "> Nota: Pesos de arestas negativos exigem **Bellman-Ford**!"
    )

    # 3. Envia para o endpoint de batch (formato JSON utilizado pelo importador do Canvas e Grimoire)
    batch_res = authenticated_client.post(
        f"/api/v1/study-maps/{map_id}/nodes/{node_id}/questions/batch",
        json={
            "questions": [
                {
                    "prompt": complex_prompt,
                    "expected_answer": complex_answer,
                }
            ]
        },
    )
    assert batch_res.status_code == 201
    created_list = batch_res.json()
    assert len(created_list) == 1
    created_q = created_list[0]

    # Verifica integridade do Markdown persistido
    assert "```python" in created_q["prompt"]
    assert "def dijkstra(graph, start):" in created_q["prompt"]
    assert "| Min-Heap Binária | O(log V) |" in created_q["prompt"]
    assert "### Critérios Técnicos:" in created_q["expected_answer"]
    assert "**Tempo Total:**" in created_q["expected_answer"]

    # 4. Acessa a página de Provações Diárias (Daily SRS Arena)
    study_res = authenticated_client.get("/questions/study")
    assert study_res.status_code == 200
    study_html = study_res.text

    # Verifica que a pergunta aparece na sessão de estudo do usuário
    assert "Dijkstra" in study_html
    assert "dijkstra(graph, start)" in study_html or "Min-Heap" in study_html

    # 5. Acessa a página do Grimório do Nó e valida que a pergunta aparece lá
    grimoire_res = authenticated_client.get(f"/study-maps/{map_id}/nodes/{node_id}")
    assert grimoire_res.status_code == 200
    grimoire_html = grimoire_res.text

    assert "Dijkstra" in grimoire_html
    assert "def dijkstra(graph, start):" in grimoire_html
    assert 'class="rpg-markdown"' in grimoire_html or "rpg-markdown" in grimoire_html
