# RPG Icons, Clean Conduits & Edge Level Calibration Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implement Game-Icons.net authentic RPG vector icons, clean outer-boundary ether conduits in Canvas, and per-edge configurable prerequisite levels (`required_level`) with an interactive dependency inspector in Forge Mode.

**Architecture:** Clean Architecture 4-layer approach. Layer 1 (Domain) adds `required_level: int = 1` to `StudyEdge` and updates `evaluate_unlock_status`. Layer 2 (Application) updates `ConnectStudyNodesUseCase` and creates `UpdateStudyEdgeUseCase`. Layer 3 (Adapters) updates persistence models, mappers, Alembic migration `e5f6a7b8c9d0`, and REST endpoints (`POST /edges`, `PATCH /edges/{id}`). Layer 4 (Web/UI) embeds the 21 Game-Icons.net SVGs, computes exact $R=42\text{px}$ boundary intersections for clean conduits, and renders the Prerequisite Inspector in Forge Mode and Node Grimoire.

**Tech Stack:** Python 3.13, FastAPI, SQLAlchemy 2.0, Alembic, PostgreSQL (Neon), Tailwind CSS, Vanilla JS, SVG, Pytest, Ruff, Mypy.

**Spec:** `docs/superpowers/specs/2026-10-26-rpg-icons-edges-and-prerequisites-design.md`

## Global Constraints

- 100% test coverage mandatory (`--cov-fail-under=100`).
- Strict Mypy type-checking (0 errors across `src` and `tests`).
- Ruff linter and formatter (0 errors, 100% formatted).
- Lines on Canvas must remain clean (no cluttering labels/badges floating on the lines themselves).
- All changes delivered to `staging` branch.

## Review Focus

- Cycle detection and edge updates must preserve DAG properties (`CyclicDependencyError`).
- Edge with `required_level > 1` must block target node until source node reaches the specified level.
- Multi-dependency unlocking (e.g. $B \ge 1$ and $A \ge 3$) must evaluate conjunctively.
- Edge geometry must smoothly handle all angles (horizontal, vertical, diagonal) without NaN or zero-division when nodes overlap.
- Game-Icons SVGs must render with high contrast and golden/bronze aura in all modern browsers.

---

### Task 1: Domain & Persistence — `StudyEdge.required_level`, Progression Logic & Alembic Migration

**Files:**
- Modify: `src/domain/entities.py`
- Modify: `src/domain/services.py`
- Modify: `src/adapters/persistence/models.py`
- Modify: `src/adapters/persistence/mappers.py`
- Modify: `src/adapters/persistence/repositories.py`
- Create: `alembic/versions/e5f6a7b8c9d0_add_required_level_to_study_edges.py`
- Test: `tests/unit/domain/test_rpg_edge_calibration.py`

**Steps:**
- [ ] Write unit tests in `tests/unit/domain/test_rpg_edge_calibration.py` testing:
  - `StudyEdge` defaults to `required_level = 1`.
  - `StudyEdge` validates `required_level >= 1` (raises `ValueError` for `< 1`).
  - `StudyTreeProgressionService.evaluate_unlock_status`:
    - Node with single edge ($A \rightarrow B, \text{req}=1$) unlocks when $A \ge 1$, locks when $A < 1$.
    - Node with single edge ($A \rightarrow C, \text{req}=3$) unlocks when $A \ge 3$, locks when $A \in \{0, 1, 2\}$.
    - Multi-dependency node ($A \rightarrow C, \text{req}=3$ and $B \rightarrow C, \text{req}=1$):
      - Locks if $A=2, B=1$.
      - Locks if $A=3, B=0$.
      - Unlocks if $A=3, B=1$.
- [ ] Run test to verify it fails (`uv run pytest tests/unit/domain/test_rpg_edge_calibration.py`).
- [ ] Update `src/domain/entities.py`: add `required_level: int = 1` to `StudyEdge` with `__post_init__` validation.
- [ ] Update `src/domain/services.py`: in `evaluate_unlock_status`, replace `parent_level < 1` with `parent_level < edge.required_level`.
- [ ] Update `src/adapters/persistence/models.py`: add `required_level: Mapped[int] = mapped_column(Integer, default=1, nullable=False)` to `StudyEdgeModel`.
- [ ] Update `src/adapters/persistence/mappers.py`: map `required_level` in `StudyEdgeMapper.to_domain` and `to_model`.
- [ ] Update `src/adapters/persistence/repositories.py`: map `required_level` in edge repository queries and updates.
- [ ] Create Alembic migration `alembic/versions/e5f6a7b8c9d0_add_required_level_to_study_edges.py` chaining from `d4e5f6a7b8c9`.
- [ ] Run unit tests to verify they pass (`uv run pytest tests/unit/domain/test_rpg_edge_calibration.py`).
- [ ] Commit: `feat(domain): add required_level to StudyEdge and unlock evaluation`.

---

### Task 2: Use Cases & REST API — Configurable Edge Level & Prerequisite Graph

**Files:**
- Modify: `src/application/dto/study_tree_dto.py`
- Modify: `src/application/ports/repositories.py`
- Modify: `src/application/use_cases/study_tree_use_cases.py`
- Modify: `src/adapters/api/study_tree_controllers.py`
- Test: `tests/integration/test_rpg_edge_api.py`

**Steps:**
- [ ] Write integration tests in `tests/integration/test_rpg_edge_api.py` testing:
  - `POST /api/v1/study-maps/{map_id}/edges` with `{"source_node_id": ..., "target_node_id": ..., "required_level": 3}` creates edge with `required_level = 3`.
  - `PATCH /api/v1/study-maps/{map_id}/edges/{edge_id}` with `{"required_level": 2}` updates edge requirement.
  - `GET /api/v1/study-maps/{map_id}` returns edges including `required_level`.
  - Canvas progression reflects unlock state accurately based on custom required levels.
