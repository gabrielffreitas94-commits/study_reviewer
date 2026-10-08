# Casos de Uso e Matriz de Edge Cases — Sprint 09: Avaliação de Áudio & Conselho Multiagente

## 1. Casos de Uso

### UC-01: Avaliação Multimodal de Resposta em Áudio (`EvaluateAudioAnswerUseCase`)
- **Atores:** Estudante autenticado.
- **Entrada:** `question_id` (UUID), `audio_bytes` (bytes), `mime_type` (str).
- **Pré-condições:** Estudante deve ter saldo suficiente de tokens (>= 800 tokens hold); pergunta deve existir e estar no prazo de vencimento do SRS.
- **Fluxo Principal:**
  1. Valida tamanho do áudio (máximo 10MB) e formato de MIME permitido (`audio/webm`, `audio/mp3`, `audio/wav`, `audio/ogg`, etc.).
  2. Executa retenção preventiva de tokens (Pre-Auth Hold) no `TokenLedger`.
  3. Recupera os fragmentos canônicos de conhecimento do tema via RAG (com fallback Cold-Start para gabarito oficial).
  4. Encaminha o áudio para o `IAudioAnswerEvaluationService` em memória volátil.
  5. Purga imediatamente os bytes de áudio da memória RAM (`del audio_bytes`).
  6. Obtém a transcrição da fala e os scores avaliativos (cobertura, precisão e profundidade).
  7. Liquida (SETTLE) a quantidade de tokens consumida.
  8. Atualiza o nível e data de revisão do estudante no motor SRS (SuperMemo-2).
  9. Registra auditoria no `ReviewAuditLog` com `evaluation_mode="AI_AUDIO"`.
  10. Retorna DTO com transcrição, notas, feedback e saldo atualizado.

### UC-02: Conselho Multiagente de Contestação de Avaliação (`DisputeEvaluationUseCase`)
- **Atores:** Estudante autenticado.
- **Entrada:** `question_id` (UUID), `student_answer` (str), `dispute_argument` (str).
- **Pré-condições:** Estudante possui tokens suficientes para taxa de contestação (>= 1000 tokens hold); questão existe e pertence à matéria do estudante.
- **Fluxo Principal:**
  1. Sanitiza e valida o argumento de contestação (entre 5 e 5.000 caracteres).
  2. Executa retenção de tokens de deliberação multiagente.
  3. Recupera chunks canônicos do tema via RAG.
  4. Aciona a câmara multiagente (`IMultiAgentDisputeService`):
     - **StudentAdvocateAgent:** Constrói a melhor tese em favor do estudante com base nos chunks.
     - **FactualCriticAgent:** Realiza escrutínio crítico contra as evidências factuais.
     - **ArbitratorAgent:** Delibera imparcialmente e define veredito (`UPHELD` ou `REJECTED`), nova pontuação e fundamentação pedagógica.
  5. Se o veredito for `UPHELD`:
     - O valor retido é estornado ou bonificado ao estudante (`refund_hold`).
     - A nota e agendamento SRS são recalculados com a nota revisada.
     - Registra log de auditoria `MULTIAGENT_DISPUTE`.
  6. Se o veredito for `REJECTED`:
     - O valor retido é liquidado definitivamente (`settle`).
     - A nota anterior e o nível SRS permanecem inalterados.
  7. Retorna DTO com os três pareceres e a decisão deliberada.

---

## 2. Matriz de Edge Cases e Tratamento Sistemático

| # | Edge Case | Comportamento Esperado / Resolução |
|---|---|---|
| **EC-01** | **Arquivo de áudio vazio ou zerado (0 bytes)** | Lança `DomainValidationError("Arquivo de áudio não pode ser vazio.")`. Nenhum token retido. |
| **EC-02** | **Arquivo de áudio com tamanho > 10MB (Anti-DoS)** | Lança `DomainValidationError("Tamanho do arquivo de áudio excede o limite máximo permitido de 10MB.")`. |
| **EC-03** | **MIME type de áudio não suportado (ex: application/pdf ou video/mp4)** | Lança `DomainValidationError("Formato de áudio não suportado.")`. |
| **EC-04** | **Falha de inferência multimodal do provedor de IA (ex: timeout ou erro 500)** | Executa estorno atômico integral da retenção (`refund_hold`) e lança `EvaluationServiceError`. |
| **EC-05** | **Argumento de contestação com tentativa de Prompt Injection** | O adaptador multiagente enclausura em `<dispute_argument_untrusted>` e o Arbitrator emite veredito `REJECTED` apontando a violação. |
| **EC-06** | **Argumento de contestação com menos de 5 caracteres** | Lança `DomainValidationError("Argumento de contestação deve conter entre 5 e 5.000 caracteres.")`. |
| **EC-07** | **Saldo de tokens insuficiente para a contestação** | Lança `InsufficientTokensError` antes de acionar os agentes. |
| **EC-08** | **Tema em Cold-Start na contestação** | A câmara multiagente ancora seus pareceres no gabarito oficial da pergunta cadastrado na entidade `Question`. |
| **EC-09** | **Revisão SRS com nota 100 na contestação aceita** | Se a nova nota for 100, o nível SRS é promovido (`previous_level + 1`) de acordo com o `SpacingPolicyService`. |
