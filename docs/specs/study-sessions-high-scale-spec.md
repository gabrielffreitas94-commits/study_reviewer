# Especificação Arquitetural: Sessões de Estudo e Fila de Flashcards em Alta Escala
**Versão:** 2.0 (Pós-Auditoria Unânime dos 13 Especialistas)  
**Data:** 05/10/2026  
**Status:** `APROVADO PARA IMPLEMENTAÇÃO`  
**Governança:** *Study Reviewer Architecture Council*  

---

## 1. Visão Geral e Contexto do Problema

### 1.1 Diagnóstico do Bug Original na PR
No arquivo `src/application/use_cases/study_session_use_cases.py` (linhas 71-72), o término de rodada executava:
```python
shuffled = FlashcardPoolService.execute_round_shuffle(all_cards, self._rng)
self._card_repo.save_all(shuffled)
```

**Problemas identificados:**
1. **Mutação de Estado Compartilhado (Race Condition):** A entidade `Flashcard` pertence ao catálogo da matéria. Atualizar `card.position` na base global reordena o baralho para todos os usuários concorrentes estudando a mesma matéria, quebrando o ponteiro de sessão (`session.current_position`) de outros alunos.
2. **Amplificação Massiva de I/O (Write Amplification):** A cada rodada concluída por qualquer usuário, dezenas ou milhares de registros sofriam `UPDATE` no PostgreSQL, causando contenção de locks de linha e travamento sob tráfego concorrente.

### 1.2 Princípio Arquitetural Chave
> **A ordem de estudo é propriedade efêmera da Sessão do Usuário (`FlashcardPoolSession`), e NUNCA uma propriedade intrínseca da entidade de catálogo (`Flashcard`).**

### 1.3 Alinhamento de Escopo com o PRD v7.0 (Zero Gold Plating)
Conforme estabelecido nas Seções 1.1 e 2 do PRD v7.0, o módulo de Flashcards opera em **rotação contínua e sem notas qualitativas ou complexidade de agendamento por dias**. Algoritmos de repetição espaçada qualitativa (notas 'easy', 'hard', fator de facilidade) são reservados exclusivamente para o módulo de Perguntas Abertas (Sprint 3 e 4). Portanto, o registro de eventos de flashcard limita-se estritamente à confirmação de visualização/conclusão do card.

---

## 2. Metas de Escala e Requisitos Não-Funcionais

* **Volume por Usuário (10 anos):** Até 100 cards/dia $\approx$ **365.000 cards de acervo por usuário**.
* **Base de Usuários:** 10.000.000 de usuários cadastrados.
* **Usuários Ativos Simultâneos (5%):** **500.000 usuários online simultaneamente**.
* **Pico de Concorrência (Thundering Herd):** 500.000 cliques simultâneos no botão "Próximo Card".
* **Amortização de Carga na Borda:** Redução de 500.000 cliques simultâneos para no máximo **10.000 RPS** no backend via prefetching preditivo.
* **SLAs de Desempenho e Interação:**
  * **Transição de Cards:** Percepção de **0 ms** no cliente via Optimistic UI com micro-transição fluida acelerada por GPU (120ms a 150ms).
  * **Interaction to Next Paint (INP):** $\le \mathbf{50\text{ ms}}$ no cliente (I/O desacoplado da main thread via Web Worker).
  * **Cumulative Layout Shift (CLS):** $\mathbf{0.00}$ (reserva dimensional estrita e CSS containment).
  * **Latência de API:** Resposta em p99 $< \mathbf{50\text{ ms}}$.

---

## 3. Arquitetura da Solução (Padrão 3 Camadas Otimizado)

