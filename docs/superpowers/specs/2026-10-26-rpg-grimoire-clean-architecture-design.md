# Documento de Design — Reestruturação Concisa: Códice RPG (Grimório & Forja Ancestral)

**Data:** 26 de Outubro de 2026  
**Projeto:** Study Reviewer  
**Tamanho do Trabalho:** Projeto (Refatoração Estrutural Clean Slate + Redesign Visual RPG)

---

## 1. Intenção e Motivação (O Porquê)

O sistema acumulou duas arquiteturas paralelas e incompatíveis ao longo das sprints anteriores:
1. O modelo antigo baseado em pastas rasas (**Matérias `Subject`**, **Temas `Topic`** e **Flashcards `Flashcard`** sem SRS), espalhado por menus de `/cadastros`, `/subjects`, `/study` e `/flashcards/new`.
2. O modelo de **Árvore de Estudos (`StudyMap` e `StudyNode`)**, que foi acoplado por cima sem permitir criar conteúdos diretamente nos nós (exigindo "vincular" itens cadastrados nas telas antigas), sem exibir o texto dos materiais anexados e redirecionando o botão de revisão do nó para uma fila global desconectada.
3. Além disso, a interface mantinha aparência de **software corporativo / SaaS** (tons `slate`, botões `indigo-600`, tipografia de escritório), quebrando completamente a imersão de uma árvore de habilidades de RPG.

Como **não há usuários em produção**, a decisão é **derrubar todo o legado redundante e reconstruir sobre uma estrutura única, limpa e coesa**:
- Toda área de estudo é uma **Árvore de Habilidades (`StudyMap`)**.
- Todo tópico dentro da árvore é um **Nó (`StudyNode`)** conectado por pré-requisitos (`StudyEdge` em grafo acíclico dirigido — DAG).
- Todo nó possui apenas dois pilares criados e consumidos **diretamente na Página Dedicada do Nó**:
  1. **📖 Tomo de Sabedoria (`KnowledgeSource` / Notas Teóricas):** O texto teórico e/ou PDF daquele tópico para leitura e base de correção da IA (RAG).
  2. **⚔️ Provações de Maestria (`Question` com SRS de 7 níveis):** Perguntas abertas que podem ser respondidas revelando o gabarito direto (como um flashcard com SRS), digitando texto (avaliado por IA) ou gravando voz (avaliado por IA multimodal).

---

## 2. Objetivos, Não-Objetivos e Anti-Objetivos

### 2.1 Objetivos (Goals)
1. **Modelo de Domínio e Banco Unificados (Clean Slate):**
   - Eliminar `Subject`, `Topic`, `Flashcard`, `FlashcardPoolSession`, sub-mapas fractais (`parent_node_id`) e tabelas intermediárias N:N órfãs.
   - Vincular `Question` e `KnowledgeSource` **diretamente a um `StudyNode`** (`node_id UUID NOT NULL REFERENCES study_nodes(id) ON DELETE CASCADE`).
   - Vincular `ReviewAuditLog` ao `StudyMap` e `StudyNode` (`map_id`, `node_id`, `historical_map_title`, `historical_node_title`) em vez de `subject_id`/`topic_id`.
2. **Navegação Enxuta em 3 Áreas:**
   - **⚔️ Códice de Habilidades (`/study-maps`, rota raiz `/`):** Lista de Árvores de Habilidades, botão de geração imediata da Árvore Modelo (Matemática Aplicada) e acesso ao Canvas da Árvore (`/study-maps/{map_id}/canvas`).
   - **🔥 Provações Diárias (`/questions/study`):** Fila unificada de perguntas cujo prazo de repetição espaçada venceu (`next_review_date <= hoje`), permitindo filtrar opcionalmente por Árvore (`map_id`).
   - **🏆 Crônicas & Atributos (`/performance`):** Painel de métricas de retenção, saldo de tokens IA e histórico de auditoria das provações.
3. **Fluxo Árvore $\to$ Página Dedicada do Nó (Opção B):**
   - No Canvas (`/study-maps/{map_id}/canvas`), clicar em um nó navega para a **Página Dedicada do Nó (`/study-maps/{map_id}/nodes/{node_id}`)** em tela cheia (exceto quando o modo de conexão de arestas estiver ativo no editor).
   - Na Página Dedicada do Nó, o estudante visualiza o **Tomo de Sabedoria** na coluna esquerda (lendo o conteúdo completo na tela, editando o texto ou enviando PDF/DOCX/TXT) e as **Provações de Maestria (SRS)** na coluna direita (criando novas perguntas e respondendo-as ali mesmo sem sair da página).
