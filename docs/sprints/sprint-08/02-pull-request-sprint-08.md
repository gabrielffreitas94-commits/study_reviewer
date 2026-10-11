# Pull Request: Sprint 08 — Avaliação Semântica Aterrada (Texto), Tarifação de Tokens & Ledger (Marco 7 - Fase 3)

## 📌 1. Resumo Executivo

Este Pull Request conclui a implementação, homologação e auditoria formal da **Sprint 08 (Marco 7 - Fase 3)** do Study Reviewer. Esta sprint estabelece o subsistema de **avaliação semântica de respostas dissertativas em texto via IA aterrada em RAG**, acompanhado de um **Ledger transacional de tokens em duas fases (Hold & Settle)** para tarifação em tempo real e controle orçamentário anti-abuso (*FinOps*).

A arquitetura foi concebida para atender à volumetria de 1 milhão de usuários e mais de 50 mil temas independentes, assegurando:
1. **Aterramento Factual Rigoroso:** A resposta do estudante é confrontada simultaneamente com o enunciado da questão, o gabarito de referência e os fragmentos canônicos de conhecimento recuperados via busca vetorial por similaridade de cosseno (Sprint 07), com fallback transparente (*Cold-Start*) para o gabarito cadastrado quando o tema não possui base indexada.
2. **Avaliação Multidimensional:** Decomposição transparente da nota em Cobertura Conceitual (`coverage_score`), Precisão Factual (`accuracy_score`) e Profundidade Explicativa (`depth_score`), com feedback pedagógico formativo e pontos de melhoria acionáveis.
3. **Integração com Motor de Repetição Espaçada (SRS):** Atualização automática do agendamento de revisão com base na nota semântica atribuída pela IA, promovendo retenção de longo prazo.
4. **Proteção Financeira e Anti-Abuso (FinOps):** Protocolo transacional de tokens com retenção preventiva (`HOLD`), liquidação estrita pelo consumo real (`SETTLE`) e estorno automático (`REFUND_HOLD`) caso ocorra falha de inferência ou interrupção de rede.
5. **Mitigação Anti-Prompt Injection:** Enclausuramento estrito da resposta do estudante sob delimitadores `<student_answer_untrusted>` com instruções explícitas de não-obediência a comandos injetados na resposta, além de checagem defensiva de relevância com o enunciado.

A entrega cumpre rigorosamente os padrões de **Clean Architecture** e **TDD (Test-Driven Development)**:
- **100.00% de cobertura estrita de código** no backend (`src/`), com 3.912 statements e 0 linhas descobertas.
- **540 testes automatizados** passando sem qualquer falha.
- Zero alertas no linter `ruff` e zero pendências no `mypy` em modo estrito (124 arquivos validados).
- Governança de segurança AST verificada e aprovada com conformidade a CWEs e OWASP Top 10.
- Auditoria multidisciplinar concluída com aprovação unânime dos **13 Especialistas Técnicos**.

---

## 🏗️ 2. Arquitetura e Decisões Técnicas

A implementação respeita rigorosamente a inversão de dependências, mantendo o domínio totalmente desvinculado de bibliotecas de terceiros ou provedores específicos de nuvem/IA:

### 2.1 Camada de Domínio (`src/domain/`)
- **Entidades Puras:**
  - `TokenLedger`: Agregado raiz responsável pela custódia de saldo de tokens, retenções em curso (`hold_balance`), liquidação real (`settle`) e depósitos/recargas com validação de invariantes numéricas.
  - `TokenTransaction`: Registro imutável de transações no livro-razão financeiro (`HOLD`, `SETTLE`, `REFUND_HOLD`, `DEPOSIT`), com carimbo temporal e metadados contextuais.
  - `AnswerEvaluationResult`: Value object imutável contendo o veredito avaliativo com score ponderado (0-100), subscores analíticos, feedback detalhado, lista de conceitos identificados como faltantes e total de tokens consumidos na inferência.
