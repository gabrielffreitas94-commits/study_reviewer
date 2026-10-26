# Códice RPG (Grimório & Forja Ancestral) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Unificar o Study Reviewer em torno da Árvore de Habilidades RPG (`StudyMap` $\to$ `StudyNode`), criando a Página Dedicada do Nó em tela cheia (**📖 Tomo de Sabedoria** à esquerda + **⚔️ Provações de Maestria SRS** à direita), removendo os fluxos desconectados de Flashcards/Cadastros/Sub-mapas e aplicando a identidade visual **Grimório & Forja Ancestral** (*Baldur's Gate 3 / Path of Exile*).

**Architecture:** Clean Architecture em 4 camadas (`src/domain`, `src/application`, `src/adapters`, `src/infrastructure`). `StudyNode` passa a conter `theory_content` diretamente e se relaciona 1:N com `KnowledgeSource` (com `raw_text` legível) e `Question` (avaliada no motor SRS de 7 níveis `[1, 7, 15, 30, 60, 90, 180]` dias). O frontend utiliza Jinja2 + CSS RPG customizado (`Cinzel` + `Cormorant Garamond`) + JS nativo (`study_canvas.js` e `node_grimoire.html`).

**Tech Stack:** Python 3.13+, FastAPI, SQLAlchemy 2.0, Alembic, Jinja2, HTMX, Vanilla JS + SVG, Pytest.

**Spec:** `docs/superpowers/specs/2026-10-26-rpg-grimoire-clean-architecture-design.md`

## Global Constraints

- Manter separação estrita da Clean Architecture (`src/domain` sem imports de ORM ou FastAPI).
- Paleta visual obrigatória **Grimório & Forja Ancestral**: obsidiana (`#0c0908`, `#14100d`), pergaminho escuro (`#1c1612`), bronze forjado (`#785a28`), ouro ancestral (`#c89b3c`, `#f0c869`), esmeralda (`#10b981`) e carmesim (`#e11d48`), com fontes `Cinzel` e `Cormorant Garamond`.
- Navegação principal em `base.html` enxuta com 3 itens: `⚔️ Códice de Habilidades` (`/study-maps`), `🔥 Provações Diárias` (`/questions/study`) e `🏆 Crônicas & Atributos` (`/performance`).
- Nível efetivo do nó (`effective_level`) é `min(current_level)` de todas as perguntas associadas ao nó (ou `0` se não houver perguntas). Nós dependentes desbloqueiam quando todos os pré-requisitos atingem `effective_level >= 1`.

## Review Focus

- Responder na Página do Nó uma pergunta que já foi revisada hoje (`next_review_date > today`) não deve retornar erro 400 bloqueante: deve operar em **Modo Treino Livre** (`is_training_only=True`), mantendo o nível e a data de próxima revisão SRS intactos.
- Salvar `theory_content` vazio ou apenas espaços em branco num nó deve limpar o texto sem quebrar com erro de chunking.
- Criar uma pergunta diretamente na Página do Nó deve inicializar imediatamente o `UserQuestionProgress` em `current_level=0` com `next_review_date=today` e recalcular o `effective_level` do nó.
- Nós com ícones diversos (`calculator`, `trending-up`, `dice`, `activity`, `rune`, `sword`, `book`, `gem`, `brain`, `scroll`, `flask`, `shield`, `fire`, `code`) devem todos possuir glifo válido no Canvas e na Página do Nó.
- Ao responder a última pergunta pendente de um nó com nota `100`, o retorno JSON deve informar `node_effective_level >= 1` para atualizar o HUD da Página do Nó sem precisar recarregar outra tela.

---

### Task 1: Domínio, Persistência e Migração do Nó Unificado (`theory_content`, `raw_text` e vínculo direto ao `StudyNode`)

**Files:**
- Modify: `src/domain/entities.py`
- Modify: `src/adapters/persistence/models.py`
- Modify: `src/adapters/persistence/mappers.py`
- Modify: `src/adapters/persistence/repositories.py`
- Modify: `src/application/ports/repositories.py`
- Create: `alembic/versions/d4e5f6a7b8c9_unify_rpg_grimoire_node_schema.py`
- Test: `tests/unit/domain/test_rpg_grimoire_entities.py`

