---
name: billing-lifecycle-auditor
description: Audits subscription state machines, smart dunning management, pro-rata calculations, plan migrations, and PCI-DSS SAQ A compliance.
---

# Billing Lifecycle Auditor (Skill do Especialista de Pagamento e Cobrança)

Esta skill é operada pelo **Especialista de Pagamento e Cobrança** durante a fase de auditoria final da Sprint, imediatamente antes da abertura ou aprovação da Pull Request para a branch `staging`.

Seu objetivo é conduzir uma auditoria detalhada no **ciclo de vida das assinaturas, máquinas de estado de planos, gerenciamento inteligente de inadimplência (*dunning management*), cálculo matemático de pro-rata e conformidade estrita com as normas de segurança PCI-DSS SAQ A**.

---

## 1. Entrada e Gatilho
* **Arquivos e Artefatos Base:**
  * Entidades e serviços de assinatura: `src/domain/entities/`, `src/domain/services/billing/`.
  * Casos de uso de planos e renovações: `src/application/use_cases/`.
  * Modelos de banco de dados: `src/adapters/persistence/models.py`.
  * Git diff da branch da sprint contra a branch `staging` (`git diff staging...HEAD`).
* **Gatilho de Execução:** Auditoria de PR para alterações que envolvam ciclo de vida de assinaturas, planos de estudantes, cancelamento, renovação automática, retentativas de faturamento ou checkout de cartão.

---

## 2. Checklist Exaustivo de Auditoria de Ciclo de Vida e Faturamento

O Especialista de Pagamento e Cobrança avalia o sistema sob os seguintes critérios:

1. **Máquina de Estados Determinística de Assinaturas:**
   * *Estados Claros e Transições Válidas:* O modelo de assinatura opera sobre uma máquina de estados explícita (`Trialing`, `Active`, `PastDue`, `Canceled`, `Incomplete`), proibindo transições ambíguas (ex: passar direto de `Canceled` para `Active` sem novo checkout)?
   * *Revogação e Expiração Atômica:* A expiração ou o cancelamento do plano revoga os privilégios pagos de forma precisa e auditada na data de corte acordada (*current_period_end*)?

2. **Gestão Inteligente de Inadimplência (Smart Dunning Management):**
   * *Período de Carência (*Grace Period*):* Quando uma tentativa de renovação com cartão falha, o sistema entra em status `PastDue` com período de tolerância antes de suspender o acesso do estudante?
   * *Retentativas Programadas:* O sistema agenda retentativas com espaçamento progressivo e dispara notificações proativas de falha de cobrança orientando o estudante a atualizar seu meio de pagamento?

3. **Cálculo Matemático Auditado de Pro-Rata:**
   * *Upgrades e Downgrades Justos:* Mudanças de plano no meio do ciclo de faturamento calculam a proporção exata de dias utilizados versus o valor do novo plano, gerando créditos ou cobranças complementares auditáveis sem arredondamentos arbitrários?

4. **Conformidade com PCI-DSS SAQ A (Zero Dados de Cartão):**
   * *Zero Armazenamento de PAN/CVV:* O backend, banco de dados ou logs jamais armazenam números de cartão de crédito (PAN), códigos de segurança (CVV) ou datas de validade?
   * *Tokenização na Borda:* A coleta de dados do cartão é realizada estritamente pelo SDK/IFrame do provedor de pagamento (ex: Stripe Elements), trafegando apenas o `payment_method_id` tokenizado para o backend?
   * *Logs Sem Dados Sensíveis:* Registros de log de pagamento não expõem identificadores sensíveis ou dados que possam reconstruir instrumentos de pagamento?

---

## 3. Emissão de Parecer na PR

A skill gera a saída formal padronizada para inclusão na tabela de especialistas da Pull Request:

### Caso Aprovado:
```markdown
| **17** | **Especialista de Pagamento e Cobrança** | `[APROVADO]` | Ciclo de faturamento e conformidade PCI auditados com sucesso. Máquina de estados de assinaturas determinística, dunning management com retentativas inteligentes, cálculo correto de pro-rata e conformidade estrita com PCI-DSS SAQ A (zero dados de cartão). |
```

### Caso Reprovado / Bloqueante:
```markdown
| **17** | **Especialista de Pagamento e Cobrança** | `[BLOQUEANTE]` | Falha de faturamento ou compliance identificada: [descrever se houve campo de cartão no banco de dados, transição inválida de estado de assinatura ou suspensão abrupta sem dunning]. Correção obrigatória antes do merge. |
```