```mermaid
flowchart TD
    subgraph Cliente ["Cliente (Mobile / Web)"]
        UI["Interface de Estudo (Optimistic UI 0ms)"]
        Worker["Dedicated Web Worker (study-sync.worker.js)"]
        LocalDB[("Outbox Local: IndexedDB / SQLite")]
        PrefetchBuffer["Buffer em Memória (Janela 50 cards)"]
        
        UI -->|Avança Card| PrefetchBuffer
        UI -->|Despacha Resposta| Worker
        Worker -->|Gravação Não-Bloqueante| LocalDB
    end

    subgraph API ["Borda e API"]
        Gateway["Cloudflare / API Gateway (WAF, Rate Limit 20/min)"]
        Backend["Serviço de Sessões (FastAPI Async + orjson)"]
        Gateway --> Backend
    end

    subgraph Cache ["Camada de Sessão Efêmera"]
        Redis[("Redis Cluster (6-8 GB RAM, volatile-ttl)")]
    end

    subgraph Banco ["Persistência Definitiva (PostgreSQL 16)"]
        PostgresCatálogo[("Catálogo Imutável: flashcards")]
        PostgresEvents[("Histórico Append-Only: study_events<br/>PARTITION BY RANGE (reviewed_at)")]
    end

    PrefetchBuffer -.->|Pede próximo lote (Low-Water Mark 10 cards)| Gateway
    Worker -.->|fetch keepalive com W3C TraceContext| Gateway
    Backend <-->|Fila da Rodada Ativa (TTL 24h)| Redis
    Backend -->|selectinload(topics)| PostgresCatálogo
    Backend -->|Bulk Insert Idempotente| PostgresEvents
```

### 3.1 Camada 1: Cliente e Borda (Prefetching Preditivo & Web Worker)
* **Tamanho da Rodada Ativa:** Cada rodada é configurada para blocos focados de **50 a 100 cards**. A fila efêmera armazena apenas a fatia da rodada corrente, e não os 365.000 cards históricos do aluno.
* **Prefetch Preditivo com Low-Water Mark (10 cards):** O cliente baixa antecipadamente 50 cards completos (frente/verso). Quando o ponteiro local atinge o card 40 (restam 10 cards no buffer), o cliente dispara em background a requisição do próximo lote, eliminando pausas perceptíveis no card 50.
* **Dedicated Web Worker (`study-sync.worker.js`):** Todo o I/O do `IndexedDB` e a sincronização de rede são isolados em uma thread dedicada em segundo plano. A thread principal de renderização do DOM permanece livre, garantindo **INP $\le 50$ms** e taxa constante de 60 FPS.
* **Isolamento de Layout e Prevenção de CLS:** O container do flashcard utiliza CSS Containment (`contain: layout size;`) e altura mínima fixa (`min-h-[380px]`), impedindo Layout Thrashing e assegurando **CLS = 0**.

### 3.2 Camada 2: Sessão Efêmera no Redis (Sizing Real e Alta Disponibilidade)
* **Escopo da Fila em Memória:** As listas do Redis armazenam estritamente a fatia ativa da rodada (50 a 100 UUIDs por usuário conectado).
* **Dimensionamento Real de Produção (Sizing):**
  * Para 500.000 usuários ativos $\times$ 100 UUIDs: carga líquida de dados $\approx 2,5 \text{ GB}$.
  * Overhead de metadados (`robj`, `quicklist`, `dictEntry`), fragmentação de memória do alocador `jemalloc` (fator 1.3x), buffers de conexão de clientes e reserva para *copy-on-write* durante forks (`BGSAVE`/AOF rewrite).
  * **Dimensionamento Obrigatório:** Instâncias gerenciadas provisionadas com **6 GB a 8 GB de RAM** (mínimo nó equivalente a `cache.m6g.large`).
* **Política de Eviction e Higiene de Cache:**
  * Configuração mandatória: `maxmemory-policy volatile-ttl`. Em situações de pico extremo de tráfego, o Redis descarta unicamente sessões antigas ou próximas da expiração, prevenindo erros 500 (`OOM command not allowed`).
  * TTL estrito de **24 horas** em todas as chaves de sessão.
* **Namespacing Padronizado:**
  `tenant:{tenant_id}:user:{user_id}:session:{session_id}:queue`
* **Resiliência e Cache Warming:** Se um nó do Redis reiniciar ou sofrer failover, a aplicação detecta o cache miss e executa a reconstrução a quente da sessão a partir dos dados do PostgreSQL de forma transparente, sem deslogar o aluno.

