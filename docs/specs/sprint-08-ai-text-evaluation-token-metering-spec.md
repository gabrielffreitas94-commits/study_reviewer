# Especificação Técnica: Sprint 08 — Avaliação Semântica Aterrada (Texto), Tarifação de Tokens em Tempo Real & Ledger de Monetização (Marco 7 - Fase 3)

## 1. Visão Geral e Objetivos

A Sprint 08 implementa o motor de **Avaliação Semântica Aterrada de Respostas Dissertativas (Texto)** com inteligência artificial, integrado ao algoritmo de **Repetição Espaçada (SRS)** e ao sistema de **Tarifação Atômica de Tokens em Duas Fases (Pre-Auth Hold & Settlement)**.

O objetivo é permitir que o estudante responda perguntas abertas com seu próprio texto, receba uma avaliação justa, profunda e sem alucinações (com notas de 0 a 100, rubricas analíticas e citações das fontes do tema), enquanto o sistema assegura a viabilidade econômica (FinOps) do negócio através de um ledger imutável de créditos e débitos de tokens.

---

## 2. Invariantes de Arquitetura e Domínio

1. **Clean Architecture Estrita:**
   - A camada de domínio (`src/domain/`) permanece 100% pura, sem importação de SDKs externos (`google-genai`, `openai`, `fastapi`, `sqlalchemy`).
   - Toda comunicação com modelos fundacionais de IA e repositórios é intermediada por protocolos (`IAnswerEvaluationService`, `ITokenLedgerRepository`).
2. **FinOps & Prevenção de Inadimplência Concorrente (Two-Phase Token Metering):**
   - Toda avaliação inicia com uma retenção prévia de garantia (`hold_tokens`, padrão: 500 tokens).
   - Se o saldo disponível (`balance - held_balance`) for insuficiente, a requisição é rejeitada de imediato com `InsufficientTokensError` (`HTTP 402 Payment Required`), impedindo consumo não pago da API de IA.
   - Concluída a inferência, ocorre a liquidação (`settle`), onde apenas os tokens efetivamente consumidos pelo modelo são debitados e a retenção é liberada. Em caso de falha de inferência, o hold é integralmente cancelado (`refund_hold`).
3. **Aterramento Factual e Resiliência a Cold-Start:**
   - O caso de uso busca os chunks mais relevantes do tema da pergunta via similaridade vetorial (`KnowledgeGroundingService`).
   - Caso o tema ainda não possua materiais cadastrados (*Cold-Start*), o sistema faz fallback gracioso para o gabarito canônico da pergunta (`expected_answer`), garantindo que o estudante nunca fique sem avaliação.
4. **Proteção Anti-Prompt Injection:**
   - O texto do estudante é sanitizado e encapsulado dentro de delimitadores XML explícitos (`<student_answer_untrusted>`), instruindo a IA a tratar a entrada unicamente como dado de resposta, e nunca como diretiva executável de sistema.
5. **Atualização do Algoritmo SRS:**
   - O score da IA (0 a 100) é repassado ao `SpacingPolicyService.calculate_next_schedule`, que atualiza o `UserQuestionProgress` (nível 0 a 6 e próxima data de revisão).
   - Um registro indelével de auditoria (`ReviewAuditLog`) é persistido com `evaluation_mode = "AI_TEXT"`.

---

## 3. Estruturas de Dados do Domínio

### 3.1 Entidades
- **`TokenLedger`**:
  - `user_id: UUID`
  - `balance: int` (saldo total de tokens adquiridos)
  - `held_balance: int` (saldo temporariamente retido em requisições ativas)
  - Métodos: `available_balance`, `hold(amount)`, `settle(hold_amount, actual_tokens)`, `deposit(amount)`, `refund_hold(amount)`.
- **`TokenTransaction`**:
  - `id: UUID`
  - `user_id: UUID`
  - `transaction_type: str` (`"DEPOSIT"`, `"HOLD"`, `"SETTLEMENT"`, `"REFUND"`)
  - `amount: int`
  - `reference_id: str | None`
  - `created_at: datetime`
- **`AnswerEvaluationResult`**:
  - `score: int` (0 a 100)
  - `feedback: str`
  - `coverage_score: int` (0 a 100)
  - `accuracy_score: int` (0 a 100)
  - `depth_score: int` (0 a 100)
  - `evidence_quotes: tuple[str, ...]`
  - `tokens_used: int`
  - `cached_context: bool`
  - `evaluation_mode: str = "AI_TEXT"`

---

## 4. Casos de Uso da Aplicação

1. **`EvaluateStudentAnswerUseCase`**:
   - Entrada: `user_id: UUID`, `question_id: UUID`, `student_answer: str`.
   - Validações: estudante autorizado, pergunta vencida para revisão (`QuestionNotDueError` se futura), resposta não-vazia.
   - Retenção: reserva 500 tokens no ledger do usuário.
   - RAG: busca e ranqueia chunks do tema ou fallback para gabarito.
   - Inferência: avalia resposta com IA.
   - Liquidação: debita tokens reais e libera retenção.
   - SRS: atualiza `UserQuestionProgress` e grava `ReviewAuditLog`.
   - Saída: `EvaluateAnswerResponseDTO`.

2. **`GetUserTokenBalanceUseCase`**:
   - Retorna saldo total, saldo retido e saldo disponível do usuário.

3. **`DepositTokensUseCase`**:
   - Adiciona créditos de tokens à conta do usuário com registro de transação `DEPOSIT`.

4. **`ListTokenTransactionsUseCase`**:
   - Lista o histórico de transações de tokens do usuário ordenado por data descendente.

---

## 5. Endpoints da API REST

- `POST /api/v1/questions/{question_id}/evaluate-text`: Avalia resposta dissertativa com IA e atualiza progresso SRS.
- `GET /api/v1/users/me/token-balance`: Consulta saldo atual de tokens.
- `POST /api/v1/users/me/tokens/deposit`: Recarga de tokens (compra ou concessão).
- `GET /api/v1/users/me/tokens/transactions`: Extrato de transações do ledger.