**Interfaces:**
- Produces:
  - `StudyNode(map_id: UUID, title: str, description: str | None = None, theory_content: str = "", pos_x: float = 0.0, pos_y: float = 0.0, icon: str = "brain", ...)` with `update_theory(content: str) -> None`
  - `KnowledgeSource(..., raw_text: str = "", node_id: UUID | None = None)`
  - `Question(..., node_id: UUID | None = None)` (`topic_ids` optional when `node_id` is provided)
  - `SqlAlchemyQuestionRepository.list_by_node(node_id: UUID) -> list[Question]`
  - `SqlAlchemyKnowledgeSourceRepository.list_by_node(node_id: UUID) -> list[KnowledgeSource]`

- [ ] **Step 1: Write the failing test in `tests/unit/domain/test_rpg_grimoire_entities.py`**

```python
from uuid import uuid4
from src.domain.entities import KnowledgeSource, Question, StudyNode


def test_study_node_holds_and_updates_theory_content() -> None:
    node = StudyNode(
        map_id=uuid4(),
        title="Álgebra Linear",
        theory_content="  Matrizes ortogonais preservam normas.  ",
    )
    assert node.theory_content == "Matrizes ortogonais preservam normas."
    node.update_theory("Decomposição SVD e autovalores.")
    assert node.theory_content == "Decomposição SVD e autovalores."
    node.update_theory("   ")
    assert node.theory_content == ""


def test_question_and_knowledge_source_accept_direct_node_id() -> None:
    node_id = uuid4()
    q = Question(
        prompt="O que é uma matriz ortogonal?",
        expected_answer="Uma matriz Q tal que Q^T Q = I.",
        node_id=node_id,
    )
    assert q.node_id == node_id
    assert q.prompt == "O que é uma matriz ortogonal?"

    src = KnowledgeSource(
        title="Pergaminho de Matrizes",
        node_id=node_id,
        raw_text="Texto integral do pergaminho para leitura no Tomo.",
        content_type="TEXT",
    )
    assert src.node_id == node_id
    assert src.raw_text == "Texto integral do pergaminho para leitura no Tomo."
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/unit/domain/test_rpg_grimoire_entities.py -v`
Expected: FAIL with `TypeError: StudyNode.__init__() got an unexpected keyword argument 'theory_content'`

- [ ] **Step 3: Implement domain entities, ORM models, mappers, repositories, and Alembic migration**

