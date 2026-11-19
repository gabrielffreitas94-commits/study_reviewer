# Edição Sutil de Pergunta e Gabarito nas Provações Diárias - Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Permitir que o estudante proprietário edite de forma sutil o enunciado e o gabarito (resposta esperada) de uma pergunta diretamente durante as Provações Diárias (`/questions/study`), sem causar quebras de layout ou sair do fluxo de revisão SRS.

**Architecture:** Adicionar o campo `can_edit: bool` ao DTO da fila SRS (`DueQuestionItemDTO`), computando a propriedade da matéria/mapa na consulta do repositório. No template [`question_card.html`](src/adapters/web/templates/questions/partials/question_card.html), renderizar um botão minimalista posicionado abaixo de "Contestar Avaliação" (visível apenas para o proprietário) que abre um modal acessível para ajuste de texto, salvando via `PUT /api/v1/questions/{question_id}` e atualizando o card dinamicamente com o renderizador de Markdown.

**Tech Stack:** Python 3.12+, FastAPI, SQLAlchemy, Jinja2, HTMX, Tailwind CSS, Vanilla JS, pytest.

**Spec:** [`docs/superpowers/specs/2026-10-30-daily-srs-question-inline-edit-design.md`](docs/superpowers/specs/2026-10-30-daily-srs-question-inline-edit-design.md)

## Global Constraints
- Estrita observância de Clean Architecture (DTOs na camada 2, repositórios e controladores na camada 3).
- Validação e higienização obrigatória de Markdown via `MarkdownSanitizerService.sanitize()`.
- Verificação rigorosa de autorização: apenas o proprietário da matéria ou mapa pode visualizar o botão e editar a pergunta (`403 Forbidden` caso contrário).
- Acessibilidade WCAG 2.1 AA (fechamento via `Esc`, armadilha de foco, rótulos `aria-*`).
- Zero Cumulative Layout Shift (CLS) no card de estudo durante a interação.

## Review Focus
1. Não-proprietário acessando pergunta de matéria pública compartilhada: botão `btn-edit-question-modal` não deve ser renderizado e requisição direta `PUT` deve retornar `403 Forbidden`.
2. Edição de gabarito contendo Markdown avançado (blocos de código com indentação, listas com negrito, tabelas): deve ser persistido integralmente e re-renderizado com `rpg-markdown` e `window.applyRpgMarkdownAll()`.
3. Validação de tamanho: prompt ou expected_answer vazios ou com mais de 10.000 caracteres devem ser rejeitados com feedback claro e sem corromper o estado do card.
4. Fechamento do modal via botão cancelar ou tecla `Esc`: deve restaurar o foco no botão de edição sem submeter dados.
5. Preservação do progresso da sessão SRS: editar a pergunta não pode resetar o valor selecionado no slider de autoavaliação ou reiniciar a fila do dia.

---

### Task 1: Adicionar `can_edit` a `DueQuestionItemDTO` e Cálculo no Repositório

**Files:**
- Modify: `src/application/dto/question_dto.py:130-143`
- Modify: `src/adapters/persistence/repositories.py:575-646`
- Modify: `tests/unit/application/fakes.py:365-375`
- Test: `tests/unit/application/test_question_use_cases.py`
- Test: `tests/integration/adapters/test_question_progress_repository.py` (ou `tests/integration/web/test_question_web_controllers.py`)

- [ ] **Step 1:** Escrever o teste unitário/integração que verifica `card.can_edit == True` quando o usuário é dono da matéria e `False` quando pertence a outro proprietário.
- [ ] **Step 2:** Executar o teste com `uv run pytest` e confirmar a falha (campo `can_edit` inexistente).
- [ ] **Step 3:** Adicionar `can_edit: bool = False` ao dataclass `DueQuestionItemDTO` em `src/application/dto/question_dto.py`.
- [ ] **Step 4:** Atualizar a query em `SqlAlchemyQuestionProgressRepository.get_due_questions` em `src/adapters/persistence/repositories.py` para selecionar `(func.coalesce(SubjectModel.owner_id, StudyMapModel.owner_id) == user_id).label("can_edit")` e repassar a `DueQuestionItemDTO`. Atualizar também `FakeQuestionProgressRepository` em `tests/unit/application/fakes.py`.
- [ ] **Step 5:** Executar a suíte de testes de aplicação e adaptadores para garantir aprovação de 100%.
- [ ] **Step 6:** Commit das alterações de DTO e Repositório.

