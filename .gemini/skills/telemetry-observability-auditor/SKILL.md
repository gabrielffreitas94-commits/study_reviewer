---
name: telemetry-observability-auditor
description: Audits pull request diff against staging for structured JSON logging, correlation IDs, log level discipline, audit trail integrity, and sensitive data scrubbing.
---

# Telemetry & Observability Auditor (Skill do Especialista de Telemetria)

Esta skill é utilizada pelo **Especialista de Telemetria** durante a auditoria final da Sprint, imediatamente antes da abertura ou aprovação da Pull Request.

Seu objetivo é auditar o código para garantir que o sistema possua **observabilidade de alta fidelidade**, com logs estruturados em JSON, rastreabilidade ponta a ponta com identificadores de correlação (*Correlation IDs*), severidade semântica disciplinada, higienização rigorosa contra dados sensíveis (PII) e integridade absoluta das trilhas de auditoria de negócio.

---

## 1. Entrada e Gatilho
* **Arquivos e Artefatos Base:**
  * Git diff da branch da sprint contra a branch `staging` (`git diff staging...HEAD`).
  * Módulos e serviços em `src/`, configurações de logging e middlewares.
  * Modelos e repositórios de auditoria e persistência de eventos.
* **Gatilho de Execução:** Auditoria final de PR, em conjunto com os demais especialistas.

---

## 2. Checklist Exaustivo de Observabilidade e Telemetria

O Especialista de Telemetria inspeciona o código respondendo a sete dimensões essenciais:

1. **Proibição Estrita de `print()` em Código de Produção:**
   * O diff contra `staging` não contém nenhuma ocorrência de `print()` em `src/`.
   * Toda e qualquer emissão operacional é realizada através da biblioteca padrão `logging` ou do módulo de logging estruturado oficial do projeto.

2. **Padronização Estruturada em JSON (Structured Logging):**
   * Os logs são emitidos com campos estruturados em chave-valor, contendo minimamente:
     * `timestamp`: Data/hora em UTC no formato ISO 8601 (`YYYY-MM-DDTHH:MM:SS.sssZ`).
     * `level`: Severidade padronizada (`DEBUG`, `INFO`, `WARNING`, `ERROR`, `CRITICAL`).
     * `event` / `message`: Mensagem concisa do evento operacional ou de negócio.
     * `logger`: Nome do módulo/camada de origem.
     * `extra`: Dicionário com metadados contextuais (ex: `entity_id`, `action`, `user_id`).

3. **Correlação e Rastreabilidade (Correlation ID / Request ID):**
   * As requisições HTTP e operações em segundo plano possuem ou recebem um identificador único de rastreamento (`correlation_id` / `request_id`).
   * Esse identificador é propagado para o contexto de log, permitindo correlacionar todos os eventos e erros de uma mesma transação de ponta a ponta.

4. **Disciplina Semântica de Níveis de Log (Log Level Discipline):**
   * **INFO:** Reservado exclusivamente para marcos de negócio relevantes (ex: "flashcard_created", "review_cycle_completed", "audit_log_persisted") e ciclo de vida da aplicação (inicialização/finalização de serviços).
   * **DEBUG:** Utilizado para detalhes granulares de diagnóstico interno (ex: contagem de loops, dump de payloads intermediários em desenvolvimento).
   * **WARNING:** Utilizado para situações anômalas, mas toleráveis ou auto-recuperáveis (ex: retry de conexão, degradação controlada de cache).
   * **ERROR:** Utilizado para exceções tratadas de negócio ou falhas operacionais que impactaram a ação do usuário, acompanhado obrigatoriamente de `exc_info=True` ou `logger.exception`.
   * **CRITICAL:** Falhas graves que causam indisponibilidade de serviços centrais.

5. **Higienização de Dados e Proteção de Privacidade (Data & PII Scrubbing):**
   * O código garante que nenhuma informação confidencial seja registrada nos logs:
     * Proibição total de logar senhas, tokens Bearer, chaves privadas, segredos de API ou dados de autenticação em texto claro.
     * Mascaramento ou omissão de dados pessoais identificáveis (PII) sensíveis.

6. **Integridade de Trilhas de Auditoria Histórica (Audit Trail Integrity):**
   * Quando a sprint envolver tabelas ou eventos de auditoria de domínio:
     * Os registros de auditoria são imutáveis e operam estritamente como *append-only* (sem operações de `UPDATE` ou `DELETE`).
     * Snapshots históricos (ex: nomes de matérias/temas congelados no momento de uma ação) são persistidos desnormalizados conforme especificado no domínio, sem sofrer mutação por alterações futuras nas entidades originais.
     * Todo log de auditoria possui datação calendária ou timestamp preciso da ocorrência.

7. **Monitoramento Operacional de Desempenho e Erros:**
   * Rotinas de processamento volumoso ou operações críticas registram o tempo de execução (`duration_ms`) e status final para fins de monitoramento e análise de gargalos.

---

## 3. Emissão de Parecer na PR

A skill gera a saída formal padronizada para inclusão na tabela de especialistas da Pull Request:

### Caso Aprovado:
```markdown
| **5** | **Especialista de Telemetria** | `[APROVADO]` | Observabilidade auditada com sucesso. Zero ocorrências de print(), logs estruturados em JSON com metadados semânticos e correlation_id, severidade de eventos disciplinada e trilha de auditoria íntegra sem vazamento de segredos ou PII. |
```

### Caso Reprovado / Bloqueante:
```markdown
| **5** | **Especialista de Telemetria** | `[BLOQUEANTE]` | Falha de observabilidade identificada: [descrever se há uso de print(), falta de estruturação JSON, ausência de correlation_id, vazamento de PII/segredos em logs ou violação na imutabilidade da trilha de auditoria]. Ajuste necessário antes do merge. |
```