Update `StudyNode`, `Question`, and `KnowledgeSource` in `src/domain/entities.py` so:
- `StudyNode` has `theory_content: str = ""` and `update_theory(self, content: str) -> None`.
- `Question` accepts `node_id: UUID | None = None`; if `node_id` is set and `topic_ids` is empty, `topic_ids` defaults to `(node_id,)` so existing invariants remain satisfied without requiring a legacy `Topic`.
- `KnowledgeSource` accepts `node_id: UUID | None = None` and `raw_text: str = ""`; if `node_id` is set and `topic_ids` is empty, `topic_ids` defaults to `(node_id,)`.
- In `src/adapters/persistence/models.py`, add `theory_content: Mapped[str] = mapped_column(Text, nullable=False, default="")` to `StudyNodeModel`, `node_id: Mapped[UUID | None] = mapped_column(Uuid, ForeignKey("study_nodes.id", ondelete="CASCADE"), nullable=True, index=True)` and `raw_text: Mapped[str] = mapped_column(Text, nullable=False, default="")` to `KnowledgeSourceModel`, and `node_id: Mapped[UUID | None] = mapped_column(Uuid, ForeignKey("study_nodes.id", ondelete="CASCADE"), nullable=True, index=True)` to `QuestionModel`.
- Update `StudyNodeMapper`, `QuestionMapper`, `KnowledgeSourceMapper` in `src/adapters/persistence/mappers.py`, and add `list_by_node(self, node_id: UUID)` to `SqlAlchemyQuestionRepository` and `SqlAlchemyKnowledgeSourceRepository` in `src/adapters/persistence/repositories.py` (querying both `node_id == node_id` and `NodeQuestionModel` / `NodeKnowledgeSourceModel` union).
- Create migration `alembic/versions/d4e5f6a7b8c9_unify_rpg_grimoire_node_schema.py` adding `theory_content` to `study_nodes`, `node_id` and `raw_text` to `knowledge_sources`, and `node_id` to `questions`.

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/unit/domain/test_rpg_grimoire_entities.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/domain/entities.py src/application/ports/repositories.py src/adapters/persistence/models.py src/adapters/persistence/mappers.py src/adapters/persistence/repositories.py alembic/versions/d4e5f6a7b8c9_unify_rpg_grimoire_node_schema.py tests/unit/domain/test_rpg_grimoire_entities.py
git commit -m "feat(domain,persistence): add node theory_content, raw_text, and direct node_id bindings"
```

---

### Task 2: Casos de Uso do Grimório do Nó (Tomo, Forja de Provações SRS Diretas, Treino Livre e Árvore Modelo)

**Files:**
- Modify: `src/application/dto/study_tree_dto.py`
- Modify: `src/application/use_cases/study_tree_use_cases.py`
- Modify: `src/application/use_cases/sample_study_map_use_case.py`
- Test: `tests/unit/application/test_node_grimoire_use_cases.py`

**Interfaces:**
- Consumes: `StudyNode`, `Question`, `KnowledgeSource` from Task 1.
- Produces:
  - `UpdateNodeTheoryUseCase.execute(map_id: UUID, node_id: UUID, user_id: UUID, theory_content: str) -> StudyNodeDTO`
  - `CreateNodeQuestionUseCase.execute(map_id: UUID, node_id: UUID, user_id: UUID, prompt: str, expected_answer: str) -> dict[str, Any]`
  - `DeleteNodeQuestionUseCase.execute(map_id: UUID, node_id: UUID, user_id: UUID, question_id: UUID) -> None`
  - `ReviewNodeQuestionUseCase.execute(map_id: UUID, node_id: UUID, user_id: UUID, question_id: UUID, score: int) -> dict[str, Any]` (returns `previous_level`, `new_level`, `next_review_date`, `interval_days`, `is_promoted`, `is_training_only`, `node_effective_level`, `node_is_mastered`)
  - `CreateNodeMaterialUseCase.execute(map_id: UUID, node_id: UUID, user_id: UUID, title: str, raw_text: str, content_type: str = "TEXT") -> dict[str, Any]`

- [ ] **Step 1: Write the failing test in `tests/unit/application/test_node_grimoire_use_cases.py`**

```python
from datetime import date
from uuid import uuid4
from sqlalchemy.orm import Session
from src.adapters.persistence.repositories import (
    SqlAlchemyKnowledgeSourceRepository,
    SqlAlchemyNodeContentRepository,
    SqlAlchemyQuestionProgressRepository,
    SqlAlchemyQuestionRepository,
    SqlAlchemyStudyEdgeRepository,
    SqlAlchemyStudyMapRepository,
    SqlAlchemyStudyNodeRepository,
)
from src.application.dto.study_tree_dto import CreateStudyMapDTO, CreateStudyNodeDTO
from src.application.use_cases.study_tree_use_cases import (
    CreateNodeQuestionUseCase,
    CreateStudyMapUseCase,
    CreateStudyNodeUseCase,
    ReviewNodeQuestionUseCase,
    UpdateNodeTheoryUseCase,
)
from src.domain.entities import User


