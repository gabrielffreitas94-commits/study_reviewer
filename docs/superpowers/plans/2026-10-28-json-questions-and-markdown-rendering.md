# JSON Bulk Question Import & Rich Markdown Rendering Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Enable JSON-based bulk question import (with a 1-click "Copiar Prompt JSON para IA" helper) and render rich GitHub Flavored Markdown (bold, lists, code blocks, inline code, tables, blockquotes, headers) in question prompts, expected answers, and node summaries across Daily SRS Reviews, the Canvas Side Drawer, and the Node Grimoire.

**Architecture:**
- **Global RPG Markdown Renderer (`base.html`):** Add `.rpg-markdown` CSS rules and `window.renderRpgMarkdown(text)` / `window.applyRpgMarkdownAll()` in `base.html` so every template (`questions/study.html`, `canvas.html`, `node_grimoire.html`) renders Markdown cleanly while preserving raw server-side text for pytest HTML assertions.
- **JSON Bulk Importer & AI Prompt Generator (`canvas.html`, `study_canvas.js`, `node_grimoire.html`):** Upgrade `parseBulkQuestions` and `importPastedQuestions` to parse JSON arrays `[...]`, `{"questions": [...]}`, and fenced ```` ```json ... ``` ```` blocks (with fallback to `P:/R:` text), plus a 1-click button that copies a context-aware prompt instructing ChatGPT/Claude to output complex Markdown-formatted questions in the exact JSON schema.

**Tech Stack:** HTML5, Tailwind CSS, Vanilla JS, FastAPI/Jinja2, nh3 sanitization, Pytest.

**Spec:** User discussion (2026-10-28).

## Global Constraints

- Maintain 100.00% pytest coverage on `src/`.
- 0 Ruff lint/format errors, 0 Mypy errors.
- Preserve all existing integration test assertions.

---

### Task 1: Global `.rpg-markdown` Styling & Progressive Markdown Renderer (`base.html` & `question_card.html` & `sanitization.py`)

**Files:**
- Modify: `src/infrastructure/security/sanitization.py`
- Modify: `src/adapters/web/templates/base.html`
- Modify: `src/adapters/web/templates/questions/partials/question_card.html`
- Modify: `src/adapters/web/templates/questions/study.html`

- [ ] **Step 1:** Expand `ALLOWED_TAGS` in `src/infrastructure/security/sanitization.py` to include `h1`, `h2`, `h3`, `h4`, `blockquote`, `hr`, `table`, `thead`, `tbody`, `tr`, `th`, `td` so sanitized HTML/Markdown tags are preserved.
- [ ] **Step 2:** Add `.rpg-markdown` CSS styling and `window.renderRpgMarkdown(raw)` + `window.applyRpgMarkdownAll(root)` in `src/adapters/web/templates/base.html` supporting fenced code blocks (```` ```lang ... ``` ````), inline code (`` `...` ``), headers (`#` to `####`), blockquotes (`>`), unordered/ordered lists, tables, bold/italic, and line breaks, auto-running on `DOMContentLoaded` and `htmx:afterSwap`.
- [ ] **Step 3:** Mark `#question-prompt` and `#expected-answer-section .prose` in `src/adapters/web/templates/questions/partials/question_card.html` with `rpg-markdown-render` so Daily SRS cards render Markdown on initial load and after HTMX swaps.

---

### Task 2: JSON Bulk Question Importer, AI Prompt Helper & Markdown in Canvas Side Drawer & Node Grimoire

**Files:**
- Modify: `src/adapters/web/templates/study_tree/canvas.html`
- Modify: `src/adapters/web/static/js/study_canvas.js`
- Modify: `src/adapters/web/templates/study_tree/node_grimoire.html`
- Create: `tests/integration/test_json_questions_and_markdown_rendering.py`

- [ ] **Step 1:** Update `canvas.html` and `study_canvas.js`:
  - Add `"📋 Copiar Prompt JSON para IA"` button (`id="btn-copy-ai-json-prompt"`, `onclick="copyAiJsonPrompt()"`) in the Side Drawer's Questions tab.
  - Upgrade `parseBulkQuestions(rawText)` in `study_canvas.js` to accept JSON (`[...]`, `{"questions": [...]}`, or fenced ```` ```json ```` blocks) with keys `prompt`/`question`/`pergunta` and `expected_answer`/`answer`/`resposta`/`gabarito`, while preserving fallback to text format for backward compatibility.
  - Render question prompts and answers in `#drawer-questions-list` using `window.renderRpgMarkdown`.
- [ ] **Step 2:** Update `node_grimoire.html`:
  - Add `"📋 Copiar Prompt JSON para IA"` button (`id="btn-grimoire-copy-ai-json"`, `onclick="copyGrimoireAiJsonPrompt()"`).
  - Upgrade `importPastedQuestions()` to parse JSON arrays/objects and fenced ```` ```json ```` blocks alongside legacy text format.
  - Use `window.renderRpgMarkdown` when displaying `#arena-question-prompt`, `#arena-expected-answer`, `#theory-display-area`, and question cards.
- [ ] **Step 3:** Create `tests/integration/test_json_questions_and_markdown_rendering.py` testing JSON import, Markdown renderer presence, sanitization tags, and UI elements.

---

### Task 3: Full Verification & AWS Staging Deployment

- [ ] **Step 1:** Run Ruff, Mypy, and full pytest suite with 100.00% coverage.
- [ ] **Step 2:** Commit, push to `origin/staging`, and trigger AWS Staging deployment.
