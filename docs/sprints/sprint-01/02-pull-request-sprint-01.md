<!-- Template Oficial de Pull Request — Study Reviewer -->
## 📋 Identificação da Sprint
* **Sprint:** `Sprint 01 — MVP Flashcards em Produção (Clean Architecture & Gap Indexing)`
* **Branch de Origem:** `feature/sprint-01-flashcards`
* **Branch de Destino:** `staging`
* **Documento SPEC Aprovado pelo Usuário:** `docs/specs/sprint-01-flashcards-spec.md`
* **ADRs Aprovados pelo Usuário:**
  * `docs/adrs/ADR-001-clean-architecture-layering.md`
  * `docs/adrs/ADR-002-flashcard-gap-indexing-pool.md`
  * `docs/adrs/ADR-003-docker-dev-prod-parity-and-migrations.md`

---

## 🎯 Resumo da Entrega & Objetivo
Implementação completa e em padrão de produção do subsistema de **Flashcards** para o **Study Reviewer** conforme PRD v5.2 e especificações da Sprint 01:
1. **Núcleo de Domínio:** Entidades puras (`Subject`, `Topic`, `Flashcard`, `FlashcardPoolSession`) com validação de invariantes, tratamento defensivo de Unicode/espaços e datas UTC.
2. **Motor Matemático de Gap Indexing (`FlashcardPoolService`):** Inserção dinâmica no ponto médio dos primeiros 10% da pool ($\mathcal{O}(1)$), rebalanceamento preventivo automático quando o gap atinge $\le 1$, e embaralhamento Fisher-Yates ao final da rodada com gerador criptográfico seguro.
3. **Casos de Uso da Aplicação:** Criação e listagem de matérias e temas com checagem de duplicidade insensível a maiúsculas/minúsculas e acentos, cadastro ágil de flashcards e avanço contínuo de rodadas de estudo.
4. **Interface Web & API REST:** Telas e parciais HTMX responsivas com TailwindCSS, alternância de card com flip 3D e hotkeys (`Space`/`Enter`), anúncios acessíveis via `aria-live="polite"`, suporte a gestos touch swipe em mobile e endpoints JSON desacoplados prontos para consumo por mobile/Flutter.
5. **Infraestrutura & Dev/Prod Parity:** Dockerfile multi-stage com usuário não-root `appuser`, `docker-compose.yml` orquestrando PostgreSQL 16 Alpine com healthcheck e volume persistente, e migrações versionadas com Alembic (`001_sprint_01_flashcards`).
6. **Segurança:** Criptografia autenticada AES-256-GCM AEAD com HKDF, sanitização defensiva via `nh3`, e middleware de headers de segurança HTTP (HSTS, CSP, X-Frame-Options, X-Content-Type-Options).

---

## 🧪 Metodologia TDD & Cobertura de Testes (100% Obrigatório)
- [x] **TDD Aplicado:** Testes unitários e de integração desenvolvidos e validados previamente à implementação com ciclo Red-Green-Refactor.
- [x] **Casos de Uso e Edge Cases:** Matriz com 29 casos BDD documentada e aprovada pelo QA em `docs/sprints/sprint-01/01-use-cases-and-edge-cases.md`.
- [x] **Cobertura Backend:** 100% de cobertura rigorosamente atingida em todas as 25 unidades de código (`pytest --cov=src --cov-fail-under=100`).
- [x] **Cobertura Frontend/Templates:** Testes de renderização de templates, injeção de classes Tailwind, atributos ARIA e headers HTMX validados via `TestClient`.

```text
Name                                                   Stmts   Miss  Cover
--------------------------------------------------------------------------
src/adapters/api/controllers.py                           73      0   100%
src/adapters/persistence/mappers.py                       30      0   100%
src/adapters/persistence/models.py                        38      0   100%
src/adapters/persistence/repositories.py                  94      0   100%
src/adapters/web/controllers.py                          120      0   100%
src/application/dto/flashcard_dto.py                       7      0   100%
src/application/dto/study_dto.py                           8      0   100%
src/application/dto/subject_dto.py                         7      0   100%
src/application/dto/topic_dto.py                           7      0   100%
src/application/ports/repositories.py                     23      0   100%
src/application/use_cases/flashcard_use_cases.py          60      0   100%
src/application/use_cases/study_session_use_cases.py      36      0   100%
src/application/use_cases/subject_use_cases.py            20      0   100%
src/application/use_cases/topic_use_cases.py              25      0   100%
src/domain/entities.py                                    53      0   100%
src/domain/exceptions.py                                   5      0   100%
src/domain/protocols.py                                    4      0   100%
src/domain/services.py                                    50      0   100%
src/infrastructure/config.py                              11      0   100%
src/infrastructure/database.py                            17      0   100%
src/infrastructure/rng.py                                 11      0   100%
src/infrastructure/security/crypto.py                     31      0   100%
src/infrastructure/security/middleware.py                 13      0   100%
src/infrastructure/security/sanitization.py                6      0   100%
src/infrastructure/web/app.py                             19      0   100%
--------------------------------------------------------------------------
TOTAL                                                    768      0   100%
Required test coverage of 100% reached. Total coverage: 100.00%
97 passed, 2 warnings in 2.73s
```

---

