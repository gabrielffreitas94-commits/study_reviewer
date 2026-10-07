# ADR-009: Trilha de Auditoria Imutável de Revisões, Snapshot Isolation e Hub de Desempenho

* **Status:** `Proposto` (Aguardando aprovação formal do usuário)
* **Data:** 2026-10-07
* **Autor:** Especialista Arquiteto
* **Contexto Técnico:** [PRD.md](../../PRD.md) v7.0 (Seção 4 e Marco 4 da Seção 8), [ADR-001](ADR-001-clean-architecture-layering.md), [ADR-006](ADR-006-google-oauth2-oidc-multitenancy.md), [ADR-007](ADR-007-session-management-aes-256-gcm.md) e [SPEC Sprint 03](../specs/sprint-03-open-questions-srs-spec.md)

---

## 1. Contexto e Problema

Com a conclusão da Sprint 03, o sistema opera o algoritmo de Repetição Espaçada por Calendário (SRS Estrito) para Perguntas Abertas, atualizando a entidade mutável `UserQuestionProgress`. No entanto, para atender aos requisitos de conformidade, análise de retenção de longo prazo e métricas de desempenho do estudante (Marco 4 do PRD v7.0), a aplicação precisa de:

1. **Rastreabilidade Histórica Indelével:** Um registro imutável (*append-only*) de cada tentativa de revisão realizada pelo estudante.
2. **Resiliência a Mutações do Catálogo (*Snapshot Isolation*):** Se o proprietário de uma matéria alterar seu nome (ex: de *"Direito Constitucional"* para *"Direito Constitucional II"*) ou excluir a matéria/tema/pergunta, o histórico de estudos do estudante que revisou aquele conteúdo não pode ser corrompido, adulterado ou perdido.
3. **Hub de Desempenho e Curva de Retenção Madura:** Visualização clara da evolução do aprendizado ao longo do tempo, destacando especialmente as perguntas que alcançaram a fase de fixação madura (**Nível 4 ou superior: 60, 90 e 180 dias**).
4. **Portabilidade de Dados (LGPD Art. 18):** Disponibilização de exportação integral do histórico e progresso nos formatos **JSON** (estruturado) e **CSV** (tabular para planilhas).
5. **Privacidade e Descarte de Dados (LGPD Art. 16, IV):** Garantia de que, caso um usuário exclua sua conta, os dados históricos de revisão possam ser retidos de forma verdadeiramente anonimizada para fins estatísticos e calibração de modelos sem violar direitos do titular.

---

## 2. Decisão Arquitetural

### 2.1 Modelo de Dados `review_audit_logs` e Desacoplamento Relacional
Adota-se a tabela append-only `review_audit_logs` no PostgreSQL com o seguinte contrato estrutural:

```sql
CREATE TABLE review_audit_logs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID,                                        -- Nullable para anonimização (Art. 16, IV LGPD)
    question_id UUID,                                    -- Nullable caso pergunta seja deletada
    subject_id UUID,                                     -- Nullable caso matéria seja deletada
    topic_id UUID,                                       -- Nullable caso tema seja deletado
    historical_subject_name VARCHAR(100) NOT NULL,       -- Snapshot congelado no momento da revisão
    historical_topic_name VARCHAR(100) NOT NULL,         -- Snapshot congelado no momento da revisão
    review_date DATE NOT NULL,                           -- Data de calendário da revisão (YYYY-MM-DD)
    score INTEGER NOT NULL,                              -- 0 a 100
    level_before INTEGER NOT NULL,                       -- 0 a 6
    level_after INTEGER NOT NULL,                        -- 0 a 6
    evaluation_mode VARCHAR(20) NOT NULL DEFAULT 'MANUAL', -- 'MANUAL', 'AI_TEXT', 'AI_AUDIO'
    logged_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    
    CONSTRAINT fk_audit_user FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE SET NULL,
    CONSTRAINT fk_audit_question FOREIGN KEY (question_id) REFERENCES questions(id) ON DELETE SET NULL,
    CONSTRAINT fk_audit_subject FOREIGN KEY (subject_id) REFERENCES subjects(id) ON DELETE SET NULL,
    CONSTRAINT fk_audit_topic FOREIGN KEY (topic_id) REFERENCES topics(id) ON DELETE SET NULL
);
```

#### Justificativas:
* **Snapshot de Nomes (`historical_subject_name`, `historical_topic_name`):** Garante integridade analítica absoluta. Mesmo se uma matéria for renomeada ou sumariamente deletada do catálogo, os relatórios históricos, gráficos de esforço e exportações continuam reportando exatamente o que foi estudado.
* **`ON DELETE SET NULL` em Chaves Estrangeiras:** Evita exclusão em cascata (`CASCADE`) que apagaria os dados de estudo do aluno quando o catálogo é modificado.
* **`ON DELETE SET NULL` em `user_id`:** Permite a desidentificação irreversível exigida pela LGPD (Art. 18, VI) mantendo agregados estatísticos globais de retenção (Art. 16, IV).

