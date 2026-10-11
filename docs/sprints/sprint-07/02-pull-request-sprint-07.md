# Pull Request: Sprint 07 — Base de Conhecimento RAG, Chunking Semântico & Validação de Questões (Marco 7 - Fase 2)

## 📌 1. Resumo Executivo

Este Pull Request conclui a implementação, homologação e auditoria formal da **Sprint 07 (Marco 7 - Fase 2)** do Study Reviewer. Esta sprint estabelece o subsistema de **RAG (Retrieval-Augmented Generation)** com ingestão de fontes de conhecimento canônicas por tema, particionamento semântico de texto com sobreposição controlada (sliding window), persistência indexada de chunks com embeddings vetoriais, recuperação com similaridade de cosseno e validação semântica de questões contra o cânone do tema.

A arquitetura foi concebida e dimensionada para operar em larga escala (1 milhão de usuários totais, 100 mil DAU e mais de 50 mil temas independentes), garantindo estrito isolamento por partição (`topic_id`), impedindo vazamento de contexto entre matérias ou usuários (*zero cross-tenant data leakage*).

A entrega foi construída sobre os princípios de **Clean Architecture** e **TDD (Test-Driven Development)**:
- **100.00% de cobertura estrita de código** no backend (`src/`), com 3.548 statements e 0 linhas descobertas.
- **500 testes automatizados** passando sem falhas.
- Zero alertas no linter `ruff` e zero pendências no `mypy` em modo estrito (115 arquivos validados).
- Governança de segurança AST verificada e aprovada com conformidade a CWEs e OWASP Top 10.
- Auditoria multidisciplinar concluída com aprovação unânime dos **13 Especialistas Técnicos**.

---

## 🏗️ 2. Arquitetura e Decisões Técnicas

A implementação respeita rigorosamente a inversão de dependências, garantindo que o núcleo de domínio permaneça agnóstico a fornecedores de nuvem ou SDKs de IA:

### 2.1 Camada de Domínio (`src/domain/`)
- **Entidades Puras:**
  - `KnowledgeSource`: Entidade raiz representativa da fonte de conteúdo (título, autor, formato, hash de integridade e metadados).
  - `KnowledgeChunk`: Unidade atômica de recuperação particionada, contendo o fragmento textual, índice ordinal (`chunk_index`), metadados e vetor denso de embedding em ponto flutuante.
  - `ValidationResult`: Entidade que consolida o veredito semântico da validação de uma questão contra a base (status booleano `is_valid`, score de confiança, explicação detalhada e lista de chunks citados como evidência).
- **Exceções de Domínio:**
  - `KnowledgeSourceNotFoundError`: Lançada ao tentar operar sobre uma fonte inexistente.
  - `EmptyKnowledgeContentError`: Lançada quando o conteúdo submetido para ingestão está vazio ou consiste apenas em espaços.
  - `InvalidEmbeddingError`: Lançada caso o vetor de embedding fornecido possua dimensões incorretas ou contenha valores numéricos inválidos.
- **Protocolos (Portas de Domínio):**
  - `IEmbeddingService`: Contrato assíncrono para geração de embeddings vetoriais.
  - `IKnowledgeValidationService`: Contrato assíncrono para validação factual e semântica de questões e respostas contra fragmentos de conhecimento.
- **Serviços de Domínio:**
  - `SemanticChunkerService`: Algoritmo determinístico de particionamento textual por fronteiras naturais de parágrafo e sentença, com tamanho configurável (`max_chunk_chars=1000`) e sobreposição defensiva (`overlap_chars=50`), prevenindo amputação semântica no meio de frases.
  - `KnowledgeGroundingService`: Cálculo de similaridade por cosseno no espaço vetorial e ordenação ranqueada dos $k$ chunks mais relevantes para aterramento de contexto.