### 3.3 Camada 3: Persistência Relacional (PostgreSQL 16)
* **Catálogo Imutável:** A tabela `flashcards` nunca sofre `UPDATE` em tempo de estudo. A busca do lote de 50 cards carrega relacionamentos antecipadamente via `selectinload(FlashcardModel.topics)`, eliminando completamente consultas N+1.
* **Histórico Append-Only com Particionamento Temporal:** A tabela `study_events` utiliza **`PARTITION BY RANGE (reviewed_at)`** com partições semanais automatizadas via extensão `pg_partman`.
  * *Eficiência em Escala de 1 Bilhão de Inserções/Dia:* Descartar eventos com mais de 60 dias torna-se uma operação instantânea de metadados em $\mathcal{O}(1)$ (`ALTER TABLE study_events DETACH PARTITION ...; DROP TABLE ...;`), eliminando o risco de colapso de I/O, autovacuum e geração massiva de WAL causados por comandos `DELETE` em massa.
* **Tabela de Consolidação de Estado (Rollup):** Uma tabela enxuta `user_flashcard_progress (user_id, card_id, reviews_count, last_reviewed_at)` é atualizada no encerramento da rodada, permitindo leituras analíticas em $\mathcal{O}(1)$ sem varrer bilhões de registros históricos.

---

## 4. Modelagem de Dados e Contratos de Domínio

### 4.1 Entidade de Domínio: `FlashcardPoolSession` (Otimizada para Python 3.13)
```python
from dataclasses import dataclass
from uuid import UUID
from datetime import datetime
from src.domain.exceptions import DomainValidationError

@dataclass(slots=True)
class FlashcardPoolSession:
    """Entidade de domínio rica representando a sessão efêmera de estudo.
    
    A fila `card_queue` contém exclusivamente a fatia da rodada ativa
    (50 a 100 UUIDs), otimizando o consumo de RAM em larga escala.
    """
    id: UUID
    user_id: UUID
    subject_id: UUID
    topic_id_filter: UUID | None
    round_number: int
    current_index: int          # Cursor na fila (0 a N-1)
    card_queue: list[UUID]      # Janela ativa da rodada exclusiva deste usuário
    created_at: datetime
    updated_at: datetime

    def __post_init__(self) -> None:
        if self.current_index < 0:
            raise DomainValidationError("O índice atual não pode ser negativo.")
        if self.round_number < 1:
            raise DomainValidationError("O número da rodada deve ser >= 1.")

    def get_current_card_id(self) -> UUID | None:
        if self.current_index < len(self.card_queue):
            return self.card_queue[self.current_index]
        return None

    def advance(self) -> None:
        self.current_index += 1

    def is_round_finished(self) -> bool:
        return self.current_index >= len(self.card_queue)

    def start_new_round(self, shuffled_ids: list[UUID]) -> None:
        if not shuffled_ids:
            raise DomainValidationError("A nova rodada requer uma lista não-vazia de IDs.")
        self.round_number += 1
        self.card_queue = shuffled_ids
        self.current_index = 0
```

### 4.2 Hierarquia de Exceções de Sessão
Para assegurar contratos de erro tipados e determinismo na camada de aplicação:
```python
class StudySessionError(Exception):
    """Exceção base para o subsistema de sessões de estudo."""

class SessionExpiredError(StudySessionError):
    """Sessão efêmera expirou no cache após 24h de inatividade."""

class SessionQueueEmptyError(StudySessionError):
    """Fila de cards da matéria/tópico esgotada ou sem registros."""

class SessionDesynchronizedError(StudySessionError):
    """Inconsistência detectada entre cursor local e estado remoto."""
```

### 4.3 DDL do PostgreSQL Corrigido (Particionamento Temporal)
```sql
-- Tabela de histórico com Particionamento por Intervalo Temporal
CREATE TABLE study_events (
    id UUID DEFAULT gen_random_uuid(),
    reviewed_at TIMESTAMPTZ NOT NULL,
    user_id UUID,                     -- Nullable para permitir anonimização (Art. 16, IV LGPD)
    card_id UUID NOT NULL,            -- Validado na aplicação; sem FK física para evitar lock sob 11k writes/s
    session_id UUID NOT NULL,
    status VARCHAR(20) NOT NULL,      -- 'viewed', 'completed' (PRD v7.0 Flashcards)
    device_id VARCHAR(50),
    CONSTRAINT pk_study_events PRIMARY KEY (reviewed_at, user_id, id),
    CONSTRAINT fk_user FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE SET NULL
) PARTITION BY RANGE (reviewed_at);

-- Índice cobridor para consultas analíticas do aluno (Index-Only Scans)
CREATE INDEX ix_study_events_user_card_review 
ON study_events (user_id, card_id, reviewed_at DESC) 
INCLUDE (status);

-- Exemplo de partição temporal criada automaticamente via pg_partman
CREATE TABLE study_events_y2026w41 PARTITION OF study_events
    FOR VALUES FROM ('2026-10-05 00:00:00+00') TO ('2026-10-12 00:00:00+00');
```