---

### Task 2: Implementar Botão Sutil e Modal Acessível de Edição em `question_card.html`

**Files:**
- Modify: `src/adapters/web/templates/questions/partials/question_card.html:345-355` e final do arquivo
- Test: `tests/integration/web/test_question_web_controllers.py`

- [ ] **Step 1:** Escrever testes de integração em `tests/integration/web/test_question_web_controllers.py`:
  - Validar que o botão `id="btn-edit-question-modal"` aparece na tela de Provações Diárias quando `card.can_edit` é True.
  - Validar que `btn-edit-question-modal` NÃO aparece quando a matéria pertence a outro usuário (`can_edit=False`).
  - Validar que a estrutura do modal `id="edit-question-modal"` e os campos de formulário estão presentes.
- [ ] **Step 2:** Executar o teste e verificar que falha (botão e modal ainda não existem no template).
- [ ] **Step 3:** No template `src/adapters/web/templates/questions/partials/question_card.html`:
  - Adicionar o botão sutil logo abaixo de `#btn-dispute-evaluation`:
    ```html
    {% if card.can_edit %}
    <div class="mt-2 text-right sm:text-left">
        <button
            type="button"
            id="btn-edit-question-modal"
            onclick="openEditQuestionModal()"
            class="inline-flex items-center text-xs text-slate-400 hover:text-slate-600 dark:text-slate-500 dark:hover:text-slate-300 transition-colors focus:outline-none focus:ring-1 focus:ring-indigo-500 rounded px-1.5 py-1 cursor-pointer"
            title="Editar enunciado ou gabarito desta pergunta"
        >
            <span class="mr-1.5" aria-hidden="true">✏️</span>
            <span>Editar Pergunta / Gabarito</span>
        </button>
    </div>
    {% endif %}
    ```
  - Inserir o componente modal acessível `#edit-question-modal` com:
    - Textarea para `edit-question-prompt` preenchido com o texto da pergunta.
    - Textarea para `edit-question-expected-answer` preenchido com o texto do gabarito.
    - Botão "Salvar Alterações" e "Cancelar".
    - Funções JavaScript `openEditQuestionModal()`, `closeEditQuestionModal()` e `saveQuestionEdits(questionId)`.
  - Na função `saveQuestionEdits`:
    - Realiza `fetch('/api/v1/questions/' + questionId, { method: 'PUT', ... })`.
    - Ao receber status 200, atualiza o HTML de `#question-prompt` e `#expected-answer-content`.
    - Chama `if (window.applyRpgMarkdownAll) { window.applyRpgMarkdownAll(); }`.
    - Exibe feedback de sucesso efêmero e fecha o modal.
- [ ] **Step 4:** Executar `uv run pytest tests/integration/web/test_question_web_controllers.py` e verificar aprovação.
- [ ] **Step 5:** Commit das mudanças no template e controladores.

---

### Task 3: Teste End-to-End da Edição de Pergunta e Gabarito com Markdown Rico

**Files:**
- Create: `tests/integration/test_daily_srs_question_inline_edit.py`

- [ ] **Step 1:** Escrever teste de ponta a ponta simulando o fluxo completo:
  - Criação de matéria, tema e pergunta com Markdown mal formatado pelo usuário A.
  - Carregamento da página de Provações Diárias (`GET /questions/study`).
  - Verificação da presença de `btn-edit-question-modal` e do modal de edição.
  - Submissão da atualização via `PUT /api/v1/questions/{question_id}` com nova formatação de Markdown corrigida (com código e tabelas).
  - Recarregamento da página ou verificação do endpoint confirmando persistência e conformidade anti-XSS.
  - Validação de isolamento: usuário B acessa a mesma pergunta compartilhada, verifica ausência de `btn-edit-question-modal`, e tentativa de `PUT` retorna 403.
- [ ] **Step 2:** Executar o teste e garantir aprovação.
- [ ] **Step 3:** Executar a suíte de testes de regressão completa (`uv run pytest tests/`).
- [ ] **Step 4:** Commit final da funcionalidade.
