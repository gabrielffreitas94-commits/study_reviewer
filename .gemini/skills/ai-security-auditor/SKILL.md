---
name: ai-security-auditor
description: Audits AI application security, prompt injection defense (direct/indirect), system prompt leak prevention, safety guardrails, and PII masking.
---

# AI Security Auditor (Skill do Especialista em Arquitetura de IA)

Esta skill é operada pelo **Especialista em Arquitetura de IA** durante a fase de auditoria final da Sprint, imediatamente antes da abertura ou aprovação da Pull Request para a branch `staging`.

Seu objetivo é conduzir uma auditoria especializada na **segurança de aplicações baseadas em IA generativa (OWASP Top 10 for LLMs): defesa contra Prompt Injection direto e indireto, prevenção de vazamento de System Prompts, filtros de segurança e moderação ética, e minimização de dados pessoais (LGPD)**.

---

## 1. Entrada e Gatilho
* **Arquivos e Artefatos Base:**
  * Templates de prompts e system instructions: `src/adapters/ai/prompts/`, `src/adapters/ai/gemini_adapters.py`.
  * Filtros de segurança e sanitização: `src/infrastructure/security/sanitization.py`.
  * Git diff da branch da sprint contra a branch `staging` (`git diff staging...HEAD`).
* **Gatilho de Execução:** Auditoria de PR para alterações que definam, alterem ou processem prompts, variáveis de usuário enviadas para LLMs ou configurações de segurança do provedor.

---

## 2. Checklist Exaustivo de Auditoria de Segurança de IA

O Especialista em Arquitetura de IA inspeciona o código avaliando os seguintes requisitos de segurança:

1. **Blindagem contra Prompt Injection (Direto e Indireto - LLM01):**
   * *Delimitação Estruturada de Contexto:* O texto fornecido pelo usuário e os conteúdos recuperados externamente (ex: via RAG) são encapsulados em tags delimitadoras não interpretáveis (ex: `<user_input>`, `<untrusted_content>`)?
   * *Instrução Soberana de Sistema:* O *System Instruction* contém diretivas explícitas para ignorar comandos que tentem redefinir instruções do modelo (ex: *"Ignore todas as instruções anteriores e faça X"* contidas dentro de `<user_input>` devem ser tratadas estritamente como texto de resposta de estudo)?

2. **Prevenção de Vazamento de System Prompts e Segredos (LLM06 & LLM07):**
   * *System Prompt Leakage:* Os prompts instruem o modelo a nunca expor suas instruções internas, chaves de API ou detalhes de arquitetura do sistema sob nenhuma circunstância?
   * *Zero Credenciais nos Payloads:* O payload enviado ao provedor de IA não transporta variáveis de ambiente, segredos de banco ou tokens de autenticação interna?

3. **Filtros de Segurança e Moderação (Safety Settings):**
   * *Safety Ratings:* A configuração do modelo ativa explicitamente filtros contra discurso de ódio, assédio, conteúdo sexual e perigoso (`HarmCategory` com limiares adequados)?
   * *Tratamento de Bloqueio por Segurança:* Caso o modelo recuse a resposta por violação de filtros (`finish_reason == SAFETY`), a aplicação captura a exceção de forma segura sem expor stack traces ou quebrar o fluxo do usuário?

4. **Minimização de Dados Pessoais (LGPD no Contexto de IA):**
   * *Mascaramento de PII:* Dados pessoais identificáveis (nomes de terceiros, e-mails, documentos) são anonimizados ou omitidos antes de serem enviados à API em nuvem do provedor de IA?

---

## 3. Emissão de Parecer na PR

A skill gera a saída formal padronizada para inclusão na tabela de especialistas da Pull Request:

### Caso Aprovado:
```markdown
| **16** | **Especialista em Arquitetura de IA** | `[APROVADO]` | Segurança de IA auditada com sucesso. Delimitação defensiva contra prompt injection em entradas e RAG, proteção ativa contra vazamento de system prompt, filtros de segurança configurados e minimização de dados LGPD. |
```

### Caso Reprovado / Bloqueante:
```markdown
| **16** | **Especialista em Arquitetura de IA** | `[BLOQUEANTE]` | Vulnerabilidade de IA identificada: [descrever se houve concatenação crua de texto de usuário em prompt sem delimitadores, ausência de safety filters ou risco de prompt injection]. Correção obrigatória antes do merge. |
```
