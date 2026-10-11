# ADR-004: Relacionamento N:N entre Flashcards e Temas (Taxonomia Multidisciplinar)

* **Status:** `Aprovado`
* **Data:** 2026-10-02
* **Autor:** Especialista Arquiteto
* **Contexto Técnico:** [PRD.md](file:///c:/Users/Pichau/Desktop/study_reviewer/PRD.md) v5.2, [ADR-001](file:///c:/Users/Pichau/Desktop/study_reviewer/docs/adrs/ADR-001-clean-architecture-layering.md), [ADR-002](file:///c:/Users/Pichau/Desktop/study_reviewer/docs/adrs/ADR-002-flashcard-gap-indexing-pool.md) e [ADR-003](file:///c:/Users/Pichau/Desktop/study_reviewer/docs/adrs/ADR-003-docker-dev-prod-parity-and-migrations.md)

---

## 1. Contexto e Problema
No modelo original da Sprint 01, o vínculo entre temas e flashcards foi modelado como 1:N (`flashcards.topic_id`). No entanto, o aprendizado em concursos de alto rendimento, vestibulares e certificações é **inerentemente interdisciplinar**:
- Uma questão sobre *Mandado de Segurança Coletivo* envolve **Direito Constitucional** e **Direito Processual Civil**.
- Uma pergunta sobre *Glicólise e Cetoacidose* transita entre **Bioquímica** e **Fisiologia/Patologia**.

No modelo 1:N, o estudante é forçado a escolher um único tema ou a duplicar manualmente o card para poder revisá-lo em ambas as matérias. A duplicação gera dados inconsistentes, sobrecarga de armazenamento e quebra a eficácia do algoritmo de repetição da pool.

---

## 2. Decisão Arquitetural
Adotar a relação **N:N (muitos-para-muitos)** entre `Flashcards` e `Topics`:

1. **Camada de Domínio (`src/domain/entities.py`):**
   * A entidade `Flashcard` substitui o campo `topic_id: UUID` por `topic_ids: tuple[UUID, ...]`.
   * **Invariantes de Domínio Obrigatórias:**
     - `len(topic_ids) >= 1`: nenhum flashcard pode ser órfão de tema.
     - `len(topic_ids) <= 5`: teto defensivo para evitar dispersão temática excessiva.
     - `len(set(topic_ids)) == len(topic_ids)`: integridade de conjunto sem IDs duplicados.
2. **Camada de Aplicação (`src/application/`):**
   * `CreateFlashcardDTO`: campo `topic_ids: list[UUID]` com validação de tamanho.
   * `FlashcardDTO`: campos `topic_ids: list[UUID]` e metadados de temas.
   * `CreateFlashcardUseCase`: valida a existência prévia de todos os `topic_ids` via `ITopicRepository`.
3. **Camada de Persistência (`src/adapters/persistence/`):**
   * Tabela associativa declarativa `flashcard_topics`:
     - `flashcard_id: UUID` (FK `flashcards.id`, `ON DELETE CASCADE`)
     - `topic_id: UUID` (FK `topics.id`, `ON DELETE CASCADE`)
     - Chave primária composta `(flashcard_id, topic_id)`
     - Índices em `(topic_id)` e `(flashcard_id)` para consultas de pool em tempo constante $\mathcal{O}(1)$.
   * Consultas de pool (`list_pool`): utilizam `JOIN` com `flashcard_topics` e `DISTINCT(flashcards.id)` para garantir que um card com múltiplos temas da mesma matéria não seja duplicado na listagem de estudo.
4. **Migrações de Banco de Dados com Zero Perda de Dados (Alembic):**
   * Criar a tabela `flashcard_topics`.
   * Migrar retroativamente os registros existentes:
     `INSERT INTO flashcard_topics (flashcard_id, topic_id) SELECT id, topic_id FROM flashcards;`
   * Descontinuar e remover a coluna legada `flashcards.topic_id`.

---

## 3. Consequências e Trade-offs

### Impactos Positivos:
* **Fidelidade Pedagógica:** Elimina duplicatas artificiais de flashcards e reflete o estudo interdisciplinar autêntico.
* **Flexibilidade de Estudo:** O mesmo flashcard aparece tanto ao revisar o Tema A quanto ao revisar o Tema B, mas continua com apenas **uma única posição na pool global**.
* **Zero Perda de Dados:** Migração segura do schema preservando todos os flashcards já criados na base.

### Custos / Impactos Negativos:
* **Queries Relacionais com JOIN:** Exige `JOIN` na tabela associativa e deduplicação via `DISTINCT`. *Mitigado pelo uso de índices cobrindo as chaves estrangeiras com tempo de execução inferior a 2ms.*
* **Componente de UI:** Exige seleção multi-tema no formulário em vez de um select mono-valor. *Mitigado por interface limpa com tags/checkboxes e agrupamento por matéria.*