- **Exceções de Domínio:**
  - `InsufficientTokensError`: Lançada com saldo disponível e valor requerido quando o estudante não possui saldo suficiente para a estimativa da avaliação.
  - `EvaluationServiceError`: Lançada quando a infraestrutura de IA apresenta falhas irrecuperáveis, disparando estorno de segurança do hold.
- **Protocolos (Portas de Domínio):**
  - `IAnswerEvaluationService`: Contrato assíncrono para avaliação de respostas dissertativas em texto contra gabaritos e fragmentos de conhecimento RAG.

### 2.2 Camada de Aplicação (`src/application/`)
- **Portas de Repositório (`src/application/ports/repositories.py`):**
  - `ITokenLedgerRepository`: Interface assíncrona para persistência e recuperação de livro-razão de tokens (`get_by_user_id`, `save`, `save_transaction`, `list_transactions_by_user_id`).
- **Casos de Uso (`src/application/use_cases/evaluation_use_cases.py`):**
  - `EvaluateStudentAnswerUseCase`: Orquestra verificação de titularidade da questão, validação de vencimento no SRS, pré-reserva transacional de tokens (`HOLD`), recuperação de contexto RAG via busca vetorial no tema, inferência semântica aterrada, liquidação exata dos tokens gastos (`SETTLE`), estorno seguro em caso de exceções (`REFUND_HOLD`), atualização do progresso SRS do usuário e registro no `ReviewAuditLog`.
  - `GetUserTokenBalanceUseCase`: Consulta o saldo total, saldo retido e saldo líquido disponível para novas avaliações.
  - `DepositTokensUseCase`: Credita tokens adquiridos ou bonificados pelo sistema no livro-razão do usuário com rastreabilidade auditável.
  - `ListTokenTransactionsUseCase`: Extrato histórico detalhado de todas as movimentações financeiras de tokens do usuário.
- **DTOs (`src/application/dto/evaluation_dto.py`):**
  - Modelos imutáveis com validação estrita para requisições de avaliação, respostas formatadas, saldos e extratos de transações.

### 2.3 Camada de Adaptadores & Infraestrutura (`src/adapters/` & `src/infrastructure/`)
- **Persistência Relacional (`src/adapters/persistence/`):**
  - `TokenLedgerModel` e `TokenTransactionModel`: Tabelas relacionais `token_ledgers` e `token_transactions` com integridade referencial, índices compostos e suporte para locking pessimista.
  - `TokenLedgerMapper` e `TokenTransactionMapper`: Mapeadores bidirecionais isolando ORM de entidades puras.
  - `SqlAlchemyTokenLedgerRepository`: Implementação assíncrona sobre `AsyncSession`.
- **Adaptadores de IA (`src/adapters/ai/gemini_adapters.py`):**
  - `GeminiAnswerEvaluationAdapter`: Implementa `IAnswerEvaluationService` utilizando modelos Gemini com JSON Schema forçado para resposta estruturada determinística, delimitação anti-prompt injection `<student_answer_untrusted>`, verificação de dispersão semântica (resposta totalmente desconexa recebe penalização com feedback construtivo) e suporte resiliente para cenários de Cold-Start.
- **Controladores de API REST (`src/adapters/api/evaluation_controllers.py`):**
  - `POST /api/v1/questions/{question_id}/evaluate-answer`: Submissão de resposta dissertativa com avaliação e tarifação atômica.
  - `GET /api/v1/users/{user_id}/token-balance`: Consulta de saldo de créditos de tokens.
  - `POST /api/v1/users/{user_id}/tokens/deposit`: Recarga ou crédito de saldo de tokens.
  - `GET /api/v1/users/{user_id}/tokens/transactions`: Extrato de auditoria transacional.
  - Injeção e registro configurados no FastAPI em `src/infrastructure/web/app.py`.

---

## 🛡️ 3. Pareceres Técnicos Formais dos 13 Especialistas