4. **Identidade Visual RPG — Grimório & Forja Ancestral (Direção 1):**
   - Paleta baseada em pedra obsidiana (`#0c0908`, `#14100d`), couro/pergaminho escuro (`#1c1612`), bronze forjado (`#785a28`), ouro ancestral (`#c89b3c`, `#f0c869`), verde esmeralda arcano (`#10b981`) e carmesim de alerta (`#e11d48`).
   - Tipografia épica serifada (`Cinzel`) para títulos, cabeçalhos, patentes (`RANK 0..VI`) e botões de ação; tipografia editorial (`Cormorant Garamond` / serifada legível) para leitura de textos teóricos no Tomo; `Plus Jakarta Sans` / `Inter` para formulários e controles densos.
   - Nós no Canvas renderizados como **Medalhões Circulares de Habilidade** com molduras que evoluem visualmente conforme o Rank SRS:
     - **Selado (Bloqueado):** Ferro fosco tracejado + cadeado (`🔒 SELADO`).
     - **Rank 0 (Despertado):** Moldura de ferro/pedra ativa, pronta para estudo.
     - **Rank I a II (Bronze Forjado):** Todas as perguntas do nó atingiram nível $\ge 1$ (libera as trilhas de energia dourada para os nós dependentes).
     - **Rank III a IV (Prata Rúnica):** Maestria intermediária ($15\text{d}$ a $30\text{d}$).
     - **Rank V a VI (Ouro Lendário):** Maestria máxima ($60\text{d}$ a $180\text{d}$) com halo dourado pulsante.
     - **Alerta de Decaimento (Overdue):** Pulsação carmesim quando há provações vencidas no nó.

### 2.2 Não-Objetivos (Non-Goals)
- Não haverá módulo separado de Flashcards (o modo *🔮 Revelar Runas / Gabarito Direto* nas Perguntas SRS cumpre esse papel com progressão real).
- Não haverá Sub-mapas Fractais (`parent_node_id`). Cada Árvore é um grafo plano e claro.
- Não haverá "Biblioteca Global" separada nem modal de "+ Vincular item existente" — cada resumo/material e cada pergunta pertence diretamente ao seu Nó.
- Não manteremos compatibilidade com rotas ou tabelas legadas de `Subject`, `Topic` e `Flashcard`.

### 2.3 Anti-Objetivos (Anti-Goals)
- **Aparência de SaaS Corporativo:** É proibido usar o visual antigo de escritório (`bg-slate-50`, cards brancos genéricos, botões `indigo-600` padrão) nas telas do produto.
- **Fluxos Cegos ou Quebrados:** Clicar para estudar/revisar dentro de um Nó nunca deve jogar o usuário em uma tela sem contexto; o estudo do Nó acontece dentro da própria Página Dedicada do Nó (`/study-maps/{map_id}/nodes/{node_id}`).

---

## 3. Restrições Arquiteturais (Constraints)

1. **Clean Architecture em 4 Camadas (`ADR-001`):**
   - `src/domain/`: Entidades puras (`User`, `StudyMap`, `StudyNode`, `StudyEdge`, `Question`, `UserQuestionProgress`, `KnowledgeSource`, `KnowledgeChunk`, `ReviewAuditLog`), serviços de domínio (`DAGValidatorService`, `StudyTreeProgressionService`, `SpacingPolicyService`, `DocumentTextExtractorService`) e exceções. Zero dependências de ORM/FastAPI.
   - `src/application/`: Casos de uso, DTOs e portas (`repositories.py`).
   - `src/adapters/`: Controladores Web (Jinja2 + HTMX + JS nativo), Controladores REST API (`/api/v1/...`), Repositórios SQLAlchemy e Adaptadores de IA Gemini (`gemini_adapters.py`).
   - `src/infrastructure/`: Banco de dados, autenticação Google OAuth2 / sessão AES-256-GCM, configuração, clock e sanitização HTML/Markdown.
2. **Zero Build Step Complexo de Frontend:**
   - Continuamos com Jinja2 + HTMX + Vanilla JS (`study_canvas.js`) + CSS (`tailwind.css` + variáveis e classes RPG em `app.css` e Google Fonts `Cinzel` / `Cormorant Garamond`), mantendo o deploy Docker/Lambda leve e instantâneo.
