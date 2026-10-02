---
name: product-requirements-auditor
description: Audits pull request changes against the project PRD.md and approved use cases to ensure exact scope adherence, zero scope creep, and business rule compliance.
---

# Product Requirements Auditor (Skill do Especialista de Produto)

Esta skill é utilizada pelo **Especialista de Produto** durante a auditoria final da Sprint, imediatamente antes da abertura ou aprovação da Pull Request.

O funcionamento desta skill é agnóstico a projetos, extraindo os critérios de aceitação e regras de negócio do `PRD.md` vigente no repositório.

---

## 1. Entrada e Gatilho
* **Arquivos Base:**
  * `PRD.md` (requisitos da Sprint em avaliação).
  * `docs/sprints/sprint-XX/01-use-cases-and-edge-cases.md` (matriz de casos de uso aprovada).
  * Código implementado na branch `feature/sprint-XX-*` e testes correspondentes.
* **Gatilho de Execução:** Término do ciclo TDD e prontidão para submissão da PR.

---

## 2. Checklist de Auditoria de Produto

O Especialista de Produto executa uma checagem rigorosa respondendo às seguintes perguntas:

1. **Rastreabilidade de Casos de Uso:**
   * Todos os cenários descritos na matriz `01-use-cases-and-edge-cases.md` possuem testes correspondentes passando na suíte de testes?
2. **Ausência de Escopo Fantasma (*Gold Plating*):**
   * Foi adicionado algum campo, tabela, rota ou funcionalidade que não estava prevista no `PRD.md` para a sprint atual?
3. **Fidelidade às Regras de Negócio do PRD:**
   * As regras centrais e restrições de negócio documentadas no `PRD.md` foram rigorosamente respeitadas no comportamento do sistema?
4. **Critérios de Aceitação da Sprint:**
   * O entregável prometido na documentação de requisitos para a sprint atual está 100% satisfeito?

---

## 3. Emissão de Parecer

A skill deve gerar a saída no formato padronizado para inclusão na Pull Request:

### Caso Aprovado:
```markdown
| **1** | **Especialista de Produto** | `[APROVADO]` | Todos os XX casos de uso foram verificados e validados contra os requisitos da Sprint no PRD.md. Zero escopo fantasma identificado. Critérios de aceitação atendidos integralmente. |
```

### Caso Reprovado / Ressalvas:
```markdown
| **1** | **Especialista de Produto** | `[BLOQUEANTE]` | Identificado desvio de produto: [descrever o desvio ou funcionalidade faltante/excedente em relação ao PRD.md]. Ajuste necessário antes de prosseguir com a PR. |
```