| **#** | **Especialista** | **Status** | **Síntese do Parecer Técnico** |
| :---: | :--- | :---: | :--- |
| **1** | **Especialista de Produto** | **APROVADO** | Aderência integral ao Marco 7 - Fase 3. Avaliação semântica com feedback formativo e notas multidimensionais (cobertura, precisão e profundidade) eleva substancialmente o valor percebido da plataforma. |
| **2** | **Especialista QA** | **APROVADO** | Testes de unidade e integração cobrem 100% dos fluxos e caminhos de exceção (hold, settle, refund, saldo insuficiente, cold-start, injection e auditoria). 540 testes passando com 100.00% de cobertura estrita. |
| **3** | **Especialista Arquiteto** | **APROVADO** | Princípios de Clean Architecture e DDD rigorosamente seguidos. Entidades `TokenLedger` e `AnswerEvaluationResult` são puras. Inversão de dependência via protocolo `IAnswerEvaluationService` isola o domínio do SDK de IA. |
| **4** | **Especialista de Segurança** | **APROVADO** | Proteção robusta contra Prompt Injection via enclausuramento em `<student_answer_untrusted>`, validação estrita de ownership da questão e prevenção de vazamento de créditos via transação em duas fases com UoW. |
| **5** | **Especialista de Telemetria** | **APROVADO** | Auditoria dupla: todas as avaliações gravam no `ReviewAuditLog` com contagem exata de tokens, tempo de resposta e método avaliativo, além do extrato imutável em `TokenTransaction`. |
| **6** | **Especialista de UX** | **APROVADO** | Resposta pedagógica de alta qualidade: o estudante recebe nota decomposta, justificativa clara e conceitos faltantes sem jargões técnicos ou exposição de prompts internos. |
| **7** | **Especialista de UI** | **APROVADO** | Contratos REST retornam estruturas previsíveis com status e mensagens claras para feedback visual instantâneo em componentes de progresso e saldo. |
| **8** | **Especialista de DevOps** | **APROVADO** | Código perfeitamente integrado à pipeline de CI/CD, execução em containers e compatibilidade simultânea com SQLite local e PostgreSQL / Neon em produção. |
| **9** | **Especialista de Acessibilidade** | **APROVADO** | Retorno JSON estruturado permite que leitores de tela anunciem notas, feedbacks e conceitos faltantes de forma hierarquizada e contextualizada. |
| **10** | **Especialista em LGPD** | **APROVADO** | Não há retenção desnecessária de identificadores biométricos ou PII nos logs de inferência; histórico financeiro de tokens vinculado de forma segura ao ciclo de vida da conta do titular (Art. 16 e 18). |
| **11** | **Especialista de Perf Python** | **APROVADO** | Utilização consistente de operações assíncronas (`async/await`) em todas as etapas de I/O de rede e banco, eliminando risco de gargalos no event loop principal. |
| **12** | **Especialista de Perf Mobile** | **APROVADO** | Payloads de resposta otimizados e DTOs enxutos, minimizando tráfego de dados e consumo de bateria em conexões móveis. |
| **13** | **Especialista de Perf de BD** | **APROVADO** | Índices em `user_id` e chaves estrangeiras; suporte a transações atômicas com `AsyncSession`, garantindo isolamento ACID durante retenção e liquidação de saldo sem lock prolongado. |

---

## 📊 4. Métricas Finais de Qualidade e Governança

```text
=============================== tests coverage ================================
TOTAL: 3.912 statements | 0 missed | 100.00% strict coverage
Result: 540 passed in 19.61s (Backend)
Governance AST: test_security_governance.py aprovado (100% compliance)
Security Markers: 87 security-marked tests passed
Linter (ruff): All checks passed!
Type Checking (mypy): Success: no issues found in 124 source files
```

---

## 🚀 5. Próximos Passos (Sprint 09)

Após a aprovação e merge deste PR em `staging`:
- **Sprint 09 (Marco 7 - Fase 4):**
  - Avaliação Multimodal de Respostas em Áudio (Voz Efêmera, Sem Armazenamento de Biometria de Voz - LGPD Art. 16).
  - Conselho Multiagente de Contestação / Crítica ("Contestar Avaliação"): Generator, Critic e Auditor reavaliando respostas contestadas pelo aluno contra a base RAG.