3. **Motor SRS e Avaliação Multimodal IA Preservados:**
   - O calendário SRS estrito de 7 níveis (`[1, 7, 15, 30, 60, 90, 180]` dias em `SpacingPolicyService`), a avaliação por Texto com RAG (`EvaluateTextAnswerUseCase`), a avaliação por Voz Multimodal (`EvaluateAudioAnswerUseCase`) e o Conselho Multiagente de Contestação (`DisputeEvaluationUseCase`) continuam funcionando integralmente, agora ancorados diretamente no `StudyNode`.

---

## 4. Abordagens Consideradas e Escolha

1. **Abordagem 1 — Camada de Fachada sobre `Subject`/`Topic` Legados:**
   - Esconderia `Subject`, `Topic` e `Flashcard` apenas na interface, mantendo as tabelas antigas e sincronizando registros fantasmas nos bastidores.
   - *Desvantagem:* Mantém código morto, tabelas duplicadas e complexidade desnecessária num projeto que ainda não tem usuários em produção.
2. **Abordagem 2 (Escolhida pelo Usuário) — Reestruturação Limpa do Zero (Clean Slate):**
   - Derruba as tabelas, entidades, rotas e templates legados de `Subject`, `Topic` e `Flashcard`, consolidando uma migração limpa centrada exclusivamente em `StudyMap` $\to$ `StudyNode` $\to$ (`KnowledgeSource` + `Question`).
   - *Vantagem:* Arquitetura enxuta, banco de dados coeso, zero código zumbi e compreensão imediata de ponta a ponta.

---

## 5. Especificação Detalhada do Design

### 5.1 Esquema de Dados Consolidado (`src/adapters/persistence/models.py`)

- **`users`**: `id (PK)`, `google_sub`, `email`, `name`, `avatar_url`, `monthly_token_limit`, `tokens_used_this_month`, `billing_cycle_Anchor`, `created_at`.
- **`study_maps`**:
  - `id (UUID PK)`
  - `owner_id (UUID FK -> users.id ON DELETE CASCADE, INDEX)`
  - `title (VARCHAR(200) NOT NULL)`
  - `description (TEXT)`
  - `is_public (BOOLEAN NOT NULL DEFAULT FALSE)`
  - `created_at`, `updated_at`
- **`study_nodes`**:
  - `id (UUID PK)`
  - `map_id (UUID FK -> study_maps.id ON DELETE CASCADE, INDEX)`
  - `title (VARCHAR(150) NOT NULL)`
  - `description (TEXT)` — Breve subtítulo/resumo do medalhão
  - `theory_content (TEXT NOT NULL DEFAULT '')` — Texto principal do **Tomo de Sabedoria** editável diretamente na Página do Nó (também indexado em chunks RAG quando salvo!)
  - `pos_x (FLOAT NOT NULL DEFAULT 0.0)`
  - `pos_y (FLOAT NOT NULL DEFAULT 0.0)`
  - `icon (VARCHAR(50) NOT NULL DEFAULT 'rune')`
  - `created_at`, `updated_at`
- **`study_edges`**:
  - `id (UUID PK)`
  - `map_id (UUID FK -> study_maps.id ON DELETE CASCADE, INDEX)`
  - `source_node_id (UUID FK -> study_nodes.id ON DELETE CASCADE)`
  - `target_node_id (UUID FK -> study_nodes.id ON DELETE CASCADE)`
  - `created_at`
  - Unique `(map_id, source_node_id, target_node_id)` e Check `source_node_id <> target_node_id`.
- **`knowledge_sources`** (Arquivos/Textos complementares do Tomo do Nó para leitura e RAG):
  - `id (UUID PK)`
  - `node_id (UUID FK -> study_nodes.id ON DELETE CASCADE, INDEX)`
  - `owner_id (UUID FK -> users.id ON DELETE CASCADE, INDEX)`
  - `title (VARCHAR(200) NOT NULL)`
  - `content_type (VARCHAR(20) NOT NULL)` — `TEXT`, `PDF`, `DOCX`, `MARKDOWN`
  - `raw_text (TEXT NOT NULL DEFAULT '')` — Texto integral extraído para leitura direta no Tomo do Nó!
  - `char_count (INT)`, `total_chunks (INT)`, `created_at`
