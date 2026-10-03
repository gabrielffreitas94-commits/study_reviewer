---
name: parallel-audit-orchestrator
description: Orchestrates the parallel execution of the 13 audit specialists grouped into 4 concurrent clusters using invoke_subagent for fast, thorough PR sign-off.
---

# Parallel Audit Orchestrator (Skill de Orquestração Concorrente da Bancada)

Esta skill é operada pelo agente orquestrador ao término de cada Sprint, imediatamente antes da abertura ou atualização da Pull Request para a branch `staging`.

Seu objetivo é **paralelizar a auditoria dos 13 especialistas técnicos**, despachando **4 clusters concorrentes via `invoke_subagent`**, eliminando a latência da execução sequencial e consolidando a tabela oficial de pareceres da PR de forma unificada.

---

## 1. Entrada e Gatilho
* **Gatilho de Execução:** Finalização da implementação do código e garantia de 100% de cobertura nos testes.
* **Artefatos Inspecionados:**
  * Git diff contra a branch `staging`: `git diff staging...HEAD`.
  * Resultados da suíte de testes e linters: `pytest`, `ruff`, `mypy`.
  * Arquivos de configuração, templates e infraestrutura alterados.

---

## 2. Protocolo de Invocação Concorrente

O agente orquestrador deve chamar `invoke_subagent` com um único payload contendo exatamente os 4 clusters:

```json
{
  "Subagents": [
    {
      "TypeName": "self",
      "Role": "Cluster 1: Core & Arquitetura Auditor",
      "Prompt": "Você é o auditor técnico responsável pelos Especialistas #1 (Produto), #2 (QA) e #3 (Arquiteto). Inspecione o diff contra staging (git diff staging...HEAD) e a base de código. Avalie: (1) atendimento estrito ao PRD sem escopo fantasma; (2) cobertura de testes unitários e de integração; (3) regra de dependência da Clean Architecture e conformidade com ADRs. Retorne exatamente as 3 linhas formatadas em markdown para a tabela da PR com status [APROVADO] ou [BLOQUEANTE] com justificativa técnica."
    },
    {
      "TypeName": "self",
      "Role": "Cluster 2: Segurança & Compliance Auditor",
      "Prompt": "Você é o auditor técnico responsável pelos Especialistas #4 (Segurança), #5 (Telemetria) e #10 (LGPD). Inspecione o diff contra staging e a base de código. Avalie: (1) vulnerabilidades OWASP, sanitização na borda e decorators/docstrings de segurança AST; (2) logging estruturado e observabilidade; (3) minimização de dados e privacidade LGPD. Retorne exatamente as 3 linhas formatadas em markdown para a tabela da PR com status [APROVADO] ou [BLOQUEANTE] com justificativa técnica."
    },
    {
      "TypeName": "self",
      "Role": "Cluster 3: Experiência & Interface Auditor",
      "Prompt": "Você é o auditor técnico responsável pelos Especialistas #6 (UX), #7 (UI), #9 (Acessibilidade) e #12 (Performance Frontend). Inspecione templates Jinja2, estilos Tailwind CSS e scripts. Avalie: (1) ergonomia e atalhos de teclado; (2) fidelidade visual e ausência de FOUC; (3) conformidade WCAG 2.1 AA e navegação assistiva; (4) minificação de CSS e Core Web Vitals (LCP/INP/CLS). Retorne exatamente as 4 linhas formatadas em markdown para a tabela da PR com status [APROVADO], [BLOQUEANTE] ou [N/A JUSTIFICADO] com justificativa técnica."
    },
    {
      "TypeName": "self",
      "Role": "Cluster 4: Engenharia, Dados & Ops Auditor",
      "Prompt": "Você é o auditor técnico responsável pelos Especialistas #8 (DevOps), #11 (Performance Python) e #13 (Performance de Banco). Inspecione o Dockerfile, Compose, consultas SQLAlchemy e código backend. Avalie: (1) Docker multi-stage, usuário não-root e dev/prod parity; (2) complexidade algorítmica Big-O, uso de geradores e ausência de loops redundantes; (3) prevenção inegociável de queries N+1, índices B-tree/covering e persistência bulk. Retorne exatamente as 3 linhas formatadas em markdown para a tabela da PR com status [APROVADO] ou [BLOQUEANTE] com justificativa técnica."
    }
  ]
}
```

---

## 3. Consolidação e Preenchimento da PR

Ao receber as respostas dos 4 subagentes, o agente orquestrador:
1. Valida se todos os 13 especialistas emitiram seus pareceres formais (nenhum especialista pode ser omitido).
2. Ordena os pareceres do #1 ao #13.
3. Preenche a tabela oficial no template de Pull Request (`.github/PULL_REQUEST_TEMPLATE.md` e documento da Sprint em `docs/sprints/`).