def test_node_grimoire_lifecycle_theory_question_and_free_training(db_session: Session) -> None:
    user_id = uuid4()
    map_repo = SqlAlchemyStudyMapRepository(db_session)
    node_repo = SqlAlchemyStudyNodeRepository(db_session)
    content_repo = SqlAlchemyNodeContentRepository(db_session)
    q_repo = SqlAlchemyQuestionRepository(db_session)
    prog_repo = SqlAlchemyQuestionProgressRepository(db_session)

    study_map = CreateStudyMapUseCase(map_repo, node_repo).execute(
        owner_id=user_id,
        dto=CreateStudyMapDTO(title="Grimório de Cálculo"),
    )
    node = CreateStudyNodeUseCase(map_repo, node_repo).execute(
        map_id=study_map.id,
        user_id=user_id,
        dto=CreateStudyNodeDTO(title="Derivadas Parciais", icon="scroll"),
    )

    updated = UpdateNodeTheoryUseCase(map_repo, node_repo).execute(
        map_id=study_map.id,
        node_id=node.id,
        user_id=user_id,
        theory_content="O gradiente aponta na direção de maior crescimento.",
    )
    assert updated.theory_content == "O gradiente aponta na direção de maior crescimento."

    created_q = CreateNodeQuestionUseCase(
        map_repo=map_repo,
        node_repo=node_repo,
        question_repo=q_repo,
        progress_repo=prog_repo,
        content_repo=content_repo,
    ).execute(
        map_id=study_map.id,
        node_id=node.id,
        user_id=user_id,
        prompt="Para onde aponta o vetor gradiente?",
        expected_answer="Direção de máxima taxa de crescimento.",
    )
    assert created_q["current_level"] == 0

    review_uc = ReviewNodeQuestionUseCase(
        map_repo=map_repo,
        node_repo=node_repo,
        question_repo=q_repo,
        progress_repo=prog_repo,
        content_repo=content_repo,
    )
    first_res = review_uc.execute(
        map_id=study_map.id,
        node_id=node.id,
        user_id=user_id,
        question_id=created_q["id"],
        score=100,
    )
    assert first_res["new_level"] == 1
    assert first_res["is_training_only"] is False
    assert first_res["node_effective_level"] == 1
    assert first_res["node_is_mastered"] is True

    # Segunda resposta no mesmo dia deve operar em Modo Treino Livre sem erro
    second_res = review_uc.execute(
        map_id=study_map.id,
        node_id=node.id,
        user_id=user_id,
        question_id=created_q["id"],
        score=50,
    )
    assert second_res["is_training_only"] is True
    assert second_res["new_level"] == 1
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/unit/application/test_node_grimoire_use_cases.py -v`
Expected: FAIL with `ImportError: cannot import name 'UpdateNodeTheoryUseCase'`

- [ ] **Step 3: Implement Node Grimoire use cases and update `CreateSampleMathStudyMapUseCase`**

In `src/application/dto/study_tree_dto.py` and `src/application/use_cases/study_tree_use_cases.py`:
- Add `theory_content: str = ""` to `StudyNodeDTO` and `CreateStudyNodeDTO` / `UpdateStudyNodeDTO`.
- Implement `UpdateNodeTheoryUseCase`, `CreateNodeQuestionUseCase`, `DeleteNodeQuestionUseCase`, `ReviewNodeQuestionUseCase`, `CreateNodeMaterialUseCase`, and `DeleteNodeMaterialUseCase`.
- Update `GetNodeStudyHubUseCase` so `materials` includes `"raw_text": m.raw_text` and `node` includes `"theory_content": node.theory_content`.
- Update `CreateSampleMathStudyMapUseCase` in `src/application/use_cases/sample_study_map_use_case.py` so each of the 5 Applied Math nodes receives rich `theory_content` (Markdown/formatted academic text), `raw_text` in its `KnowledgeSource`, and `node_id` on its `Question`s and `KnowledgeSource`s.

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/unit/application/test_node_grimoire_use_cases.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/application/dto/study_tree_dto.py src/application/use_cases/study_tree_use_cases.py src/application/use_cases/sample_study_map_use_case.py tests/unit/application/test_node_grimoire_use_cases.py
git commit -m "feat(application): implement node grimoire use cases, free training mode, and rich sample math tome"
```

---

### Task 3: Rotas API e Controlador Web da Página Dedicada do Nó (`/study-maps/{map_id}/nodes/{node_id}`)

**Files:**
- Modify: `src/adapters/api/study_tree_controllers.py`
- Modify: `src/adapters/web/study_tree_web_controllers.py`
- Modify: `src/adapters/web/controllers.py`
- Test: `tests/integration/test_node_grimoire_api_and_web.py`

**Interfaces:**
- Consumes: `UpdateNodeTheoryUseCase`, `CreateNodeQuestionUseCase`, `DeleteNodeQuestionUseCase`, `ReviewNodeQuestionUseCase`, `CreateNodeMaterialUseCase`, `DeleteNodeMaterialUseCase`, `GetNodeStudyHubUseCase` from Task 2.
- Produces:
  - `GET /study-maps/{map_id}/nodes/{node_id}` (renders `study_tree/node_grimoire.html`)
  - `PATCH /api/v1/study-maps/{map_id}/nodes/{node_id}/theory`
  - `POST /api/v1/study-maps/{map_id}/nodes/{node_id}/questions`
  - `DELETE /api/v1/study-maps/{map_id}/nodes/{node_id}/questions/{question_id}`
  - `POST /api/v1/study-maps/{map_id}/nodes/{node_id}/questions/{question_id}/review`
  - `POST /api/v1/study-maps/{map_id}/nodes/{node_id}/materials`
  - `DELETE /api/v1/study-maps/{map_id}/nodes/{node_id}/materials/{source_id}`

