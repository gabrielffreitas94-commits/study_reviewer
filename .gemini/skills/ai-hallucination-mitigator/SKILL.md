---
name: ai-hallucination-mitigator
description: Audits AI hallucination mitigation, factual grounding in RAG knowledge bases, strict Structured Outputs (Pydantic/JSON Schema), temperature calibration, and faithfulness evaluation.
---

# AI Hallucination Mitigator (Skill do Especialista em Arquitetura de IA)

Esta skill é operada pelo **Especialista em Arquitetura de IA** durante a fase de auditoria final da Sprint, imediatamente antes da abertura ou aprovação da Pull Request para a branch `staging`.

Seu objetivo é conduzir uma auditoria científica na **mitigação de alucinações e garantia de precisão factual das respostas do modelo: ancoragem estrita (*grounding*) em bases de conhecimento RAG, uso compulsório de Saídas Estruturadas (*Structured Outputs*), calibração determinística de hiperparâmetros de amostragem e validação de fidelidade semântica**.

---

## 1. Entrada e Gatilho
* **Arquivos e Artefatos Base:**
  * Schemas de saída e validação: `src/domain/entities/`, Pydantic models de resposta.
  * Configuração de geração do modelo: `temperature`, `top_p`, `response_schema`.
  * Casos de uso de avaliação e geração de feedback: `src/application/use_cases/evaluation_use_cases.py`.
  * Git diff da branch da sprint contra a branch `staging` (`git diff staging...HEAD`).
* **Gatilho de Execução:** Auditoria de PR para alterações que implementem respostas automáticas de IA, avaliações semânticas de respostas de estudantes ou geração de flashcards a partir de documentos.

---

## 2. Checklist Exaustivo de Mitigação de Alucinação

O Especialista em Arquitetura de IA avalia a solução sob os seguintes critérios de fidelidade:

1. **Ancoragem Factual Estrita em Contexto (RAG Grounding):**
   * *Grounding Compulsório:* As instruções do sistema exigem que as respostas e avaliações se baseiem estritamente no material fornecido no contexto de estudo?
   * *Diretiva de Abstenção Explícita:* O prompt contém instrução clara de abstenção quando a resposta não constar no material (ex: *"Se o contexto fornecido não contiver elementos suficientes para responder ou validar a afirmação, responda estritamente que não há dados suficientes para a avaliação"*), impedindo que o modelo invente fatos plausíveis?

2. **Saídas Estruturadas (Structured Outputs via JSON Schema / Pydantic):**
   * *Zero Parsing Frágil com Regex:* Respostas avaliativas que geram métricas, notas, classificações ou listas de pontos fracos utilizam `response_schema` com classes Pydantic estritas e tipadas, proibindo texto livre em markdown para posterior extração com expressões regulares?
   * *Validação Prévia ao Domínio:* O objeto retornado é validado contra o modelo de domínio antes de qualquer efeito colateral no banco de dados?

3. **Calibração Determinística de Hiperparâmetros de Amostragem:**
   * *Temperatura Baixa para Avaliações:* Tarefas de correção de respostas, validação factual ou notas de estudo utilizam temperatura determinística calibrada ($\text{temperature} \le 0.2$), garantindo reproducibilidade e consistência lógica entre execuções repetidas?
   * *Top-p e Top-k Restritos:* Parâmetros de diversidade léxica são mantidos em valores conservadores para evitar deriva alucinatória?

4. **Framework de Avaliação e Testes de Fidelidade Semântica:**
   * *Métricas de Qualidade Semântica:* Existem testes automatizados ou rotinas que verifiquem métricas de fidelidade (*Faithfulness* e *Answer Relevance*) contra respostas padrão conhecidas (*ground truth*)?

---

## 3. Emissão de Parecer na PR

A skill gera a saída formal padronizada para inclusão na tabela de especialistas da Pull Request:

### Caso Aprovado:
```markdown
| **16** | **Especialista em Arquitetura de IA** | `[APROVADO]` | Mitigação de alucinações auditada com sucesso. Ancoragem estrita (grounding) via RAG com regras de abstenção, saídas estruturadas obrigatórias validadas via Pydantic/JSON Schema e temperatura calibrada (<= 0.2). |
```

### Caso Reprovado / Bloqueante:
```markdown
| **16** | **Especialista em Arquitetura de IA** | `[BLOQUEANTE]` | Risco de alucinação de IA identificado: [descrever se houve geração de resposta avaliativa sem grounding, temperatura excessiva > 0.2 ou parsing frágil de texto livre sem Structured Outputs]. Correção obrigatória antes do merge. |
```