---

## 5. Resiliência, Segurança de Borda e Casos Extremos

### 5.1 Despacho Confiável de Respostas com `fetch(keepalive: true)`
* **Padrão de Despacho Assíncrono:** Para garantir o envio íntegro de lotes mesmo no fechamento da aba ou evento `visibilitychange`, o cliente utiliza `fetch()` com a opção `keepalive: true`:
  ```javascript
  // Executado pelo Web Worker no evento de visibilidade ou conclusão de lote
  await fetch("/api/study/sync-answers", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      "Authorization": `Bearer ${authToken}`,
      "X-CSRF-Token": csrfToken,
      "traceparent": currentTraceParent
    },
    body: JSON.stringify(outboxBatch),
    keepalive: true
  });
  ```
* **Particionamento de Lotes:** Lotes do outbox local são fatiados em blocos de até 25 itens ($\approx 15 \text{ KB}$), garantindo margem de segurança contra qualquer limite de keepalive do sistema operacional.
* **Idempotência no Servidor:**
  ```python
  stmt = insert(StudyEventModel).values(events_payload)
  stmt = stmt.on_conflict_do_nothing(index_elements=["reviewed_at", "user_id", "id"])
  await db_session.execute(stmt)
  ```

### 5.2 Blindagem de Segurança no Endpoint Batch (`POST /study/sync-answers`)
1. **Controle Estrito de Acesso (Anti-IDOR - CWE-639):**
   * O `authenticated_user_id` é extraído exclusivamente do token criptográfico de sessão validado pelo middleware.
   * O backend carrega a sessão ativa e valida: `session.user_id == authenticated_user_id`. Caso haja divergência, a requisição é sumariamente rejeitada com `HTTP 403 Forbidden`.
   * Cada `card_id` contido no lote é checado contra a lista de IDs autorizados daquela sessão (`session.card_queue`).
2. **Mitigação de DoS por Exaustão de Recursos (OWASP A04):**
   * Tamanho do corpo da requisição limitado a no máximo **256 KB** no API Gateway.
   * Schema Pydantic com teto numérico: `events: list[StudyEventDTO] = Field(..., max_length=100)`.
   * Rate limiting na borda (Leaky Bucket: máximo de 20 requisições de sincronização por minuto por usuário).
3. **Validação Temporal e Anti-Tampering (Prevenção de Clock Skew e Replay):**
   * Rejeição de eventos com `reviewed_at > now() + 60s` (relógio adiantado / fraude).
   * Janela máxima de tolerância offline: `now() - reviewed_at <= 30 dias`.

### 5.3 Conflito Multi-Dispositivo e Convergência de Cursor
* **Histórico Cronológico:** O histórico no PostgreSQL é append-only; eventos recebidos de múltiplos dispositivos são ordenados por `reviewed_at`.
* **Convergência do Cursor no Servidor:** Para evitar que o descarregamento tardio de um celular regrida a posição de um estudante que já avançou no desktop, o servidor adota a regra determinística:
  $$\text{new\_current\_index} = \max(\text{session.current\_index}, \text{incoming\_batch\_index})$$

### 5.4 Bloqueio de Armazenamento Local (Modo Anônimo / Quota Excedida)
* O cliente detecta restrições no `IndexedDB` na inicialização.
* **Degradação Graciosa Acolhedora:** Em vez de alertas alarmistas, o sistema exibe um banner informativo em linguagem natural: *"Modo de navegação privada detectado: seu progresso será salvo diretamente na nuvem a cada card respondido."* O sistema reduz o batch para 1 card e opera em memória volátil.

