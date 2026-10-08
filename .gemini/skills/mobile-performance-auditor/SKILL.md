---
name: mobile-performance-auditor
description: Audits mobile application platform performance, cold/warm start latency, battery and radio consumption, lifecycle management, and network caching.
---

# Mobile Performance Auditor (Skill do Especialista Mobile)

Esta skill é operada pelo **Especialista Mobile** durante a fase de auditoria final da Sprint, imediatamente antes da abertura ou aprovação da Pull Request para a branch `staging`.

Seu objetivo é auditar exaustivamente a **performance do aplicativo móvel no nível de plataforma e sistema operacional: tempos de inicialização a frio e a quente, racionalização de consumo de bateria e rádio móvel, descarte de recursos no ciclo de vida e eficiência de rede**.

---

## 1. Entrada e Gatilho
* **Arquivos e Artefatos Base:**
  * Camada de rede, clientes HTTP e lifecycle: `mobile/lib/core/network/`, `mobile/lib/app.dart`.
  * Configurações de inicialização do app móvel.
  * Git diff da branch da sprint contra a branch `staging` (`git diff staging...HEAD`).
* **Gatilho de Execução:** Auditoria de PR para alterações que afetem inicialização do app, sincronização de background, requisições de rede ou consumo de recursos no dispositivo móvel.

---

## 2. Checklist Exaustivo de Auditoria de Performance de Plataforma Mobile

O Especialista Mobile avalia o código sob os seguintes critérios de performance:

1. **Tempos de Inicialização (App Startup Latency):**
   * *Cold Start:* O tempo de inicialização a frio do aplicativo (desde o clique no ícone até o primeiro frame interativo) não ultrapassa o limite de $1.5\text{s}$?
   * *Warm Start:* A retomada do app suspenso ocorre em $\le 500\text{ms}$?
   * *Inicialização Lazy:* Serviços e dependências secundárias (analítica, crash reporting, sincronizadores pesados) são inicializados de forma assíncrona ou tardia (*lazy*), sem bloquear o thread principal na inicialização?

2. **Consumo Racional de Bateria e Rádio Móvel:**
   * *Zero Polling Agressivo:* O app evita disparar requisições periódicas curtas em loop para o servidor? O uso de polling em background é estritamente proibido em prol de conexões pontuais ou push notifications?
   * *Batching de Requisições:* Mutações de progresso de estudo (respostas de cards) são agrupadas em lote (*batching*) para minimizar a quantidade de ativações do modem de rádio móvel?

3. **Gerenciamento do Ciclo de Vida do Sistema Operacional (`AppLifecycleState`):**
   * *Liberação em Background:* Quando o app entra no estado `paused` ou `detached`, todos os timers, animações, streams contínuos e sensores são imediatamente suspensos para economizar CPU e bateria?
   * *Restauração Limpa:* Ao retornar para `resumed`, o estado visual e os dados são restaurados sem travamentos ou recarregamentos integrais desnecessários?

4. **Cache de Rede e Otimização de Payloads:**
   * *Cache Local com TTL:* Respostas de API (ex: matérias, tópicos, flashcards) são armazenadas em cache local com tempo de expiração explícito, evitando downloads redundantes de rede?
   * *Compressão de Transferência:* As requisições HTTP solicitam e aceitam compressão gzip/brotli (`Accept-Encoding`)?

---

## 3. Emissão de Parecer na PR

A skill gera a saída formal padronizada para inclusão na tabela de especialistas da Pull Request:

### Caso Aprovado:
```markdown
| **14** | **Especialista Mobile** | `[APROVADO]` | Performance mobile de plataforma auditada com sucesso. Cold start otimizado (<= 1.5s), ciclo de vida respeitado com suspensão de timers em background, batching de requisições sem polling agressivo e cache local com TTL. |
```

### Caso Reprovado / Bloqueante:
```markdown
| **14** | **Especialista Mobile** | `[BLOQUEANTE]` | Ineficiência de plataforma mobile identificada: [descrever se houve polling contínuo em background, inicialização pesada síncrona bloqueando o cold start ou vazamento de timers com app pausado]. Correção obrigatória antes do merge. |
```
