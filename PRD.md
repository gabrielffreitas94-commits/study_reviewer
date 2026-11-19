# Product Requirements Document (PRD) — v10.0
## Study Reviewer — Workspace Local Offline de Revisão Ativa, Repetição Espaçada & Árvore de Habilidades RPG

> **Resumo da Versão v10.0 (Edição Local & Offline):**
> - **Workspace 100% Local e Offline:** Execução autossuficiente via FastAPI + Jinja2 + HTMX + Tailwind CSS estático, sem dependência de internet, CDNs externas, serviços de nuvem ou provedores de IA.
> - **Autenticação Local Segura:** Registro e login com credenciais locais (hash criptográfico com salt) e sessões stateless cifradas com **AES-256-GCM** (cookies `HttpOnly` / `SameSite=Lax` e Bearer tokens).
> - **Flashcards por Pool Contínua:** Rotação de baralho com Gap Indexing (múltiplos de 100), inserção estocástica nos primeiros 10% do acervo, flip 3D client-side e sincronização assíncrona.
> - **Perguntas Abertas com SRS Estrito:** Algoritmo determinístico por calendário (`[1, 7, 15, 30, 60, 90, 180]` dias) com modo **Responder por Escrito** (`WRITTEN_SELF_REVIEW`) e **Gabarito Direto** (`MANUAL`), além de edição inline com Markdown.
> - **Códice de Habilidades (Árvore RPG) & Tomo do Nó:** Grafo interativo no canvas HTML/SVG com pré-requisitos entre nós, desbloqueio por nível, editor Markdown de resumo teórico, importação de questões em lote via JSON e modo treino livre.
> - **Biblioteca de Materiais Locais:** Cadastro de textos e extração local de documentos `.pdf`, `.docx`, `.txt` e `.md` vinculados a múltiplos temas (`N:N`).
> - **Hub de Desempenho (`Crônicas & Atributos`) & LGPD:** Auditoria histórica imutável (*snapshot isolation*), métricas de retenção madura (Nível 4+), exportação integral em **CSV** e **JSON**, e fluxo de exclusão/anonimização de conta local.

---

## 1. Visão Geral do Produto

### 1.1 Missão
O **Study Reviewer** é uma aplicação web local e offline projetada para maximizar a retenção cognitiva de longo prazo por meio de estudo ativo, organização visual em grafo RPG e repetição espaçada determinística, mantendo soberania total dos dados no dispositivo do estudante.

### 1.2 Pilares Funcionais
1. **Códice de Habilidades (Árvore de Estudos RPG & Tomo do Nó):**
   * Canvas interativo com pan, zoom, arraste de medalhões, criação rápida de nós filhos e conexões de pré-requisito com nível mínimo exigido.
   * Side Drawer rápido e página dedicada (**Tomo do Nó**) com resumo em Markdown, materiais de apoio anexados, arena de revisão com 4 botões SRS (`again`, `hard`, `good`, `easy`), rascunho escrito opcional e cadastro de questões unitário, em tabela ou em bloco JSON.
2. **Flashcards (Pool Contínua por Rodadas):**
   * Fila de estudo por matéria/tema ou global com ordenação base por Gap Indexing (múltiplos de 100) e inserção nos primeiros 10% do catálogo.
   * Virada 3D 100% client-side, atalhos de teclado (`Espaço`, `Enter`, `Seta Direita`) e buffer de prefetch local.
3. **Provações Diárias (Perguntas Abertas com SRS Estrito):**
   * Fila diária de revisões vencidas com renderização Markdown segura (`rpg-markdown`).
   * Dois modos de estudo: **Responder por Escrito** (o aluno redige a resposta localmente e compara com o gabarito antes de pontuar) e **Gabarito Direto** (recordação mental + autoavaliação de 0% a 100% via slider ou presets).
   * Edição inline de enunciado e gabarito pelo proprietário da matéria com modal acessível (WCAG 2.1 AA).
