<!-- Template Oficial de Pull Request — Study Reviewer -->
## 📋 Identificação da Sprint
* **Entrega:** `PR de Melhorias Pré-Sprint 2 — Especialistas de Performance e CI/CD Modular`
* **Branch de Origem:** `feature/improvements-specialists-and-cicd`
* **Branch de Destino:** `staging`
* **ADRs Aprovados pelo Usuário:**
  * `docs/adrs/ADR-001-clean-architecture-layering.md`
  * `docs/adrs/ADR-002-flashcard-gap-indexing-pool.md`
  * `docs/adrs/ADR-003-docker-dev-prod-parity-and-migrations.md`
  * `docs/adrs/ADR-004-flashcard-many-to-many-topics.md`

---

## 🎯 Resumo da Entrega & Objetivo
Implementação do pacote de melhorias estruturais de engenharia, governança técnica e automação contínua antes do início da Sprint 02:
1. **Bancada dos 13 Especialistas de Auditoria:**
   - Criação da **Persona 11: Especialista de Performance de Programação Python** (`docs/personas/11-python-performance-specialist.md`) e respectiva skill (`.gemini/skills/python-performance-auditor/SKILL.md`) para auditar complexidade algorítmica ($\mathcal{O}(1)/\mathcal{O}(n)$ vs $\mathcal{O}(n^2)$), uso de geradores, alocação de memória e idiomas eficientes em Python 3.13+.
   - Criação da **Persona 12: Especialista de Performance de Frontend** (`docs/personas/12-frontend-performance-specialist.md`) e respectiva skill (`.gemini/skills/frontend-performance-auditor/SKILL.md`) para auditar Core Web Vitals (LCP, INP, CLS), compilação estática e purga do Tailwind CSS, renderização no DOM sem layout thrashing e fragmentos HTMX enxutos.
   - Criação da **Persona 13: Especialista de Performance de Banco de Dados** (`docs/personas/13-database-performance-specialist.md`) e respectiva skill (`.gemini/skills/database-performance-auditor/SKILL.md`) para auditar e eliminar o antipadrão N+1 queries, validar covering indexes e índices compostos, impor persistência em lote (`save_all`) e delimitar ciclos transacionais enxutos.
2. **Segregação Modular do CI/CD no GitHub Actions:**
   - Eliminação do workflow monolítico sobrecarregado (`ci.yml`).
   - Implementação de 7 pipelines paralelos e independentes, cada um com sua responsabilidade atômica:
     - `ci-backend-lint.yml`: Linting e formatação estrita com Ruff.
     - `ci-backend-types.yml`: Verificação estática de tipos com Mypy strict.
     - `ci-backend-governance.yml`: Governança arquitetural Clean Architecture (ADR-001) e meta-testes AST.
     - `ci-backend-tests-coverage.yml`: Suíte completa de testes com exigência de 100% de cobertura.
     - `ci-frontend-assets.yml`: Ambiente Node.js isolado para compilação estática do Tailwind CSS (`npm run build:css`).
     - `ci-frontend-quality.yml`: Validação sintática e integridade de todos os templates Jinja2 e componentes HTML/HTMX.
     - `cd-docker-parity.yml`: Build de contêiner multi-stage e teste de paridade sob usuário não-root `appuser`.
3. **Protocolo de Auditoria Concorrente por Clusters (Multi-Agente):**
   - Formalização do protocolo de paralelização em `docs/personas/00-parallel-audit-protocol.md`.
   - Criação da skill de orquestração `.gemini/skills/parallel-audit-orchestrator/SKILL.md`.
   - Distribuição dos 13 especialistas em 4 clusters de competência executados simultaneamente via `invoke_subagent`.
4. **Governança Automatizada e Integridade de Templates:**
   - Novo teste de governança AST (`tests/governance/test_personas_governance.py`) para validar programaticamente a completude documental e técnica dos 13 especialistas, workflows e protocolo paralelo.
   - Novo teste de frontend (`tests/unit/web/test_frontend_templates.py`) validando sintaxe de templates Jinja2 e presença de assets estáticos compilados.
   - Atualização do ciclo de vida em `.gemini/rules/sprint-development-lifecycle.md`, `.github/PULL_REQUEST_TEMPLATE.md` e `PRD.md`.
   - Adição do arquivo de lock determinístico `package-lock.json`.