- [ ] **Step 1: Write the failing test in `tests/integration/test_node_grimoire_api_and_web.py`**

```python
from fastapi.testclient import TestClient


def test_node_grimoire_api_endpoints_and_dedicated_page(authenticated_client: TestClient) -> None:
    # 1. Cria árvore e nó
    map_res = authenticated_client.post(
        "/api/v1/study-maps",
        json={"title": "Códice de Física", "description": "Mecânica Clássica"},
    )
    assert map_res.status_code == 201
    map_id = map_res.json()["id"]

    node_res = authenticated_client.post(
        f"/api/v1/study-maps/{map_id}/nodes",
        json={"title": "Leis de Newton", "icon": "sword", "pos_x": 100, "pos_y": 100},
    )
    assert node_res.status_code == 201
    node_id = node_res.json()["id"]

    # 2. Salva teoria no Tomo do Nó
    theory_res = authenticated_client.patch(
        f"/api/v1/study-maps/{map_id}/nodes/{node_id}/theory",
        json={"theory_content": "A resultante das forças é F = m * a."},
    )
    assert theory_res.status_code == 200
    assert theory_res.json()["theory_content"] == "A resultante das forças é F = m * a."

    # 3. Cria provação SRS diretamente no Nó
    q_res = authenticated_client.post(
        f"/api/v1/study-maps/{map_id}/nodes/{node_id}/questions",
        json={
            "prompt": "Enuncie a Segunda Lei de Newton.",
            "expected_answer": "A força resultante é igual à taxa de variação do momento linear (F = ma).",
        },
    )
    assert q_res.status_code == 201
    q_id = q_res.json()["id"]

    # 4. Responde à provação no Nó e sobe para Rank I
    rev_res = authenticated_client.post(
        f"/api/v1/study-maps/{map_id}/nodes/{node_id}/questions/{q_id}/review",
        json={"score": 100},
    )
    assert rev_res.status_code == 200
    assert rev_res.json()["new_level"] == 1
    assert rev_res.json()["node_effective_level"] == 1

    # 5. Acessa a Página Dedicada do Nó (Opção B)
    page_res = authenticated_client.get(f"/study-maps/{map_id}/nodes/{node_id}")
    assert page_res.status_code == 200
    assert "Leis de Newton" in page_res.text
    assert "A resultante das forças é F = m * a." in page_res.text
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/integration/test_node_grimoire_api_and_web.py -v`
Expected: FAIL with 404 Not Found on `/api/v1/study-maps/{map_id}/nodes/{node_id}/theory`

- [ ] **Step 3: Implement API & Web controllers for Node Grimoire**

- In `src/adapters/api/study_tree_controllers.py`, add the 6 REST endpoints (`theory`, `questions`, `questions/{question_id}`, `questions/{question_id}/review`, `materials`, `materials/{source_id}`) with Anti-IDOR checks returning 403 on `ResourceOwnershipError` and 404 on `StudyMapNotFoundError` / `StudyNodeNotFoundError`.
- In `src/adapters/web/study_tree_web_controllers.py`, add `GET /study-maps/{map_id}/nodes/{node_id}` (`study_node_grimoire_page`), computing node unlock status, prerequisite node titles, mastered questions count, and rendering `study_tree/node_grimoire.html`.

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/integration/test_node_grimoire_api_and_web.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/adapters/api/study_tree_controllers.py src/adapters/web/study_tree_web_controllers.py tests/integration/test_node_grimoire_api_and_web.py
git commit -m "feat(adapters): add REST and web controllers for dedicated node grimoire page"
```

---

### Task 4: Identidade Visual RPG "Grimório & Forja Ancestral" (`app.css`, `base.html`, `maps_list.html`, `canvas.html`, `study_canvas.js`)

**Files:**
- Modify: `src/adapters/web/static/css/app.css`
- Modify: `src/adapters/web/templates/base.html`
- Modify: `src/adapters/web/templates/study_tree/maps_list.html`
- Modify: `src/adapters/web/templates/study_tree/canvas.html`
- Modify: `src/adapters/web/static/js/study_canvas.js`
- Test: `tests/integration/test_rpg_navigation_and_canvas_ui.py`

**Interfaces:**
- Consumes: `/study-maps`, `/study-maps/{map_id}/canvas`, `/study-maps/{map_id}/nodes/{node_id}` routes.
- Produces:
  - RPG Grimoire & Forge theme across `base.html`, `maps_list.html`, and `canvas.html`.
  - `study_canvas.js` clicking a node in Study/Journey mode navigates to `/study-maps/${state.mapId}/nodes/${node.id}`.

- [ ] **Step 1: Write the failing test in `tests/integration/test_rpg_navigation_and_canvas_ui.py`**

```python
from fastapi.testclient import TestClient