- **`knowledge_chunks`**:
  - `id (UUID PK)`, `source_id (UUID FK -> knowledge_sources.id ON DELETE CASCADE)`, `chunk_index`, `content`, `embedding_json`, `created_at`.
- **`questions`** (Provações de Maestria SRS do Nó):
  - `id (UUID PK)`
  - `node_id (UUID FK -> study_nodes.id ON DELETE CASCADE, INDEX)`
  - `owner_id (UUID FK -> users.id ON DELETE CASCADE, INDEX)`
  - `prompt (TEXT NOT NULL)`
  - `expected_answer (TEXT NOT NULL)`
  - `created_at (DATE NOT NULL)`
- **`user_question_progress`**:
  - `user_id (UUID PK, FK -> users.id ON DELETE CASCADE)`
  - `question_id (UUID PK, FK -> questions.id ON DELETE CASCADE)`
  - `current_level (INT NOT NULL DEFAULT 0)` — `0` a `6`
  - `next_review_date (DATE NOT NULL, INDEX)`
  - `last_reviewed_at (TIMESTAMP WITH TIME ZONE NULL)`
- **`review_audit_logs`**:
  - `id (UUID PK)`, `user_id`, `question_id (NULLABLE ON DELETE SET NULL)`, `map_id (UUID)`, `node_id (UUID)`, `historical_map_title (VARCHAR(200))`, `historical_node_title (VARCHAR(150))`, `review_date`, `score`, `level_before`, `level_after`, `evaluation_mode`, `ai_feedback_json`, `logged_at`.

### 5.2 Fluxo de Telas e Interações

#### Tela 1: Códice de Habilidades (`/study-maps` e `/`)
- Exibe os cards das Árvores de Habilidades do usuário em estilo **Placa de Grimório** (fundo obsidiana/couro, borda de bronze `#785a28`, título em `Cinzel`, progresso de nós dominados `X / Y Nós Despertados`, alerta se houver provações vencidas naquela árvore).
- Ações no topo:
  - **✨ Forjar Nova Árvore:** Modal em estilo grimório para criar mapa em branco (Título, Descrição, Público/Privado).
  - **📐 Invocar Árvore Modelo (Matemática Aplicada):** Gera instantaneamente a árvore demonstrativa com 5 nós conectados em DAG, textos teóricos ricos no Tomo de cada nó e 3 Provações SRS por nó.

#### Tela 2: Canvas da Árvore de Talentos (`/study-maps/{map_id}/canvas`)
- **Barra de Comando da Árvore:**
  - Botão `← Códice de Árvores`, Título da Árvore em `Cinzel`, resumo de progresso (`Nós Dominados: X/Y`).
  - Alternância clara: **⚔️ Modo Jornada (Estudo)** vs **⚒️ Modo Forja (Editor da Árvore)**.
  - No **Modo Forja (Editor)**: botões `+ Forjar Nó` e `🔗 Traçar Vínculo (Pré-requisito)`, além de permitir arrastar nós livremente (salvando coordenadas via debounce) e remover conexões clicando nelas.
- **Visual do Canvas:**
  - Fundo escuro de pedra obsidiana com grade pontilhada dourada sutil e vinheta dramática.
  - Arestas (`StudyEdge`): Linhas tracejadas de ferro quando o pré-requisito está em `Rank 0`; feixes contínuos de **energia dourada brilhante** quando o pré-requisito atingiu `Rank >= I`.
  - Nós (`StudyNode`): **Medalhões Circulares** com ícone rúnico/temático, badge inferior `RANK 0..VI` (ou `🔒 SELADO` se bloqueado), contador de provações (`⚔️ 3`) e chama carmesim se houver revisão vencida.
- **Ação ao Clicar num Nó:**
  - Em vez do antigo drawer estreito, clicar em um nó no Modo Jornada abre diretamente a **Página Dedicada do Nó (`/study-maps/{map_id}/nodes/{node_id}`)** (no Modo Forja, há também um botão rápido de editar título/ícone/excluir ou abrir o Grimório do nó).

