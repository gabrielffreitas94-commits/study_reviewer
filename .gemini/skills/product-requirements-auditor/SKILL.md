---
name: product-requirements-auditor
description: Audits pull request changes against PRD.md and approved use cases to ensure exact scope adherence, zero scope creep, and business rule compliance.
---

# Product Requirements Auditor (Skill do Especialista de Produto)

Esta skill é utilizada pelo **Especialista de Produto** durante a auditoria final da Sprint, imediatamente antes da abertura ou aprovação da Pull Request direcionada para a branch `staging`.

---

## 1. Entrada e Gatilho
* **Arquivos Base:**
  * `PRD.md` (requisitos da Sprint).
  * `docs/sprints/sprint-XX/01-use-cases-and-edge-cases.md` (matriz de casos de uso).
  * Código implementado na branch `feature/sprint-XX-*` e testes correspondentes.
* **Gatilho de Execução:** Término do ciclo TDD e prontidão para submissão da PR.

---

## 2. Checklist de Auditoria de Produto

O Especialista de Produto executa uma checagem rigorosa respondendo às seguintes perguntas:

1. **Rastreabilidade de Casos de Uso:**
   * Todos os cenários descritos na matriz `01-use-cases-and-edge-cases.md` possuem testes correspondentes passando na suíte de testes?
2. **Ausência de Escopo Fantasma (*Gold Plating*):**
   * Foi adicionado algum campo, tabela, rota ou funcionalidade que não estava prevista no PRD da Sprint? (Ex: tentar implementar sistema de notas em flashcards na Sprint 1).
3. **Fidelidade às Regras de Domínio:**
   * As regras centrais do PRD foram rigorosamente respeitadas?
     * Flashcards: Inserção nos primeiros 10% ($\max(1, \lfloor 0.1 \times N \rfloor)$) e shuffle geral ao atingir o fim da fila.
     * Perguntas Abertas (a partir da Sprint 2): Calendário estrito `[1, 7, 15, 30, 60, 90, 180]`, avanço apenas com 100% e queda de 6 para 2.
4. **Critérios de Aceitação da Sprint:**
   * O entregável prometido no PRD (ex: sistema funcional rodando em container Docker) está 100% satisfeito?

---

## 3. Emissão de Parecer

A skill deve gerar a saída no formato padronizado para inclusão na Pull Request:

### Caso Aprovado:
```markdown
| **1** | **Especialista de Produto** | `[APROVADO]` | Todos os XX casos de uso foram verificados e validados contra os requisitos da Sprint XX no PRD v5.1. Zero escopo fantasma identificado. Critérios de aceitação atendidos integralmente. |
```

### Caso Reprovado / Ressalvas:
```markdown
| **1** | **Especialista de Produto** | `[BLOQUEANTE]` | Identificado desvio de produto: [descrever o desvio ou funcionalidade faltante/excedente]. Ajuste necessário antes de prosseguir com a PR. |
```
