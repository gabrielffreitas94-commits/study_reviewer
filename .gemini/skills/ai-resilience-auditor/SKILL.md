---
name: ai-resilience-auditor
description: Audits AI system resilience, circuit breakers, graceful fallback mechanisms, exponential backoff with jitter, and strict timeout budgets.
---

# AI Resilience Auditor (Skill do Especialista em Arquitetura de IA)

Esta skill é operada pelo **Especialista em Arquitetura de IA** durante a fase de auditoria final da Sprint, imediatamente antes da abertura ou aprovação da Pull Request para a branch `staging`.

Seu objetivo é auditar exaustivamente a **tolerância a falhas, resiliência operacional e estabilidade das integrações com provedores de IA: implementação de circuit breakers, estratégias de fallback gracioso, retentativas exponenciais com jitter e isolamento contra quedas em cascata**.

---

## 1. Entrada e Gatilho
* **Arquivos e Artefatos Base:**
  * Camada de infraestrutura e serviços de IA: `src/adapters/ai/`, `src/infrastructure/`.
  * Casos de uso de avaliação: `src/application/use_cases/evaluation_use_cases.py`.
  * Tratamento de exceções e políticas de retentativa.
  * Git diff da branch da sprint contra a branch `staging` (`git diff staging...HEAD`).
* **Gatilho de Execução:** Auditoria de PR para qualquer código que execute chamadas de rede para APIs externas de IA (Google Gemini, OpenAI, etc.).

---

## 2. Checklist Exaustivo de Auditoria de Resiliência de IA

O Especialista em Arquitetura de IA avalia a solução sob os seguintes critérios de resiliência:

1. **Circuit Breakers para Provedores Externos de IA:**
   * *Proteção contra Saturação:* Toda integração com a API do provedor de IA está envolvida por um padrão *Circuit Breaker* que abre o circuito caso a taxa de erros 5xx ou timeouts consecutivos ultrapasse o limiar seguro?
   * *Recuperação Automática:* O circuit breaker possui transição para o estado *half-open* com verificação de canário para restabelecer o tráfego normal gradualmente?

2. **Degradação Graciosa e Estratégias de Fallback:**
   * *Alternância de Modelos:* Em caso de falha transitória do modelo principal (ex: Gemini 1.5 Pro indisponível), o sistema possui fallback automático para modelo mais leve e rápido (ex: Gemini Flash)?
   * *Contingência Heurística:* Se todos os modelos externos falharem, o sistema possui uma rota de contingência não destrutiva (ex: agendamento de avaliação assíncrona em fila ou resposta heurística offline), garantindo que a sessão de estudo do usuário nunca seja perdida?
   * *Isolamento de Falhas:* A indisponibilidade total da IA não afeta a navegação, revisão de flashcards estáticos e autenticação dos usuários.

3. **Retentativas Inteligentes com Backoff e Jitter:**
   * *Backoff Exponencial com Jitter:* Retentativas de erros transitórios (erros 429 de Rate Limit, timeouts de rede) aplicam espaçamento exponencial com aleatorização (*full jitter*), prevenindo ataques de manada (*thundering herd*) contra o provedor?
   * *Limite de Retentativas:* O número de tentativas é estritamente limitado (máximo 2 a 3 tentativas) antes de acionar o fallback.

4. **Timeouts Rígidos por Requisição (Timeout Budgets):**
   * *Timeout Explicito:* Toda chamada HTTP ou RPC para o provedor de IA define um timeout estrito (ex: 5 a 10 segundos), prevenindo o consumo indefinido de threads e workers da aplicação?

---

## 3. Emissão de Parecer na PR

A skill gera a saída formal padronizada para inclusão na tabela de especialistas da Pull Request:

### Caso Aprovado:
```markdown
| **16** | **Especialista em Arquitetura de IA** | `[APROVADO]` | Resiliência de IA auditada com sucesso. Circuit breakers ativos, rotas de fallback e degradação graciosa implementadas, retentativas com exponential backoff e jitter, e timeouts rígidos isolando o core da aplicação. |
```

### Caso Reprovado / Bloqueante:
```markdown
| **16** | **Especialista em Arquitetura de IA** | `[BLOQUEANTE]` | Falha de resiliência de IA identificada: [descrever se houve chamada à API de IA sem timeout, ausência de circuit breaker para mitigar erros 503 ou travamento do app caso a IA falhe]. Correção obrigatória antes do merge. |
```
