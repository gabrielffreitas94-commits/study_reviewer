# Node Usability & Jargon Cleanup Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Clean up excessive RPG jargon across the application into clear, direct terminology while preserving the Dark RPG aesthetic, and redesign the Node page (`node_grimoire.html`) with a clear separation between Study Mode (spoiler-free study & practice) and Edit/Management Mode (easy theory editing, drag-and-drop file upload for PDF/DOCX/TXT/MD, and batch question registration without page reload).

**Architecture:** Frontend Jinja2 templates, Tailwind CSS, and vanilla JS leveraging existing Clean Architecture endpoints (`POST /api/v1/knowledge/extract-file` for document text extraction, `POST /api/v1/study-maps/{map_id}/nodes/{node_id}/questions` for fast question creation, and `PATCH /api/v1/study-maps/{map_id}/nodes/{node_id}/theory`).

**Tech Stack:** Python 3.12, FastAPI, Jinja2, Tailwind CSS, JavaScript (ES6+), Gemini RAG & Text Extraction (via existing backend services).

**Spec:** Direct user requirements to eliminate confusing jargon ("Tomo", "Pergaminho", "Provação", "Revelar Runas", "Conjurar Resposta", "Forjar", "Dissipar", "Selar"), implement easy file upload & text extraction in the node, allow fast batch question registration without full-page reloads, and separate Study Mode from Edit/Management Mode.

## Global Constraints
- Keep 100% pytest test suite passing (all 783 tests), 0 Ruff warnings, 0 Mypy errors.
- Preserve Dark RPG styling: golden borders, dark obsidian backgrounds, Cinzel headers, Cormorant Garamond / font-tome text, and Game-Icons.net vector SVG runes.
- Maintain clean outer-boundary conduits on the canvas without text/badges on edges.
- Use existing backend extraction endpoint (`/api/v1/knowledge/extract-file`) which already handles PDF, DOCX, TXT, MD up to 15MB.
- Maintain documentation integrity and clean architecture separation.

## Review Focus
1. User can switch seamlessly between "📖 Modo Estudo" and "⚙️ Gerenciar Nó (Conteúdo & Questões)" inside the node.
2. File upload correctly extracts text from PDF/DOCX/TXT/MD and populates/appends to the node's theory or creates a material.
3. Questions can be added one-by-one or in batch without page reload (`window.location.reload()` removed in favor of asynchronous DOM updates).
4. No spoilers in Study Mode (all answers/expected answers are hidden until the user clicks "👁️ Ver Gabarito" or submits an answer).
5. All buttons and headers use clear, self-explanatory Portuguese labels.

---

### Task 1: Clean Up RPG Jargon Across All Templates

**Files:**
- Modify: `src/adapters/web/templates/study_tree/maps_list.html`
- Modify: `src/adapters/web/templates/study_tree/canvas.html`
- Modify: `src/adapters/web/static/js/study_canvas.js`
- Test: `tests/unit/test_study_tree_web.py`

- [ ] **Step 1: Update terminology in `maps_list.html`**
  - "Campanhas de Conhecimento" -> "Árvores de Estudo & Conhecimento"
  - "Forjar Nova Árvore" -> "+ Nova Árvore de Estudos"
  - "Forjar Nova Campanha" -> "Criar Nova Árvore"
  - "Dissipar Campanha" -> "Excluir Árvore"
  - Clearer descriptions for public/private badges and node counts.

- [ ] **Step 2: Update terminology in `canvas.html` and `study_canvas.js`**
  - "Forja Ancestral" -> "Árvore de Conhecimento"
  - "Forjar Nó" -> "+ Novo Nó"
  - "Traçar Vínculo" -> "🔗 Conectar Nós"
  - "Gravar Medalhão" -> "Salvar Nó"
  - "Dissipar Medalhão" -> "Excluir Nó"
  - "Dissipar vínculo" -> "Excluir conexão"
  - "Conectar Bloqueio" -> "+ Adicionar Pré-requisito"
  - Prompt confirmation: "Deseja excluir este nó e suas perguntas?" instead of "Deseja dissipar o medalhão..."

- [ ] **Step 3: Run web tests to verify no regressions**
  - Command: `.venv\Scripts\python.exe -m pytest tests/unit/test_study_tree_web.py`

- [ ] **Step 4: Commit Task 1 changes**
  - Git commit: `refactor(ui): clean up excessive RPG jargon in maps list and canvas`

---

### Task 2: Redesign Node Grimoire Template (`node_grimoire.html`) - Study Mode vs Edit Mode

**Files:**
- Modify: `src/adapters/web/templates/study_tree/node_grimoire.html`
- Test: `tests/unit/test_study_tree_web.py`

