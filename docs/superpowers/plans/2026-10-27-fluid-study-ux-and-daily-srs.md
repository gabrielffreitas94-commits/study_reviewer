# Fluid Study UX & Daily SRS Unification Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Create a completely frictionless study flow where users land directly on Daily SRS Reviews (aggregating questions across all their tree nodes), can spawn connected child nodes with a single `+` click on the canvas, and can manage notes and paste bulk AI questions inside an interactive slide-over Side Drawer directly on the canvas.

**Architecture:**
- **Daily SRS Unification:** Adapt SQL queries and use cases so questions created inside tree nodes seamlessly enter the daily spaced repetition queue (`/questions/study`) and can be reviewed with SRS scoring.
- **1-Click Connected Node Creation:** Add a `+` handle to canvas nodes that creates a child node positioned beside the parent and automatically establishes the prerequisite edge via the REST API.
- **Canvas Slide-Over Drawer:** Embed a slide-over panel on the canvas (`#node-side-drawer`) allowing students who study side-by-side with an AI to paste summaries, import bulk questions, and manage prerequisites without leaving the canvas.

**Tech Stack:** FastAPI, Jinja2, Tailwind CSS, Canvas 2D/DOM, SQLAlchemy 2.0 (PostgreSQL/SQLite), Spaced Repetition (SuperMemo/Leitner).

**Spec:** Audio Think-Aloud Feedback from User (Session 2026-10-27).

## Global Constraints

- Preserve 100.00% pytest test coverage on `src/`.
- 0 Ruff linter errors, 0 Ruff formatting issues.
- 0 Mypy static typing errors in `src/`.
- Maintain the Dark RPG aesthetic (Cinzel/Cormorant fonts, obsidian/gold panels).
- Fully responsive on desktop and mobile.

## Review Focus

1. **Node questions in daily SRS:** Questions created on tree nodes must appear in `/questions/study` and correctly display the map title as subject and node title as topic.
2. **Reviewing node questions:** Submitting an SRS rating for a node question on `/questions/study` must not raise `EntityNotFoundError("Tema não encontrado")`.
3. **Login & root landing:** Logging in via Google or password, or visiting `/`, must land directly on `/questions/study`.
4. **1-Click child node creation:** Clicking `+` on a node creates the node with an offset position and connects the edge without page reload.
5. **Side Drawer with AI bulk paste:** Pasting questions in the side drawer and clicking save must create questions via the batch endpoint and update the question list instantly.

---

### Task 1: Unify Daily SRS Queue & Review Use Case for Tree Node Questions

**Files:**
- Modify: `src/adapters/persistence/repositories.py` (`SqlAlchemyQuestionProgressRepository.get_due_questions`)
- Modify: `src/application/use_cases/question_use_cases.py` (`ReviewQuestionUseCase.execute`)
- Modify: `src/adapters/web/controllers.py` (`index()`)
- Modify: `src/adapters/web/auth_controllers.py` (`_safe_redirect_url`)
- Test: `tests/integration/test_daily_srs_node_questions_unification.py`

- [ ] **Step 1:** Write the failing integration test in `tests/integration/test_daily_srs_node_questions_unification.py`.
- [ ] **Step 2:** Run pytest to verify the test fails on current implementation.
- [ ] **Step 3:** In `src/adapters/persistence/repositories.py`, update `get_due_questions` to use `outerjoin` on `TopicModel`, `SubjectModel`, `StudyNodeModel`, and `StudyMapModel`, coalescing names for node questions.
- [ ] **Step 4:** In `src/application/use_cases/question_use_cases.py`, update `ReviewQuestionUseCase.execute` to handle `question.node_id` and bypass/adapt legacy topic check.
- [ ] **Step 5:** In `src/adapters/web/controllers.py` and `src/adapters/web/auth_controllers.py`, update default redirect to `/questions/study`.
- [ ] **Step 6:** Run pytest and verify all tests pass with 100.00% coverage.
- [ ] **Step 7:** Commit Task 1 changes.

---

### Task 2: 1-Click Connected Child Node Creation (`+` on Node)

**Files:**
- Modify: `src/adapters/web/static/js/study_canvas.js`
- Modify: `src/adapters/web/templates/study_tree/canvas.html`
- Test: `tests/integration/test_canvas_quick_add_child.py`

- [ ] **Step 1:** Write tests in `tests/integration/test_canvas_quick_add_child.py` verifying quick-add child logic and canvas template contract.
- [ ] **Step 2:** In `src/adapters/web/static/js/study_canvas.js`, add `quick-add-child-btn` markup on nodes.
- [ ] **Step 3:** Implement `quickAddChildNode(parentNode)` to prompt/input title, calculate offset coordinates, call `POST /nodes`, and call `POST /edges`.
- [ ] **Step 4:** Run tests and check Ruff/Mypy.
- [ ] **Step 5:** Commit Task 2 changes.

---

### Task 3: Interactive Side Drawer on Canvas (Notes, Bulk AI Questions & Prereqs)

**Files:**
- Modify: `src/adapters/web/templates/study_tree/canvas.html`
- Modify: `src/adapters/web/static/js/study_canvas.js`
- Test: `tests/integration/test_canvas_side_drawer.py`

- [ ] **Step 1:** Write integration test `tests/integration/test_canvas_side_drawer.py` asserting on drawer structure, IDs, and endpoints.
- [ ] **Step 2:** Add `#node-side-drawer` template markup in `canvas.html` with tabs for Theory/Notes, AI Bulk Questions, and Prerequisites.
- [ ] **Step 3:** In `study_canvas.js`, implement `openNodeDrawer`, `closeNodeDrawer`, `saveDrawerTheory`, `submitDrawerBatchQuestions`, and `deleteDrawerQuestion`.
- [ ] **Step 4:** Wire node click on canvas to open the Side Drawer seamlessly.
- [ ] **Step 5:** Run full test suite, Ruff, Mypy and confirm 100.00% coverage.
- [ ] **Step 6:** Commit Task 3 changes.

---

### Task 4: Verification, Full Suite Coverage & Staging Deployment

- [ ] **Step 1:** Run full pytest suite with `--cov=src --cov-report=term-missing`.
- [ ] **Step 2:** Run `ruff check .` and `ruff format --check .`.
- [ ] **Step 3:** Run `mypy src`.
- [ ] **Step 4:** Push to `origin/staging` and trigger AWS deployment workflow.
- [ ] **Step 5:** Verify smoke test and report to user.