### 5.5 Matéria Viva (Adições e Remoções de Cards em Tempo Real)
* **Snapshot Isolation por Rodada:** Toda rodada de estudo é atrelada ao `deck_version` do início da rodada. Novos cards adicionados durante a sessão ingressam apenas no ciclo seguinte.
* **Tombstones:** Cards excluídos recebem `deleted_at = NOW()`. Se o aluno responder a um card pré-carregado que foi excluído no servidor, o evento é registrado normalmente, mas o card é aposentado para rodadas futuras.

---

## 6. Conformidade Legal: LGPD (Privacy by Design)

### 6.1 Correção Conceitual: Pseudonimização vs Art. 16, IV
* **Enquadramento Jurídico Rigoroso:** Enquanto o registro na tabela `study_events` mantiver `user_id` associado a `users(id)` e `device_id`, ele é legalmente classificado como **dado pseudonimizado (Art. 13, § 4º da Lei nº 13.709/2018)**, e **NÃO** dado anonimizado.
* **Procedimento de Desidentificação no Direito à Eliminação (Art. 18, VI):** Caso o titular solicite a exclusão de sua conta, o sistema executa a anonimização efetiva:
  ```sql
  UPDATE study_events 
  SET user_id = NULL, device_id = NULL 
  WHERE user_id = :deleted_user_id;
  ```
  Ao desvincular irreversivelmente os eventos de qualquer pessoa natural, o histórico restante passa a configurar **dado verdadeiramente anonimizado (Art. 5º, XI)**, legitimando sua retenção sob o Art. 16, IV para calibragem de modelos estatísticos.

### 6.2 Purga Obrigatória no Logout (Privacy by Default)
* Para prevenir o vazamento de conteúdo textual de flashcards (UGC) em computadores compartilhados (universidades, bibliotecas, laboratórios), o evento de confirmação de logout (`POST /auth/logout`) aciona a limpeza física mandatória do cliente:
  ```javascript
  await window.indexedDB.deleteDatabase("study_reviewer_outbox");
  window.localStorage.clear();
  window.sessionStorage.clear();
  ```
* Opcional: recurso *"Modo Computador Compartilhado"* na tela de login, que instrui o frontend a manter o prefetch estritamente na memória RAM, sem tocar o disco local.

### 6.3 TTL de Segurança em Lotes Offline
* Cada lote de prefetch armazenado no cliente possui validade máxima de **2 horas**.
* Expirada a janela, o cliente é obrigado a revalidar a conectividade e permissões com o backend antes de exibir o card seguinte. Se a matéria tiver sido convertida para privada (`privacy_version` alterada) ou o acesso revogado, a API retorna `HTTP 403 Forbidden` e o cliente expurga o lote local imediatamente.

### 6.4 Ciclo de Vida para Exclusão de Conta do Titular
1. Invalidação imediata de chaves ativas no Redis via padrão `tenant:*:user:{user_id}:*`.
2. Execução da rotina de desidentificação de `study_events` conforme Seção 6.1.
3. Expurgo físico de flashcards autorais privados (`"[CONTEÚDO REMOVIDO]"` e soft delete imediato).

---

## 7. Experiência do Estudante, Interface e Acessibilidade (UX / UI / a11y)

### 7.1 Os 5 Estados Essenciais de Interface
1. **Ideal State:** Card centralizado com tipografia nítida, botões de ação ergonômicos e micro-transição fluida acelerada por GPU (120ms a 150ms).
2. **Empty State:** Rodada concluída com sucesso (Victory State). Exibe tela acolhedora com métricas do bloco estudado (quantidade de cards, tempo de foco, streak) e botão de ação primário para iniciar nova rodada ou retornar ao painel.
3. **Loading State:** Skeleton Screen com dimensões estritamente reservadas (`min-h-[380px]`) evitando qualquer deslocamento visual da tela (CLS zero).
4. **Error State:** Banner discreto e não-bloqueante no topo da tela com botão de retry contextual: *"Não foi possível sincronizar agora. Suas respostas estão guardadas no aparelho e serão enviadas assim que a rede estabilizar."*
5. **Partial State:** Indicador visual de modo offline ou sincronização em andamento.