def test_rpg_grimoire_topbar_and_canvas_medallions(authenticated_client: TestClient) -> None:
    res = authenticated_client.get("/study-maps")
    assert res.status_code == 200
    assert "Cinzel" in res.text
    assert "Códice de Habilidades" in res.text
    assert "Provações Diárias" in res.text
    assert "Crônicas" in res.text
    # Menu legado "Cadastros" não deve existir na barra de navegação
    assert 'id="cadastros-menu-btn"' not in res.text
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/integration/test_rpg_navigation_and_canvas_ui.py -v`
Expected: FAIL (`"Cinzel" in res.text` is False)

- [ ] **Step 3: Implement RPG Grimoire CSS, Topbar, Maps List, and Skill Medallion Canvas**

- In `src/adapters/web/static/css/app.css`, define `.rpg-font` (`Cinzel`), `.tome-font` (`Cormorant Garamond`), `.rpg-panel` (obsidian/leather gradient with `#785a28` bronze border and `#c89b3c` gold accents), `.rpg-medallion` (circular skill medallions for Locked Iron, Rank 0 Stone, Rank I-II Forged Bronze, Rank III-IV Runic Silver, Rank V-VI Legendary Gold, and Overdue Crimson Pulse).
- In `src/adapters/web/templates/base.html`, load Google Fonts `Cinzel` and `Cormorant Garamond`, style the header and mobile bottom bar in Grimório & Forja Ancestral palette, and display the 3 unified navigation items (`⚔️ Códice de Habilidades`, `🔥 Provações Diárias`, `🏆 Crônicas & Atributos`).
- In `src/adapters/web/templates/study_tree/maps_list.html`, apply the Grimoire aesthetic, remove the legacy migration button, and highlight `✨ Forjar Nova Árvore` and `📐 Invocar Árvore Modelo (Matemática Aplicada)`.
- In `src/adapters/web/templates/study_tree/canvas.html` and `src/adapters/web/static/js/study_canvas.js`:
  - Expand `ICON_MAP` to support all icons (`brain`, `sword`, `shield`, `book`, `code`, `fire`, `scroll`, `flask`, `gem`, `calculator`, `trending-up`, `dice`, `activity`, `rune`).
  - Render circular RPG Skill Medallions with `RANK 0..VI` / `🔒 SELADO` badges and golden energy curves (`#c89b3c` / `#f59e0b`).
  - Clicking a node in `study` (Modo Jornada) navigates directly to `/study-maps/${state.mapId}/nodes/${node.id}`. In `edit` (Modo Forja), clicking opens the quick node metadata modal (with a direct link to open the Node Grimoire page as well).

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/integration/test_rpg_navigation_and_canvas_ui.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/adapters/web/static/css/app.css src/adapters/web/templates/base.html src/adapters/web/templates/study_tree/maps_list.html src/adapters/web/templates/study_tree/canvas.html src/adapters/web/static/js/study_canvas.js tests/integration/test_rpg_navigation_and_canvas_ui.py
git commit -m "feat(ui): apply RPG Grimoire & Forge theme to navigation, maps list, and skill tree canvas"
```

---

### Task 5: Página Dedicada do Nó (`study_tree/node_grimoire.html`) Completa + Alinhamento Visual de Provações Diárias e Crônicas

**Files:**
- Create: `src/adapters/web/templates/study_tree/node_grimoire.html`
- Modify: `src/adapters/web/templates/questions/study.html`
- Modify: `src/adapters/web/templates/performance/performance_hub.html`
- Test: `tests/integration/test_node_grimoire_full_flow.py`

**Interfaces:**
- Consumes: REST endpoints from Task 3 (`/api/v1/study-maps/{map_id}/nodes/{node_id}/theory`, `/questions`, `/questions/{q_id}/review`, `/materials`, plus `/api/v1/questions/{q_id}/evaluate-text` and `/evaluate-audio`).
- Produces: Complete interactive full-screen Node Grimoire page (`study_tree/node_grimoire.html`).

- [ ] **Step 1: Write the failing test in `tests/integration/test_node_grimoire_full_flow.py`**

```python
from fastapi.testclient import TestClient


