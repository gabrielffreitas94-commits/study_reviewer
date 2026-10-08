---
name: payment-transactions-auditor
description: Audits financial transaction integrity, strict idempotency enforcement (Idempotency-Key), double-spending prevention, and immutable ledger accounting.
---

# Payment Transactions Auditor (Skill do Especialista de Pagamento e Cobrança)

Esta skill é operada pelo **Especialista de Pagamento e Cobrança** durante a fase de auditoria final da Sprint, imediatamente antes da abertura ou aprovação da Pull Request para a branch `staging`.

Seu objetivo é conduzir uma auditoria rigorosa na **integridade transacional e consistência financeira do sistema: obrigatoriedade de chaves de idempotência em mutações financeiras, prevenção inegociável de double-spending via locks atômicos, atomicidade ACID entre débito e liberação de serviço, e escrituração imutável em Ledger contábil**.

---

## 1. Entrada e Gatilho
* **Arquivos e Artefatos Base:**
  * Controladores de pagamento e checkout: `src/adapters/api/`, `src/adapters/web/`.
  * Casos de uso de transação financeira: `src/application/use_cases/`.
  * Modelos de banco de dados e repositórios de transação: `src/adapters/persistence/models.py`, `src/adapters/persistence/repositories.py`.
  * Git diff da branch da sprint contra a branch `staging` (`git diff staging...HEAD`).
* **Gatilho de Execução:** Auditoria de PR para alterações que criem cobranças, processem autorizações de pagamento, emitam ordens financeiras ou debitem saldos/créditos de usuários.

---

## 2. Checklist Exaustivo de Auditoria de Transações Financeiras

O Especialista de Pagamento e Cobrança avalia o código sob os seguintes critérios de integridade:

1. **Idempotência Estrita em Mutações Financeiras:**
   * *`Idempotency-Key` Obrigatório:* Qualquer endpoint que inicie checkout, autorize pagamento, debite saldo ou conceda créditos exige o envio de uma chave de idempotência no cabeçalho ou payload?
   * *Persistência da Resposta de Idempotência:* O resultado de uma operação idempotente bem-sucedida é gravado em cache/banco de modo que chamadas subsequentes com a mesma chave retornem a resposta original sem reexecutar o débito?

2. **Prevenção de Double-Spending e Travas de Concorrência:**
   * *Bloqueio Distribuído Atômico:* O sistema utiliza locks atômicos (Redis distributed lock / `SELECT ... FOR UPDATE` no Postgres) para garantir que requisições simultâneas do mesmo usuário não processem cobranças concorrentes duplicadas (*double-click / race conditions*)?
   * *Validação de Saldo/Limite Atômica:* A verificação de limites ou saldos e sua dedução ocorrem atomicamente, sem brecha temporal (*check-then-act vulnerability*)?

3. **Atomicidade Transacional ACID:**
   * *Zero Estados Órfãos:* A gravação do registro de pagamento confirmado e a liberação correspondente do plano/recurso do estudante são executadas dentro do mesmo bloco de transação (`session.begin()`), garantindo que nunca ocorra cobrança sem concessão do serviço ou vice-versa?

4. **Escrituração Contábil Imutável (Ledger):**
   * *Livro-Razão Auditável:* Todas as movimentações financeiras geram lançamentos imutáveis com valor, moeda, identificador de usuário, timestamp UTC e status, sendo terminantemente proibida a mutação destrutiva (`UPDATE` ou `DELETE`) de registros contábeis históricos?

---

## 3. Emissão de Parecer na PR

A skill gera a saída formal padronizada para inclusão na tabela de especialistas da Pull Request:

### Caso Aprovado:
```markdown
| **17** | **Especialista de Pagamento e Cobrança** | `[APROVADO]` | Integridade de transações financeiras auditada com sucesso. Idempotência estrita com Idempotency-Key, prevenção absoluta de double-spending via locks atômicos, atomicidade ACID garantida e ledger contábil imutável. |
```

### Caso Reprovado / Bloqueante:
```markdown
| **17** | **Especialista de Pagamento e Cobrança** | `[BLOQUEANTE]` | Falha de integridade financeira identificada: [descrever se houve endpoint de cobrança sem Idempotency-Key, ausência de lock atômico contra double-spending ou commit parcial sem atomicidade ACID]. Correção obrigatória antes do merge. |
```