### 7.2 Widget Discreto de Status de Sincronização
Integrado ao cabeçalho da interface com tokens semânticos do Tailwind CSS:
* **Sincronizado:** Ponto verde (`bg-emerald-500`) acompanhado de texto acessível: *"Progresso salvo na nuvem"*.
* **Sincronizando:** Ícone giratório discreto índigo (`text-indigo-600 animate-spin`): *"Sincronizando respostas..."*.
* **Modo Offline:** Ponto âmbar (`bg-amber-500`): *"Modo offline (X respostas salvas no dispositivo)"*.
* **Falha Temporária:** Ponto rosa (`bg-rose-500`): *"Aguardando conexão para envio"*.

### 7.3 Componente Flip 100% CSS 3D (Client-Side)
* **Aposentadoria de Rota HTTP:** A rota `/study/flip` via HTMX é completamente descontinuada para a sessão de estudo. O giro da frente para o verso ocorre localmente em **0 ms** via CSS 3D:
  ```css
  .card-container {
    perspective: 1000px;
  }
  .card-inner {
    position: relative;
    width: 100%;
    transition: transform 0.25s ease-in-out;
    transform-style: preserve-3d;
  }
  .card-inner.is-flipped {
    transform: rotateY(180deg);
  }
  .card-face {
    position: absolute;
    width: 100%;
    backface-visibility: hidden;
  }
  .card-back {
    transform: rotateY(180deg);
  }
  ```

### 7.4 Acessibilidade (WCAG 2.1 nível AA)
* **Retenção Programática de Foco (Eliminação do Focus Loss):** Ao avançar para o próximo card em 0ms, o JavaScript retém o foco ativo no elemento `#card-surface` ou no botão de ação principal via `.focus()`, impedindo que o cursor de navegação por teclado retorne ao início do `document.body`.
* **Região Viva para Leitores de Tela:**
  ```html
  <div id="card-announcer" class="sr-only" aria-live="polite" aria-atomic="true">
    <!-- Atualizado dinamicamente: "Card 15 de 50: [Pergunta do Card]" -->
  </div>
  ```
* **Conformidade com WCAG 2.1.4 (Atalhos de Teclado):** Atalhos rápidos de tecla única (ex: `Espaço` para virar, `Enter` para avançar) são automaticamente desabilitados quando o foco estiver dentro de campos de entrada de texto e possuem opção de desligamento nas preferências de acessibilidade.
* **Contraste e Sensibilidade ao Movimento:** Contraste mínimo de texto de **4.5:1** e ícones semânticos associados a cores. Sob a preferência do sistema `@media (prefers-reduced-motion: reduce)`, a animação 3D de rotação é substituída por transição estática de opacidade sem movimento tridimensional.

---

## 8. Telemetria e Observabilidade em Alta Escala

### 8.1 Propagação de Contexto W3C TraceContext
O cliente Web Worker gera ou propaga o cabeçalho `traceparent` (padrão OpenTelemetry / W3C) nas requisições em lote para o endpoint `/study/sync-answers`, permitindo a correlação distribuída de ponta a ponta entre a interação do estudante e a gravação relacional no APM.

### 8.2 Métricas de Saúde e Monitoramento do Redis Cluster (Prometheus)
* **Latência de Comandos:** `histogram_quantile(0.99, rate(redis_command_duration_seconds_bucket[5m]))` (Alerta p99 > 5ms).
* **Taxa de Acertos de Cache:** `study_cache_hit_ratio` (Alerta se < 95%).
* **Saúde de Memória:** `redis_memory_fragmentation_ratio` (Alerta se > 1.4) e `redis_evicted_keys_total` (Alerta de aviso de capacidade).

### 8.3 Métricas de Sincronização e Lag
* **Histograma de Defasagem Temporal:** `study_sync_lag_seconds` medindo o intervalo entre `reviewed_at` e a ingestão no servidor.
* **Volume de Lotes:** `study_sync_batch_size` e contador `study_sync_events_total{status="synced|deduplicated|rejected"}`.

