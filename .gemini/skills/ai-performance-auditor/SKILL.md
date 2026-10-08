---
name: ai-performance-auditor
description: Audits AI inference latency, Time-to-First-Token (TTFT), asynchronous token streaming, context caching, and token budgeting/metering.
---

# AI Performance Auditor (Skill do Especialista em Arquitetura de IA)

Esta skill é operada pelo **Especialista em Arquitetura de IA** durante a fase de auditoria final da Sprint, imediatamente antes da abertura ou aprovação da Pull Request para a branch `staging`.

Seu objetivo é auditar exaustivamente a **performance e eficiência computacional dos modelos generativos e LLMs: latência de inferência (TTFT), streaming assíncrono de tokens, uso de context caching para bases de conhecimento RAG e medição estrita de consumo de tokens (token budgeting e metering)**.

---

## 1. Entrada e Gatilho
* **Arquivos e Artefatos Base:**
  * Adaptadores de IA e Gemini: `src/adapters/ai/`, `src/adapters/gemini/`.
  * Controladores de avaliação e streaming: `src/adapters/api/evaluation_controllers.py`.
  * Schemas DTO e entidades de token: `src/application/dto/evaluation_dto.py`, `src/domain/entities.py`.
  * Git diff da branch da sprint contra a branch `staging` (`git diff staging...HEAD`).
* **Gatilho de Execução:** Auditoria de PR para alterações que envolvam chamadas a LLMs, prompts de avaliação, geração de embeddings, streaming ou contabilização de tokens de IA.

---

## 2. Checklist Exaustivo de Auditoria de Performance de IA

O Especialista em Arquitetura de IA avalia a solução sob os seguintes critérios de performance:

1. **Latência de Inferência e Streaming de Tokens (TTFT):**
   * *Time-to-First-Token $\le 800\text{ms}$:* O fluxo interativo com o estudante (ex: feedback de resposta aberta) utiliza streaming de tokens (Server-Sent Events) para entregar as primeiras palavras em menos de $800\text{ms}$?
   * *Ausência de Bloqueio:* O backend processa o streaming de forma assíncrona (`async for chunk in response`), sem acumular todo o payload do modelo em memória antes de iniciar a resposta ao cliente?

2. **Context Caching e Compactação de Prompt:**
   * *Aproveitamento de Context Caching:* Para bases de conhecimento RAG extensas e estáticas (manuais, apostilas de estudo), o sistema utiliza a API de Context Caching (ex: Gemini CachedContent) para reduzir latência e custos de inferência?
   * *Compressão de Contexto:* O prompt seleciona apenas os trechos (*chunks*) estritamente relevantes via busca semântica, sem enviar volumes massivos de texto irrelevante para a janela de contexto?

3. **Medição, Limites e Budgeting de Tokens:**
   * *Token Metering:* Cada chamada ao modelo contabiliza explicitamente os tokens de entrada (*prompt tokens*) e de saída (*completion tokens*) retornados pelos metadados de uso (`usage_metadata`)?
   * *Limites Rígidos por Requisição:* Há parâmetros explícitos de `max_output_tokens` configurados para evitar que gerações descontroladas estourem orçamentos ou causem latências excessivas?

4. **Vetorização e Embeddings Eficientes:**
   * *Geração em Lote:* Vetorização de múltiplos documentos ou perguntas utiliza endpoints em batch (`embed_content` com lista), evitando uma requisição HTTP individual por parágrafo?
   * *Cache de Embeddings:* Vetores de perguntas e conteúdos já processados são armazenados em cache (Redis/banco de dados) para evitar re-computações idênticas?

---

## 3. Emissão de Parecer na PR

A skill gera a saída formal padronizada para inclusão na tabela de especialistas da Pull Request:

### Caso Aprovado:
```markdown
| **16** | **Especialista em Arquitetura de IA** | `[APROVADO]` | Performance de IA auditada com sucesso. Streaming assíncrono com TTFT <= 800ms, context caching aproveitado para bases estáticas, medição de tokens (metering/budgeting) e limites rígidos de max_output_tokens implementados. |
```

### Caso Reprovado / Bloqueante:
```markdown
| **16** | **Especialista em Arquitetura de IA** | `[BLOQUEANTE]` | Ineficiência de IA identificada: [descrever se houve geração síncrona bloqueante sem streaming em fluxo interativo, ausência de max_output_tokens ou re-vetorização redundante sem cache]. Correção obrigatória antes do merge. |
```