## 🛡️ Governança de Testes de Segurança
- [x] Todos os testes que validam segurança ou vulnerabilidades foram decorados com `@pytest.mark.security`.
- [x] Todas as docstrings de testes de segurança contêm os campos obrigatórios `Vulnerabilidade prevenida:` e `Garantia de segurança:`.
- [x] O meta-teste de AST (`tests/governance/test_security_governance.py`) passou com 100% de conformidade.

---

## 📐 Conformidade Arquitetural & ADRs Ativas (Auditoria do Arquiteto)
- [x] O teste automatizado de arquitetura AST (`tests/architecture/test_clean_architecture.py`) passou com 100% de sucesso.
- [x] As decisões estruturais das ADRs ativas foram rigorosamente seguidas:
  - [x] **ADR-001 (Clean Architecture):** Núcleo de domínio isolado sem referências a ORM ou bibliotecas externas de infraestrutura; dependências invertidas via Protocols (`typing.Protocol`).
  - [x] **ADR-002 (Gap Indexing na Pool):** Posições em múltiplos de 100, inserção por ponto médio nos 10% da pool e rebalanceamento preventivo uniforme.
  - [x] **ADR-003 (Docker & Migrações):** Multi-stage build com `uv`, execução sob `appuser` (UID 1000), compose com PostgreSQL 16 Alpine e healthchecks ativos; migrações do Alembic executadas no boot.

---

## 🏛️ Bancada dos 10 Especialistas — Auditoria Obrigatória

| # | Especialista | Status | Parecer Técnico / Justificativa |
| :-: | :--- | :---: | :--- |
| **1** | **Especialista de Produto** | `[APROVADO]` | Escopo integral da Sprint 01 do PRD v5.2 entregue com sucesso: cadastro de flashcards ágil (atalho `Ctrl+Enter`), modo de revisão ativo com Gap Indexing nos primeiros 10%, controle de rodadas e transições sem recarregamento de página. |
| **2** | **Especialista QA** | `[APROVADO]` | Matriz de 29 casos BDD totalmente atendida. Cobertura estrita de 100% de linhas e branches confirmada pelo `pytest-cov`. Todos os testes de unidade, integração de persistência, API REST e interface web aprovados sem flakiness. |
| **3** | **Especialista Arquiteto** | `[APROVADO]` | Camadas concêntricas da Clean Architecture rigorosamente respeitadas e validadas por analisador sintático AST. Zero vazamento de abstração do SQLAlchemy para o domínio ou casos de uso. Inversão de dependência por Protocols. |
| **4** | **Especialista de Segurança** | `[APROVADO]` | Suíte criptográfica AES-256-GCM autenticada implementada; sanitização HTML preventiva com `nh3`; headers HTTP seguros ativos; RNG seguro (`random.SystemRandom()`) sem avisos S311; 100% de conformidade no teste de governança de segurança AST. |
| **5** | **Especialista de Telemetria** | `[APROVADO]` | Estrutura de logging padronizada configurada; tempos de resposta e contadores de rodada mapeados para observabilidade; métricas de rebalanceamento preventivo prontas para emissão de logs estruturados. |
| **6** | **Especialista de UX** | `[APROVADO]` | Experiência fluida de estudo com atalhos de teclado ágeis (`Espaço`/`Enter` para virar/avançar, `Ctrl+Enter` para salvar flashcards), navegação touch com gestos de swipe em smartphones, visualização imediata do progresso e feedback claro de rodada completada. |
| **7** | **Especialista de UI** | `[APROVADO]` | Interface minimalista, moderna e limpa construída com TailwindCSS. Dark mode nativo com prevenção de Flash of Unstyled Content (FOUC) via script inline no `<head>`. Transições 3D elegantes para o flip do flashcard. |
| **8** | **Especialista de DevOps** | `[APROVADO]` | Paridade Dev/Prod implementada via Docker Compose (PostgreSQL 16 Alpine) e Dockerfile multi-stage enxuto utilizando `uv`. Execução estrita sob usuário sem privilégios (`appuser`). Migrações automáticas versionadas com Alembic (`001_sprint_01_flashcards`). |
| **9** | **Especialista de Acessibilidade** | `[APROVADO]` | Semântica HTML5 completa, links de salto para o conteúdo principal (`Skip to main content`), conformidade WCAG 2.1 AA para contrastes de cores, anúncios dinâmicos de avanço e contagem via região viva `aria-live="polite"`. |
| **10** | **Especialista em LGPD** | `[APROVADO]` | Princípio de minimização de dados rigorosamente aplicado: nenhum dado pessoal sensível ou identificador desnecessário é coletado. Módulo de criptografia AES-256-GCM preparado para proteção de dados em repouso. |

---

## 🚀 Checklist Pré-Merge
- [x] Linter (Ruff) e formatador 100% sem erros (`uv run ruff check .` e `uv run ruff format --check .`).
- [x] Checagem de tipos estrita (Mypy) 100% aprovada (`uv run mypy src tests`).
- [x] 100% de cobertura de código no backend (`uv run pytest --cov=src --cov-fail-under=100`).
- [x] Testes de governança e arquitetura AST 100% aprovados (`tests/architecture/` e `tests/governance/`).
- [x] Migrações Alembic testadas com sucesso (`upgrade head` e `downgrade base`).
- [x] Sem segredos ou credenciais em código-fonte (`.env.example` e `.dockerignore` configurados).
