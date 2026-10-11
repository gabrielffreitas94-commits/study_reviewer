<!-- Template Oficial de Pull Request — Study Reviewer -->
## 📋 Identificação da Sprint
* **Sprint:** `Sprint XX — [Nome da Sprint]`
* **Branch de Origem:** `feature/sprint-XX-[nome]`
* **Branch de Destino:** `staging`
* **Documento SPEC Aprovado pelo Usuário:** `docs/specs/sprint-XX-[nome]-spec.md`
* **ADRs Aprovados pelo Usuário:** `docs/adrs/ADR-XXX-...`

---

## 🎯 Resumo da Entrega & Objetivo
<!-- Descreva sucintamente o objetivo da sprint e o valor entregue ao produto -->

---

## 🧪 Metodologia TDD & Cobertura de Testes (100% Obrigatório)
- [ ] **TDD Aplicado:** Testes unitários e de integração foram escritos antes da implementação (Red-Green-Refactor).
- [ ] **Casos de Uso e Edge Cases:** Matriz completa gerada e validada autonomamente antes da codificação.
- [ ] **Cobertura Backend:** 100% de cobertura confirmada via `pytest --cov=src --cov-fail-under=100`.
- [ ] **Cobertura Frontend / Mobile:** Testes de UI, templates e componentes executados e validados em processos isolados.

```bash
# Cole aqui o resumo da execução do pytest com coverage
```

---

## 🛡️ Governança de Testes de Segurança
- [ ] Todos os testes que validam segurança ou vulnerabilidades foram decorados com `@pytest.mark.security`.
- [ ] Todas as docstrings de testes de segurança contêm:
  - `Vulnerabilidade prevenida:`
  - `Garantia de segurança:`
- [ ] O meta-teste de AST (`tests/governance/test_security_governance.py`) passou com 100% de sucesso.

---

## 📐 Conformidade Arquitetural & ADRs Ativas (Auditoria do Arquiteto)
- [ ] O teste automatizado de arquitetura AST (`tests/architecture/test_clean_architecture.py`) passou com 100% de sucesso.
- [ ] As decisões estruturais das ADRs ativas foram rigorosamente seguidas:
  - [ ] **ADR-001 (Clean Architecture):** Núcleo de domínio puro (zero imports de ORM/frameworks), inversão de dependência via Protocols e use cases agnósticos.
  - [ ] **ADR-002 (Gap Indexing na Pool):** Posições em múltiplos de 100, inserção por ponto médio nos 10% e rebalanceamento preventivo implementado.
  - [ ] **ADR-003 (Docker & Migrações):** Paridade dev/prod via Docker Compose com healthchecks, execução não-root e migrações versionadas no Alembic.

---

## 🏛️ Bancada dos 17 Especialistas — Auditoria Obrigatória
> **Importante:** Todo especialista deve emitir seu parecer. Status permitidos: `[APROVADO]` ou `[N/A JUSTIFICADO]`.

| # | Especialista | Status | Parecer Técnico / Justificativa |
| :-: | :--- | :---: | :--- |
| **1** | **Especialista de Produto** | `[APROVADO]` / `[N/A JUSTIFICADO]` | <!-- Justificativa --> |
| **2** | **Especialista QA** | `[APROVADO]` / `[N/A JUSTIFICADO]` | <!-- Justificativa --> |
| **3** | **Especialista Arquiteto** | `[APROVADO]` / `[N/A JUSTIFICADO]` | <!-- Justificativa --> |
| **4** | **Especialista de Segurança** | `[APROVADO]` / `[N/A JUSTIFICADO]` | <!-- Justificativa --> |
| **5** | **Especialista de Telemetria** | `[APROVADO]` / `[N/A JUSTIFICADO]` | <!-- Justificativa --> |
| **6** | **Especialista de UX** | `[APROVADO]` / `[N/A JUSTIFICADO]` | <!-- Justificativa --> |
| **7** | **Especialista de UI** | `[APROVADO]` / `[N/A JUSTIFICADO]` | <!-- Justificativa --> |
| **8** | **Especialista de DevOps** | `[APROVADO]` / `[N/A JUSTIFICADO]` | <!-- Justificativa --> |
| **9** | **Especialista de Acessibilidade** | `[APROVADO]` / `[N/A JUSTIFICADO]` | <!-- Justificativa --> |
| **10** | **Especialista em LGPD** | `[APROVADO]` / `[N/A JUSTIFICADO]` | <!-- Justificativa --> |
| **11** | **Especialista de Performance Python** | `[APROVADO]` / `[N/A JUSTIFICADO]` | <!-- Justificativa --> |
| **12** | **Especialista de Performance Frontend** | `[APROVADO]` / `[N/A JUSTIFICADO]` | <!-- Justificativa --> |
| **13** | **Especialista de Performance de Banco** | `[APROVADO]` / `[N/A JUSTIFICADO]` | <!-- Justificativa --> |
| **14** | **Especialista Mobile** | `[APROVADO]` / `[N/A JUSTIFICADO]` | <!-- Justificativa --> |
| **15** | **Especialista Flutter** | `[APROVADO]` / `[N/A JUSTIFICADO]` | <!-- Justificativa --> |
| **16** | **Especialista em Arquitetura de IA** | `[APROVADO]` / `[N/A JUSTIFICADO]` | <!-- Justificativa --> |
| **17** | **Especialista de Pagamento e Cobrança** | `[APROVADO]` / `[N/A JUSTIFICADO]` | <!-- Justificativa --> |

---

## 🚀 Checklist Pré-Merge
- [ ] CI/CD Modular no GitHub Actions 100% verde (Lint, Types, Governance, Tests 100% Cov, Frontend Assets, Frontend Quality e Docker Parity).
- [ ] Linter (Ruff) e checagem de tipos (Mypy) sem nenhum aviso.
- [ ] Sem dados sensíveis ou segredos commitados (`.env.example` atualizado).
- [ ] Paridade Docker verificada localmente (`docker compose up`).
