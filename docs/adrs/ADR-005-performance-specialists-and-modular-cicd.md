# ADR-005: Especialistas de Performance Tripartidos e Modularização do CI/CD

* **Status:** `Aprovado`
* **Data:** 2026-10-03
* **Autor:** Especialista Arquiteto
* **Contexto Técnico:** [PRD.md](file:///c:/Users/Pichau/Desktop/study_reviewer/PRD.md) v5.2, [ADR-001](file:///c:/Users/Pichau/Desktop/study_reviewer/docs/adrs/ADR-001-clean-architecture-layering.md), [ADR-003](file:///c:/Users/Pichau/Desktop/study_reviewer/docs/adrs/ADR-003-docker-dev-prod-parity-and-migrations.md) e [.gemini/rules/sprint-development-lifecycle.md](file:///c:/Users/Pichau/Desktop/study_reviewer/.gemini/rules/sprint-development-lifecycle.md)

---

## 1. Contexto e Problema

Com a conclusão e aprovação da Sprint 01 em produção (Pull Request #1), o sistema atingiu alta maturidade arquitetural e funcional. No entanto, duas necessidades críticas de evolução emergiram antes do início da Sprint 02:

1. **Auditoria Especializada de Performance Ausente na Bancada:**
   * A bancada original de 10 especialistas concentrava qualidade funcional, segurança (OWASP), arquitetura e usabilidade/acessibilidade, mas não possuía guardiões com mandato formal e métricas específicas para performance de backend em Python, renderização de interface no frontend e eficiência de consultas/persistência no banco de dados.
   * Sem personas dedicadas, problemas como queries N+1, complexidade assintótica acidental $\mathcal{O}(n^2)$, alocação excessiva de memória ou inchaço de assets estáticos poderiam escapar da esteira de auditoria.

2. **Pipeline de CI/CD Monolítico e Sobrecarrregado:**
   * O pipeline original (`.github/workflows/ci.yml`) agregava em um único job todas as responsabilidades do backend (Ruff linter, Ruff format, Mypy strict, AST de arquitetura, meta-teste de segurança e 100% de cobertura com Pytest), além de um job básico de frontend.
   * Esse acoplamento causava:
     - Feedback lento e sequencial (falha de formatação impedia saber se os testes passavam).
     - Dificuldade de diagnóstico imediato em Pull Requests.
     - Falta de paralelismo entre checagens independentes.
     - Ausência de validação automatizada de compilação de assets estáticos do Tailwind CSS e integridade de templates Jinja2.

---

## 2. Decisão Arquitetural

Adotar uma expansão estrutural da governança técnica e uma segregação estrita por responsabilidade única no CI/CD:

### 2.1 Expansão da Bancada para 13 Especialistas de Auditoria
Criar formalmente 3 novos especialistas e suas respectivas skills:
1. **Persona 11: Especialista de Performance de Programação Python** (`11-python-performance-specialist.md` / `python-performance-auditor`):
   - Guardião da complexidade assintótica ($\mathcal{O}(1)/\mathcal{O}(n)$ vs $\mathcal{O}(n^2)$), uso de estruturas ideais (`set`, `deque`, `dict`), alocação de memória e geradores, e idiomas de alta performance do Python 3.13+.
2. **Persona 12: Especialista de Performance de Frontend** (`12-frontend-performance-specialist.md` / `frontend-performance-auditor`):
   - Guardião dos Core Web Vitals (LCP $\le 2.5\text{s}$, INP $\le 200\text{ms}$, CLS $\le 0.1$), minificação estática de Tailwind CSS, eficiência no DOM sem layout thrashing e fragmentos HTMX parciais enxutos.
3. **Persona 13: Especialista de Performance de Banco de Dados** (`13-database-performance-specialist.md` / `database-performance-auditor`):
   - Guardião da eliminação de queries N+1 via eager loading (`selectinload`), cobertura de índices B-Tree e *covering indexes* (`INCLUDE`), persistência em lote atômica (`save_all`), e transações com ciclo de vida curto.

### 2.2 Segregação Modular do CI/CD em Workflows de Responsabilidade Única
Substituir o workflow monolítico `ci.yml` por pipelines independentes em `.github/workflows/`, disparados em paralelo:
1. `ci-backend-lint.yml`: Linting e formatação estrita com Ruff.
2. `ci-backend-types.yml`: Verificação estática de tipos com Mypy em modo estrito.
3. `ci-backend-governance.yml`: Governança arquitetural Clean Architecture (ADR-001) e meta-testes AST de segurança e especialistas.
4. `ci-backend-tests-coverage.yml`: Suíte completa de testes unitários e de integração com barreira obrigatória de 100% de cobertura.
5. `ci-frontend-assets.yml`: Ambiente Node.js isolado para compilação estática e minificação do Tailwind CSS via `npm run build:css`.
6. `ci-frontend-quality.yml`: Validação sintática e integridade estrutural de todos os templates Jinja2 e componentes HTML/HTMX.
7. `cd-docker-parity.yml`: Build da imagem multi-stage e teste de paridade de contêiner com usuário não-root.

---

## 3. Consequências

### Positivas
* **Prevenção Ativa de Gargalos:** Cada PR será inspecionada por especialistas dedicados a tempo de execução Python, renderização no cliente e I/O de banco de dados.
* **Execução Paralela no CI/CD:** O tempo total de execução da esteira cai drasticamente com a execução simultânea dos 7 workflows no GitHub Actions.
* **Isolamento de Falhas:** Erros de lint, tipagem, templates ou testes são identificados instantaneamente em badges e status checks dedicados no GitHub.
* **Paridade Garantida:** Compilação do Tailwind CSS e templates Jinja2 passam a ser validados automaticamente em toda PR antes do merge.

### Considerações e Trade-offs
* O template de Pull Request passa a exigir a assinatura formal de todos os 13 especialistas.
* Para PRs de escopo restrito (ex: puramente backend), os especialistas de frontend emitem `[N/A JUSTIFICADO]`, mantendo a governança sem onerar o ciclo de entrega.
