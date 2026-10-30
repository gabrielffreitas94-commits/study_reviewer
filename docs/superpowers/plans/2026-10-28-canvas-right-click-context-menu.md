# Canvas Right-Click RPG Context Menu Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a custom Dark RPG right-click context menu on canvas nodes (with 7 direct actions across expansion, AI content, study, and maintenance) and on the empty canvas background (to create a node at exact cursor coordinates).

**Architecture:**
- Intercept `contextmenu` events on node DOM elements and on `#canvas-viewport` in `study_canvas.js`.
- Render two floating RPG menus (`#node-context-menu` and `#canvas-context-menu`) in `canvas.html` with viewport boundary clamping so they never overflow the screen.
- Wire each action to existing/enhanced functions in `study_canvas.js` (including coordinate-aware node creation at cursor position and direct tab + input focus on `#node-side-drawer`).

**Tech Stack:** HTML5, Tailwind CSS, Vanilla JS (`study_canvas.js`), FastAPI/Jinja2, Pytest.

**Spec:** User discussion (2026-10-28).

## Global Constraints

- Preserve 100.00% pytest coverage on `src/`.
- 0 Ruff lint/format issues, 0 Mypy issues.
- Preserve all existing test contracts in `tests/integration/`.

---

### Task 1: Implement Node & Canvas Context Menus (`canvas.html` & `study_canvas.js`) + Integration Tests

**Files:**
- Modify: `src/adapters/web/templates/study_tree/canvas.html`
- Modify: `src/adapters/web/static/js/study_canvas.js`
- Create: `tests/integration/test_canvas_context_menu.py`

- [ ] **Step 1:** Add `#node-context-menu` and `#canvas-context-menu` markup in `src/adapters/web/templates/study_tree/canvas.html`.
- [ ] **Step 2:** In `src/adapters/web/static/js/study_canvas.js`, attach `contextmenu` listener on each node in `renderNodes()` and on `viewport`, implement viewport-clamped positioning, and implement the 7 node actions + background "Criar Nó Aqui" action at cursor world coordinates.
- [ ] **Step 3:** Create `tests/integration/test_canvas_context_menu.py` verifying all context menu actions, IDs, and JS handlers.
- [ ] **Step 4:** Run all canvas integration tests to ensure zero regressions.

---

### Task 2: Quality Gate & AWS Staging Deployment

- [ ] **Step 1:** Run Ruff, Mypy, and full pytest suite with 100% coverage check.
- [ ] **Step 2:** Commit, push to `origin/staging`, and trigger AWS Staging deployment.