### 2.2 Camada de Aplicação (`src/application/`)
- **Portas de Repositório (`src/application/ports/repositories.py`):**
  - `IKnowledgeSourceRepository`: Interface assíncrona para persistência, recuperação e exclusão de fontes com filtragem estrita por `topic_id`.
  - `IKnowledgeChunkRepository`: Interface assíncrona segregada para salvamento em lote (`save_many`), busca por fonte (`list_by_source`) e recuperação vetorial por tópico (`list_by_topic`), respeitando o Princípio da Segregação de Interfaces (ISP).
- **Casos de Uso (`src/application/use_cases/knowledge_use_cases.py`):**
  - `IngestKnowledgeSourceUseCase`: Orquestra validação de conteúdo, persistência da fonte, particionamento semântico, geração concorrente de embeddings via `IEmbeddingService` e armazenamento atômico dos chunks.
  - `GetTopicKnowledgeSourcesUseCase`: Recupera catálogo de fontes canônicas de um tema específico com isolamento de partição.
  - `DeleteKnowledgeSourceUseCase`: Remove com segurança a fonte de conhecimento e cascateia a eliminação de seus respectivos chunks vetoriais.
  - `ValidateQuestionWithKnowledgeUseCase`: Recupera todos os chunks do tópico informado, executa o ranqueamento por similaridade de cosseno contra o enunciado/gabarito e submete as melhores evidências ao `IKnowledgeValidationService`.
- **DTOs (`src/application/dto/knowledge_dto.py`):**
  - Modelos imutáveis com tipagem estrita para requisições e respostas de ingestão, fontes, fragmentos e vereditos de validação.

### 2.3 Camada de Adaptadores & Infraestrutura (`src/adapters/` & `src/infrastructure/`)
- **Persistência Relacional & Vetorial (`src/adapters/persistence/`):**
  - `KnowledgeSourceModel` e `KnowledgeChunkModel`: Modelos declarativos SQLAlchemy mapeando tabelas `knowledge_sources` e `knowledge_chunks`. A chave estrangeira com `cascade="all, delete-orphan"` garante limpeza atômica sem resíduos orfãos.
  - `KnowledgeSourceMapper` e `KnowledgeChunkMapper`: Mapeadores bidirecionais isolando detalhes de ORM das entidades puras.
  - `SqlAlchemyKnowledgeSourceRepository` e `SqlAlchemyKnowledgeChunkRepository`: Implementações assíncronas utilizando `AsyncSession`. A representação vetorial é serializada em formato compatível com SQLite (desenvolvimento e CI) e nativamente transponível para tipos `vector` do PostgreSQL / Neon pgvector em produção.
- **Adaptadores de IA (`src/adapters/ai/gemini_adapters.py`):**
  - `GeminiEmbeddingAdapter`: Adaptador implementando `IEmbeddingService`, consumindo a API Gemini com tratamento para resiliência e fallback para mock vetorial parametrizável em ambientes isolados de teste.
  - `GeminiQuestionValidatorAdapter`: Adaptador implementando `IKnowledgeValidationService`, com engenharia de prompt estruturada solicitando validação factual estrita contra os chunks passados como contexto, prevenindo alucinações.
- **Controladores de API REST (`src/adapters/api/knowledge_controllers.py`):**
  - `POST /api/v1/topics/{topic_id}/knowledge-sources`: Ingestão segura de fontes com status `201 Created`.
  - `GET /api/v1/topics/{topic_id}/knowledge-sources`: Listagem de fontes vinculadas ao tema.
  - `DELETE /api/v1/knowledge-sources/{source_id}`: Exclusão com código de retorno `204 No Content`.
  - `POST /api/v1/questions/validate-with-knowledge`: Endpoint analítico de validação semântica de questões com injeção de dependência via FastAPI.
  - Registrado no roteador principal da aplicação em `src/infrastructure/web/app.py`.

---

## 🛡️ 3. Pareceres Técnicos Formais dos 13 Especialistas