4. **Biblioteca de Materiais Locais:**
   * Armazenamento de textos didáticos e extração textual offline de arquivos `.pdf`, `.docx`, `.txt` e `.md` (limite de 15 MB) vinculados a múltiplos temas (`N:N`) ou nós da árvore.
5. **Crônicas & Atributos (Hub de Desempenho & Portabilidade LGPD):**
   * Trilha de auditoria imutável (`review_audit_logs`) com *snapshot* histórico de nomes de matéria e tema.
   * Indicadores de retenção global, retenção madura (Nível 4+: 60, 90 e 180 dias), paginação HTMX e exportação completa em **JSON** e **CSV**.

---

## 2. Arquitetura e Engenharia

### 2.1 Clean Architecture (4 Camadas)
* **Domain (`src/domain/`):** Entidades, exceções, protocolos e serviços de domínio em Python puro (sem dependência de FastAPI, SQLAlchemy ou bibliotecas web).
* **Application (`src/application/`):** Casos de uso agnósticos e DTOs orientados a protocolos/interfaces.
* **Adapters (`src/adapters/`):** Controladores Web (Jinja2 + HTMX) e REST API (FastAPI), repositórios SQLAlchemy, mappers, gerador de ícones SVG e assets estáticos locais.
* **Infrastructure (`src/infrastructure/`):** Configuração via Pydantic Settings, conexão SQLite/PostgreSQL, criptografia AES-256-GCM, hashing de senhas, sanitização HTML (`nh3`), rate limiting local e logging estruturado.

### 2.2 Algoritmo SRS das Perguntas Abertas
$$\text{Intervalos} = [1, 7, 15, 30, 60, 90, 180] \text{ dias}$$

| Nível | Intervalo | Nota = 100% | Nota < 100% |
| :---: | :---: | :--- | :--- |
| **0** | 1 dia | Avança para **Nível 1** (+7 dias) | Permanece no **Nível 0** (`hoje + 1d`) |
| **1** | 7 dias | Avança para **Nível 2** (+15 dias) | Permanece no **Nível 1** (`hoje + 7d`) |
| **2** | 15 dias | Avança para **Nível 3** (+30 dias) | Permanece no **Nível 2** (`hoje + 15d`) |
| **3** | 30 dias | Avança para **Nível 4** (+60 dias) | Permanece no **Nível 3** (`hoje + 30d`) |
| **4** | 60 dias | Avança para **Nível 5** (+90 dias) | Permanece no **Nível 4** (`hoje + 60d`) |
| **5** | 90 dias | Avança para **Nível 6** (+180 dias) | Permanece no **Nível 5** (`hoje + 90d`) |
| **6** | 180 dias | Permanece no **Nível 6** (`hoje + 180d`) | Regride para o **Nível 2** (`hoje + 15d`) |

---

## 3. Segurança, Privacidade e Acessibilidade

* **Sessões AES-256-GCM:** Tokens de sessão cifrados com nonce aleatório de 96 bits e tag de autenticação de 128 bits, entregues em cookie `HttpOnly` / `SameSite=Lax` ou `Authorization: Bearer`.
* **Isolamento Multi-Tenant Local (Anti-IDOR):** Toda leitura e mutação valida a titularidade do usuário autenticado (`user_id == owner_id`).
* **Sanitização XSS:** Conteúdos em Markdown e textos livres são higienizados antes da persistência com `nh3` e escapados na renderização client-side.
* **Zero Dependências Externas em Runtime:** Todos os scripts (`htmx.min.js`, `study.js`, `study_canvas.js`, `rpg_icons.js`) e folhas de estilo (`tailwind.css`, `app.css`) são servidos localmente.
* **Acessibilidade (WCAG 2.1 AA):** Link *"Pular para o conteúdo principal"*, regiões `aria-live="polite"`, navegação por teclado e modais com `role="dialog"`, `aria-modal="true"` e fechamento via `Escape`.
* **LGPD Local:** Portabilidade de dados (CSV/JSON) e exclusão de conta com anonimização estatística (`ON DELETE SET NULL` no histórico).