---

## 🧪 Metodologia TDD & Cobertura de Testes (100% Obrigatório)
- [x] **TDD Aplicado:** Testes de governança e integridade desenvolvidos e validados previamente à consolidação.
- [x] **Cobertura Backend:** 100% de cobertura rigorosamente mantida em todas as 25 unidades de código de produção (`pytest --cov=src --cov-fail-under=100`).
- [x] **Cobertura Frontend:** Testes sintáticos automatizados cobrindo todos os templates Jinja2 e parciais HTMX.

```text
Name                                                   Stmts   Miss  Cover
--------------------------------------------------------------------------
src\adapters\api\controllers.py                          111      0   100%
src\adapters\persistence\mappers.py                       31      0   100%
src\adapters\persistence\models.py                        42      0   100%
src\adapters\persistence\repositories.py                 144      0   100%
src\adapters\web\controllers.py                          147      0   100%
src\application\dto\flashcard_dto.py                      19      0   100%
src\application\dto\study_dto.py                          18      0   100%
src\application\dto\subject_dto.py                         7      0   100%
src\application\dto\topic_dto.py                           7      0   100%
src\application\ports\repositories.py                     26      0   100%
src\application\use_cases\flashcard_use_cases.py          65      0   100%
src\application\use_cases\study_session_use_cases.py     105      0   100%
src\application\use_cases\subject_use_cases.py            20      0   100%
src\application\use_cases\topic_use_cases.py              25      0   100%
src\domain\entities.py                                    50      0   100%
src\domain\exceptions.py                                   5      0   100%
src\domain\protocols.py                                    4      0   100%
src\domain\services.py                                    50      0   100%
src\infrastructure\config.py                              11      0   100%
src\infrastructure\database.py                            22      0   100%
src\infrastructure\rng.py                                 11      0   100%
src\infrastructure\security\crypto.py                     31      0   100%
src\infrastructure\security\middleware.py                 13      0   100%
src\infrastructure\security\sanitization.py                6      0   100%
src\infrastructure\web\app.py                             24      0   100%
--------------------------------------------------------------------------
TOTAL                                                    994      0   100%
Required test coverage of 100% reached. Total coverage: 100.00%
126 passed, 2 warnings in 3.32s
```

---

## 🛡️ Governança de Testes de Segurança
- [x] Todos os testes que validam segurança ou vulnerabilidades foram decorados com `@pytest.mark.security`.
- [x] Todas as docstrings de testes de segurança contêm os campos obrigatórios `Vulnerabilidade prevenida:` e `Garantia de segurança:`.
- [x] O meta-teste de AST (`tests/governance/test_security_governance.py`) passou com 100% de conformidade.

---

## 📐 Conformidade Arquitetural & ADRs Ativas (Auditoria do Arquiteto)
- [x] O teste automatizado de arquitetura AST (`tests/architecture/test_clean_architecture.py`) passou com 100% de sucesso.
- [x] Todas as ADRs vigentes seguem o padrão Nygard e foram validadas pelo teste `test_all_adrs_follow_nygard_standard()`:
  - [x] **ADR-001 (Clean Architecture):** Núcleo de domínio isolado sem dependências de frameworks ou ORM; contratos puros via Protocols.
  - [x] **ADR-002 (Gap Indexing na Pool):** Posições em múltiplos de 100, ponto médio nos 10% e rebalanceamento preventivo.
  - [x] **ADR-003 (Docker & Migrações):** Multi-stage build com usuário não-root e compose com healthchecks.
  - [x] **ADR-004 (Relacionamento N:N):** Vínculo muitos-para-muitos entre Flashcards e Topics via tabela associativa declarativa.

---

## 🏛️ Bancada dos 13 Especialistas — Auditoria Obrigatória

