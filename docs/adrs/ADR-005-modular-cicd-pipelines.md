# ADR-005: Segregação Modular de Pipelines de CI/CD em Workflows Independentes

* **Status:** `Aprovado`
* **Data:** 2026-10-03
* **Autor:** Especialista Arquiteto
* **Contexto Técnico:** [PRD.md](file:///c:/Users/Pichau/Desktop/study_reviewer/PRD.md) v5.2, [ADR-001](file:///c:/Users/Pichau/Desktop/study_reviewer/docs/adrs/ADR-001-clean-architecture-layering.md), [ADR-003](file:///c:/Users/Pichau/Desktop/study_reviewer/docs/adrs/ADR-003-docker-dev-prod-parity-and-migrations.md) e [.gemini/rules/sprint-development-lifecycle.md](file:///c:/Users/Pichau/Desktop/study_reviewer/.gemini/rules/sprint-development-lifecycle.md)

---

## 1. Contexto e Problema
O pipeline original de automação contínua (`.github/workflows/ci.yml`) agregava em um único job todas as etapas de validação do backend (Ruff linter, Ruff format, Mypy strict, AST de arquitetura, meta-teste de segurança e 100% de cobertura com Pytest), além de um placeholder básico para o frontend.

Esse modelo monolítico apresentava limitações arquiteturais:
1. **Feedback Sequencial Lento:** Falhas cosméticas de formatação ou linter bloqueavam a execução dos testes e a verificação de tipos.
2. **Falta de Paralelismo:** Processos independentes (como verificação estática de tipos, compilação de assets frontend e checagens AST) eram forçados a rodar em série.
3. **Ausência de Validação de Assets:** Não havia validação isolada do build estático do Tailwind CSS e da integridade de sintaxe dos templates Jinja2.

---

## 2. Decisão Arquitetural
Adotar a segregação estrita por **Responsabilidade Única (SRP)** nas esteiras de integração e entrega contínua, decompondo o arquivo monolítico em 7 workflows paralelos e atômicos em `.github/workflows/`:

1. `ci-backend-lint.yml`: Linting e formatação estrita com Ruff (`ruff check` e `ruff format --check`).
2. `ci-backend-types.yml`: Verificação estática estrita de tipos com Mypy (`mypy src tests`).
3. `ci-backend-governance.yml`: Conformidade arquitetural Clean Architecture (ADR-001) e meta-testes AST.
4. `ci-backend-tests-coverage.yml`: Suíte completa de testes com exigência de 100% de cobertura (`pytest-cov`).
5. `ci-frontend-assets.yml`: Ambiente Node.js isolado para compilação estática do Tailwind CSS (`npm run build:css`).
6. `ci-frontend-quality.yml`: Validação sintática e integridade estrutural de templates Jinja2 em processo isolado.
7. `cd-docker-parity.yml`: Build da imagem multi-stage e teste de fumaça sob usuário não-root `appuser`.

---

## 3. Consequências

### Positivas
* **Execução Paralela:** O tempo total de validação da esteira cai drasticamente no GitHub Actions, com jobs independentes executando em paralelo (cada um concluindo entre 7s e 16s).
* **Diagnóstico Imediato:** Identificação precisa e isolada de falhas diretamente nos checks do GitHub.
* **Isolamento de Contexto:** Processos de frontend (Node.js) e backend (Python 3.13) rodam em ambientes totalmente apartados.

### Considerações e Trade-offs
* Múltiplos arquivos de configuração em `.github/workflows/`, exigindo manutenção modular de cada etapa.
