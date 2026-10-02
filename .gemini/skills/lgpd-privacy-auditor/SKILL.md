---
name: lgpd-privacy-auditor
description: Audits pull request diff against staging for LGPD / GDPR data privacy compliance, data minimization, user rights, retention policies, and PII protection.
---

# LGPD & Data Privacy Auditor (Skill do Especialista em LGPD)

Esta skill é utilizada pelo **Especialista em LGPD** durante a auditoria final da Sprint, imediatamente antes da abertura ou aprovação da Pull Request.

Seu objetivo é auditar os modelos de dados, rotas de API, fluxos de persistência e registros no diff contra a branch `staging`, assegurando **conformidade estrita com a Lei Geral de Proteção de Dados (LGPD - Lei nº 13.709/2018)**, os princípios de *Privacy by Design*, a minimização rigorosa de dados e a garantia integral dos direitos dos titulares.

---

## 1. Entrada e Gatilho
* **Arquivos e Artefatos Base:**
  * Git diff da branch da sprint contra a branch `staging` (`git diff staging...HEAD`).
  * Modelos de banco de dados (SQLAlchemy / ORM), migrações de schema e schemas de API (Pydantic / DTOs).
  * Linhas de emissão de logs e configurações de persistência em `src/`.
* **Gatilho de Execução:** Auditoria final de PR para qualquer alteração que introduza ou modifique dados de usuários, persistência, rotas ou rastreamentos.

---

## 2. Checklist Exaustivo de Privacidade e Proteção de Dados (LGPD)

O Especialista em LGPD inspeciona o código respondendo a sete dimensões regulatórias essenciais:

1. **Minimização de Dados e Princípio da Necessidade (Art. 6º, III):**
   * *O sistema coleta e processa apenas os dados estritamente necessários para cumprir a finalidade do serviço?*
   * Proibição de solicitar ou armazenar dados pessoais excessivos ou secundários que não sejam indispensáveis para o funcionamento da funcionalidade de estudo e revisão.
   * Proibição estrita de coleta de dados sensíveis (origem racial, convicção religiosa, saúde, vida sexual, biometria ou dados genéticos) sem justificativa e base legal inequívoca.

2. **Finalidade Específica e Bases Legais (Art. 6º, I e Art. 7º):**
   * Todo dado coletado possui uma finalidade legítima, específica, informada e transparente ao titular (ex: execução de contrato para viabilizar as rotinas de estudo, legítimo interesse balanceado ou cumprimento de dever legal).
   * O sistema não reutiliza dados pessoais para finalidades secundárias ou incompatíveis sem transparência ou novo consentimento.

3. **Garantia dos Direitos dos Titulares de Dados (Art. 18):**
   * O código e a modelagem asseguram suporte efetivo aos direitos fundamentais do titular:
     * **Acesso e Confirmação:** O usuário tem meios programáticos de consultar seus dados armazenados.
     * **Correção:** Possibilidade de retificar dados cadastrais incompletos, inexatos ou desatualizados.
     * **Eliminação e Esquecimento:** O titular pode solicitar a exclusão de sua conta e dos seus dados pessoais associados.
     * **Portabilidade:** Capacidade de exportar seus dados de estudo em formato interoperável.

4. **Ciclo de Vida, Retenção e Descarte Seguro:**
   * Rotinas de exclusão de dados removem efetivamente os dados pessoais do banco de dados ou realizam a anonimização irreversível dos identificadores.
   * Proibição de implementar exclusões puramente cosméticas (*soft-delete*) que mantenham dados pessoais confidenciais legíveis e vulneráveis indefinidamente sem justificativa de retenção legal.

5. **Pseudonimização e Ausência de PII em Logs e URLs:**
   * Logs operacionais e mensagens de erro nunca registram nomes completos, e-mails, senhas, CPFs, números de telefone ou IPs não anonimizados.
   * Parâmetros de consulta em URLs (`query strings`) não transportam dados pessoais que possam ser armazenados em caches de navegador, proxies ou logs de servidores web.

6. **Segurança no Armazenamento e Acesso (Privacy by Design - Art. 46):**
   * Dados pessoais são armazenados de forma segura e acessíveis exclusivamente pelo titular autenticado ou por serviços autorizados sob o princípio do privilégio mínimo.
   * Proibição de rotas públicas sem autenticação que exponham listagens ou dados de usuários.

7. **Transparência e Consentimento Revogável:**
   * Caso alguma funcionalidade dependa de consentimento opcional (ex: envio de lembretes opcionais, compartilhamento de estatísticas com terceiros), o consentimento deve ser granular, destacado e com revogação simples a qualquer momento pelo usuário.

---

## 3. Emissão de Parecer na PR

A skill gera a saída formal padronizada para inclusão na tabela de especialistas da Pull Request:

### Caso Aprovado:
```markdown
| **10** | **Especialista em LGPD** | `[APROVADO]` | Conformidade com a LGPD e Privacy by Design auditada com sucesso. Coleta estritamente minimizada, bases legais e finalidades específicas respeitadas, garantia de direitos dos titulares (acesso/eliminação) preservada e zero PII exposta em logs ou URLs no diff contra staging. |
```

### Caso Reprovado / Bloqueante:
```markdown
| **10** | **Especialista em LGPD** | `[BLOQUEANTE]` | Violação de privacidade / LGPD identificada: [descrever se há coleta excessiva de dados sem finalidade, exposição de PII em logs/URLs, ausência de suporte à eliminação ou tratamento indevido de dados pessoais]. Ajuste obrigatório antes do merge. |
```

### Caso N/A Justificado (Sem tratamento de dados pessoais):
```markdown
| **10** | **Especialista em LGPD** | `[N/A JUSTIFICADO]` | Esta PR trata de escopo puramente de infraestrutura/algoritmos internos sem persistência, manipulação ou exposição de dados pessoais ou identificadores de usuários. |
```