| # | Especialista | Status | Parecer Técnico / Justificativa |
| :-: | :--- | :---: | :--- |
| **1** | **Especialista de Produto** | `[APROVADO]` | Melhorias estruturais pré-Sprint 2 implementadas com sucesso: governança expandida para performance e pipelines de CI/CD desacoplados com responsabilidades atômicas, garantindo escalabilidade para o roadmap do produto. |
| **2** | **Especialista QA** | `[APROVADO]` | Qualidade holística validada: 126 testes passando com 100% de cobertura confirmada no backend (`pytest-cov`) e novos testes de integridade de templates Jinja2 e governança das 13 personas executados com sucesso. |
| **3** | **Especialista Arquiteto** | `[APROVADO]` | Arquitetura de governança e esteira de entrega aprovadas. Princípio da Responsabilidade Única (SRP) aplicado com louvor ao CI/CD. ADR-005 formalizada e compatível com ADR-001/003. Domínio e use cases 100% puros e desacoplados. |
| **4** | **Especialista de Segurança** | `[APROVADO]` | Segurança e conformidade validadas. Meta-teste AST aprovado, testes de segurança devidamente decorados com `@pytest.mark.security` e docstrings explicativas estruturadas. Zero segredos ou credenciais expostas. |
| **5** | **Especialista de Telemetria** | `[APROVADO]` | Telemetria e rastreabilidade mantidas íntegras. Pipeline de CI/CD agora publica artefatos de cobertura e logs estruturados de execução isolada para cada responsabilidade. |
| **6** | **Especialista de UX** | `[APROVADO]` | Experiência do desenvolvedor (DX) maximizada pela redução drástica do tempo de feedback nos PRs via execução paralela e isolamento claro de erros. Preservação de acessibilidade e tempos de resposta rápidos. |
| **7** | **Especialista de UI** | `[APROVADO]` | Integridade da camada visual assegurada. Compilação estática de Tailwind CSS automatizada no pipeline de CI com verificação de geração de bundle minificado e testes sintáticos de templates Jinja2. |
| **8** | **Especialista de DevOps** | `[APROVADO]` | Infraestrutura de CI/CD modernizada com 7 workflows paralelos e atômicos (lint, types, governance, tests-cov, frontend-assets, frontend-quality, docker-parity). Determinismo garantido via lockfiles (`uv.lock` e `package-lock.json`). |
| **9** | **Especialista de Acessibilidade** | `[APROVADO]` | Conformidade com WCAG 2.1 AA preservada em todos os templates e validada via testes automatizados de estrutura e integridade de markup. |
| **10** | **Especialista em LGPD** | `[APROVADO]` | Princípio de minimização de dados rigorosamente mantido. Nenhuma informação pessoal ou telemetria invasiva adicionada aos fluxos ou artefatos de build. |
| **11** | **Especialista de Performance Python** | `[APROVADO]` | Persona e skill `python-performance-auditor` estabelecidas com sucesso. Diretrizes de complexidade algorítmica Big-O (tempo e espaço), uso de geradores e hashing O(1) formalizadas e integradas ao ciclo de engenharia. |
| **12** | **Especialista de Performance Frontend** | `[APROVADO]` | Persona e skill `frontend-performance-auditor` estabelecidas com sucesso. Pipeline agora valida formalmente a geração de Tailwind CSS minificado estático e a ausência de bibliotecas de script desnecessárias. |
| **13** | **Especialista de Performance de Banco** | `[APROVADO]` | Persona e skill `database-performance-auditor` estabelecidas com sucesso. Critérios rigorosos contra queries N+1, obrigatoriedade de índices B-tree/covering e persistência em lote atômica consolidados como portões de aprovação obrigatórios. |

---

## 🚀 Checklist Pré-Merge
- [x] CI/CD Modular no GitHub Actions 100% verde (Lint, Types, Governance, Tests 100% Cov, Frontend Assets, Frontend Quality e Docker Parity).
- [x] Linter (Ruff) e checagem de tipos (Mypy) sem nenhum aviso.
- [x] Sem dados sensíveis ou segredos commitados (`.env.example` atualizado).
- [x] Paridade Docker verificada localmente (`docker compose up`).