#### Tela 3: Página Dedicada do Nó — O Grimório Aberto (`/study-maps/{map_id}/nodes/{node_id}`)
- **Cabeçalho do Nó (HUD RPG):**
  - Link `← Retornar à Árvore: {map.title}`.
  - Ícone em medalhão, Título do Nó em `Cinzel`, subtítulo/descrição, badge de status (`🔓 Desbloqueado` ou `🔒 Selado — Requer: [Lista de Nós Pré-requisitos]`), **Patente Atual (`RANK 0` a `RANK VI`)** e **Barra de Progresso de Maestria** (mostrando quantas provações do nó já alcançaram pelo menos `Rank I`).
  - Botões de edição rápida do Nó (Editar Título/Ícone ou Excluir Nó, se proprietário).
- **Layout Bipartido em Tela Cheia (Duas Colunas do Grimório):**
  - **Coluna Esquerda — 📖 Tomo de Sabedoria (Teoria & Pergaminhos):**
    - Exibe o **Texto Teórico Principal (`theory_content`)** formatado com tipografia de livro (`Cormorant Garamond`, leitura confortável sobre fundo de pergaminho escuro `#14100d`).
    - Botão **`[✍️ Escrever / Editar Tomo]`**: Abre o editor inline ali mesmo para o estudante escrever ou colar seu resumo em Markdown/texto e salvar direto no nó (indexando automaticamente para o RAG da IA).
    - Seção **Pergaminhos Anexados (PDF / DOCX / TXT)**: Permite fazer upload de arquivos complementares para aquele nó e **expandir/ler o texto extraído diretamente ali**, sem sair da página.
  - **Coluna Direita — ⚔️ Provações de Maestria (SRS & IA):**
    - **Arena de Provação Ativa no Topo da Coluna:**
      - Se houver perguntas no nó, o estudante pode clicar em **"⚔️ Iniciar Provação deste Nó"** (ou selecionar qualquer pergunta da lista abaixo) para responder ali mesmo na coluna direita!
      - O card de provação oferece os 3 modos:
        1. **🔮 Revelar Runas (Gabarito Direto):** Revela a resposta esperada na hora e permite autoavaliar de `0%` a `100%` (presets `0%`, `25%`, `50%`, `75%`, `100%` + slider).
        2. **✍️ Conjurar Resposta (Texto + IA RAG):** Digita a resposta e recebe nota + feedback pedagógico da IA ancorado no Tomo da coluna esquerda.
        3. **🎙️ Voz Arcana (Áudio + IA Multimodal):** Grava a explicação falada e recebe transcrição + nota da IA.
      - Ao confirmar a nota:
        - Se a pergunta estava em `Rank 0` ou vencida (`next_review_date <= hoje`), atualiza o nível SRS no banco, registra no `ReviewAuditLog` e atualiza imediatamente o Rank do Nó! Se todas as perguntas do nó atingirem `Rank >= I`, exibe um banner épico: **"⚡ NÓ DOMINADO (RANK I)! Novos caminhos foram destrancados na Árvore!"**.
        - Se a pergunta já foi revisada hoje (`next_review_date > hoje`), permite responder em **Modo Treino Livre** (mostra o gabarito/feedback da IA normalmente, mantendo a data oficial da próxima revisão SRS intacta em vez de travar com erro).
    - **Lista de Provações do Nó + Botão `[+ Forjar Nova Provação]`:**
      - Formulário inline rápido para criar uma nova pergunta (Enunciado + Gabarito Esperado) direto no nó com 1 clique, além de editar ou excluir perguntas existentes do nó.

#### Tela 4: Provações Diárias (`/questions/study`) e Crônicas (`/performance`)
- **`/questions/study`**: Mantém a fila global de revisões vencidas hoje (`next_review_date <= hoje`) com o novo tema visual **Grimório & Forja Ancestral**, mostrando a qual **Árvore / Nó** cada pergunta pertence e permitindo filtrar por Árvore (`map_id`).
- **`/performance`**: Exibe os indicadores de retenção, uso de tokens IA e tabela de auditoria com os nomes históricos da Árvore e do Nó, totalmente estilizados na paleta RPG.

---

## 6. O que fica a critério do Construtor (Builder's Calls)

- Detalhes de espaçamento CSS, animações de brilho (`box-shadow` / `keyframes`) e SVGs ornamentais das molduras dos medalhões.
- Organização interna dos endpoints HTMX/JSON entre a Página Dedicada do Nó e os casos de uso.
- Estratégia de reset das migrations Alembic (consolidar em uma migration limpa ou adicionar uma migration de reestruturação total compatível com SQLite de testes e PostgreSQL/Neon).