- [ ] Run test to verify it fails.
- [ ] Update `src/application/dto/study_tree_dto.py`: add `required_level: int = 1` to `ConnectNodesDTO` and `StudyEdgeDTO`, create `UpdateStudyEdgeDTO`.
- [ ] Update `src/application/ports/repositories.py`: add `update_edge(self, edge: StudyEdge) -> StudyEdge` if not present.
- [ ] Update `src/application/use_cases/study_tree_use_cases.py`:
  - `ConnectStudyNodesUseCase`: support `dto.required_level`.
  - Create `UpdateStudyEdgeUseCase`: update edge `required_level` validating ownership.
  - `GetStudyMapCanvasUseCase`: include `required_level` in edge payload and calculate node unlock states with edge-specific thresholds.
- [ ] Update `src/adapters/api/study_tree_controllers.py`:
  - `POST /study-maps/{map_id}/edges`: accept `required_level`.
  - Add `PATCH /study-maps/{map_id}/edges/{edge_id}`: calls `UpdateStudyEdgeUseCase`.
- [ ] Run tests to verify they pass (`uv run pytest tests/integration/test_rpg_edge_api.py`).
- [ ] Commit: `feat(api): support configurable required_level on study edges`.

---

### Task 3: Game-Icons.net SVG Library Integration

**Files:**
- Create: `src/adapters/web/static/js/rpg_icons.js` (or inline SVG dictionary)
- Modify: `src/adapters/web/static/js/study_canvas.js`
- Modify: `src/adapters/web/templates/study_tree/node_grimoire.html`
- Modify: `src/adapters/web/templates/study_tree/canvas.html`
- Test: `tests/integration/test_rpg_icons_rendering.py`

**Steps:**
- [ ] Write integration test in `tests/integration/test_rpg_icons_rendering.py` asserting:
  - Canvas template loads Game-Icons SVG registry.
  - Node Grimoire template renders authentic SVG icons rather than emojis.
  - All 21 standard icon tokens map to valid SVG paths with `viewBox="0 0 512 512"` and golden styling.
- [ ] Run test to verify it fails.
- [ ] Create `src/adapters/web/static/js/rpg_icons.js` containing the 21 authentic Game-Icons.net SVG definitions (clean vector paths, scalable, styled with CSS fill and filter).
- [ ] Update `src/adapters/web/static/js/study_canvas.js`:
  - Replace emoji text rendering inside `<text>` element in `renderNodes()` with `<g class="rpg-node-icon">` rendering the vector SVG icon centered inside the medallion.
- [ ] Update `src/adapters/web/templates/study_tree/node_grimoire.html`:
  - Replace emoji lookup in header medallion with the corresponding Game-Icons SVG.
- [ ] Update icon select dropdown in `canvas.html` so options preview the RPG icon name cleanly.
- [ ] Run tests to verify they pass (`uv run pytest tests/integration/test_rpg_icons_rendering.py`).
- [ ] Commit: `feat(ui): integrate 21 Game-Icons.net SVG fantasy runes`.

---

### Task 4: Clean Conduits Geometry & Forge Mode Prerequisite Inspector

**Files:**
- Modify: `src/adapters/web/static/js/study_canvas.js`
- Modify: `src/adapters/web/templates/study_tree/canvas.html`
- Modify: `src/adapters/web/templates/study_tree/node_grimoire.html`
- Test: `tests/integration/test_rpg_canvas_conduits_and_inspector.py`

**Steps:**
- [x] Write integration test in `tests/integration/test_rpg_canvas_conduits_and_inspector.py` checking:
  - `canvas.html` contains the Forge Mode Prerequisite Manager markup (`#node-prerequisites-list`, `#add-prerequisite-select`, `#add-prerequisite-level`).
  - `node_grimoire.html` renders explicit required level per prerequisite (e.g. `Requer: Álgebra Linear (Nv. 1), Fundamentos (Nv. 3)`).
- [x] Run test to verify it fails.
- [x] Update `renderEdges` in `src/adapters/web/static/js/study_canvas.js`:
  - Calculate trigonometric unit vector: $D = \text{hypot}(\Delta x, \Delta y)$, $ux = \Delta x / D$, $uy = \Delta y / D$.
  - Start position: $(sx + 42 \cdot ux, sy + 42 \cdot uy)$.
  - End position: $(tx - 42 \cdot ux, ty - 42 \cdot uy)$.
  - Keep line clean: no floating text or badges on the path.
  - Style with ether gradient and subtle diamond terminal.
- [x] Update Forge Inspector in `canvas.html` and `study_canvas.js`:
  - When a node is selected in Forge Mode, query incoming edges for that node.
  - Render list of prerequisites with:
    - Source node title
    - Level selector: `[Nv. 1 | Nv. 2 | Nv. 3 | Nv. 4]` triggering `PATCH /api/v1/study-maps/{mapId}/edges/{edgeId}` on change.
    - Delete button calling `DELETE /api/v1/study-maps/{mapId}/edges/{edgeId}`.
    - Form to add new incoming prerequisite edge to the selected node.
- [x] Update `node_grimoire.html` header:
  - If locked, format prerequisite requirements including required level: `🔒 Selado — Requer: Nome (Nv. X)`.
- [x] Run tests to verify they pass (`uv run pytest tests/integration/test_rpg_canvas_conduits_and_inspector.py`).
- [x] Run full test suite with 100% coverage, Ruff and Mypy.
- [x] Commit: `feat(ui): implement clean outer-boundary conduits and Forge Mode prerequisite inspector`.