### 2.2 Índices Cobridores de Alta Performance (Index-Only Scans)
Para garantir respostas em menos de 10ms na renderização do Hub de Desempenho e relatórios analíticos, criam-se os seguintes índices B-Tree:

```sql
-- Índice cobridor para listagem e agregação cronológica do estudante
CREATE INDEX ix_review_audit_user_date 
ON review_audit_logs (user_id, review_date DESC, logged_at DESC) 
INCLUDE (score, level_before, level_after, evaluation_mode);

-- Índice para agregação e filtragem por matéria
CREATE INDEX ix_review_audit_user_subject 
ON review_audit_logs (user_id, subject_id, review_date DESC);

-- Índices dedicados para chaves estrangeiras com ON DELETE SET NULL (evita Seq Scans em deleções no catálogo)
CREATE INDEX ix_review_audit_subject_id ON review_audit_logs (subject_id);
CREATE INDEX ix_review_audit_topic_id ON review_audit_logs (topic_id);
CREATE INDEX ix_review_audit_question_id ON review_audit_logs (question_id);
```

### 2.3 Atomicidade Transacional no Caso de Uso de Revisão
A gravação do registro em `review_audit_logs` ocorre de forma estritamente síncrona e atômica dentro do `ReviewQuestionUseCase`:
* A atualização do progresso (`user_question_progress`) e a inserção do log de auditoria ocorrem sob a mesma transação de banco de dados.
* Caso qualquer falha ocorra (ex: erro de banco ou violação de integridade), ambas as operações sofrem rollback automático, prevenindo descompasso entre o nível atual do SRS e a trilha histórica.

### 2.4 Interface de Usuário: Aba "Desempenho" e Hub Analítico
* **Navegação Global:** Adição de uma 4ª aba principal na barra superior:
  `[ Estudar Flashcards ]  [ Revisão SRS (badge) ]  [ Desempenho ]  [ Cadastros ▾ ]`
* **Hub Analítico (`/performance`):**
  1. **Cards de KPIs:** Taxa de Retenção Global (% acertos 100%), Perguntas em Retenção Madura (Nível 4 ou mais), Total de Revisões e Dias Ativos.
  2. **Gráfico de Curva de Retenção Madura (Nível 4+):** Visualização da evolução temporal das perguntas consolidadas em memória de longo prazo (intervalos de 60, 90 e 180 dias).
  3. **Gráfico de Consistência Temporal:** Volume de revisões diárias/semanais.
  4. **Distribuição SRS Atual:** Distribuição proporcional das perguntas cadastradas entre os Níveis 0 a 6.
  5. **Tabela de Histórico Paginada:** Lista auditável com badges de notas e transição de nível (`Nível X → Nível Y`) com contraste WCAG 2.1 AA.
  6. **Seção de Portabilidade LGPD:** Botões de download direto para **JSON** e **CSV**.

### 2.5 Exportação de Dados em Formato Híbrido (JSON e CSV)
Disponibilização de exportação via Web e API REST (`GET /api/v1/performance/export?format=json|csv`):
* **JSON:** Estrutura completa e tipada com metadados do estudante, resumo de retenção e array com todos os logs históricos e detalhes das perguntas.
* **CSV:** Arquivo tabular com cabeçalhos sanitizados em português, delimitador vírgula e encoding UTF-8 com BOM para compatibilidade nativa com Microsoft Excel e Google Sheets.

---

## 3. Consequências

### Positivas:
* **Auditoria Robusta e Segura:** Impossibilidade de adulteração ou perda de histórico mesmo sob deleções do catálogo.
* **Conformidade Legal Estrita:** Cumprimento simultâneo dos Artigos 16, IV (retenção estatística pós-anonimização) e 18, V (portabilidade total) da LGPD.
* **Alta Eficiência de Leitura:** Consultas analíticas suportadas por índices cobridores sem sobrecarga nas tabelas operacionais do catálogo.
* **Clareza de Aprendizado para o Estudante:** Acompanhamento motivacional da evolução do estudo por meio do indicador de Retenção Madura (Nível 4+).

### Neutras / Mitigações:
* **Crescimento de Armazenamento:** A tabela `review_audit_logs` cresce linearmente com as revisões. Mitigado por tipagem compacta (UUID, inteiros, strings limitadas a 100 caracteres) e suporte futuro a arquivamento/particionamento caso atinja dezenas de milhões de linhas.