- [ ] **Step 1: Implement Mode Selector at the top of `node_grimoire.html`**
  - Add tab toggle header:
    - `📖 Modo Estudo` (active by default for learning and answering questions)
    - `⚙️ Gerenciar Conteúdo & Questões` (available to the map owner for editing)
  - Ensure mode state can be persisted in `localStorage` or URL hash (e.g. `#edit` or `#study`).

- [ ] **Step 2: Refactor "Modo Estudo" (Clean & Focused Study View)**
  - Left column:
    - Clean reading panel with "📖 Conteúdo & Resumo do Tópico" with markdown/prose styling.
    - "📎 Materiais de Apoio Anexados" list with expandable reading.
  - Right column:
    - "🎯 Revisão de Questões":
      - Progress bar and level badge (Nv. X).
      - Question carousel/card without answer spoilers.
      - 3 clear answer actions:
        - `👁️ Ver Gabarito` (reveals answer + 4 SRS buttons: Esqueci, Difícil, Bom, Fácil)
        - `✍️ Responder por Texto` (input box + "Avaliar com IA")
        - `🎙️ Responder por Voz` (record button + "Avaliar com IA")
      - REMOVE the full list of all question answers/spoilers from the study view (moves to Edit Mode).

- [ ] **Step 3: Verify Study Mode rendering and tests**
  - Run pytest on web controllers to ensure Jinja2 context variables match.

---

### Task 3: Implement Easy Content & File Upload in Node Edit Mode

**Files:**
- Modify: `src/adapters/web/templates/study_tree/node_grimoire.html`
- Test: `tests/unit/test_study_tree_web.py`

- [ ] **Step 1: Add Direct Content Editor with File Upload Dropzone in Edit Mode**
  - Editor for `theory_content` with "Salvar Conteúdo".
  - Drag-and-drop or click file upload box accepting `.pdf`, `.docx`, `.txt`, `.md` (up to 15MB).
  - JS handler calling existing `/api/v1/knowledge/extract-file`:
    - Shows progress spinner during extraction.
    - Options upon extraction:
      - "Inserir no Resumo do Nó" (appends or replaces `theory_content`).
      - "Salvar como Material Anexo" (calls `POST /api/v1/study-maps/{map_id}/nodes/{node_id}/materials`).

- [ ] **Step 2: Add Material Management section**
  - List of attached materials with quick delete button and instant DOM removal.

---

### Task 4: Implement Fast Question Creation (Single & Batch) without Page Reload

**Files:**
- Modify: `src/adapters/web/templates/study_tree/node_grimoire.html`
- Modify: `src/adapters/api/study_tree_controllers.py` (if batch creation endpoint is needed)
- Test: `tests/unit/test_study_tree_web.py`
- Test: `tests/unit/test_study_tree_api.py`

- [ ] **Step 1: Build Batch Question Creator in Edit Mode**
  - Quick single question form that submits via AJAX and appends to the question list immediately (no `window.location.reload()`).
  - Batch question creator allowing multiple questions at once:
    - Button `+1 Linha de Pergunta` / `+5 Linhas`.
    - Each line has Prompt and Expected Answer.
    - Single "Salvar Todas as Perguntas" button that saves them asynchronously and updates the list.
  - "Importar / Colar Perguntas em Lote":
    - Modal or textarea where the user can paste questions formatted like `Pergunta: ... | Resposta: ...` and parse automatically.

- [ ] **Step 2: Update Question List in Edit Mode**
  - Table or card list showing all questions of this node with:
    - Prompt, Answer, Level, Next Review Date.
    - Quick "🗑️ Excluir" button with instant DOM removal.

- [ ] **Step 3: Test Question creation without reload**
  - Run pytest on study tree API and Web controllers.

---

### Task 5: End-to-End Verification, Code Quality & Staging Deployment

**Files:**
- All modified files
- Tests: `tests/`

- [ ] **Step 1: Run Ruff linter and formatter**
  - Command: `.venv\Scripts\python.exe -m ruff check .`
  - Command: `.venv\Scripts\python.exe -m ruff format --check .`

- [ ] **Step 2: Run Mypy static type checker**
  - Command: `.venv\Scripts\python.exe -m mypy src`

- [ ] **Step 3: Run full Pytest test suite with 100% coverage verification**
  - Command: `.venv\Scripts\python.exe -m pytest --cov=src --cov-report=term-missing`

- [ ] **Step 4: Push to `origin/staging` and trigger AWS deployment workflow**
  - Git push staging
  - `gh workflow run deploy-aws.yml --ref staging -f environment=staging`
  - Monitor run to completion.