def test_sample_math_tree_to_node_grimoire_end_to_end(authenticated_client: TestClient) -> None:
    sample_res = authenticated_client.post("/api/v1/study-maps/sample-math")
    assert sample_res.status_code == 201
    map_id = sample_res.json()["id"]

    graph_res = authenticated_client.get(f"/api/v1/study-maps/{map_id}")
    assert graph_res.status_code == 200
    nodes = graph_res.json()["nodes"]
    assert len(nodes) == 5

    first_node = next(n for n in nodes if "Álgebra Linear" in n["title"])
    node_page = authenticated_client.get(f"/study-maps/{map_id}/nodes/{first_node['id']}")
    assert node_page.status_code == 200
    assert "Tomo de Sabedoria" in node_page.text
    assert "Provações de Maestria" in node_page.text
    assert "Forjar Nova Provação" in node_page.text
    assert "Revelar Runas" in node_page.text
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/integration/test_node_grimoire_full_flow.py -v`
Expected: FAIL (missing `Tomo de Sabedoria` / `Forjar Nova Provação` in `node_grimoire.html`)

- [ ] **Step 3: Implement `study_tree/node_grimoire.html` and align `questions/study.html` & `performance_hub.html`**

- Build `src/adapters/web/templates/study_tree/node_grimoire.html` with:
  - **Cabeçalho RPG do Nó:** Link `← Retornar à Árvore`, Medalhão com ícone, título em `Cinzel`, status `🔓 Despertado` ou `🔒 Selado (Requer: ...)`, badge `RANK 0..VI` e barra de progresso de maestria.
  - **Coluna Esquerda — 📖 Tomo de Sabedoria:** Leitura em fonte `Cormorant Garamond` do `theory_content`, editor inline `[✍️ Escrever / Editar Tomo]` que salva via `PATCH /api/v1/study-maps/{map_id}/nodes/{node_id}/theory`, lista de Pergaminhos complementares (`materials`) com texto expansível (`raw_text`) e formulário inline para adicionar novo pergaminho/texto.
  - **Coluna Direita — ⚔️ Provações de Maestria (SRS):**
    - **Arena de Provação Ativa:** Permite navegar entre as perguntas do nó, alternar entre `🔮 Revelar Runas (Gabarito Direto)`, `✍️ Conjurar Resposta (Texto + IA)` e `🎙️ Voz Arcana (Áudio + IA)`, atribuir nota de `0%` a `100%` e submeter em `POST /api/v1/study-maps/{map_id}/nodes/{node_id}/questions/{q_id}/review`, atualizando o Rank do Nó na tela e exibindo o banner dourado quando o nó alcança `RANK I+`.
    - **Forja de Provações:** Formulário inline `+ Forjar Nova Provação` (Enunciado + Gabarito Esperado) e lista das perguntas do nó com badge `RANK 0..VI`, próxima revisão e botão de exclusão.
- Update `src/adapters/web/templates/questions/study.html` and `src/adapters/web/templates/performance/performance_hub.html` headings and wrappers to match the Grimório & Forja Ancestral visual style.

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/integration/test_node_grimoire_full_flow.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/adapters/web/templates/study_tree/node_grimoire.html src/adapters/web/templates/questions/study.html src/adapters/web/templates/performance/performance_hub.html tests/integration/test_node_grimoire_full_flow.py
git commit -m "feat(ui): implement full-screen node grimoire page with tome editor and SRS challenge arena"
```