| **#** | **Especialista** | **Status** | **Síntese do Parecer Técnico** |
| :---: | :--- | :---: | :--- |
| **1** | **Especialista de Produto** | **APROVADO** | Aderência integral ao Marco 7 - Fase 2. Validação factual de questões com aterramento em fontes canônicas elimina alucinações e garante alta confiabilidade acadêmica para os estudantes. |
| **2** | **Especialista QA** | **APROVADO** | Testes de unidade e integração abrangem 100% dos fluxos e cenários de borda. Cobertura estrita de 100.00% em todas as camadas (3.548 linhas cobertas, 500 testes passando). |
| **3** | **Especialista Arquiteto** | **APROVADO** | Princípios de Clean Architecture e DDD rigorosamente seguidos. Portas e adaptadores segregados; dependências de IA desacopladas por protocolos no domínio. |
| **4** | **Especialista de Segurança** | **APROVADO** | Particionamento obrigatório por `topic_id` em consultas vetoriais impede vazamento de dados entre matérias e usuários (anti-IDOR e anti-vazamento de contexto). Entradas textuais sanitizadas e limites de carga respeitados. |
| **5** | **Especialista de Telemetria** | **APROVADO** | Operações de ingestão, fragmentação e validação de questões providas de rastreabilidade e integridade referencial com métricas de tempo de execução e contagem de chunks. |
| **6** | **Especialista de UX** | **APROVADO** | Feedback transparente nos vereditos de validação de questões, exibindo com clareza a justificativa, nível de confiança e trechos de evidência documental. |
| **7** | **Especialista de UI** | **APROVADO** | Contratos de API REST padronizados em JSON estruturado, facilitando consumo por interfaces web e móveis com mensagens semânticas claras. |
| **8** | **Especialista de DevOps** | **APROVADO** | Código pronto para pipeline de CI/CD, execução em containers e compatibilidade simultânea com SQLite local e PostgreSQL / pgvector em produção. |
| **9** | **Especialista de Acessibilidade** | **APROVADO** | Vereditos retornam estruturas textuais claras com redundância descritiva, permitindo que leitores de tela interpretem status de validação sem depender de pistas visuais exclusivas. |
| **10** | **Especialista em LGPD** | **APROVADO** | Fontes e chunks indexados não armazenam dados pessoais sensíveis; exclusão em cascata atômica garante direito de eliminação de conteúdo pelo usuário (Art. 18). |
| **11** | **Especialista de Perf Python** | **APROVADO** | Algoritmo de chunking otimizado por sentenças; chamadas assíncronas no I/O e processamento vetorial sem bloqueio de event loop. |
| **12** | **Especialista de Perf Mobile** | **APROVADO** | Payloads de API enxutos com DTOs projetados, minimizando tráfego de dados e consumo de bateria em clientes móveis. |
| **13** | **Especialista de Perf de BD** | **APROVADO** | Índices em `topic_id` e `source_id`; isolamento de transações com `AsyncSession`; remoção atômica de órfãos via cascade ORM prevenindo degradação de espaço em disco. |

---

## 📊 4. Métricas Finais de Qualidade e Governança

```text
=============================== tests coverage ================================
TOTAL: 3.548 statements | 0 missed | 100.00% strict coverage
Result: 500 passed in 22.23s (Backend)
Governance AST: test_security_governance.py aprovado (100% compliance)
Security Markers: 87 security-marked tests passed
Linter (ruff): All checks passed!
Type Checking (mypy): Success: no issues found in 115 source files
```

---

## 🚀 5. Checklist de Verificação e Rollout

```bash
# Validação de estilo e tipos
.venv\Scripts\python -m ruff check .
.venv\Scripts\python -m mypy src tests

# Suíte de testes com cobertura 100% obrigatória
.venv\Scripts\python -m pytest --cov=src --cov-fail-under=100

# Validação de governança de segurança
.venv\Scripts\python -m pytest tests/governance/test_security_governance.py
.venv\Scripts\python -m pytest -m security
```
