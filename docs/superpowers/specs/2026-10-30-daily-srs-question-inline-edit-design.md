# Design Doc: Edição Sutil de Pergunta e Gabarito nas Provações Diárias

- **Data:** 2026-10-30
- **Status:** Proposto
- **Escopo:** Pequena Mudança (Small Change)

---

## 1. Intenção e Motivação
Durante as sessões de estudo ativo nas Provações Diárias (`/questions/study`), o usuário pode se deparar com enunciados ou gabaritos (`expected_answer`) mal formatados (como quebras de linha em Markdown, blocos de código ou tabelas desajustados). Atualmente, corrigir esse texto exige sair da tela de estudo, navegar até o catálogo de matérias ou gerenciador de perguntas e reencontrar o item. O objetivo é permitir que o usuário proprietário da pergunta possa editá-la e corrigir a formatação de forma imediata e sutil, sem interromper ou desorganizar a revisão SRS.

---

## 2. Metas, Não-Metas e Anti-Metas

### Metas
- Inserir um botão de ação discreto na interface do card das Provações Diárias, posicionado logo abaixo/ao lado do botão "Contestar Avaliação".
- Exibir esse botão **exclusivamente** quando o usuário autenticado for o proprietário da matéria ou mapa de estudo ao qual a pergunta pertence (`card.can_edit == True`).
- Permitir edição tanto do enunciado (`prompt`) quanto da resposta esperada (`expected_answer`).
- Salvar as alterações via API existente (`PUT /api/v1/questions/{question_id}`), mantendo a sanitização de segurança (anti-XSS).
- Atualizar o DOM na hora e reexecutar a renderização de Markdown (`applyRpgMarkdownAll()`) sem recarregar a página e sem perder o estado atual da sessão (slider de nota, presets, timers).

### Não-Metas
- Permitir edição de perguntas por estudantes que não sejam proprietários (matérias públicas/compartilhadas).
- Alterar o algoritmo de repetição espaçada (SRS) ou os intervalos ao editar o texto.
- Implementar histórico complexo de versões ou controle de diff no card.

### Anti-Metas
- Evitar poluição visual ou botões chamativos que distraiam do fluxo de memorização ativa quando não forem necessários.
- Evitar saltos de layout (*Cumulative Layout Shift* - CLS) que desloquem os controles de autoavaliação (slider de 0 a 100% e presets).

---

## 3. Restrições
- **Segurança & Propriedade:** Manter o princípio de menor privilégio e verificação rigorosa de posse (`can_be_edited_by`). Se um usuário não for o dono, a API retorna `403 Forbidden` e a interface nem sequer exibe o botão.
- **Higienização:** O input deve passar obrigatoriamente por `MarkdownSanitizerService.sanitize()` no backend.
- **Acessibilidade (WCAG 2.1 AA):** O modal de edição deve ter rótulos `aria-*`, fechamento com tecla `Esc` e foco adequado.

---

## 4. Abordagens Consideradas

1. **Abordagem 1: Modal Rápido de Edição (Escolhida)**
   - Um botão discreto (`✏️ Editar Pergunta`) abaixo de "Contestar Avaliação" abre um modal leve com textareas para Enunciado e Gabarito. Ao salvar, atualiza os nós `#question-prompt` e `#expected-answer-content` e reaplica o Markdown.
   - *Vantagens:* Consistência com os modais existentes no card (Áudio e Contestação), zero deslocamento de layout na sessão de estudo, responsivo em mobile e desktop.
   - *Trade-off:* Requer abrir e fechar uma camada sobreposta.

2. **Abordagem 2: Edição Inline no Próprio Card**
   - Transforma o enunciado e o gabarito no próprio card em textareas editáveis ao clicar no botão.
   - *Trade-off descartado:* Textos longos com tabelas e código causam layout shift severo, empurrando o formulário de notas SRS para fora da viewport visível.

3. **Abordagem 3: Micro-edição Exclusiva do Gabarito**
   - Um link sutil que altera somente a caixa do gabarito.
   - *Trade-off descartado:* Não resolve quando o erro de formatação estiver no enunciado (`prompt`).

---

## 5. Especificação da Solução (Como será construído)

### 5.1 Backend & DTOs
1. **`DueQuestionItemDTO`** (`src/application/dto/question_dto.py`):
   - Adicionar o campo `can_edit: bool = False`.
2. **`SqlAlchemyQuestionProgressRepository.get_due_questions`** (`src/adapters/persistence/repositories.py`):
   - Na query SQL, incluir cálculo de propriedade comparando `coalesce(SubjectModel.owner_id, StudyMapModel.owner_id) == user_id` e preencher `can_edit=row.can_edit`.

### 5.2 Frontend & Template
1. **`src/adapters/web/templates/questions/partials/question_card.html`**:
   - Logo abaixo do contêiner do botão `#btn-dispute-evaluation`, renderizar condicionalmente:
     ```html
     {% if card.can_edit %}
     <div class="pt-2 flex justify-end sm:justify-start">
         <button
             type="button"
             id="btn-edit-question-modal"
             onclick="openEditQuestionModal()"
             class="inline-flex items-center text-xs text-slate-400 hover:text-slate-600 dark:text-slate-500 dark:hover:text-slate-300 transition-colors focus:outline-none focus:ring-1 focus:ring-indigo-500 rounded px-1.5 py-1"
             title="Editar enunciado ou gabarito desta pergunta"
         >
             <span class="mr-1" aria-hidden="true">✏️</span>
             <span>Editar Pergunta / Gabarito</span>
         </button>
     </div>
     {% endif %}
     ```
   - Inserir o modal acessível `#edit-question-modal` com:
     - Campo `prompt` (textarea com contador e suporte a Markdown).
     - Campo `expected_answer` (textarea com contador e suporte a Markdown).
     - Botões "Cancelar" e "Salvar Alterações".
     - Script JS com função `saveQuestionEdits(questionId)` que dispara `fetch('PUT /api/v1/questions/' + questionId)`, atualiza o DOM e chama `applyRpgMarkdownAll()`.

---

## 6. Decisões do Construtor
- Reutilizar classes utilitárias já padronizadas no card (`rpg-panel`, `focus:ring-indigo-500`).
- Atualizar os testes de integração para verificar o render condicional de `can_edit` e a integridade da edição.
