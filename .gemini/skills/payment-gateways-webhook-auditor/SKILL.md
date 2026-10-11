---
name: payment-gateways-webhook-auditor
description: Audits payment gateway integrations, cryptographic webhook signature validation (HMAC SHA-256), transactional outbox pattern, event deduplication, and Ports & Adapters decoupling.
---

# Payment Gateways & Webhook Auditor (Skill do Especialista de Pagamento e Cobrança)

Esta skill é operada pelo **Especialista de Pagamento e Cobrança** durante a fase de auditoria final da Sprint, imediatamente antes da abertura ou aprovação da Pull Request para a branch `staging`.

Seu objetivo é conduzir uma auditoria rigorosa nas **integrações com gateways de pagamento (Stripe, Mercado Pago, PIX BACEN, In-App Purchases) e recepção de webhooks: validação criptográfica compulsória de assinaturas HMAC, ingestão assíncrona resiliente via Transactional Outbox Pattern, deduplicação de eventos repetidos e desacoplamento arquitetural**.

---

## 1. Entrada e Gatilho
* **Arquivos e Artefatos Base:**
  * Controladores e rotas de webhooks: `src/adapters/api/webhook_controllers.py`.
  * Adaptadores de gateway: `src/adapters/payment/`.
  * Filas, workers e outbox: `src/adapters/persistence/outbox.py`.
  * Git diff da branch da sprint contra a branch `staging` (`git diff staging...HEAD`).
* **Gatilho de Execução:** Auditoria de PR para alterações que criem ou modifiquem endpoints de webhooks, clientes de gateways de pagamento ou mensageria de liquidação.

---

## 2. Checklist Exaustivo de Auditoria de Gateways e Webhooks

O Especialista de Pagamento e Cobrança avalia o código sob os seguintes critérios de integração:

1. **Validação Criptográfica de Assinatura (HMAC SHA-256):**
   * *Verificação Prévia ao Parse:* O endpoint de webhook valida a assinatura criptográfica do provedor (ex: `Stripe-Signature` via HMAC SHA-256 com chave secreta) antes de desserializar o corpo da requisição?
   * *Comparação em Tempo Constante:* A verificação utiliza comparação imune a ataques de temporização (*timing-safe compare* como `hmac.compare_digest`), prevenindo *timing attacks*?
   * *Rejeição Imediata:* Qualquer requisição sem assinatura válida ou com assinatura corrompida retorna HTTP 400/401 imediatamente, sem disparar processamento interno?

2. **Deduplicação de Eventos e Tolerância a Repetições:**
   * *Chave Única por Evento (`event_id`):* O sistema armazena os IDs dos eventos recebidos e verifica a duplicidade antes de executar regras de negócio? Webhooks reenviados pelo gateway são ignorados de forma idempotente com HTTP 200/204?

3. **Ingestão Assíncrona e Resiliência (Transactional Outbox Pattern):**
   * *Resposta Rápida ao Gateway:* O controlador de webhook limita-se a validar a assinatura, gravar o evento em tabela de outbox ou fila e responder HTTP 200 em menos de $500\text{ms}$, prevenindo timeouts no webhook?
   * *Fila com Dead-Letter Queue (DLQ):* O processamento assíncrono do evento possui política de retentativas e fila de mensagens mortas (DLQ) para eventos que falhem por motivos de consistência?

4. **Desacoplamento e Inversão de Dependência (Clean Architecture):**
   * *Ports & Adapters:* A camada de domínio depende apenas de interfaces abstratas (`IPaymentGateway`), sem importar SDKs proprietárias de provedores externos?
   * *Suporte Multi-Gateway:* A arquitetura permite adicionar novos meios de pagamento (ex: PIX além de cartão) apenas implementando novos adaptadores de infraestrutura?

---

## 3. Emissão de Parecer na PR

A skill gera a saída formal padronizada para inclusão na tabela de especialistas da Pull Request:

### Caso Aprovado:
```markdown
| **17** | **Especialista de Pagamento e Cobrança** | `[APROVADO]` | Gateways e webhooks de pagamento auditados com sucesso. Validação criptográfica HMAC com timing-safe compare, ingestão assíncrona desacoplada via outbox/filas, deduplicação de eventos por ID e Clean Architecture preservada. |
```

### Caso Reprovado / Bloqueante:
```markdown
| **17** | **Especialista de Pagamento e Cobrança** | `[BLOQUEANTE]` | Vulnerabilidade de integração ou webhook identificada: [descrever se houve webhook sem validação de assinatura HMAC, processamento síncrono bloqueante no webhook ou ausência de deduplicação de eventos]. Correção obrigatória antes do merge. |
```