### 8.4 Logging Estruturado sem Vazamento de Dados Pessoais
Logs estruturados em formato JSON estrito, sem expor e-mails, tokens ou conteúdo textual dos flashcards:
```json
{
  "timestamp": "2026-10-05T09:30:00.000Z",
  "level": "INFO",
  "logger": "study_reviewer.application.sync",
  "event": "study_batch_synced",
  "correlation_id": "c1f2e3d4-b5a6-4f7e-8c9d-0a1b2c3d4e5f",
  "user_id": "a9b8c7d6-e5f4-...",
  "session_id": "12345678-...",
  "batch_size": 25,
  "sync_lag_p50_ms": 850,
  "duration_ms": 14.2
}
```

---

## 9. Roteiro Unificado de Implementação da Sprint

Todas as frentes de engenharia (domínio, infraestrutura Redis, banco particionado, Web Worker e frontend acessível) serão implementadas e entregues de forma integrada nesta Sprint:

### 9.1 Domínio e Regras de Negócio
* [ ] Modificar `FlashcardPoolSession` no domínio adicionando `@dataclass(slots=True)`, `card_queue: list[UUID]` e `current_index: int`.
* [ ] Adicionar validações de invariantes no `__post_init__` da entidade (`current_index >= 0`, `round_number >= 1`).
* [ ] Implementar hierarquia de exceções de sessão (`SessionExpiredError`, `SessionQueueEmptyError`, `SessionDesynchronizedError`).
* [ ] Atualizar o método `execute_round_shuffle` para projetar e embaralhar exclusivamente a lista escalar de UUIDs, armazenando-a exclusivamente na sessão.
* [ ] **Remover em definitivo** `self._card_repo.save_all(shuffled)` de `study_session_use_cases.py`.

### 9.2 Infraestrutura, Cache e Persistência
* [ ] Adicionar serviço `redis: 7-alpine` ao `docker-compose.yml` com healthcheck `redis-cli ping` e `REDIS_URL` no `.env.example`.
* [ ] Implementar interface `ISessionStore` e adaptador `RedisSessionRepository` com conexão assíncrona (`redis.asyncio`), suportando `fakeredis` nos testes unitários e no CI.
* [ ] Criar migração Alembic para a tabela `study_events` com `PARTITION BY RANGE (reviewed_at)` e PK composta `(reviewed_at, user_id, id)`.
* [ ] Implementar endpoint assíncrono `POST /study/sync-answers` com validação anti-IDOR, rate limit (20 req/min), schema Pydantic com teto de 100 eventos e bulk insert via `asyncpg`.

### 9.3 Frontend, Web Worker e Experiência do Estudante
* [ ] Implementar o Dedicated Web Worker (`study-sync.worker.js`) com `IndexedDB` e despacho via `fetch(keepalive: true)`.
* [ ] Implementar prefetch preditivo com Low-Water Mark (10 cards) e Optimistic UI com micro-transições suaves (120-150ms).
* [ ] Implementar o componente de Flip 100% CSS 3D (`.is-flipped`, `transform: rotateY(180deg)`) e aposentar a rota HTTP `/study/flip`.
* [ ] Implementar o widget discreto de status de sincronização no cabeçalho com tokens semânticos Tailwind CSS.
* [ ] Especificar e tratar os 5 Estados Essenciais de Interface (Ideal, Empty/Victory State, Loading Skeleton, Error, Partial).
* [ ] Implementar acessibilidade WCAG 2.1 AA: retenção programática de foco (`.focus()`), live region atômica (`aria-live="polite"`), atalhos de teclado seguros (WCAG 2.1.4) e fallback `prefers-reduced-motion`.
* [ ] Implementar rotina de purga local no logout e script de anonimização da LGPD (Art. 16, IV / 18, VI).

### 9.4 Cobertura de Testes e Governança
* [ ] Assegurar 100% de cobertura nos testes unitários e de integração (`pytest --cov=src --cov-fail-under=100`).
* [ ] Decorar testes de segurança e controle de acesso com `@pytest.mark.security` e docstrings com `Vulnerabilidade prevenida:` e `Garantia de segurança:`.
* [ ] Garantir conformidade com linters e tipagem estrita (`ruff check`, `ruff format --check`, `mypy`).
